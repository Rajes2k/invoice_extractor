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
        # 1) prefer uploaded file via form-data key 'file'
        if 'file' in request.files:
            f = request.files['file']
            if f.filename == '':
                return jsonify({"error": "empty filename"}), 400
            saved_path = os.path.join(UPLOAD_FOLDER, f.filename)
            f.save(saved_path)
            used_path = saved_path
            LOG.info(f"Saved uploaded file to: {saved_path}")

        else:
            # 2) fallback to sample in repo
            sample_name = request.form.get('sample', 'invoice1.pdf')
            used_path = os.path.join(SAMPLE_FOLDER, sample_name)
            if not os.path.exists(used_path):
                LOG.error(f"Sample file not found at: {used_path}")
                return jsonify({
                    "error": "sample file not found",
                    "path_checked": used_path
                }), 404
            LOG.info(f"Using sample file: {used_path}")

        # call the (placeholder) extraction function
        extracted = extract_text_from_pdf(used_path)

        return jsonify({
            "status": "success",
            "file_used": used_path,
            "extracted": extracted
        })

    except Exception as e:
        LOG.exception("Unexpected error in /extract")
        return jsonify({"error": "internal server error", "message": str(e)}), 500


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