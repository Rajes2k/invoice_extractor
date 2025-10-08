# app.py
from flask import Flask, request, jsonify
import pdfplumber
import os
import requests

app = Flask(__name__)

GROQ_MODEL = os.getenv("GROQ_MODEL")  # e.g., groq/llama3-7b-instruct
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Your GROQ API key

def extract_with_groq(text):
    url = f"https://api.groq.ai/v1/models/{GROQ_MODEL}/infer"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"input": text}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("output", "")
    else:
        return {"error": f"GROQ API error: {response.status_code} - {response.text}"}

@app.route("/extract", methods=["POST"])
def extract_invoice():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        # Extract text from PDF
        with pdfplumber.open(file) as pdf:
            content = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

        if not content.strip():
            return jsonify({"error": "PDF contains no extractable text"}), 400

        # Call GROQ LLM to extract invoice data
        extracted_data = extract_with_groq(content)
        return jsonify({"extracted_data": extracted_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Invoice Extractor is live"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render uses PORT env
    app.run(host="0.0.0.0", port=port)
