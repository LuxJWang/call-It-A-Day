from __future__ import annotations

from typing import Any, Dict, List, Optional

from config import get_settings

settings = get_settings()


class DiarySearchIndex:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is not None:
            return self._client
        try:
            from elasticsearch import Elasticsearch

            self._client = Elasticsearch(settings.ELASTICSEARCH_URL)
            self._ensure_index()
        except Exception:
            self._client = None
        return self._client

    def _ensure_index(self):
        if not self._client or self._client.indices.exists(index=settings.ELASTICSEARCH_DIARY_INDEX):
            return
        self._client.indices.create(
            index=settings.ELASTICSEARCH_DIARY_INDEX,
            mappings={
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "diary_id": {"type": "integer"},
                    "chunk_index": {"type": "integer"},
                    "content": {"type": "text"},
                    "title": {"type": "text"},
                    "metadata": {"type": "object", "enabled": True},
                    "created_at": {"type": "date"},
                    "occurred_at": {"type": "date"},
                }
            },
        )

    def index_chunks(self, rows: List[Dict[str, Any]]):
        client = self.client
        if not client:
            return
        try:
            from elasticsearch.helpers import bulk

            actions = [
                {
                    "_op_type": "index",
                    "_index": settings.ELASTICSEARCH_DIARY_INDEX,
                    "_id": row["chunk_id"],
                    "_source": row,
                }
                for row in rows
            ]
            bulk(client, actions)
        except Exception:
            return

    def search(self, query: str, top_k: int, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        client = self.client
        if not client:
            return []

        must = [{"multi_match": {"query": query, "fields": ["content^3", "title^2", "metadata.*"]}}]
        filter_clauses = []
        filters = filters or {}
        if filters.get("start_at") or filters.get("end_at"):
            date_range = {}
            if filters.get("start_at"):
                date_range["gte"] = filters["start_at"]
            if filters.get("end_at"):
                date_range["lte"] = filters["end_at"]
            filter_clauses.append({"range": {"created_at": date_range}})

        body = {
            "query": {
                "bool": {
                    "must": must,
                    "filter": filter_clauses,
                }
            },
            "size": top_k,
        }
        try:
            response = client.search(index=settings.ELASTICSEARCH_DIARY_INDEX, body=body)
        except Exception:
            return []

        hits = []
        for hit in response.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            hits.append({
                "chunk_id": source.get("chunk_id"),
                "diary_id": source.get("diary_id"),
                "chunk_index": source.get("chunk_index"),
                "content": source.get("content"),
                "created_at": source.get("created_at"),
                "metadata": source.get("metadata"),
                "sparse_score": float(hit.get("_score") or 0.0),
                "source": "elasticsearch",
            })
        return hits


search_index = DiarySearchIndex()
