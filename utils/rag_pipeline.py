import uuid

from langchain_community.document_loaders import PyMuPDFLoader

from .files_loader import chunked_files
from .os_function import FILES_DIR, normalize_username
from .vector_db import VectorStoreManager, embedding_model


def load_user_pdfs(username=None):
    if not FILES_DIR.exists():
        raise FileNotFoundError("Files directory does not exist.")

    safe_username = normalize_username(username)
    pdf_files = [
        file
        for file in FILES_DIR.iterdir()
        if file.is_file()
        and file.suffix.lower() == ".pdf"
        and (not safe_username or file.name.startswith(f"{safe_username}_"))
    ]

    if not pdf_files:
        raise ValueError("No PDF files found to vectorize.")

    docs = []
    for pdf_file in pdf_files:
        docs.extend(PyMuPDFLoader(pdf_file).load())

    return pdf_files, docs

def create_rag(file_name = None, username = None, embed_model = None):
    if embed_model is None:
        embed_model = embedding_model()

    _, docs = load_user_pdfs(username=username)
    chunked_doc = chunked_files(docs)
    text = [doc.page_content for doc in chunked_doc]
    if username != None:
        vector_store = VectorStoreManager(collection_name = f"{username}_{uuid.uuid4()}")
    else:
        vector_store = VectorStoreManager()
    embeddings_ = embed_model.generate_embeddings(text)
    name = vector_store.add_files(chunked_doc, embeddings_)
    return name


def vectorize_uploaded_files(username = None, embed_model = None):
    safe_username = normalize_username(username)
    if not FILES_DIR.exists():
        raise FileNotFoundError("Files directory does not exist.")

    uploaded_files = [
        file
        for file in FILES_DIR.iterdir()
        if file.is_file()
        and (not safe_username or file.name.startswith(f"{safe_username}_"))
    ]
    pdf_files = [file for file in uploaded_files if file.suffix.lower() == ".pdf"]
    skipped_files = [file.name for file in uploaded_files if file.suffix.lower() != ".pdf"]

    if not pdf_files:
        raise ValueError("No PDF files found to vectorize.")

    collection_name = create_rag(username = username, embed_model = embed_model)
    _, docs = load_user_pdfs(username=username)
    chunked_doc = chunked_files(docs)

    return {
        "collection_name": collection_name,
        "processed_files": len(pdf_files),
        "skipped_files": skipped_files,
        "vectorized_chunks": len(chunked_doc),
    }
