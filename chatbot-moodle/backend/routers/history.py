from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import jwt as pyjwt

from database import get_db, Message
from schemas import HistoryItem
from jwt_service import verify_jwt

router = APIRouter()


@router.get("/history/{user_id}", response_model=list[HistoryItem])
def get_history(user_id: int, token: str = Query(...), db: Session = Depends(get_db)):
    try:
        payload = verify_jwt(token)
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    if payload["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    messages = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.timestamp.asc())
        .all()
    )
    return messages
