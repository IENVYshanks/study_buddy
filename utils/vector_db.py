import uuid
import os
import chromadb
from sentence_transformers import SentenceTransformer
class VectorStoreManager:
    def __init__(self, persist_dir = "files", collection_name = f"{uuid.uuid4()}"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.collection = None
        self.client = None

        self._initialize_vector()

    def _initialize_vector(self):
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path = self.persist_dir)
        
        self.collection = self.client.get_or_create_collection(
            name = self.collection_name,
            metadata = {"description" : "created for me mf"}
        )

    def add_files(self, doc, embeddings):
        if len(doc) != len(embeddings):
            raise ValueError("num of docs does not match num of embeddings")
        
        ids = []
        metadatas = []
        documents = []
        embedding_lists = []

        for i, (doc, embed) in enumerate(zip(doc, embeddings)):
            doc_id = f"doc_{uuid.uuid4()}"
            ids.append(doc_id)
            metadata = dict(doc.metadata)
            metadata["doc_index"] = i
            metadata["content_length"] = len(doc.page_content)
            metadatas.append(metadata)
            documents.append(doc.page_content)
            embedding_lists.append(embed)

        self.collection.add(
            ids = ids,
            metadatas = metadatas,
            documents = documents,
            embeddings = embedding_lists

        )
        return self.collection_name


class embedding_model:
    def __init__(self , model_name = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = SentenceTransformer(self.model_name)

    def generate_embeddings(self, text):
        embeddings = self.model.encode(text)
        return embeddings


