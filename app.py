from flask import Flask, request, jsonify
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import pandas as pd

app = Flask(__name__)

@app.route('/')
def home():
    return "Invoice Extractor API is live!"

@app.route('/extract', methods=['POST'])
def extract_invoice():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save PDF temporarily
        file_path = f"temp_{file.filename}"
        file.save(file_path)

        # Extract text from PDF
        text = ''
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + '\n'

        # Example: Return extracted text
        return jsonify({'text': text})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
