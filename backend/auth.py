from datetime import datetime, timedelta
from typing import Optional
import uuid

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserSession
from utils import generate_token, hash_password, verify_password

SESSION_TTL_SECONDS = 24 * 60 * 60
security = HTTPBearer(auto_error=False)


def create_user(db: Session, username: str, password: str) -> User:
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail='用户名已存在')

    salt, password_hash = hash_password(password)
    user = User(username=username, password_hash=password_hash, password_salt=salt)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_salt, user.password_hash):
        return None
    return user


def create_user_session(db: Session, user_id: int) -> str:
    token = generate_token()
    now = datetime.utcnow()
    session = UserSession(
        token=token,
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(seconds=SESSION_TTL_SECONDS),
        last_active_at=now,
    )
    db.add(session)
    db.commit()
    return token


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != 'bearer' or not credentials.credentials:
        raise HTTPException(status_code=401, detail='请先登录')

    token = credentials.credentials
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if not session:
        raise HTTPException(status_code=401, detail='登录凭证无效')

    now = datetime.utcnow()
    if session.expires_at < now:
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail='登录已过期，请重新登录')

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail='登录用户不存在')

    session.last_active_at = now
    session.expires_at = now + timedelta(seconds=SESSION_TTL_SECONDS)
    db.commit()
    return user


def require_session(session_id: Optional[str], user_id: int, db: Session) -> str:
    from models import ChatSession

    now = datetime.utcnow()
    if session_id:
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id, ChatSession.user_id == user_id).first()
        if session:
            if session.expires_at < now:
                session = None
            else:
                session.expires_at = now + timedelta(seconds=SESSION_TTL_SECONDS)
                session.updated_at = now
                db.commit()
                return session.session_id

    new_session_id = f'{uuid.uuid4().hex}'
    session = ChatSession(
        session_id=new_session_id,
        user_id=user_id,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(seconds=SESSION_TTL_SECONDS),
    )
    db.add(session)
    db.commit()
    return new_session_id
