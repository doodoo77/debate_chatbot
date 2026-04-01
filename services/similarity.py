from __future__ import annotations

from typing import Optional

import numpy as np

from services.llm import get_embedding_model


def semantic_similarity(text_a: str, text_b: str) -> float:
    if not text_a or not text_b:
        return 0.0

    try:
        embedding_model = get_embedding_model()
        vec_a = np.array(embedding_model.embed_query(text_a))
        vec_b = np.array(embedding_model.embed_query(text_b))
        denom = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
        if denom == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / denom)
    except Exception:
        tokens_a = set(text_a.split())
        tokens_b = set(text_b.split())
        if not tokens_a or not tokens_b:
            return 0.0
        return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
