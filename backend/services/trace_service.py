from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ai_tracing import get_current_langsmith_run_id
from models import ChatTraceEvent


class TraceRecorder:
    def __init__(self, db: Session, run_id: str, session_id: str, user_id: Optional[int] = None):
        self.db = db
        self.run_id = run_id
        self.session_id = session_id
        self.user_id = user_id

    def record(
        self,
        node_name: str,
        event_type: str,
        layer: Optional[str] = None,
        tool_name: Optional[str] = None,
        input_json: Optional[Dict[str, Any]] = None,
        output_json: Optional[Dict[str, Any]] = None,
        latency_ms: Optional[int] = None,
        langsmith_run_id: Optional[str] = None,
    ):
        if langsmith_run_id is None:
            langsmith_run_id = get_current_langsmith_run_id()
        event = ChatTraceEvent(
            user_id=self.user_id or 0,
            run_id=self.run_id,
            session_id=self.session_id,
            layer=layer,
            node_name=node_name,
            event_type=event_type,
            tool_name=tool_name,
            input_json=_json_safe(input_json),
            output_json=_json_safe(output_json),
            latency_ms=latency_ms,
            langsmith_run_id=langsmith_run_id,
        )
        self.db.add(event)
        self.db.commit()

    @contextmanager
    def timed(self, node_name: str, event_type: str, **kwargs):
        started = time.perf_counter()
        try:
            yield
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.record(node_name=node_name, event_type=event_type, latency_ms=latency_ms, **kwargs)


def _json_safe(value):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool, list, dict)):
        return value
    return {"repr": repr(value)}
