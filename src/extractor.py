import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import re
import pandas as pd
import os

# If Tesseract OCR path is needed, uncomment and set path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF. Handles scanned (image) PDFs too."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
            else:
                # If page_text is None, use OCR
                images = page.images
                pil_images = convert_from_path(pdf_path)
                for img in pil_images:
                    text += pytesseract.image_to_string(img)
    return text

def extract_line_items_from_text(text):
    """Extract table line items from text."""
    lines = text.split("\n")
    line_items = []
    for line in lines:
        # Basic detection, can customize according to your invoice layout
        if re.search(r'\d+\s+\d+(\.\d+)?', line):
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 2:
                line_items.append({
                    "description": parts[0],
                    "qty": parts[1] if len(parts) > 1 else None,
                    "price": parts[2] if len(parts) > 2 else None,
                    "amount": float(parts[-1].replace("₹", "").replace(",", "")) if parts[-1].replace("₹", "").replace(",", "").replace(".", "").isdigit() else None
                })
    return line_items

def extract_invoice_dict(pdf_path):
    text = extract_text_from_pdf(pdf_path)
    
    invoice_number_match = re.search(r"Invoice Number\s*[:#]?\s*(\S+)", text, re.IGNORECASE)
    invoice_number = invoice_number_match.group(1) if invoice_number_match else None
    
    date_match = re.findall(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", text)
    
    total_amount_match = re.search(r"Total\s*[:$₹]?\s*([\d.,]+)", text, re.IGNORECASE)
    total_amount = float(total_amount_match.group(1).replace(",", "")) if total_amount_match else None
    
    line_items = extract_line_items_from_text(text)
    
    # Save CSV
    csv_path = os.path.join("output", os.path.basename(pdf_path).replace(".pdf", "_line_items.csv"))
    if line_items:
        df = pd.DataFrame(line_items)
        df.to_csv(csv_path, index=False)
    
    return {
        "raw_text_snippet": text[:1000],  # first 1000 chars
        "invoice_number": invoice_number,
        "dates": date_match,
        "total_amount": total_amount,
        "line_items": line_items,
        "line_items_csv": csv_path if line_items else "",
        "scanned": True  # assume scanned if OCR used
    }
