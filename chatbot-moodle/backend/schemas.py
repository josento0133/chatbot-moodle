from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ChatRequest(BaseModel):
    token: str
    message: str
    subject: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    suggest_exercise: bool


class HistoryItem(BaseModel):
    role: str
    content: str
    subject: Optional[str]
    timestamp: datetime

    model_config = {"from_attributes": True}


class ExerciseRequest(BaseModel):
    token: str
    topic: str
    subject: Optional[str] = None


class ExerciseResponse(BaseModel):
    question: str
    answer: str
    exercise_id: int


class AnswerRequest(BaseModel):
    token: str
    exercise_id: int
    answer: str
