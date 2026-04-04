from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from config import get_settings
from services.llm import get_embedding_model

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


@dataclass
class CacheHit:
    response: str
    similarity: float
    metadata: Dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "response": self.response,
            "similarity": self.similarity,
            "metadata": self.metadata,
        }


class SemanticRedisCache:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.namespace = "debate_cache"
        self._memory_store: List[Dict[str, Any]] = []
        self.client = None

        if redis is not None:
            try:
                self.client = redis.Redis.from_url(self.settings.redis_url, decode_responses=True)
                self.client.ping()
            except Exception:
                self.client = None

    def _embed(self, text: str) -> List[float]:
        embedding_model = get_embedding_model()
        return embedding_model.embed_query(text)

    @staticmethod
    def _cosine_similarity(left: List[float], right: List[float]) -> float:
        left_arr = np.array(left)
        right_arr = np.array(right)
        denom = np.linalg.norm(left_arr) * np.linalg.norm(right_arr)
        if denom == 0:
            return 0.0
        return float(np.dot(left_arr, right_arr) / denom)

    def lookup(self, user_text: str, phase: str, topic: str, scope: str = "") -> Optional[CacheHit]:
        try:
            query_embedding = self._embed(user_text)
        except Exception:
            return None

        entries = self._load_entries()
        best_hit: Optional[CacheHit] = None

        for entry in entries:
            if entry.get("phase") != phase or entry.get("topic") != topic:
                continue
            if (entry.get("scope") or "") != (scope or ""):
                continue
            similarity = self._cosine_similarity(query_embedding, entry.get("embedding", []))
            if similarity < self.settings.cache_similarity_threshold:
                continue
            if best_hit is None or similarity > best_hit.similarity:
                best_hit = CacheHit(
                    response=entry["response"],
                    similarity=similarity,
                    metadata=entry,
                )
        return best_hit

    def store(
        self,
        user_text: str,
        phase: str,
        topic: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
        scope: str = "",
    ) -> None:
        try:
            payload = {
                "id": str(uuid.uuid4()),
                "user_text": user_text,
                "phase": phase,
                "topic": topic,
                "scope": scope,
                "response": response,
                "metadata": metadata or {},
                "created_at": time.time(),
                "embedding": self._embed(user_text),
            }
        except Exception:
            return

        if self.client is None:
            self._memory_store.append(payload)
            return

        key = f"{self.namespace}:{payload['id']}"
        self.client.set(key, json.dumps(payload, ensure_ascii=False))

    def _load_entries(self) -> List[Dict[str, Any]]:
        if self.client is None:
            return list(self._memory_store)

        keys = self.client.keys(f"{self.namespace}:*")
        entries: List[Dict[str, Any]] = []
        for key in keys:
            raw = self.client.get(key)
            if not raw:
                continue
            try:
                entries.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return entries
