import json
from unittest.mock import AsyncMock, patch
from database import Exercise
from datetime import datetime


def test_create_exercise_success(client, valid_token):
    llm_resp = json.dumps({"question": "¿Cuánto es 3×2?", "answer": "6"})
    with patch("routers.exercise.call_ollama", new=AsyncMock(return_value=llm_resp)):
        r = client.post("/exercise", json={
            "token": valid_token, "topic": "multiplicación", "subject": "Matemáticas"
        })
    assert r.status_code == 200
    data = r.json()
    assert data["question"] == "¿Cuánto es 3×2?"
    assert data["answer"] == "6"
    assert "exercise_id" in data


def test_create_exercise_invalid_token(client):
    r = client.post("/exercise", json={"token": "bad", "topic": "suma"})
    assert r.status_code == 401


def test_submit_correct_answer(client, valid_token, db):
    ex = Exercise(user_id=42, question="¿3×2?", answer="6", timestamp=datetime.now())
    db.add(ex)
    db.commit()
    db.refresh(ex)
    with patch("routers.exercise.call_ollama", new=AsyncMock(return_value="SI, correcto. La respuesta es 6.")):
        r = client.post("/exercise/answer", json={
            "token": valid_token, "exercise_id": ex.id, "answer": "6"
        })
    assert r.status_code == 200
    assert r.json()["correct"] is True


def test_submit_wrong_answer(client, valid_token, db):
    ex = Exercise(user_id=42, question="¿3×2?", answer="6", timestamp=datetime.now())
    db.add(ex)
    db.commit()
    db.refresh(ex)
    with patch("routers.exercise.call_ollama", new=AsyncMock(return_value="NO, la respuesta correcta es 6.")):
        r = client.post("/exercise/answer", json={
            "token": valid_token, "exercise_id": ex.id, "answer": "7"
        })
    assert r.status_code == 200
    assert r.json()["correct"] is False


def test_submit_answer_wrong_user_returns_404(client, valid_token, db):
    ex = Exercise(user_id=99, question="q", answer="a", timestamp=datetime.now())
    db.add(ex)
    db.commit()
    db.refresh(ex)
    r = client.post("/exercise/answer", json={
        "token": valid_token, "exercise_id": ex.id, "answer": "x"
    })
    assert r.status_code == 404
