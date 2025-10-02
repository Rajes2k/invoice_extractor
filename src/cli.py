import argparse
from extractor import extract_invoice

def main():
    parser = argparse.ArgumentParser(description="Invoice extraction CLI")
    parser.add_argument("--pdf", type=str, required=True, help="Path to invoice PDF")
    parser.add_argument("--out", type=str, default="output", help="Output folder")
    args = parser.parse_args()

    extract_invoice(args.pdf, args.out)

if __name__ == "__main__":
    main()
