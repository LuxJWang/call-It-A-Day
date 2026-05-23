"""Compatibility wrapper around the Milvus-backed diary vector store."""

from typing import Any, Dict, List

from services.embedding_model import embed_query, embed_texts
from services.vector_store import vector_store


class EmbeddingStore:
    def add_entry(self, entry_id: str, content: str, metadata: Dict[str, Any]) -> str:
        vectors = embed_texts([content])
        if vectors:
            vector_store.upsert_chunks(
                [{
                    "chunk_id": entry_id,
                    "diary_id": int(metadata.get("entry_id") or 0),
                    "chunk_index": 0,
                    "content": content,
                    "created_at": metadata.get("created_at", ""),
                }],
                vectors,
            )
        return entry_id

    def search_similar(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        vector = embed_query(query)
        return vector_store.search(vector, n_results) if vector else []

    def get_recent_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    def delete_entry(self, entry_id: str):
        return None


embedding_store = EmbeddingStore()
