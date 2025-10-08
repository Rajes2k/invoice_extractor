import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

app = Flask(__name__)
CORS(app)

HF_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "gpt2")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Invoice Extractor API is running!"})

@app.route("/extract", methods=["POST"])
def extract_invoice():
    try:
        if "file" not in request.files:
            app.logger.error("No file uploaded in request.")
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        content = file.read()

        app.logger.info(f"Received file: {file.filename}, size={len(content)} bytes")

        # Prepare Hugging Face request
        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json"
        }

        # Simple test prompt — replace with actual extraction later
        data = {"inputs": "Extract invoice details from this text: sample invoice amount 500 INR"}

        app.logger.info(f"Sending request to Hugging Face model: {HF_MODEL}")
        hf_url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
        response = requests.post(hf_url, headers=headers, json=data)

        app.logger.info(f"HF response: {response.status_code} {response.text[:200]}")

        if response.status_code != 200:
            return jsonify({"error": f"Hugging Face API returned {response.status_code}", "details": response.text}), 500

        return jsonify({"status": "ok", "model_output": response.json()})

    except Exception as e:
        app.logger.error("Exception occurred in /extract")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
