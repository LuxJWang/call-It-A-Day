from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import Counter
import re

from models import DiaryEntry, ChatMessage
from tools.diary_tools import get_diary_count


def build_agent_summary(db: Session, session_id: str = "default") -> Dict[str, Any]:
    """
    Build a summary of the user's diary and chat history for the agent.

    Args:
        db: Database session
        session_id: Current chat session ID

    Returns:
        Dictionary containing summary statistics
    """
    total_diaries = get_diary_count(db)

    recent_diaries = db.query(DiaryEntry).order_by(
        DiaryEntry.created_at.desc()
    ).limit(20).all()

    recent_topics = extract_topics(recent_diaries)

    last_diary = db.query(DiaryEntry).order_by(
        DiaryEntry.created_at.desc()
    ).first()
    last_diary_date = last_diary.created_at.strftime("%Y-%m-%d") if last_diary else None

    session_start = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).first()

    if session_start:
        session_duration = datetime.utcnow() - session_start.created_at
        session_minutes = int(session_duration.total_seconds() / 60)
    else:
        session_minutes = 0

    mood_trend = analyze_mood_trend(recent_diaries)

    return {
        "total_diaries": total_diaries,
        "recent_topics": recent_topics[:5],
        "last_diary_date": last_diary_date,
        "chat_session_duration_minutes": session_minutes,
        "user_mood_trend": mood_trend
    }


def extract_topics(diaries: list) -> list:
    """Extract common topics from diary entries."""
    if not diaries:
        return []

    all_text = " ".join([d.content for d in diaries]).lower()

    common_words = ["the", "and", "for", "are", "but", "not", "you", "all", "can",
                   "had", "her", "was", "one", "our", "out", "day", "get", "has",
                   "him", "his", "how", "its", "may", "new", "now", "old", "see",
                   "two", "who", "boy", "did", "she", "use", "her", "way", "many",
                   "oil", "sit", "set", "run", "eat", "far", "sea", "eye", "ago",
                   "off", "too", "any", "say", "man", "try", "ask", "end", "why",
                   "let", "put", "say", "she", "try", "way", "own", "say", "too",
                   "old", "tell", "very", "when", "much", "would", "there", "their",
                   "what", "said", "each", "which", "will", "about", "could", "other",
                   "after", "first", "never", "these", "think", "where", "being",
                   "every", "great", "might", "shall", "still", "those", "while",
                   "today", "yesterday", "tomorrow", "morning", "evening", "night"]

    words = re.findall(r'\b[a-z]{3,}\b', all_text)
    filtered = [w for w in words if w not in common_words]

    counter = Counter(filtered)
    return [word for word, count in counter.most_common(10)]


def analyze_mood_trend(diaries: list) -> str:
    """Analyze the general mood trend from recent diaries."""
    if not diaries:
        return "neutral"

    positive_words = ["happy", "good", "great", "excellent", "wonderful", "amazing",
                      "love", "enjoyed", "fantastic", "awesome", "best", "perfect",
                      "glad", "excited", "grateful", "peaceful", "relaxed"]
    negative_words = ["sad", "bad", "terrible", "awful", "hate", "worst", "angry",
                      "frustrated", "disappointed", "upset", "worried", "stressed",
                      "tired", "exhausted", "depressed", "anxious", "hurt", "pain"]

    all_text = " ".join([d.content for d in diaries]).lower()

    pos_count = sum(1 for word in positive_words if word in all_text)
    neg_count = sum(1 for word in negative_words if word in all_text)

    if pos_count > neg_count * 1.5:
        return "positive"
    elif neg_count > pos_count * 1.5:
        return "negative"
    else:
        return "mixed"
