from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from PyPDF2 import PdfReader
from io import BytesIO

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Invoice Extractor is live"}), 200


@app.route("/extract", methods=["POST"])
def extract_invoice():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        # ✅ Extract text from PDF
        pdf = PdfReader(BytesIO(file.read()))
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""

        if not text.strip():
            return jsonify({"error": "No text found in PDF"}), 400

        # ✅ Send request to GROQ API
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are an invoice data extractor."},
                {"role": "user", "content": f"Extract key invoice details from this text:\n{text}"}
            ]
        }

        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
        result = response.json()

        if response.status_code != 200:
            return jsonify({"error": f"GROQ API error: {result}"}), 500

        extracted_text = result["choices"][0]["message"]["content"]

        return jsonify({"extracted_data": extracted_text}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
