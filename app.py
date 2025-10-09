import os
import re
import fitz  # PyMuPDF
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")

@app.route("/")
def home():
    return jsonify({
        "message": "Invoice Extractor is live.",
        "llm_provider": LLM_PROVIDER
    })

@app.route("/extract", methods=["POST"])
def extract_invoice():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    pdf_bytes = file.read()
    
    # --- Step 1: Extract text with PyMuPDF ---
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        for page in pdf:
            text += page.get_text("text")

    # --- Step 2: Simple regex parsing ---
    parsed_basic = {
        "invoice_number": re.search(r"INV[-\s]*\d+", text, re.IGNORECASE),
        "invoice_date": re.search(r"\b\d{1,2}\s*[A-Za-z]{3,}\s*\d{4}\b", text),
        "total_amount": re.search(r"\$\s*\d+[\.,]?\d*", text)
    }
    for key in parsed_basic:
        parsed_basic[key] = parsed_basic[key].group(0) if parsed_basic[key] else None

    llm_output = None
    llm_error = None

    # --- Step 3: LLM (Groq) enhancement ---
    if LLM_PROVIDER == "groq" and GROQ_API_KEY:
        try:
            payload = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an AI assistant that extracts structured invoice data (date, invoice number, amount, company name, etc.)"},
                    {"role": "user", "content": text}
                ]
            }
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                              headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            llm_output = r.json()
        except Exception as e:
            llm_error = str(e)

    return jsonify({
        "message": f"Invoice extracted from {file.filename}",
        "content": text[:3000],  # preview limit
        "parsed_basic": parsed_basic,
        "llm_output": llm_output,
        "llm_error": llm_error
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
