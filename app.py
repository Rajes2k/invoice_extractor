from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import pdfplumber
import json
import logging

logging.basicConfig(level=logging.INFO)


app = Flask(__name__)
CORS(app)  # Allow frontend to call this API

load_dotenv()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
HF_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

if not HF_API_TOKEN:
    print("WARNING: HUGGINGFACE_API_TOKEN not set. HF inference will fail.")

def call_hf_inference(prompt, max_tokens=512, temperature=0.0):
    """Call Hugging Face Inference API and return generated text."""
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"} if HF_API_TOKEN else {}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": max_tokens, "temperature": temperature},
        "options": {"wait_for_model": True}
    }

    try:
        resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=300)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"HF API request failed: {str(e)}"}

    try:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
            return {"text": data[0]["generated_text"]}
        if isinstance(data, dict) and "generated_text" in data:
            return {"text": data["generated_text"]}
        return {"text": json.dumps(data)}
    except Exception:
        return {"text": resp.text}

def extract_json_from_text(text):
    """Try to extract JSON from LLM text."""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        i = text.find("{")
        j = text.rfind("}")
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(text[i:j+1])
            except Exception:
                return None
    return None

@app.route("/")
def home():
    return "Invoice Extractor LLM agent is running!"

@app.route("/extract", methods=["POST"])
def extract():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        os.remove(filepath)
        return jsonify({"error": f"Failed to read PDF: {str(e)}"}), 500

    prompt = f"""
You are an invoice extraction assistant. Extract these fields from the invoice text and return ONLY a VALID JSON object:

- invoice_number (string or null)
- invoice_date (string or null)
- total_amount (number or string, include currency if possible)
- currency (string or null)
- vendor (string or null)
- customer (string or null)
- tax_amount (number or string) or null
- line_items (array of objects: description, qty, unit_price, total) - null if not available

Invoice text:
\"\"\"{text[:40000]}\"\"\"
"""

    hf_resp = call_hf_inference(prompt)
    if "error" in hf_resp:
        os.remove(filepath)
        return jsonify({"error": "HF API error", "detail": hf_resp}), 502

    raw_llm_text = hf_resp.get("text", "")
    parsed_json = extract_json_from_text(raw_llm_text)

    try:
        os.remove(filepath)
    except Exception:
        pass

    return jsonify({
        "message": f"Invoice extracted from {file.filename}",
        "raw_text": text,
        "llm_output_text": raw_llm_text,
        "llm_parsed": parsed_json
    }), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
