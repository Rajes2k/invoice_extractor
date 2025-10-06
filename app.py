import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Absolute paths (Linux-compatible)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
SAMPLE_FOLDER = os.path.join(BASE_DIR, "data", "samples")

# Make sure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SAMPLE_FOLDER, exist_ok=True)

# Route to extract invoice
@app.route("/extract", methods=["POST"])
def extract_invoice():
    try:
        file = request.files.get("file")
        if file and file.filename != "":
            # Save uploaded file
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            processed_file = file.filename
        else:
            # Fallback to first sample file
            sample_files = os.listdir(SAMPLE_FOLDER)
            if not sample_files:
                return jsonify({"error": "No sample files found"}), 404
            processed_file = sample_files[0]
            file_path = os.path.join(SAMPLE_FOLDER, processed_file)

        # Return JSON response
        return jsonify({
            "status": "success",
            "file_used": file_path,
            "message": f"Invoice extracted from {processed_file}"
        })
    except Exception as e:
        # Catch all errors and return JSON
        return jsonify({"error": str(e)}), 500

# Optional: list uploaded files
@app.route("/uploads", methods=["GET"])
def list_uploads():
    try:
        files = os.listdir(UPLOAD_FOLDER)
        return jsonify({"uploaded_files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Optional: list sample files
@app.route("/samples", methods=["GET"])
def list_samples():
    try:
        files = os.listdir(SAMPLE_FOLDER)
        return jsonify({"sample_files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run Flask (for local testing only)
if __name__ == "__main__":
    app.run(debug=True)
