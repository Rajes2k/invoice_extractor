from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from PyPDF2 import PdfReader
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")

@app.route('/')
def home():
    return jsonify({"message": "Invoice Extractor is live"})

@app.route('/extract', methods=['POST'])
def extract():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    # Send text to Groq LLM
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are an AI that extracts key invoice fields."},
            {"role": "user", "content": f"Extract structured data (invoice number, date, total, etc.) from this text:\n{text}"}
        ]
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=data
    )

    if response.status_code != 200:
        return jsonify({"error": f"GROQ API error: {response.text}"}), response.status_code

    result = response.json()
    extracted_data = result["choices"][0]["message"]["content"]

    return jsonify({"extracted_data": extracted_data})

if __name__ == '__main__':
    app.run(debug=True)
