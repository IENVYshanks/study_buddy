import gc
import hashlib
import re
import shutil
import uuid
from pathlib import Path

import chromadb
import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction
from chromadb.utils import embedding_functions

from .os_function import normalize_username


BASE_DIR = Path(__file__).resolve().parents[2]
VECTOR_DB_DIR = BASE_DIR / "vector_store"
DEFAULT_EMBEDDING_MODEL = "local-hash"
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


class LocalHashEmbeddingFunction(EmbeddingFunction[Documents]):
    def __init__(self, dimensions=384):
        self.dimensions = dimensions

    def __call__(self, input: Documents):
        return [self._embed(document) for document in input]

    def _embed(self, document):
        vector = np.zeros(self.dimensions, dtype=np.float32)
        tokens = re.findall(r"[a-z0-9]+", (document or "").lower())

        if not tokens:
            tokens = [(document or "").lower()]

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector


def get_embedding_function(model_name=DEFAULT_EMBEDDING_MODEL):
    if model_name not in _EMBEDDING_FUNCTIONS:
        if model_name == DEFAULT_EMBEDDING_MODEL:
            _EMBEDDING_FUNCTIONS[model_name] = LocalHashEmbeddingFunction()
        else:
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
        model_name=DEFAULT_EMBEDDING_MODEL,
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
    def get_user_persist_dir(cls, username, persist_dir=VECTOR_DB_DIR):
        safe_username = normalize_username(username)
        if not safe_username:
            raise ValueError("A valid username is required.")

        return Path(persist_dir) / safe_username

    @staticmethod
    def _remove_persist_dir_if_user_scoped(path):
        resolved_base = VECTOR_DB_DIR.resolve()
        resolved_path = Path(path).resolve()

        if resolved_path == resolved_base or resolved_base not in resolved_path.parents:
            return

        if resolved_path.exists():
            shutil.rmtree(resolved_path)

    @staticmethod
    def _release_client(client):
        identifier = getattr(client, "_identifier", None)

        try:
            client._system.stop()
        except Exception:
            pass

        if identifier:
            client._identifier_to_system.pop(identifier, None)
            client._identifier_to_refcount.pop(identifier, None)
            return

        client.clear_system_cache()

    @classmethod
    def get_collection_for_user(
        cls,
        username,
        collection_name=None,
        persist_dir=VECTOR_DB_DIR,
        model_name=DEFAULT_EMBEDDING_MODEL,
    ):
        safe_username = normalize_username(username)
        if not safe_username:
            raise ValueError("A valid username is required.")

        user_persist_dir = cls.get_user_persist_dir(safe_username, persist_dir)
        if not user_persist_dir.exists():
            raise ValueError("No vector collection found for this user.")

        client = chromadb.PersistentClient(path=str(user_persist_dir))
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
            persist_dir=user_persist_dir,
            collection_name=resolved_name,
            model_name=model_name,
        )

    @classmethod
    def delete_collection_for_user(
        cls,
        username,
        collection_name=None,
        persist_dir=VECTOR_DB_DIR,
        missing_ok=False,
    ):
        safe_username = normalize_username(username)
        if not safe_username:
            raise ValueError("A valid username is required.")

        user_persist_dir = cls.get_user_persist_dir(safe_username, persist_dir)
        if not user_persist_dir.exists():
            return 0

        client = chromadb.PersistentClient(path=str(user_persist_dir))
        available_names = _collection_names(client)
        prefix = f"{safe_username}_"

        if collection_name:
            if collection_name not in available_names:
                if missing_ok:
                    cls._release_client(client)
                    del client
                    gc.collect()
                    return 0
                raise ValueError("Requested collection was not found.")
            if not collection_name.startswith(prefix):
                raise PermissionError("Requested collection does not belong to this user.")
            targets = [collection_name]
        else:
            targets = [name for name in available_names if name.startswith(prefix)]

        if not targets:
            if not collection_name:
                cls._release_client(client)
                del client
                gc.collect()
                cls._remove_persist_dir_if_user_scoped(user_persist_dir)
            return 0

        for target in targets:
            client.delete_collection(name=target)

        should_remove_persist_dir = not _collection_names(client)
        cls._release_client(client)
        del client
        gc.collect()

        if should_remove_persist_dir:
            cls._remove_persist_dir_if_user_scoped(user_persist_dir)

        return len(targets)
