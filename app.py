from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Folder to save uploaded files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return "Invoice Extractor API is live! Use /extract to POST a PDF."

@app.route('/extract', methods=['POST'])
def extract_invoice():
    # Check if a file is in the request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Placeholder for invoice extraction logic
    # You can replace this with your actual extraction code
    return jsonify({
        'status': 'success',
        'message': f'Invoice extracted from {filename}'
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
