import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import logging
import sys
from dotenv import load_dotenv
load_dotenv()


# Enable detailed logs for Render
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


app = Flask(__name__)
CORS(app)

HF_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "gpt2")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Invoice Extractor API is running!"})

@app.route("/extract", methods=["POST"])
def extract():
    try:
        file = request.files["file"]
        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        # Save file temporarily
        temp_path = "temp_invoice.pdf"
        file.save(temp_path)

        # Send PDF to Hugging Face Inference API
        headers = {
            "Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_TOKEN')}",
        }

        with open(temp_path, "rb") as f:
            pdf_bytes = f.read()

        response = requests.post(
            f"https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
            headers=headers,
            json={"inputs": "Extract invoice details from this PDF."}
        )

        # Debugging info
        print("HF_TOKEN exists:", bool(os.getenv("HUGGINGFACE_API_TOKEN")))
        print("HF_MODEL:", os.getenv("HF_MODEL"))


        if response.status_code != 200:
            return jsonify({
                "error": f"HF API HTTP {response.status_code}",
                "detail": response.text
            }), 502

        result = response.json()
        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

