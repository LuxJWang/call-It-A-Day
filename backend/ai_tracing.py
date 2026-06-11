from __future__ import annotations

import logging
import os
from contextlib import ExitStack, contextmanager, nullcontext
from typing import Any, Optional

from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_LANGFUSE_CLIENT: Optional[Any] = None
_LANGSMITH_CLIENT: Optional[Any] = None


def initialize_tracing() -> None:
    if settings.LANGSMITH_TRACING:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        if settings.LANGSMITH_PROJECT:
            os.environ.setdefault("LANGSMITH_PROJECT", settings.LANGSMITH_PROJECT)
        if settings.LANGSMITH_API_KEY:
            os.environ.setdefault("LANGSMITH_API_KEY", settings.LANGSMITH_API_KEY)

    if settings.LANGFUSE_ENABLED:
        if settings.LANGFUSE_PUBLIC_KEY:
            os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.LANGFUSE_PUBLIC_KEY)
        if settings.LANGFUSE_SECRET_KEY:
            os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.LANGFUSE_SECRET_KEY)
        if settings.LANGFUSE_HOST:
            os.environ.setdefault("LANGFUSE_BASE_URL", settings.LANGFUSE_HOST)
        os.environ.setdefault("LANGFUSE_TRACING_ENABLED", "true")


def build_callback_manager() -> Optional[object]:
    try:
        from langchain_core.callbacks.manager import CallbackManager
    except ImportError:
        return None

    handlers: list[object] = []
    if settings.LANGCHAIN_VERBOSE:
        try:
            from langchain_core.callbacks.stdout import StdOutCallbackHandler

            handlers.append(StdOutCallbackHandler())
        except Exception as exc:
            logger.debug("Failed to initialize stdout callbacks: %s", exc)

    if settings.LANGSMITH_TRACING or handlers:
        try:
            return CallbackManager.configure(
                local_callbacks=handlers,
                verbose=settings.LANGCHAIN_VERBOSE,
            )
        except Exception as exc:
            logger.warning("Failed to build callback manager: %s", exc)

    return None


def _get_langsmith_client() -> Optional[Any]:
    global _LANGSMITH_CLIENT
    if _LANGSMITH_CLIENT is not None:
        return _LANGSMITH_CLIENT

    if not settings.LANGSMITH_TRACING:
        return None

    try:
        import langsmith

        _LANGSMITH_CLIENT = langsmith.Client(
            api_key=settings.LANGSMITH_API_KEY or None,
            tracing_mode="langsmith",
        )
        return _LANGSMITH_CLIENT
    except ImportError as exc:
        logger.warning("LangSmith tracing requested but langsmith package is unavailable: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Failed to initialize LangSmith client: %s", exc)
        return None


def _get_langfuse_client() -> Optional[Any]:
    global _LANGFUSE_CLIENT
    if _LANGFUSE_CLIENT is not None:
        return _LANGFUSE_CLIENT

    if not settings.LANGFUSE_ENABLED:
        return None

    try:
        import langfuse

        _LANGFUSE_CLIENT = langfuse.Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY or None,
            secret_key=settings.LANGFUSE_SECRET_KEY or None,
            base_url=settings.LANGFUSE_HOST or None,
            tracing_enabled=True,
        )
        return _LANGFUSE_CLIENT
    except ImportError as exc:
        logger.warning("LangFuse tracing requested but langfuse package is unavailable: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Failed to initialize LangFuse client: %s", exc)
        return None


def _get_langsmith_tracing_context():
    if not settings.LANGSMITH_TRACING:
        return nullcontext()

    try:
        from langchain_core.tracers.context import tracing_v2_enabled
    except ImportError as exc:
        logger.warning("LangSmith tracing requested but langchain-core tracing support is unavailable: %s", exc)
        return nullcontext()

    client = _get_langsmith_client()
    try:
        return tracing_v2_enabled(
            project_name=settings.LANGSMITH_PROJECT or None,
            client=client,
        )
    except Exception as exc:
        logger.warning("Unable to activate LangSmith tracing context: %s", exc)
        return nullcontext()


def _get_langfuse_span_context(
    name: str,
    *,
    as_type: str = "span",
    input: Optional[object] = None,
    output: Optional[object] = None,
    metadata: Optional[object] = None,
    model: Optional[str] = None,
    model_parameters: Optional[dict[str, object]] = None,
):
    client = _get_langfuse_client()
    if client is None:
        return nullcontext()

    try:
        return client.start_as_current_observation(
            name=name,
            as_type=as_type,
            input=input,
            output=output,
            metadata=metadata,
            model=model,
            model_parameters=model_parameters,
        )
    except Exception as exc:
        logger.warning("Unable to activate LangFuse span for %s: %s", name, exc)
        return nullcontext()


@contextmanager
def tracing_context(
    name: str,
    *,
    as_type: str = "span",
    input: Optional[object] = None,
    output: Optional[object] = None,
    metadata: Optional[object] = None,
    model: Optional[str] = None,
    model_parameters: Optional[dict[str, object]] = None,
):
    with ExitStack() as stack:
        stack.enter_context(_get_langsmith_tracing_context())
        stack.enter_context(
            _get_langfuse_span_context(
                name,
                as_type=as_type,
                input=input,
                output=output,
                metadata=metadata,
                model=model,
                model_parameters=model_parameters,
            )
        )
        yield


def get_current_langsmith_run_id() -> Optional[str]:
    if not settings.LANGSMITH_TRACING:
        return None

    try:
        import langsmith

        current = langsmith.get_current_run_tree()
        if current is None:
            return None
        return str(current.id)
    except Exception:
        return None
