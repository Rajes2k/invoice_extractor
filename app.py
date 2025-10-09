# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os, json, re, requests, traceback
import pdfplumber

# ---------- CONFIG ----------
app = Flask(__name__)
CORS(app)  # allow all origins (simple dev config)

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# LLM provider config (choose one or leave PROVIDER=none)
PROVIDER = os.getenv("LLM_PROVIDER", "none").lower()  # "none", "openai", "groq", "hf"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")  # change to available model in your Groq account
HF_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "")

# timeouts
REQUEST_TIMEOUT = 120

# ---------- HELPERS ----------
def extract_text_from_pdf(path):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        raise
    return text

def basic_regex_parse(text):
    def find(rex):
        m = re.search(rex, text, re.I)
        return m.group(1).strip() if m else None

    inv_no = find(r"(?:Invoice\s*(?:Number|No\.?)|Inv[#:\-]?)\s*[:#\-]?\s*([A-Z0-9\-\/]+)")
    date = find(r"(?:Invoice\s*Date|Date|Order\s*Date)[:\s\-]*([0-9]{1,2}[-\/][0-9]{1,2}[-\/][0-9]{2,4})")
    total = find(r"(?:Grand\s*Total|Total\s*Due|Total)\s*[:\s]*([₹$£€]?\s*[0-9,]+(?:\.[0-9]{2})?)")
    if not total:
        # fallback find currency amounts
        m = re.search(r"([₹$£€]\s*[0-9,]+(?:\.[0-9]{2})?)", text)
        total = m.group(1) if m else None

    return {"invoice_number": inv_no or None, "invoice_date": date or None, "total_amount": total or None}

def extract_json_from_text(text):
    # try direct json parse or substring
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        i = text.find("{")
        j = text.rfind("}")
        if i != -1 and j != -1 and j > i:
            sub = text[i:j+1]
            try:
                return json.loads(sub)
            except Exception:
                return None
    return None

# ---------- LLM CALLS (simple, wrapped with errors) ----------
def call_openai_chat(prompt, model="gpt-3.5-turbo", max_tokens=512):
    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY not set"}
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        j = r.json()
        # Chat responses: pick first choice
        txt = j.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"text": txt, "raw": j}
    except Exception as e:
        return {"error": f"OPENAI API HTTP error: {str(e)}", "status_code": getattr(e, "response", None) and getattr(e.response, "status_code", None)}

def call_groq_chat(prompt, model=GROQ_MODEL, max_tokens=512):
    if not GROQ_API_KEY:
        return {"error": "GROQ_API_KEY not set"}
    # Groq provides an OpenAI-compatible proxy endpoint in many integrations:
    url = f"https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        j = r.json()
        txt = j.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"text": txt, "raw": j}
    except Exception as e:
        return {"error": f"GROQ API HTTP error: {str(e)}"}

def call_huggingface_textgen(prompt, model=HF_MODEL, max_tokens=512):
    if not HF_API_TOKEN or not model:
        return {"error": "HUGGINGFACE_API_TOKEN or HF_MODEL not set"}
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": max_tokens}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        # HF returns list/dict; try to extract text
        try:
            data = r.json()
            if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
                return {"text": data[0]["generated_text"], "raw": data}
            if isinstance(data, dict) and "generated_text" in data:
                return {"text": data["generated_text"], "raw": data}
            return {"text": json.dumps(data), "raw": data}
        except Exception:
            return {"text": r.text}
    except Exception as e:
        return {"error": f"HF API HTTP error: {str(e)}"}

# ---------- ROUTES ----------
@app.route("/")
def home():
    return jsonify({"message": "Invoice Extractor is live", "llm_provider": PROVIDER})

@app.route("/extract", methods=["POST"])
def extract_invoice():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file part in request"}), 400
        f = request.files["file"]
        if f.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        fname = secure_filename(f.filename)
        saved_path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
        f.save(saved_path)

        # Extract text from PDF
        try:
            text = extract_text_from_pdf(saved_path)
        except Exception as e:
            # cleanup and return helpful error
            try:
                os.remove(saved_path)
            except Exception:
                pass
            return jsonify({"error": "Failed to read PDF", "detail": str(e)}), 500

        # Basic parsed fields (guaranteed)
        basic = basic_regex_parse(text)

        # If no provider configured, return extracted text + basic parse
        if PROVIDER == "none":
            try:
                os.remove(saved_path)
            except Exception:
                pass
            return jsonify({"message": f"Extracted (no-LLM)", "content": text, "parsed_basic": basic}), 200

        # Prepare LLM prompt asking for strict JSON
        prompt = f"""You are an invoice extraction assistant. Return ONLY a valid JSON object (no markdown).
Fields: invoice_number, invoice_date, total_amount, currency, vendor, customer, tax_amount, line_items (array of objects with description, qty, unit_price, total) or null if not present.
Invoice text:
\"\"\"{text[:40000]}\"\"\""""

        # Call the selected provider
        if PROVIDER == "openai":
            llm_resp = call_openai_chat(prompt)
        elif PROVIDER == "groq":
            llm_resp = call_groq_chat(prompt)
        elif PROVIDER == "hf":
            llm_resp = call_huggingface_textgen(prompt)
        else:
            llm_resp = {"error": f"Unknown PROVIDER '{PROVIDER}'"}

        # If LLM call resulted in error, fallback to basic parse and include the error
        if "error" in llm_resp:
            try:
                os.remove(saved_path)
            except Exception:
                pass
            return jsonify({
                "message": "LLM call failed, returned basic extraction",
                "llm_error": llm_resp.get("error"),
                "content": text,
                "parsed_basic": basic
            }), 200

        llm_text = llm_resp.get("text", "")
        parsed = extract_json_from_text(llm_text)
        # final response: prefer parsed LLM JSON, otherwise basic parse
        out = {
            "message": f"Invoice extracted using {PROVIDER}",
            "content": text,
            "llm_raw_text": llm_text,
            "llm_parsed": parsed,
            "parsed_basic": basic
        }
        try:
            os.remove(saved_path)
        except Exception:
            pass
        return jsonify(out), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Server error", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
