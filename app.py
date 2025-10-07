# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import pdfplumber
import json
import re

# Optional: load local .env for dev testing (install python-dotenv if you want)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__)
CORS(app)  # allow requests from your frontend

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Hugging Face model to use (change if you prefer another HF model)
HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
HF_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")  # set this in Render env vars
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

if not HF_API_TOKEN:
    print("WARNING: HUGGINGFACE_API_TOKEN not set. Set it in your environment to call HF Inference API.")


def call_hf_inference(prompt, max_tokens=256, temperature=0.0):
    """
    Call Hugging Face inference API (text generation) and return the generated text.
    """
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"} if HF_API_TOKEN else {}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": max_tokens, "temperature": temperature},
        # "options": {"use_cache": False}  # optional
    }

    try:
        resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=120)
    except Exception as e:
        return {"error": f"Request to HF failed: {str(e)}", "status_code": 500}

    if resp.status_code != 200:
        # return HF error message if exists
        try:
            return {"error": resp.json(), "status_code": resp.status_code}
        except Exception:
            return {"error": resp.text, "status_code": resp.status_code}

    # HF may return JSON or text. Handle common shapes.
    try:
        data = resp.json()
    except ValueError:
        text = resp.text
        return {"text": text}

    # common HF response forms:
    # 1) { "generated_text": "..." }
    # 2) [ { "generated_text": "..." } ]
    # 3) plain dict/list with other keys
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "generated_text" in data[0]:
        return {"text": data[0]["generated_text"]}
    if isinstance(data, dict) and "generated_text" in data:
        return {"text": data["generated_text"]}
    # fallback - try to convert the whole json to string
    return {"text": json.dumps(data)}

def extract_json_from_text(text):
    """
    Attempt to extract a JSON object from free text returned by the LLM.
    We try:
      1) direct json.loads(text)
      2) find first '{' and last '}' and parse the substring
      3) return None if parse fails
    """
    if not text:
        return None
    # try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # try to find a JSON substring between first '{' and last '}'
    i = text.find('{')
    j = text.rfind('}')
    if i != -1 and j != -1 and j > i:
        maybe = text[i:j+1]
        try:
            return json.loads(maybe)
        except Exception:
            pass

    # no parseable JSON found
    return None


@app.route("/")
def home():
    return "Invoice Extractor LLM agent (Hugging Face) is running!"


@app.route("/extract", methods=["POST"])
def extract():
    # 1) validate
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # 2) save temporarily
    filename = file.filename
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # 3) extract text from PDF (pdfplumber)
    try:
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        # cleanup
        try:
            os.remove(filepath)
        except Exception:
            pass
        return jsonify({"error": f"Failed to read PDF: {str(e)}"}), 500

    # 4) prepare an instruction prompt for HF model - request strict JSON
    prompt = f"""
You are an invoice extraction assistant. Extract the following fields from the invoice text below and return a VALID JSON object only (no commentary):

- invoice_number (string or null)
- invoice_date (string or null)
- total_amount (number or string, prefer numeric or include currency symbol)
- currency (e.g., INR, USD) or null
- vendor (string or null)
- customer (string or null)
- tax_amount (number or string) or null
- line_items (array of objects with fields: description, qty, unit_price, total) - optional, null if not present

If a value is not present in the text, set it to null. Do not wrap the JSON in markdown code fences. Return only the JSON object.

Invoice text:
\"\"\"{text[:40000]}\"\"\"
"""

    # 5) call HF inference API
    hf_resp = call_hf_inference(prompt, max_tokens=512, temperature=0.0)

    if "error" in hf_resp:
        # cleanup
        try:
            os.remove(filepath)
        except Exception:
            pass
        return jsonify({"error": "HF API error", "detail": hf_resp}), 502

    raw_llm_text = hf_resp.get("text", "")

    # 6) try parse JSON out of the model output
    parsed = extract_json_from_text(raw_llm_text)

    # 7) prepare response
    response_payload = {
        "message": f"Invoice extracted from {filename}",
        "raw_text": text,
        "llm_output_text": raw_llm_text,
        "llm_parsed": parsed
    }

    # cleanup saved file
    try:
        os.remove(filepath)
    except Exception:
        pass

    return jsonify(response_payload), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
