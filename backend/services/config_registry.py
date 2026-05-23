from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from config import get_settings
from models import ModelConfig, RuntimeConfig


settings = get_settings()


@dataclass
class LLMConfig:
    purpose: str
    provider: str
    base_url: Optional[str]
    api_key: Optional[str]
    model: str
    temperature: float
    max_tokens: Optional[int]
    enabled: bool
    extra_json: Dict[str, Any]


class ConfigRegistry:
    def __init__(self):
        self._lock = RLock()
        self._model_configs: Dict[str, LLMConfig] = {}
        self._runtime_configs: Dict[str, Dict[str, Any]] = {}

    def load_from_db(self, db: Session):
        model_rows = db.query(ModelConfig).all()
        runtime_rows = db.query(RuntimeConfig).all()
        with self._lock:
            self._model_configs = {row.purpose: self._from_model_row(row) for row in model_rows}
            self._runtime_configs = {row.key: row.value_json or {} for row in runtime_rows}

    def get_model(self, purpose: str) -> LLMConfig:
        with self._lock:
            config = self._model_configs.get(purpose)
            if config:
                return config
        return self._fallback_model(purpose)

    def set_model(self, row: ModelConfig):
        with self._lock:
            self._model_configs[row.purpose] = self._from_model_row(row)

    def get_runtime(self, key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            value = self._runtime_configs.get(key)
            if value is not None:
                return dict(value)
        return default or {}

    def set_runtime(self, row: RuntimeConfig):
        with self._lock:
            self._runtime_configs[row.key] = row.value_json or {}

    def all_models(self) -> Dict[str, LLMConfig]:
        with self._lock:
            return dict(self._model_configs)

    def all_runtime(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._runtime_configs)

    def _from_model_row(self, row: ModelConfig) -> LLMConfig:
        return LLMConfig(
            purpose=row.purpose,
            provider=row.provider,
            base_url=row.base_url,
            api_key=row.api_key,
            model=row.model,
            temperature=row.temperature,
            max_tokens=row.max_tokens,
            enabled=row.enabled,
            extra_json=row.extra_json or {},
        )

    def _fallback_model(self, purpose: str) -> LLMConfig:
        model = settings.DEFAULT_LLM_MODEL
        if purpose == "embedding":
            model = settings.EMBEDDING_MODEL
        if purpose == "cross_encoder":
            model = settings.CROSS_ENCODER_MODEL
        if purpose == "colbert":
            model = settings.COLBERT_MODEL
        return LLMConfig(
            purpose=purpose,
            provider="openai_compatible",
            base_url=settings.MODEL_BASE_URL,
            api_key=settings.MODEL_API_KEY,
            model=model,
            temperature=0.7,
            max_tokens=None,
            enabled=True,
            extra_json={},
        )


config_registry = ConfigRegistry()
