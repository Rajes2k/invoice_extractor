from flask import Flask, request, jsonify
import pdfplumber
import os

# install: pip install flask-cors
from flask_cors import CORS
app = Flask(__name__)
CORS(app)   # allow all origins (ok for testing)

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/")
def home():
    return "Invoice Extractor API is running!"

@app.route("/extract", methods=["POST"])
def extract_invoice():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

    return jsonify({
        "message": f"Invoice extracted from {file.filename}",
        "content": text[:500]   # only first 500 chars
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
