from __future__ import annotations

from typing import Any, Dict, List

from config import get_settings

settings = get_settings()


class MilvusDiaryVectorStore:
    def __init__(self):
        self._ready = False
        self._collection = None
        self._dim = None

    def ensure_collection(self, dim: int):
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

            connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)

            # If a collection with the correct schema dimension does not exist,
            # create it; otherwise just make sure it is loaded for operations.
            if not utility.has_collection(settings.MILVUS_COLLECTION):
                fields = [
                    FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
                    FieldSchema(name="diary_id", dtype=DataType.INT64),
                    FieldSchema(name="chunk_index", dtype=DataType.INT64),
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
                    FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=64),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
                ]
                schema = CollectionSchema(fields, description="Diary semantic chunks")
                collection = Collection(settings.MILVUS_COLLECTION, schema=schema)
                collection.create_index(
                    "embedding",
                    {"metric_type": "COSINE", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 200}},
                )

            self._collection = Collection(settings.MILVUS_COLLECTION)
            self._collection.load()
            self._dim = dim
            self._ready = True
        except Exception as e:
            print(f"Error occurred while ensuring collection: {e}")
            self._ready = False
            self._collection = None

    def upsert_chunks(self, rows: List[Dict[str, Any]], vectors: List[List[float]]):
        if not rows or not vectors:
            return
        self.ensure_collection(len(vectors[0]))
        if not self._collection:
            return
        entities = [
            [row["chunk_id"] for row in rows],
            [int(row["diary_id"]) for row in rows],
            [int(row["chunk_index"]) for row in rows],
            [row["content"][:4096] for row in rows],
            [row["created_at"] for row in rows],
            vectors,
        ]
        try:
            self._collection.upsert(entities)
            self._collection.flush()
        except Exception as e:
            print(f"Error occurred while upserting chunks: {e}")
            self._ready = False
            self._collection = None

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        self.ensure_collection(len(query_vector))
        if not self._collection:
            return []
        try:
            results = self._collection.search(
                data=[query_vector],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"ef": 64}},
                limit=top_k,
                output_fields=["diary_id", "chunk_index", "content", "created_at"],
            )
        except Exception as e:
            print(f"Error occurred while searching Milvus: {e}")
            self._ready = False
            self._collection = None
            return []
        hits = []
        for hit in results[0]:
            hits.append({
                "chunk_id": hit.id,
                "diary_id": hit.entity.get("diary_id"),
                "chunk_index": hit.entity.get("chunk_index"),
                "content": hit.entity.get("content"),
                "created_at": hit.entity.get("created_at"),
                "dense_score": float(hit.score),
                "source": "milvus",
            })
        return hits


vector_store = MilvusDiaryVectorStore()
