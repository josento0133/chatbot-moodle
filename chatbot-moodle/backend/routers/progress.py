from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import jwt as pyjwt

from database import get_db, Message, Exercise
from jwt_service import verify_jwt

router = APIRouter()


@router.get("/progress/{user_id}")
def get_progress(user_id: int, token: str = Query(...), db: Session = Depends(get_db)):
    try:
        payload = verify_jwt(token)
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    if payload["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    total_q = (
        db.query(func.count(Message.id))
        .filter(Message.user_id == user_id, Message.role == "user")
        .scalar()
    )
    total_ex = (
        db.query(func.count(Exercise.id))
        .filter(Exercise.user_id == user_id)
        .scalar()
    )
    correct_ex = (
        db.query(func.count(Exercise.id))
        .filter(Exercise.user_id == user_id, Exercise.correct == True)
        .scalar()
    )
    today_q = (
        db.query(func.count(Message.id))
        .filter(
            Message.user_id == user_id,
            Message.role == "user",
            func.date(Message.timestamp) == date.today(),
        )
        .scalar()
    )
    subjects = (
        db.query(Message.subject, func.count(Message.id))
        .filter(Message.user_id == user_id, Message.subject.isnot(None))
        .group_by(Message.subject)
        .all()
    )

    return {
        "total_questions": total_q,
        "total_exercises": total_ex,
        "correct_exercises": correct_ex,
        "messages_today": today_q,
        "subjects": [{"subject": s, "count": c} for s, c in subjects],
    }
