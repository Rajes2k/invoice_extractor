from flask import Flask, request, jsonify
from src.extractor import extract_invoice_dict
import os

app = Flask(__name__)

@app.route("/extract", methods=["POST"])
def extract_invoice():
    pdf_file = request.files.get("pdf")
    if not pdf_file:
        return jsonify({"error": "No PDF uploaded"}), 400

    # Save uploaded PDF temporarily
    temp_pdf_path = os.path.join("data", "samples", pdf_file.filename)
    pdf_file.save(temp_pdf_path)

    result = extract_invoice_dict(temp_pdf_path)
    return jsonify(result)

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    app.run(host="0.0.0.0", port=8080)
