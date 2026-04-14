import uuid
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from .os_function import normalize_username


BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DB_DIR = BASE_DIR / "vector_store"
_EMBEDDING_FUNCTIONS = {}


def _collection_names(client):
    names = []
    for collection in client.list_collections():
        if isinstance(collection, str):
            names.append(collection)
        else:
            name = getattr(collection, "name", None)
            if name:
                names.append(name)
    return names


def get_embedding_function(model_name="all-MiniLM-L6-v2"):
    if model_name not in _EMBEDDING_FUNCTIONS:
        _EMBEDDING_FUNCTIONS[model_name] = (
            embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model_name
            )
        )
    return _EMBEDDING_FUNCTIONS[model_name]


class VectorStoreManager:
    def __init__(
        self,
        persist_dir=VECTOR_DB_DIR,
        collection_name=None,
        model_name="all-MiniLM-L6-v2",
    ):
        self.persist_dir = str(persist_dir)
        self.collection_name = collection_name or str(uuid.uuid4())
        self.model_name = model_name
        self.collection = None
        self.client = None
        self.embedding_function = get_embedding_function(self.model_name)

        self._initialize_vector()

    def _initialize_vector(self):
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Study Buddy vector collection"},
            embedding_function=self.embedding_function,
        )

    def add_files(self, documents):
        if not documents:
            raise ValueError("No documents provided for vector storage.")

        ids = []
        metadatas = []
        contents = []

        for index, document in enumerate(documents):
            ids.append(f"doc_{uuid.uuid4()}")
            metadata = dict(document.metadata or {})
            metadata["doc_index"] = index
            metadata["content_length"] = len(document.page_content)
            metadatas.append(metadata)
            contents.append(document.page_content)

        self.collection.add(
            ids=ids,
            metadatas=metadatas,
            documents=contents,
        )
        return self.collection_name

    def query(self, query_text, n_results=4):
        if not query_text or not query_text.strip():
            raise ValueError("Query text is required.")

        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )

    @classmethod
    def get_collection_for_user(
        cls,
        username,
        collection_name=None,
        persist_dir=VECTOR_DB_DIR,
        model_name="all-MiniLM-L6-v2",
    ):
        safe_username = normalize_username(username)
        if not safe_username:
            raise ValueError("A valid username is required.")

        client = chromadb.PersistentClient(path=str(persist_dir))
        available_names = _collection_names(client)

        if collection_name:
            if collection_name not in available_names:
                raise ValueError("Requested collection was not found.")
            if not collection_name.startswith(f"{safe_username}_"):
                raise PermissionError("Requested collection does not belong to this user.")
            resolved_name = collection_name
        else:
            prefix = f"{safe_username}_"
            user_names = sorted(name for name in available_names if name.startswith(prefix))
            if not user_names:
                raise ValueError("No vector collection found for this user.")
            resolved_name = user_names[-1]

        return cls(
            persist_dir=persist_dir,
            collection_name=resolved_name,
            model_name=model_name,
        )

    @classmethod
    def delete_collection_for_user(
        cls,
        username,
        collection_name=None,
        persist_dir=VECTOR_DB_DIR,
    ):
        safe_username = normalize_username(username)
        if not safe_username:
            raise ValueError("A valid username is required.")

        client = chromadb.PersistentClient(path=str(persist_dir))
        available_names = _collection_names(client)
        prefix = f"{safe_username}_"

        if collection_name:
            if collection_name not in available_names:
                raise ValueError("Requested collection was not found.")
            if not collection_name.startswith(prefix):
                raise PermissionError("Requested collection does not belong to this user.")
            targets = [collection_name]
        else:
            targets = [name for name in available_names if name.startswith(prefix)]

        if not targets:
            return 0

        for target in targets:
            client.delete_collection(name=target)

        return len(targets)
