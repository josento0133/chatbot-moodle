from datetime import datetime, date, time as dt_time
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import Message
from config import settings


def check_rate_limit(user_id: int, db: Session, limit: int = None) -> bool:
    """True si el usuario aún puede enviar mensajes hoy."""
    limit = limit if limit is not None else settings.daily_message_limit
    today_start = datetime.combine(date.today(), dt_time.min)
    count = (
        db.query(func.count(Message.id))
        .filter(
            Message.user_id == user_id,
            Message.role == "user",
            Message.timestamp >= today_start,
        )
        .scalar()
    )
    return count < limit
