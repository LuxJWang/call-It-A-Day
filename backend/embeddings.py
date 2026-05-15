import chromadb
from chromadb.utils import embedding_functions
from config import get_settings
from typing import List, Dict, Any
from datetime import datetime

settings = get_settings()

class EmbeddingStore:
    def __init__(self):
        self.client = chromadb.HttpClient(host=settings.CHROMA_URL.replace("http://", "").split(":")[0],
                                          port=int(settings.CHROMA_URL.split(":")[-1]))
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL
        )
        self.collection = self.client.get_or_create_collection(
            name="diary_entries",
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

    def add_entry(self, entry_id: str, content: str, metadata: Dict[str, Any]) -> str:
        self.collection.add(
            ids=[entry_id],
            documents=[content],
            metadatas=[{
                "created_at": metadata.get("created_at", datetime.utcnow().isoformat()),
                "entry_id": entry_id,
                **{k: v for k, v in metadata.items() if k != "created_at"}
            }]
        )
        return entry_id

    def search_similar(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        entries = []
        for i in range(len(results["ids"][0])):
            entries.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
        return entries

    def get_recent_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        all_entries = self.collection.get()
        entries = []
        for i in range(len(all_entries["ids"])):
            entries.append({
                "id": all_entries["ids"][i],
                "content": all_entries["documents"][i],
                "metadata": all_entries["metadatas"][i]
            })
        entries.sort(key=lambda x: x["metadata"].get("created_at", ""), reverse=True)
        return entries[:limit]

    def delete_entry(self, entry_id: str):
        self.collection.delete(ids=[entry_id])


embedding_store = EmbeddingStore()
