import json
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import jwt as pyjwt

from database import get_db, Exercise
from schemas import ExerciseRequest, ExerciseResponse, AnswerRequest
from jwt_service import verify_jwt
from llm import call_ollama

router = APIRouter()


@router.post("/exercise", response_model=ExerciseResponse)
async def create_exercise(request: ExerciseRequest, db: Session = Depends(get_db)):
    try:
        payload = verify_jwt(request.token)
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user_id = payload["user_id"]
    prompt = (
        f"Crea un ejercicio de práctica sobre '{request.topic}'. "
        f"Responde ÚNICAMENTE con este JSON exacto sin texto adicional:\n"
        f'{{"question": "<pregunta>", "answer": "<respuesta completa>"}}'
    )

    try:
        raw = await call_ollama([{"role": "user", "content": prompt}])
        match = re.search(r'\{[^{}]*"question"[^{}]*"answer"[^{}]*\}', raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON found")
        data = json.loads(match.group())
    except Exception:
        raise HTTPException(status_code=503, detail="No se pudo generar el ejercicio")

    ex = Exercise(user_id=user_id, question=data["question"], answer=data["answer"])
    db.add(ex)
    db.commit()
    db.refresh(ex)

    return ExerciseResponse(question=ex.question, answer=ex.answer, exercise_id=ex.id)


@router.post("/exercise/answer")
async def submit_answer(request: AnswerRequest, db: Session = Depends(get_db)):
    try:
        payload = verify_jwt(request.token)
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    ex = db.get(Exercise, request.exercise_id)
    if not ex or ex.user_id != payload["user_id"]:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")

    prompt = (
        f"Ejercicio: {ex.question}\n"
        f"Respuesta correcta: {ex.answer}\n"
        f"Respuesta del alumno: {request.answer}\n"
        f"¿Es correcta la respuesta del alumno? Empieza con SI o NO y da una breve explicación."
    )

    try:
        feedback = await call_ollama([{"role": "user", "content": prompt}])
    except Exception:
        raise HTTPException(status_code=503, detail="No se pudo evaluar la respuesta")

    correct = feedback.strip().upper().startswith("SI")
    ex.correct = correct
    db.commit()

    return {"correct": correct, "feedback": feedback}
