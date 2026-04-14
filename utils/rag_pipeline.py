import uuid

from langchain_community.document_loaders import PyMuPDFLoader

from .files_loader import chunked_files
from .os_function import FILES_DIR, normalize_username
from .vector_db import VectorStoreManager


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
    _, docs = load_user_pdfs(username=username)
    chunked_doc = chunked_files(docs)
    if username != None:
        vector_store = VectorStoreManager(collection_name = f"{username}_{uuid.uuid4()}")
    else:
        vector_store = VectorStoreManager()
    name = vector_store.add_files(chunked_doc)
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


def query_rag(username, query_text, collection_name=None, n_results=4):
    vector_store = VectorStoreManager.get_collection_for_user(
        username=username,
        collection_name=collection_name,
    )
    results = vector_store.query(query_text=query_text, n_results=n_results)

    documents = results.get("documents", [[]])
    metadatas = results.get("metadatas", [[]])
    distances = results.get("distances", [[]])

    matches = []
    for index, content in enumerate(documents[0] if documents else []):
        matches.append(
            {
                "content": content,
                "metadata": (metadatas[0][index] if metadatas and metadatas[0] else {}),
                "distance": (distances[0][index] if distances and distances[0] else None),
            }
        )

    return {
        "collection_name": vector_store.collection_name,
        "matches": matches,
    }
