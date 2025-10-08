import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "groq/llama3-7b-instruct")

@app.route("/extract", methods=["POST"])
def extract_invoice():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    content = file.read().decode("utf-8")  # Adjust if PDF → text
    # Call Groq API
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    json_data = {"inputs": content}
    response = requests.post(f"https://api.groq.ai/v1/models/{GROQ_MODEL}/invoke", headers=headers, json=json_data)
    
    if response.status_code != 200:
        return jsonify({"error": f"Groq API error: {response.status_code} - {response.text}"}), 502

    return jsonify({"extracted_data": response.json()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
