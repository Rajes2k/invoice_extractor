import requests

URL = "https://invoice-extractor.onrender.com/extract"   # or "http://127.0.0.1:8080/extract"
PDF = "data/samples/invoice1.pdf"

# JSON response test
with open(PDF, "rb") as f:
    r = requests.post(URL, files={"pdf": f}, timeout=60)
    print("Status:", r.status_code)
    try:
        print(r.json())
    except:
        print("Response text:", r.text[:1000])

# CSV download test
with open(PDF, "rb") as f:
    r = requests.post(URL + "?csv=1", files={"pdf": f}, timeout=60)
    if r.status_code == 200:
        with open("invoice_items.csv", "wb") as out:
            out.write(r.content)
        print("Saved invoice_items.csv")
    else:
        print("CSV request failed:", r.status_code, r.text)

