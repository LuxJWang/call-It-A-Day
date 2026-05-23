from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List

from services.config_registry import config_registry


def reciprocal_rank_fusion(result_sets: List[List[Dict[str, Any]]], top_k: int, k: int = 60) -> List[Dict[str, Any]]:
    fused: Dict[str, Dict[str, Any]] = {}
    for result_set in result_sets:
        for rank, item in enumerate(result_set, start=1):
            chunk_id = item.get("chunk_id")
            if not chunk_id:
                continue
            if chunk_id not in fused:
                fused[chunk_id] = dict(item)
                fused[chunk_id]["rrf_score"] = 0.0
                fused[chunk_id]["sources"] = []
            fused[chunk_id]["rrf_score"] += 1.0 / (k + rank)
            fused[chunk_id]["sources"].append(item.get("source"))
            for score_key in ("dense_score", "sparse_score"):
                if score_key in item:
                    fused[chunk_id][score_key] = item[score_key]
    return sorted(fused.values(), key=lambda item: item.get("rrf_score", 0.0), reverse=True)[:top_k]


@lru_cache(maxsize=4)
def _load_cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


class CrossEncoderRanker:
    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        try:
            model_name = config_registry.get_model("cross_encoder").model
            model = _load_cross_encoder(model_name)
            pairs = [(query, candidate.get("content") or "") for candidate in candidates]
            scores = model.predict(pairs)
            for candidate, score in zip(candidates, scores):
                candidate["cross_encoder_score"] = float(score)
            return sorted(candidates, key=lambda item: item.get("cross_encoder_score", 0.0), reverse=True)[:top_k]
        except Exception:
            return candidates[:top_k]


class ColBERTRanker:
    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        # Hook for PyLate/RAGatouille. Disabled by default until local model assets are present.
        return candidates[:top_k]


class LambdaMARTRanker:
    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        # LambdaMART requires trained relevance labels; keep the stage pluggable.
        return candidates[:top_k]
