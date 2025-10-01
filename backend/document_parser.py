# backend/document_parser.py
import pandas as pd
import docx
from pdfminer.high_level import extract_text

# --- PDF ---
from PyPDF2 import PdfReader

def extract_pdf(file):
    file.file.seek(0)  # reset pointer
    reader = PdfReader(file.file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    # split by paragraphs / chunks
    chunks = text.split("\n\n")
    return [chunk.strip() for chunk in chunks if chunk.strip()]


# --- DOCX ---
def extract_docx(file):
    doc = docx.Document(file.file)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]

# --- CSV ---
def extract_csv(file):
    df = pd.read_csv(file.file)
    chunks = df.apply(lambda row: " ".join(row.astype(str)), axis=1).tolist()
    return chunks

# --- TXT ---
def extract_txt(file):
    text = file.file.read().decode("utf-8")  # decode bytes to string
    # Optional: split into 500-character chunks
    chunk_size = 500
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    return [c.strip() for c in chunks if c.strip()]

# --- Main extraction function ---
def extract_text_from_file(file):
    filename = file.filename.lower()
    if filename.endswith(".pdf"):
        return extract_pdf(file)
    elif filename.endswith(".docx"):
        return extract_docx(file)
    elif filename.endswith(".csv"):
        return extract_csv(file)
    elif filename.endswith(".txt"):
        return extract_txt(file)
    else:
        return []
