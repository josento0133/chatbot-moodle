from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import jwt as pyjwt

from database import get_db, Message
from schemas import ChatRequest, ChatResponse
from jwt_service import verify_jwt
from rate_limit import check_rate_limit
from llm import call_ollama
from config import settings

router = APIRouter()

EXERCISE_SUBJECTS = {"Matemáticas", "Física", "Química", "Biología"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        payload = verify_jwt(request.token)
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user_id = payload["user_id"]

    if not check_rate_limit(user_id, db):
        raise HTTPException(status_code=429, detail="Límite diario alcanzado")

    history = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.timestamp.desc())
        .limit(settings.max_history_messages)
        .all()
    )
    messages = [{"role": m.role, "content": m.content} for m in reversed(history)]
    messages.append({"role": "user", "content": request.message})

    try:
        answer = await call_ollama(messages)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="El asistente está ocupado, inténtalo en unos segundos",
        )

    db.add(Message(user_id=user_id, role="user", content=request.message, subject=request.subject))
    db.add(Message(user_id=user_id, role="assistant", content=answer, subject=request.subject))
    db.commit()

    suggest = request.subject in EXERCISE_SUBJECTS if request.subject else False
    return ChatResponse(response=answer, suggest_exercise=suggest)
