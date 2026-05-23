from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

try:
    from langchain_experimental.text_splitter import SemanticChunker
    from langchain_community.embeddings import HuggingFaceEmbeddings
except Exception:  # pragma: no cover - optional local dependency guard
    SemanticChunker = None
    HuggingFaceEmbeddings = None

from services.config_registry import config_registry


@dataclass
class SemanticChunk:
    chunk_id: str
    chunk_index: int
    content: str
    start_offset: Optional[int]
    end_offset: Optional[int]
    token_count: int
    semantic_group_id: str


class DiarySemanticSplitter:
    """Semantic splitting with a deterministic token-aware fallback."""

    def __init__(self):
        self._semantic_splitter = None

    def split(self, content: str) -> List[SemanticChunk]:
        runtime = config_registry.get_runtime("semantic_splitting")
        docs = self._semantic_split(content, runtime)
        if not docs:
            docs = self._fallback_split(content, runtime)
        return self._to_chunks(content, docs, runtime)

    def _semantic_split(self, content: str, runtime: Dict) -> List[str]:
        if SemanticChunker is None or HuggingFaceEmbeddings is None:
            return []
        try:
            if self._semantic_splitter is None:
                model_name = config_registry.get_model("embedding").model
                embeddings = HuggingFaceEmbeddings(model_name=model_name)
                kwargs = {
                    "embeddings": embeddings,
                    "buffer_size": runtime.get("buffer_size", 1),
                    "breakpoint_threshold_type": runtime.get("breakpoint_threshold_type", "gradient"),
                }
                threshold = runtime.get("breakpoint_threshold_amount")
                if threshold is not None:
                    kwargs["breakpoint_threshold_amount"] = threshold
                self._semantic_splitter = SemanticChunker(**kwargs)

            docs = self._semantic_splitter.create_documents([content])
            return [doc.page_content.strip() for doc in docs if doc.page_content.strip()]
        except Exception:
            return []

    def _fallback_split(self, content: str, runtime: Dict) -> List[str]:
        chunk_size = runtime.get("fallback_chunk_chars", 1200)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=min(120, chunk_size // 10),
            separators=["\n\n", "\n", "。", "！", "？", ";", "；", ".", " ", ""],
        )
        return [part.strip() for part in splitter.split_text(content) if part.strip()]

    def _to_chunks(self, content: str, docs: List[str], runtime: Dict) -> List[SemanticChunk]:
        min_chars = runtime.get("min_chunk_chars", 120)
        max_chars = runtime.get("max_chunk_chars", 1800)
        merged: List[str] = []

        for doc in docs:
            if merged and len(doc) < min_chars:
                merged[-1] = f"{merged[-1]}\n{doc}".strip()
            else:
                merged.append(doc)

        final_docs: List[str] = []
        for doc in merged:
            if len(doc) <= max_chars:
                final_docs.append(doc)
                continue
            final_docs.extend(self._fallback_split(doc, {"fallback_chunk_chars": max_chars}))

        chunks = []
        cursor = 0
        group_id = str(uuid.uuid4())
        for idx, doc in enumerate(final_docs):
            start = content.find(doc, cursor)
            if start < 0:
                start = None
                end = None
            else:
                end = start + len(doc)
                cursor = end
            chunks.append(SemanticChunk(
                chunk_id=str(uuid.uuid4()),
                chunk_index=idx,
                content=doc,
                start_offset=start,
                end_offset=end,
                token_count=self._rough_token_count(doc),
                semantic_group_id=group_id,
            ))
        return chunks

    def _rough_token_count(self, text: str) -> int:
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        words = len(re.findall(r"[A-Za-z0-9_]+", text))
        return chinese_chars + words
