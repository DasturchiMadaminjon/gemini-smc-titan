import PyPDF2
import os

pdf_path = r"c:\Users\Asus\.gemini\antigravity\scratch\temp_master_zip\bilim_bazasi\FIBO STRATEGY TEXO TRADE.pdf"
try:
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for i in range(len(reader.pages)):
            text += reader.pages[i].extract_text() + "\n"
        print("--- TEXNO TRADE FIBO STRATEGY.PDF MA'LUMOTLARI ---")
        print(text[:3000]) # Print first 3000 chars to understand the strategy
except Exception as e:
    print("Xato:", e)
