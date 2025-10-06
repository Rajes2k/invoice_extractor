# app.py
from flask import Flask, request, jsonify
import os
import logging

app = Flask(__name__)
LOG = logging.getLogger("invoice_extractor")
logging.basicConfig(level=logging.INFO)

# base dir where this file lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# where your sample PDF(s) live in your repo
SAMPLE_FOLDER = os.path.join(BASE_DIR, "data", "samples")
os.makedirs(SAMPLE_FOLDER, exist_ok=True)

# uploads (ephemeral)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def extract_text_from_pdf(path):
    """
    Placeholder for your extraction logic.
    Replace this with your real invoice parsing/extraction code.
    """
    # simple fake extraction to prove flow
    return {
        "filename": os.path.basename(path),
        "pages": 1,
        "text_preview": "(extracted text would appear here)"
    }


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Invoice Extractor running"})


@app.route("/extract", methods=["POST"])
def extract_invoice():
    try:
        file = request.files.get("file")
        if file and file.filename != "":
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            processed_file = file.filename
        else:
            sample_files = os.listdir(SAMPLE_FOLDER)
            if not sample_files:
                return jsonify({"error": "No sample files found"}), 404
            processed_file = sample_files[0]
            file_path = os.path.join(SAMPLE_FOLDER, processed_file)

        return jsonify({
            "status": "success",
            "file_used": file_path,
            "message": f"Invoice extracted from {processed_file}"
        })
    except Exception as e:
        return jsonify({"error": str(e)})


# Temporary debug route to list what sample files are present on the server
@app.route('/debug-sample-files', methods=['GET'])
def debug_files():
    files = []
    for root, dirs, filenames in os.walk(SAMPLE_FOLDER):
        for fn in filenames:
            files.append(os.path.join(root, fn))
    return jsonify({"sample_files": files})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # listen on 0.0.0.0 so Render (or other hosts) can reach it
    app.run(host='0.0.0.0', port=port)