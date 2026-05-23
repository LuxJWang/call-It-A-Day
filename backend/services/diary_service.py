from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from llm import get_llm_for_purpose
from models import DiaryChunk, DiaryEntry
from retrieval.rankers import ColBERTRanker, CrossEncoderRanker, LambdaMARTRanker, reciprocal_rank_fusion
from services.config_registry import config_registry
from services.embedding_model import embed_query, embed_texts
from services.search_index import search_index
from services.semantic_splitter import DiarySemanticSplitter
from services.vector_store import vector_store


class DiaryStorageService:
    def __init__(self, db: Session):
        self.db = db
        self.splitter = DiarySemanticSplitter()

    def add_diary(self, content: str, occurred_at: Optional[datetime] = None) -> DiaryEntry:
        metadata = self._extract_metadata(content, occurred_at)
        entry = DiaryEntry(
            title=metadata.get("title"),
            content=content,
            metadata_json=metadata,
            occurred_at=occurred_at,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        chunks = self.splitter.split(content)
        vectors = embed_texts([chunk.content for chunk in chunks])
        milvus_rows = []
        es_rows = []
        for chunk, vector in zip(chunks, vectors):
            db_chunk = DiaryChunk(
                diary_id=entry.id,
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                token_count=chunk.token_count,
                semantic_group_id=chunk.semantic_group_id,
                metadata_json=metadata,
            )
            self.db.add(db_chunk)
            created_at = entry.created_at.isoformat()
            row = {
                "chunk_id": chunk.chunk_id,
                "diary_id": entry.id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "title": entry.title,
                "metadata": metadata,
                "created_at": created_at,
                "occurred_at": entry.occurred_at.isoformat() if entry.occurred_at else created_at,
            }
            milvus_rows.append({**row, "created_at": created_at})
            es_rows.append(row)

        self.db.commit()
        if vectors:
            entry.embedding_id = chunks[0].chunk_id
            self.db.commit()
            vector_store.upsert_chunks(milvus_rows, vectors)
            search_index.index_chunks(es_rows)
        return entry

    def _extract_metadata(self, content: str, occurred_at: Optional[datetime]) -> Dict[str, Any]:
        prompt = """请从日记内容中抽取结构化 metadata，返回 JSON only。
字段：
- title: 12字以内标题
- summary: 简短摘要
- topics: 字符串数组
- emotions: 字符串数组
- people: 字符串数组
- places: 字符串数组
- keywords: 字符串数组
- happened_at: 如果内容中出现明确时间则 ISO8601，否则 null"""
        try:
            llm = get_llm_for_purpose("tool_enrichment")
            response = llm.invoke([
                SystemMessage(content="你是严谨的信息抽取器，只返回 JSON。"),
                HumanMessage(content=f"{prompt}\n\n日记：\n{content}"),
            ])
            metadata = json.loads(_extract_json(response.content))
        except Exception:
            metadata = {}
        metadata.setdefault("title", content.strip().splitlines()[0][:12] if content.strip() else "Diary")
        metadata.setdefault("summary", content[:160])
        metadata.setdefault("topics", [])
        metadata.setdefault("emotions", [])
        metadata.setdefault("people", [])
        metadata.setdefault("places", [])
        metadata.setdefault("keywords", [])
        metadata["ingested_at"] = datetime.utcnow().isoformat()
        if occurred_at:
            metadata["occurred_at"] = occurred_at.isoformat()
        return metadata


class DiaryRetrievalService:
    def __init__(self, db: Session):
        self.db = db
        self.cross_encoder = CrossEncoderRanker()
        self.colbert = ColBERTRanker()
        self.lambdamart = LambdaMARTRanker()

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        cfg = config_registry.get_runtime("diary_retrieval")
        query_info = self._understand_query(query)
        filters = query_info.get("filters") or {}

        dense_hits = []
        try:
            dense_hits = vector_store.search(embed_query(query_info.get("rewritten_query") or query), cfg.get("dense_top_k", 80))
        except Exception:
            dense_hits = []

        sparse_hits = search_index.search(
            query_info.get("rewritten_query") or query,
            cfg.get("sparse_top_k", 80),
            filters=filters,
        )
        fused = reciprocal_rank_fusion(
            [dense_hits, sparse_hits],
            top_k=cfg.get("fusion_top_k", 50),
            k=cfg.get("rrf_k", 60),
        )
        if cfg.get("enable_lambdamart"):
            fused = self.lambdamart.rerank(query, fused, cfg.get("fusion_top_k", 50))
        if cfg.get("enable_colbert"):
            fused = self.colbert.rerank(query, fused, min(30, len(fused)))
        ranked = self.cross_encoder.rerank(query, fused, max(limit, cfg.get("cross_encoder_top_k", 10)))
        return ranked[:limit]

    def _understand_query(self, query: str) -> Dict[str, Any]:
        prompt = """请分析日记检索 query，返回 JSON only：
{
  "rewritten_query": "更适合检索的 query",
  "filters": {"start_at": null, "end_at": null},
  "intent": "brief"
}"""
        try:
            llm = get_llm_for_purpose("tool_enrichment")
            response = llm.invoke([
                SystemMessage(content="你是检索 query 分析器，只返回 JSON。"),
                HumanMessage(content=f"{prompt}\n\nquery: {query}"),
            ])
            return json.loads(_extract_json(response.content))
        except Exception:
            return {"rewritten_query": query, "filters": {}, "intent": "fallback"}


def _extract_json(content: str) -> str:
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        return content[start:end]
    return content
