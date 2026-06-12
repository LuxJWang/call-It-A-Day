from sqlalchemy import inspect, text

from config import get_settings
from models import Base, ModelConfig, RuntimeConfig, SoulDocument, User, engine, SessionLocal
from utils import hash_password

settings = get_settings()


def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_legacy_columns()
    _seed_defaults()


def _ensure_legacy_columns():
    """Small create_all companion for local dev DBs without migrations."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    if "diary_entries" not in existing_tables:
        return

    columns = {col["name"] for col in inspector.get_columns("diary_entries")}
    statements = []
    if "title" not in columns:
        statements.append("ALTER TABLE diary_entries ADD COLUMN title VARCHAR")
    if "metadata_json" not in columns:
        statements.append("ALTER TABLE diary_entries ADD COLUMN metadata_json JSON")
    if "occurred_at" not in columns:
        statements.append("ALTER TABLE diary_entries ADD COLUMN occurred_at TIMESTAMP")
    if "updated_at" not in columns:
        statements.append("ALTER TABLE diary_entries ADD COLUMN updated_at TIMESTAMP")
    if "user_id" not in columns:
        statements.append("ALTER TABLE diary_entries ADD COLUMN user_id INTEGER")

    if "chat_messages" in existing_tables:
        chat_columns = {col["name"] for col in inspector.get_columns("chat_messages")}
        if "user_id" not in chat_columns:
            statements.append("ALTER TABLE chat_messages ADD COLUMN user_id INTEGER")

    if "chat_runs" in existing_tables:
        run_columns = {col["name"] for col in inspector.get_columns("chat_runs")}
        if "user_id" not in run_columns:
            statements.append("ALTER TABLE chat_runs ADD COLUMN user_id INTEGER")

    if "chat_trace_events" in existing_tables:
        trace_columns = {col["name"] for col in inspector.get_columns("chat_trace_events")}
        if "user_id" not in trace_columns:
            statements.append("ALTER TABLE chat_trace_events ADD COLUMN user_id INTEGER")

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _seed_defaults():
    db = SessionLocal()
    try:
        defaults = {
            "intent_recognition": {"temperature": 0.2},
            "tool_enrichment": {"temperature": 0.1},
            "response_generation": {"temperature": 0.7},
            "embedding": {"model": settings.EMBEDDING_MODEL, "temperature": 0.0},
            "cross_encoder": {"model": settings.CROSS_ENCODER_MODEL, "temperature": 0.0},
            "colbert": {"model": settings.COLBERT_MODEL, "temperature": 0.0, "enabled": False},
        }

        for purpose, override in defaults.items():
            exists = db.query(ModelConfig).filter(ModelConfig.purpose == purpose).first()
            if exists:
                continue
            db.add(ModelConfig(
                purpose=purpose,
                provider="openai_compatible",
                base_url=settings.MODEL_BASE_URL,
                api_key=settings.MODEL_API_KEY,
                model=override.get("model", settings.DEFAULT_LLM_MODEL),
                temperature=override.get("temperature", 0.7),
                enabled=override.get("enabled", True),
                extra_json={},
            ))

        runtime_defaults = {
            "chat": {
                "layer1_max_iterations": 3,
                "history_max_chars": 12000,
                "message_max_chars": 2000,
                "tool_trace_enabled": True,
            },
            "diary_retrieval": {
                "dense_top_k": 80,
                "sparse_top_k": 80,
                "fusion_top_k": 50,
                "cross_encoder_top_k": 10,
                "rrf_k": 60,
                "enable_colbert": False,
                "enable_lambdamart": False,
            },
            "semantic_splitting": {
                "breakpoint_threshold_type": "gradient",
                "breakpoint_threshold_amount": None,
                "buffer_size": 1,
                "min_chunk_chars": 120,
                "max_chunk_chars": 1800,
                "fallback_chunk_chars": 1200,
                "overlap_sentences": 1,
            },
        }
        for key, value in runtime_defaults.items():
            exists = db.query(RuntimeConfig).filter(RuntimeConfig.key == key).first()
            if not exists:
                db.add(RuntimeConfig(key=key, value_json=value))

        if not db.query(User).filter(User.username == "call_it_a_day").first():
            salt, password_hash = hash_password("call_it_a_day")
            db.add(User(username="call_it_a_day", password_hash=password_hash, password_salt=salt))

        soul_defaults = {
            "diary-soul.md": _default_diary_soul(),
            "user-soul.md": _default_user_soul(),
            "soul_system_prompt.md": _default_soul_system_prompt(),
        }
        for name, content in soul_defaults.items():
            exists = db.query(SoulDocument).filter(SoulDocument.name == name).first()
            if not exists:
                db.add(SoulDocument(name=name, content=content))

        db.commit()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _default_soul_system_prompt() -> str:
    return """你负责维护 diary-soul.md 和 user-soul.md。

所有修改必须符合社会主义核心价值观，并体现新时代四有青年要求：有理想、有道德、有文化、有纪律。
内容应真诚、积极、尊重事实、鼓励自省和建设性行动，避免空泛说教、极端化表达、歧视性表达和违背公序良俗的建议。
如果 proposed change 不符合上述原则，应明确说明原因并拒绝应用。"""


def _default_diary_soul() -> str:
    return """# Diary Soul

你是一个温暖、克制、积极的日记伙伴。回答应帮助用户看见事实、理解情绪、形成建设性行动。

价值导向：
- 弘扬社会主义核心价值观。
- 鼓励成为有理想、有道德、有文化、有纪律的新时代青年。
- 尊重用户主体性，不替用户做重大决定。
- 不制造焦虑，不用空话压过真实感受。

表达风格：
- 真诚、简洁、有同理心。
- 先理解，再建议。
- 在合适时鼓励记录、复盘和行动。"""


def _default_user_soul() -> str:
    return """# User Soul

当前尚未沉淀稳定用户画像。后续仅保存长期、明确、对对话质量有帮助的信息。"""
