from __future__ import annotations

from functools import lru_cache
from typing import List

import numpy as np

from services.config_registry import config_registry


@lru_cache(maxsize=4)
def _load_sentence_transformer(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    model_name = config_registry.get_model("embedding").model
    model = _load_sentence_transformer(model_name)
    vectors = model.encode(texts, normalize_embeddings=True)
    if isinstance(vectors, np.ndarray):
        return vectors.astype("float32").tolist()
    return [list(vector) for vector in vectors]


def embed_query(text: str) -> List[float]:
    vectors = embed_texts([text])
    return vectors[0] if vectors else []
