from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models import DiaryEntry


def get_diary_by_date(db: Session, date: str) -> Optional[DiaryEntry]:
    """
    Retrieve a diary entry by date.

    Args:
        db: Database session
        date: Date string in YYYY-MM-DD format

    Returns:
        Diary entry if found, None otherwise
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        entry = db.query(DiaryEntry).filter(
            DiaryEntry.created_at >= target_date.replace(hour=0, minute=0, second=0),
            DiaryEntry.created_at < target_date.replace(hour=23, minute=59, second=59)
        ).first()
        return entry
    except ValueError:
        return None


def get_recent_diaries(db: Session, limit: int = 10) -> List[DiaryEntry]:
    """
    Get the most recent diary entries.

    Args:
        db: Database session
        limit: Maximum number of entries to return

    Returns:
        List of recent diary entries
    """
    return db.query(DiaryEntry).order_by(DiaryEntry.created_at.desc()).limit(limit).all()


def get_diary_count(db: Session) -> int:
    """
    Get the total number of diary entries.

    Args:
        db: Database session

    Returns:
        Total count of diary entries
    """
    return db.query(DiaryEntry).count()
