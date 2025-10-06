from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import os

app = Flask(__name__)
CORS(app)  # Allow all origins (for your frontend)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/")
def home():
    return "Invoice Extractor API is running!"

@app.route("/extract", methods=["POST"])
def extract():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    # --- Sample PDF processing (replace with your real extraction) ---
    try:
        with pdfplumber.open(filepath) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        return jsonify({"error": f"Failed to read PDF: {str(e)}"}), 500

    # Return JSON in the format expected by your frontend
    return jsonify({
        "content": text,
        "message": "Invoice extracted"
    })

if __name__ == "__main__":
    app.run(debug=True)
