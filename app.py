# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import tempfile
import os
import re
import logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
# Allow frontend to call this API. You can lock origins later if desired.
CORS(app, resources={r"/*": {"origins": "*"}})

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def extract_text_from_pdf(path):
    """Extract text from a PDF using pdfplumber (works for text PDFs)."""
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            ptext = page.extract_text()
            if ptext:
                text += ptext + "\n"
    return text


def find_invoice_fields(text):
    """Simple heuristics to pull invoice_number, date and total."""
    if not text:
        return {"invoice_number": None, "invoice_date": None, "total_amount": None}

    # Normalize a bit
    plain = text

    # Invoice number patterns (try several)
    invoice_number = None
    inv_patterns = [
        r'Invoice\s*(?:Number|No\.?)\s*[:#-]?\s*([A-Z0-9\/\-\_]{3,})',
        r'\bINV[-\s]*([0-9A-Z\-]+)\b',
        r'Invoice\s*#\s*([A-Z0-9\-]+)',
        r'\bInvoice\s*[:\s]*([A-Z0-9\-\/]+)\b'
    ]
    for p in inv_patterns:
        m = re.search(p, plain, re.IGNORECASE)
        if m:
            invoice_number = m.group(1).strip()
            break

    # Date patterns
    invoice_date = None
    date_patterns = [
        r'([0-3]?\d[\/\-\.\s][0-1]?\d[\/\-\.\s](?:\d{2}|\d{4}))',                # 01-02-2025 or 1/2/25
        r'([A-Za-z]{3,9}\s+[0-3]?\d,?\s+\d{4})',                              # January 25, 2016
    ]
    for p in date_patterns:
        m = re.search(p, plain)
        if m:
            invoice_date = m.group(1).strip()
            break

    # Total amount patterns (Grand Total / Total Due / Total)
    total_amount = None
    total_patterns = [
        r'(?:Grand\s*Total|Total\s*Due|Amount\s*Due|Total(?:\s*Amount)?)\s*[:\-]?\s*([₹$£€]?\s*[0-9,]+(?:\.[0-9]{2})?)',
        r'([₹$£€]\s*[0-9,]+(?:\.[0-9]{2})?)'
    ]
    for p in total_patterns:
        m = re.search(p, plain, re.IGNORECASE)
        if m:
            total_amount = m.group(1).strip()
            break

    return {"invoice_number": invoice_number, "invoice_date": invoice_date, "total_amount": total_amount}


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Invoice Extractor is live"}), 200


@app.route("/extract", methods=["POST"])
def extract():
    # Validate file
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Save to a temp file (safer than trusting the uploaded filename)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=UPLOAD_FOLDER)
    try:
        file.save(tmp.name)
        tmp.close()

        # Extract text
        try:
            text = extract_text_from_pdf(tmp.name)
        except Exception as e:
            app.logger.exception("pdfplumber error")
            return jsonify({"error": "Failed to read PDF", "detail": str(e)}), 500

        # Heuristic parse
        parsed = find_invoice_fields(text)

        # Build response
        response = {
            "message": f"Invoice extracted from {file.filename}",
            "content": text,
            "parsed": parsed
        }
        return jsonify(response), 200

    except Exception as e:
        app.logger.exception("Unexpected error")
        return jsonify({"error": "Unexpected server error", "detail": str(e)}), 500

    finally:
        # cleanup
        try:
            os.remove(tmp.name)
        except Exception:
            pass


if __name__ == "__main__":
    # For local testing only. On Render use gunicorn app:app
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
