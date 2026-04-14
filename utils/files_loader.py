from langchain_community.document_loaders import PyMuPDFLoader
from flask import jsonify
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .os_function import FILES_DIR

doc = []
content = []

def clear():
    doc.clear()
    content.clear()

def load_single_pdf(file_name):
    file_path = FILES_DIR / file_name
    loader = PyMuPDFLoader(file_path)
    file = loader.load()
    return file

def load_all_pdfs():
    if not FILES_DIR.exists():
        return jsonify({"error": "Files directory does not exist."})

    pdf_files = [file for file in FILES_DIR.iterdir() if file.suffix.lower() == ".pdf"]
    all_docs = []
    for pdf_file in pdf_files:
        loader = PyMuPDFLoader(pdf_file)
        docs = loader.load()
        all_docs.extend(docs)

    return all_docs

def chunked_files(doc, chunk_size = 1024, chunk_overlap = 200):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return text_splitter.split_documents(doc)
    