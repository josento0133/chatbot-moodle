from database import Message, Exercise
from datetime import datetime


def test_progress_empty(client, valid_token):
    r = client.get("/progress/42", params={"token": valid_token})
    assert r.status_code == 200
    data = r.json()
    assert data["total_questions"] == 0
    assert data["total_exercises"] == 0
    assert data["correct_exercises"] == 0


def test_progress_counts(client, valid_token, db):
    db.add(Message(user_id=42, role="user", content="q1", subject="Matemáticas", timestamp=datetime.now()))
    db.add(Message(user_id=42, role="assistant", content="a1", subject="Matemáticas", timestamp=datetime.now()))
    db.add(Exercise(user_id=42, question="¿3x?", answer="6", correct=True, timestamp=datetime.now()))
    db.commit()
    r = client.get("/progress/42", params={"token": valid_token})
    data = r.json()
    assert data["total_questions"] == 1
    assert data["total_exercises"] == 1
    assert data["correct_exercises"] == 1


def test_progress_wrong_user_returns_403(client, valid_token):
    r = client.get("/progress/99", params={"token": valid_token})
    assert r.status_code == 403
