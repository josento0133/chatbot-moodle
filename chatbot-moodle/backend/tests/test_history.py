from database import Message
from datetime import datetime


def test_history_empty(client, valid_token):
    r = client.get("/history/42", params={"token": valid_token})
    assert r.status_code == 200
    assert r.json() == []


def test_history_returns_messages(client, valid_token, db):
    db.add(Message(user_id=42, role="user", content="¿qué es x?", subject="Matemáticas", timestamp=datetime.now()))
    db.add(Message(user_id=42, role="assistant", content="x es incógnita", subject="Matemáticas", timestamp=datetime.now()))
    db.commit()
    r = client.get("/history/42", params={"token": valid_token})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    assert items[0]["role"] == "user"


def test_history_wrong_user_returns_403(client, valid_token):
    r = client.get("/history/99", params={"token": valid_token})
    assert r.status_code == 403


def test_history_invalid_token_returns_401(client):
    r = client.get("/history/42", params={"token": "bad"})
    assert r.status_code == 401
