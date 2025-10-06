from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import os

app = Flask(__name__)
CORS(app)  # allow requests from frontend

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

    # save temporarily
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    # extract text using pdfplumber
    try:
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        return jsonify({"error": f"Failed to read PDF: {str(e)}"}), 500
    finally:
        # optional: remove file after processing (comment out if you want to keep)
        try:
            os.remove(filepath)
        except Exception:
            pass

    return jsonify({
        "content": text,
        "message": f"Invoice extracted from {file.filename}"
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
