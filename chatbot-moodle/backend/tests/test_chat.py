from unittest.mock import AsyncMock, patch
from database import Message
from datetime import datetime


def test_chat_invalid_token_returns_401(client):
    r = client.post("/chat", json={"token": "bad.token", "message": "hola"})
    assert r.status_code == 401


def test_chat_success(client, valid_token):
    with patch("routers.chat.call_ollama", new=AsyncMock(return_value="4")):
        r = client.post("/chat", json={
            "token": valid_token, "message": "¿Cuánto es 2+2?", "subject": "Matemáticas"
        })
    assert r.status_code == 200
    data = r.json()
    assert data["response"] == "4"
    assert data["suggest_exercise"] is True


def test_chat_non_exercise_subject_no_suggestion(client, valid_token):
    with patch("routers.chat.call_ollama", new=AsyncMock(return_value="Felipe II")):
        r = client.post("/chat", json={
            "token": valid_token, "message": "¿Quién fue Felipe II?", "subject": "Historia"
        })
    assert r.status_code == 200
    assert r.json()["suggest_exercise"] is False


def test_chat_rate_limit_returns_429(client, valid_token, db, monkeypatch):
    import config
    monkeypatch.setattr(config.settings, "daily_message_limit", 1)
    db.add(Message(user_id=42, role="user", content="prev", timestamp=datetime.now()))
    db.commit()
    with patch("routers.chat.call_ollama", new=AsyncMock(return_value="resp")):
        r = client.post("/chat", json={"token": valid_token, "message": "otra"})
    assert r.status_code == 429


def test_chat_ollama_error_returns_503(client, valid_token):
    with patch("routers.chat.call_ollama", new=AsyncMock(side_effect=Exception("timeout"))):
        r = client.post("/chat", json={"token": valid_token, "message": "hola"})
    assert r.status_code == 503
