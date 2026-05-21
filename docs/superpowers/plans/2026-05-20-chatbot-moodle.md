# Chatbot Académico Moodle — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir un plugin bloque de Moodle + backend FastAPI que dé a estudiantes de Bachillerato un chatbot académico 24/7 con generación de ejercicios y seguimiento de progreso.

**Architecture:** El plugin PHP (`block_chatbot`) renderiza el chat y genera JWTs firmados desde la sesión de Moodle. Un backend FastAPI valida tokens, llama a Ollama (LLM local) y persiste datos en tablas propias dentro de la BD de Moodle. El plugin crea las tablas vía `install.xml`.

**Tech Stack:** Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, PyJWT, httpx, pytest; PHP 8.x, Moodle Plugin API, Mustache templates, AMD JS; Ollama + Llama 3 8B o Mistral 7B; MySQL (BD compartida de Moodle); Docker para dev.

---

## Mapa de Archivos

```
chatbot-moodle/
├── backend/
│   ├── config.py                  # Settings: JWT secret, DB URL, Ollama URL, rate limit
│   ├── database.py                # SQLAlchemy engine + modelos + get_db
│   ├── schemas.py                 # Pydantic request/response
│   ├── jwt_service.py             # sign_jwt / verify_jwt
│   ├── rate_limit.py              # check_rate_limit(user_id, db)
│   ├── llm.py                     # call_ollama(messages) -> str
│   ├── routers/
│   │   ├── chat.py                # POST /chat
│   │   ├── history.py             # GET /history/{user_id}
│   │   ├── exercise.py            # POST /exercise, POST /exercise/answer
│   │   └── progress.py            # GET /progress/{user_id}
│   ├── main.py                    # FastAPI app, router registration, startup
│   ├── requirements.txt
│   └── tests/
│       ├── conftest.py            # SQLite en memoria + TestClient + fixtures
│       ├── test_jwt_service.py
│       ├── test_rate_limit.py
│       ├── test_chat.py
│       ├── test_history.py
│       ├── test_exercise.py
│       └── test_progress.py
└── moodle-plugin/
    └── block_chatbot/
        ├── version.php
        ├── block_chatbot.php      # Clase bloque: genera JWT, renderiza template
        ├── settings.php           # Admin: backend URL, JWT secret, límite diario
        ├── lang/en/
        │   └── block_chatbot.php  # Strings de idioma
        ├── db/
        │   └── install.xml        # Crea las 3 tablas en BD Moodle
        ├── templates/
        │   └── chat.mustache      # UI del chat
        ├── amd/src/
        │   └── chat.js            # AMD module: fetch + render
        └── tests/phpunit/
            └── block_chatbot_test.php
```

---

## Task 1: Entorno de Desarrollo + Estructura del Proyecto

**Files:**
- Create: `chatbot-moodle/docker-compose.yml`
- Create: `chatbot-moodle/backend/.env`
- Create: `chatbot-moodle/backend/requirements.txt`

- [ ] **Step 1: Crear la estructura de directorios**

```bash
mkdir -p chatbot-moodle/backend/routers
mkdir -p chatbot-moodle/backend/tests
mkdir -p chatbot-moodle/moodle-plugin/block_chatbot/lang/en
mkdir -p chatbot-moodle/moodle-plugin/block_chatbot/db
mkdir -p chatbot-moodle/moodle-plugin/block_chatbot/templates
mkdir -p chatbot-moodle/moodle-plugin/block_chatbot/amd/src
mkdir -p chatbot-moodle/moodle-plugin/block_chatbot/tests/phpunit
```

- [ ] **Step 2: Crear `docker-compose.yml`**

```yaml
version: '3.8'
services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: moodle
      MYSQL_USER: moodle
      MYSQL_PASSWORD: moodlepass
    ports:
      - "3306:3306"
    volumes:
      - moodle_db:/var/lib/mysql

  moodle:
    image: bitnami/moodle:4
    environment:
      MOODLE_DATABASE_HOST: db
      MOODLE_DATABASE_NAME: moodle
      MOODLE_DATABASE_USER: moodle
      MOODLE_DATABASE_PASSWORD: moodlepass
      MOODLE_USERNAME: admin
      MOODLE_PASSWORD: Admin1234!
    ports:
      - "8080:8080"
    volumes:
      - moodle_data:/bitnami/moodle
      - ./moodle-plugin/block_chatbot:/bitnami/moodle/blocks/chatbot
    depends_on:
      - db

volumes:
  moodle_db:
  moodle_data:
```

- [ ] **Step 3: Crear `backend/.env`**

```
JWT_SECRET=cambia-este-secreto-en-produccion
DATABASE_URL=mysql+mysqlconnector://moodle:moodlepass@localhost:3306/moodle
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3
DAILY_MESSAGE_LIMIT=50
MAX_HISTORY_MESSAGES=10
LLM_TIMEOUT=30
```

- [ ] **Step 4: Crear `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
pyjwt==2.10.0
httpx==0.27.2
pydantic-settings==2.6.1
python-dotenv==1.0.1
mysql-connector-python==9.1.0
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 5: Instalar dependencias del backend**

```bash
cd chatbot-moodle/backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Expected: `Successfully installed fastapi-0.115.0 uvicorn-...`

- [ ] **Step 6: Arrancar Moodle con Docker**

```bash
cd chatbot-moodle
docker compose up -d
```

Esperar ~2 minutos. Verificar: `http://localhost:8080` — debe mostrar Moodle.

- [ ] **Step 7: Instalar Ollama + modelo**

```bash
# Descargar Ollama desde https://ollama.com/download
ollama pull llama3
# Verificar:
ollama run llama3 "Hola"
```

Expected: Respuesta en texto del modelo.

---

## Task 2: Config + Modelos de Base de Datos

**Files:**
- Create: `backend/config.py`
- Create: `backend/database.py`

- [ ] **Step 1: Escribir el test de los modelos**

Crear `backend/tests/test_database.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

def test_tables_created():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from database import Base, Message, Exercise, Progress
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        msg = Message(user_id=1, role="user", content="hola")
        db.add(msg)
        db.commit()
        db.refresh(msg)
        assert msg.id is not None
        assert msg.role == "user"
```

- [ ] **Step 2: Ejecutar test para verificar que falla**

```bash
cd backend
pytest tests/test_database.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'database'`

- [ ] **Step 3: Crear `backend/config.py`**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    jwt_secret: str = "change-me"
    database_url: str = "sqlite:///./chatbot.db"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    daily_message_limit: int = 50
    max_history_messages: int = 10
    llm_timeout: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 4: Crear `backend/database.py`**

```python
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, Text
)
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import StaticPool
from config import settings

def _make_engine():
    kwargs = {}
    if "sqlite" in settings.database_url:
        kwargs["connect_args"] = {"check_same_thread": False}
        kwargs["poolclass"] = StaticPool
    return create_engine(settings.database_url, **kwargs)

engine = _make_engine()

class Base(DeclarativeBase):
    pass

class Message(Base):
    __tablename__ = "block_chatbot_messages"
    id        = Column(Integer, primary_key=True)
    user_id   = Column(Integer, nullable=False, index=True)
    role      = Column(String(16), nullable=False)   # 'user' | 'assistant'
    content   = Column(Text, nullable=False)
    subject   = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=datetime.now)

class Exercise(Base):
    __tablename__ = "block_chatbot_exercises"
    id        = Column(Integer, primary_key=True)
    user_id   = Column(Integer, nullable=False, index=True)
    question  = Column(Text, nullable=False)
    answer    = Column(Text, nullable=False)
    correct   = Column(Boolean, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)

class Progress(Base):
    __tablename__ = "block_chatbot_progress"
    id        = Column(Integer, primary_key=True)
    user_id   = Column(Integer, nullable=False, index=True)
    subject   = Column(String(64), nullable=False)
    topic     = Column(String(128), nullable=False)
    count     = Column(Integer, default=1)
    last_seen = Column(DateTime, default=datetime.now)

def get_db():
    with Session(engine) as session:
        yield session

def create_tables():
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 5: Ejecutar test para verificar que pasa**

```bash
pytest tests/test_database.py -v
```

Expected: `PASSED`

- [ ] **Step 6: Commit**

```bash
git add backend/config.py backend/database.py backend/tests/test_database.py backend/requirements.txt
git commit -m "feat: backend config and database models"
```

---

## Task 3: JWT Service

**Files:**
- Create: `backend/jwt_service.py`
- Create: `backend/tests/test_jwt_service.py`

- [ ] **Step 1: Escribir los tests**

Crear `backend/tests/test_jwt_service.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta
import jwt as pyjwt

SECRET = "test-secret-key"

def test_sign_and_verify_round_trip():
    from jwt_service import sign_jwt, verify_jwt
    token = sign_jwt(user_id=42, secret=SECRET)
    payload = verify_jwt(token, secret=SECRET)
    assert payload["user_id"] == 42

def test_expired_token_raises():
    from jwt_service import verify_jwt
    expired = pyjwt.encode(
        {"user_id": 1, "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        SECRET,
        algorithm="HS256"
    )
    with pytest.raises(pyjwt.ExpiredSignatureError):
        verify_jwt(expired, secret=SECRET)

def test_wrong_secret_raises():
    from jwt_service import sign_jwt, verify_jwt
    token = sign_jwt(user_id=1, secret=SECRET)
    with pytest.raises(pyjwt.InvalidSignatureError):
        verify_jwt(token, secret="wrong-secret")

def test_malformed_token_raises():
    from jwt_service import verify_jwt
    with pytest.raises(pyjwt.DecodeError):
        verify_jwt("not.a.valid.token", secret=SECRET)
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/test_jwt_service.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'jwt_service'`

- [ ] **Step 3: Crear `backend/jwt_service.py`**

```python
from datetime import datetime, timedelta, timezone
import jwt
from config import settings

def sign_jwt(user_id: int, secret: str = None) -> str:
    secret = secret or settings.jwt_secret
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def verify_jwt(token: str, secret: str = None) -> dict:
    secret = secret or settings.jwt_secret
    return jwt.decode(token, secret, algorithms=["HS256"])
```

- [ ] **Step 4: Ejecutar tests para verificar que pasan**

```bash
pytest tests/test_jwt_service.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/jwt_service.py backend/tests/test_jwt_service.py
git commit -m "feat: JWT sign and verify service"
```

---

## Task 4: Rate Limit + Schemas

**Files:**
- Create: `backend/rate_limit.py`
- Create: `backend/schemas.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_rate_limit.py`

- [ ] **Step 1: Crear `backend/tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

TEST_USER_ID = 42
TEST_SECRET = "test-secret-key"

@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    import config
    monkeypatch.setattr(config.settings, "jwt_secret", TEST_SECRET)
    monkeypatch.setattr(config.settings, "daily_message_limit", 50)
    monkeypatch.setattr(config.settings, "max_history_messages", 10)

@pytest.fixture
def db(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    from database import Base
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session

@pytest.fixture
def client(db, monkeypatch):
    from database import get_db
    from main import app
    def override_db():
        yield db
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def valid_token():
    from jwt_service import sign_jwt
    import config
    return sign_jwt(user_id=TEST_USER_ID, secret=config.settings.jwt_secret)
```

- [ ] **Step 2: Escribir tests de rate limit**

Crear `backend/tests/test_rate_limit.py`:

```python
from datetime import datetime
from database import Message
from rate_limit import check_rate_limit

def test_no_messages_allows(db):
    assert check_rate_limit(user_id=1, db=db, limit=50) is True

def test_under_limit_allows(db):
    for i in range(49):
        db.add(Message(user_id=1, role="user", content=f"q{i}", timestamp=datetime.now()))
    db.commit()
    assert check_rate_limit(user_id=1, db=db, limit=50) is True

def test_at_limit_blocks(db):
    for i in range(50):
        db.add(Message(user_id=1, role="user", content=f"q{i}", timestamp=datetime.now()))
    db.commit()
    assert check_rate_limit(user_id=1, db=db, limit=50) is False

def test_assistant_messages_not_counted(db):
    for i in range(50):
        db.add(Message(user_id=1, role="assistant", content=f"r{i}", timestamp=datetime.now()))
    db.commit()
    assert check_rate_limit(user_id=1, db=db, limit=50) is True

def test_different_user_not_affected(db):
    for i in range(50):
        db.add(Message(user_id=1, role="user", content=f"q{i}", timestamp=datetime.now()))
    db.commit()
    assert check_rate_limit(user_id=2, db=db, limit=50) is True
```

- [ ] **Step 3: Ejecutar tests para verificar que fallan**

```bash
pytest tests/test_rate_limit.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'rate_limit'`

- [ ] **Step 4: Crear `backend/rate_limit.py`**

```python
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
```

- [ ] **Step 5: Crear `backend/schemas.py`**

```python
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

    class Config:
        from_attributes = True

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
```

- [ ] **Step 6: Ejecutar tests de rate limit**

```bash
pytest tests/test_rate_limit.py -v
```

Expected: `5 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/rate_limit.py backend/schemas.py backend/tests/conftest.py backend/tests/test_rate_limit.py
git commit -m "feat: rate limiting service and pydantic schemas"
```

---

## Task 5: Ollama LLM Service

**Files:**
- Create: `backend/llm.py`

- [ ] **Step 1: Crear `backend/llm.py`**

```python
import httpx
from config import settings

SYSTEM_PROMPT = """Eres un asistente académico para estudiantes de Bachillerato (16-18 años).
Responde siempre en español. Sé claro, preciso y pedagógico.
Adapta el nivel al estudiante. Si la pregunta no es académica, redirige amablemente.
Materias: Matemáticas, Física, Lengua, Literatura, Inglés, Química, Biología, Historia, Ciencias Sociales."""

async def call_ollama(messages: list[dict]) -> str:
    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        response = await client.post(
            f"{settings.ollama_url}/api/chat",
            json=payload
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
```

- [ ] **Step 2: Verificar que Ollama responde correctamente**

```bash
python -c "
import asyncio
from llm import call_ollama
result = asyncio.run(call_ollama([{'role': 'user', 'content': 'Hola, di solo OK'}]))
print(result)
"
```

Expected: Texto con "OK" u alguna respuesta breve del modelo.

- [ ] **Step 3: Commit**

```bash
git add backend/llm.py
git commit -m "feat: Ollama LLM client with academic system prompt"
```

---

## Task 6: Endpoint /chat

**Files:**
- Create: `backend/routers/chat.py`
- Create: `backend/tests/test_chat.py`

- [ ] **Step 1: Escribir los tests**

Crear `backend/tests/test_chat.py`:

```python
from unittest.mock import AsyncMock, patch
from database import Message

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
    from datetime import datetime
    db.add(Message(user_id=42, role="user", content="prev", timestamp=datetime.now()))
    db.commit()
    with patch("routers.chat.call_ollama", new=AsyncMock(return_value="resp")):
        r = client.post("/chat", json={"token": valid_token, "message": "otra"})
    assert r.status_code == 429

def test_chat_ollama_error_returns_503(client, valid_token):
    with patch("routers.chat.call_ollama", new=AsyncMock(side_effect=Exception("timeout"))):
        r = client.post("/chat", json={"token": valid_token, "message": "hola"})
    assert r.status_code == 503
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/test_chat.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'routers'`

- [ ] **Step 3: Crear `backend/routers/__init__.py`**

```python
# vacío
```

- [ ] **Step 4: Crear `backend/routers/chat.py`**

```python
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
            detail="El asistente está ocupado, inténtalo en unos segundos"
        )

    db.add(Message(user_id=user_id, role="user", content=request.message, subject=request.subject))
    db.add(Message(user_id=user_id, role="assistant", content=answer, subject=request.subject))
    db.commit()

    suggest = request.subject in EXERCISE_SUBJECTS if request.subject else False
    return ChatResponse(response=answer, suggest_exercise=suggest)
```

- [ ] **Step 5: Crear `backend/main.py` (mínimo para poder testear)**

```python
from fastapi import FastAPI
from database import create_tables
from routers import chat, history, exercise, progress

app = FastAPI(title="Chatbot Académico API")

@app.on_event("startup")
def startup():
    create_tables()

app.include_router(chat.router)
```

- [ ] **Step 6: Ejecutar tests del chat**

```bash
pytest tests/test_chat.py -v
```

Expected: `5 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/routers/__init__.py backend/routers/chat.py backend/main.py backend/tests/test_chat.py
git commit -m "feat: POST /chat endpoint with JWT auth and rate limiting"
```

---

## Task 7: Endpoints /history y /progress

**Files:**
- Create: `backend/routers/history.py`
- Create: `backend/routers/progress.py`
- Create: `backend/tests/test_history.py`
- Create: `backend/tests/test_progress.py`

- [ ] **Step 1: Escribir tests de history**

Crear `backend/tests/test_history.py`:

```python
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
```

- [ ] **Step 2: Escribir tests de progress**

Crear `backend/tests/test_progress.py`:

```python
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
```

- [ ] **Step 3: Crear `backend/routers/history.py`**

```python
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
```

- [ ] **Step 4: Crear `backend/routers/progress.py`**

```python
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
```

- [ ] **Step 5: Añadir routers a `backend/main.py`**

```python
from fastapi import FastAPI
from database import create_tables
from routers import chat, history, exercise, progress

app = FastAPI(title="Chatbot Académico API")

@app.on_event("startup")
def startup():
    create_tables()

app.include_router(chat.router)
app.include_router(history.router)
app.include_router(progress.router)
```

- [ ] **Step 6: Ejecutar todos los tests**

```bash
pytest tests/test_history.py tests/test_progress.py -v
```

Expected: `7 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/routers/history.py backend/routers/progress.py backend/main.py backend/tests/test_history.py backend/tests/test_progress.py
git commit -m "feat: GET /history and GET /progress endpoints"
```

---

## Task 8: Endpoint /exercise

**Files:**
- Create: `backend/routers/exercise.py`
- Create: `backend/tests/test_exercise.py`

- [ ] **Step 1: Escribir los tests**

Crear `backend/tests/test_exercise.py`:

```python
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
    data = r.json()
    assert data["correct"] is True

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
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```bash
pytest tests/test_exercise.py -v
```

Expected: `FAILED — ModuleNotFoundError: No module named 'routers.exercise'`

- [ ] **Step 3: Crear `backend/routers/exercise.py`**

```python
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
        f'{{\"question\": \"<pregunta>\", \"answer\": \"<respuesta completa>\"}}'
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
```

- [ ] **Step 4: Añadir el router en `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
from routers import chat, history, exercise, progress

app = FastAPI(title="Chatbot Académico API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    create_tables()

app.include_router(chat.router)
app.include_router(history.router)
app.include_router(exercise.router)
app.include_router(progress.router)
```

- [ ] **Step 5: Ejecutar todos los tests del backend**

```bash
pytest tests/ -v --ignore=tests/test_database.py
```

Expected: `17 passed`

- [ ] **Step 6: Arrancar el backend y verificar docs**

```bash
uvicorn main:app --reload --port 8000
# Abrir: http://localhost:8000/docs
```

Expected: Swagger UI con los 5 endpoints visibles.

- [ ] **Step 7: Commit**

```bash
git add backend/routers/exercise.py backend/main.py backend/tests/test_exercise.py
git commit -m "feat: POST /exercise and POST /exercise/answer endpoints"
```

---

## Task 9: Plugin Moodle — Esqueleto + Tablas + Settings

**Files:**
- Create: `moodle-plugin/block_chatbot/version.php`
- Create: `moodle-plugin/block_chatbot/lang/en/block_chatbot.php`
- Create: `moodle-plugin/block_chatbot/db/install.xml`
- Create: `moodle-plugin/block_chatbot/settings.php`

- [ ] **Step 1: Crear `version.php`**

```php
<?php
defined('MOODLE_INTERNAL') || die();

$plugin->component = 'block_chatbot';
$plugin->version   = 2026052000;
$plugin->requires  = 2022041900; // Moodle 4.0 mínimo
$plugin->release   = '1.0.0';
$plugin->maturity  = MATURITY_ALPHA;
```

- [ ] **Step 2: Crear `lang/en/block_chatbot.php`**

```php
<?php
$string['pluginname']             = 'Asistente Académico';
$string['backend_url']            = 'URL del Backend';
$string['backend_url_desc']       = 'URL del servidor FastAPI (ej: http://localhost:8000)';
$string['jwt_secret']             = 'Secreto JWT';
$string['jwt_secret_desc']        = 'Secreto compartido entre Moodle y el backend. Debe coincidir con JWT_SECRET del .env';
$string['daily_limit']            = 'Límite diario de mensajes';
$string['daily_limit_desc']       = 'Máximo de mensajes que un alumno puede enviar por día.';
$string['block_chatbot:addinstance']   = 'Añadir bloque Asistente Académico';
$string['block_chatbot:myaddinstance'] = 'Añadir bloque Asistente Académico a Mi Moodle';
```

- [ ] **Step 3: Crear `db/install.xml`**

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<XMLDB PATH="blocks/chatbot/db" VERSION="20260520" COMMENT="Chatbot academic support tables">
  <TABLES>
    <TABLE NAME="block_chatbot_messages" COMMENT="Mensajes de chat por usuario">
      <FIELDS>
        <FIELD NAME="id"        TYPE="int"  LENGTH="10" NOTNULL="true" SEQUENCE="true"/>
        <FIELD NAME="user_id"   TYPE="int"  LENGTH="10" NOTNULL="true"/>
        <FIELD NAME="role"      TYPE="char" LENGTH="16" NOTNULL="true"/>
        <FIELD NAME="content"   TYPE="text" NOTNULL="true"/>
        <FIELD NAME="subject"   TYPE="char" LENGTH="64" NOTNULL="false"/>
        <FIELD NAME="timestamp" TYPE="int"  LENGTH="10" NOTNULL="true" DEFAULT="0"/>
      </FIELDS>
      <KEYS>
        <KEY NAME="primary" TYPE="primary" FIELDS="id"/>
      </KEYS>
      <INDEXES>
        <INDEX NAME="idx_user" UNIQUE="false" FIELDS="user_id"/>
      </INDEXES>
    </TABLE>
    <TABLE NAME="block_chatbot_exercises" COMMENT="Ejercicios por usuario">
      <FIELDS>
        <FIELD NAME="id"        TYPE="int"  LENGTH="10" NOTNULL="true" SEQUENCE="true"/>
        <FIELD NAME="user_id"   TYPE="int"  LENGTH="10" NOTNULL="true"/>
        <FIELD NAME="question"  TYPE="text" NOTNULL="true"/>
        <FIELD NAME="answer"    TYPE="text" NOTNULL="true"/>
        <FIELD NAME="correct"   TYPE="int"  LENGTH="1"  NOTNULL="false"/>
        <FIELD NAME="timestamp" TYPE="int"  LENGTH="10" NOTNULL="true" DEFAULT="0"/>
      </FIELDS>
      <KEYS>
        <KEY NAME="primary" TYPE="primary" FIELDS="id"/>
      </KEYS>
      <INDEXES>
        <INDEX NAME="idx_user" UNIQUE="false" FIELDS="user_id"/>
      </INDEXES>
    </TABLE>
    <TABLE NAME="block_chatbot_progress" COMMENT="Progreso por usuario y materia">
      <FIELDS>
        <FIELD NAME="id"        TYPE="int"  LENGTH="10"  NOTNULL="true" SEQUENCE="true"/>
        <FIELD NAME="user_id"   TYPE="int"  LENGTH="10"  NOTNULL="true"/>
        <FIELD NAME="subject"   TYPE="char" LENGTH="64"  NOTNULL="true"/>
        <FIELD NAME="topic"     TYPE="char" LENGTH="128" NOTNULL="true"/>
        <FIELD NAME="count"     TYPE="int"  LENGTH="10"  NOTNULL="true" DEFAULT="1"/>
        <FIELD NAME="last_seen" TYPE="int"  LENGTH="10"  NOTNULL="true" DEFAULT="0"/>
      </FIELDS>
      <KEYS>
        <KEY NAME="primary" TYPE="primary" FIELDS="id"/>
      </KEYS>
      <INDEXES>
        <INDEX NAME="idx_user_subject" UNIQUE="false" FIELDS="user_id,subject"/>
      </INDEXES>
    </TABLE>
  </TABLES>
</XMLDB>
```

- [ ] **Step 4: Crear `settings.php`**

```php
<?php
defined('MOODLE_INTERNAL') || die();

if ($ADMIN->fulltree) {
    $settings->add(new admin_setting_configtext(
        'block_chatbot/backend_url',
        get_string('backend_url', 'block_chatbot'),
        get_string('backend_url_desc', 'block_chatbot'),
        'http://localhost:8000',
        PARAM_URL
    ));

    $settings->add(new admin_setting_configpasswordunmask(
        'block_chatbot/jwt_secret',
        get_string('jwt_secret', 'block_chatbot'),
        get_string('jwt_secret_desc', 'block_chatbot'),
        ''
    ));

    $settings->add(new admin_setting_configtext(
        'block_chatbot/daily_limit',
        get_string('daily_limit', 'block_chatbot'),
        get_string('daily_limit_desc', 'block_chatbot'),
        '50',
        PARAM_INT
    ));
}
```

- [ ] **Step 5: Instalar plugin en Moodle**

1. Con Docker corriendo: `http://localhost:8080` → login como admin.
2. Ir a **Administración del sitio → Notificaciones**.
3. Moodle detectará el plugin nuevo y mostrará botón "Actualizar BD de Moodle".
4. Hacer clic. Verificar que se crean las 3 tablas sin errores.

- [ ] **Step 6: Configurar el plugin**

1. Ir a **Administración del sitio → Plugins → Bloques → Asistente Académico**.
2. Rellenar:
   - Backend URL: `http://localhost:8000`
   - JWT Secret: el valor de `JWT_SECRET` en el `.env`
   - Daily limit: `50`
3. Guardar.

- [ ] **Step 7: Commit**

```bash
git add moodle-plugin/
git commit -m "feat: Moodle plugin skeleton, install.xml tables, admin settings"
```

---

## Task 10: Clase del Bloque + Generación de JWT en PHP

**Files:**
- Create: `moodle-plugin/block_chatbot/block_chatbot.php`

- [ ] **Step 1: Crear `block_chatbot.php`**

```php
<?php
defined('MOODLE_INTERNAL') || die();

class block_chatbot extends block_base {

    public function init(): void {
        $this->title = get_string('pluginname', 'block_chatbot');
    }

    public function get_content(): stdClass {
        global $USER, $PAGE;

        if ($this->content !== null) {
            return $this->content;
        }

        $this->content = new stdClass();
        $this->content->text   = '';
        $this->content->footer = '';

        if (!isloggedin() || isguestuser()) {
            return $this->content;
        }

        $secret      = get_config('block_chatbot', 'jwt_secret');
        $backend_url = get_config('block_chatbot', 'backend_url');

        if (empty($secret) || empty($backend_url)) {
            $this->content->text = '<p class="text-muted">El asistente no está configurado.</p>';
            return $this->content;
        }

        $token = $this->generate_jwt((int) $USER->id, $secret);

        $PAGE->requires->js_call_amd('block_chatbot/chat', 'init', [[
            'token'      => $token,
            'backendUrl' => rtrim($backend_url, '/'),
            'userId'     => (int) $USER->id,
        ]]);

        $this->content->text = $this->render_container($token, $backend_url);
        return $this->content;
    }

    private function generate_jwt(int $user_id, string $secret): string {
        $header  = $this->b64url(json_encode(['alg' => 'HS256', 'typ' => 'JWT']));
        $payload = $this->b64url(json_encode([
            'user_id' => $user_id,
            'exp'     => time() + 3600,
            'iat'     => time(),
        ]));
        $sig = $this->b64url(hash_hmac('sha256', "$header.$payload", $secret, true));
        return "$header.$payload.$sig";
    }

    private function b64url(string $data): string {
        return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
    }

    private function render_container(string $token, string $backend_url): string {
        $token_esc   = htmlspecialchars($token, ENT_QUOTES, 'UTF-8');
        $backend_esc = htmlspecialchars($backend_url, ENT_QUOTES, 'UTF-8');
        return <<<HTML
<div id="block-chatbot-root"
     data-token="{$token_esc}"
     data-backend="{$backend_esc}">
</div>
HTML;
    }

    public function applicable_formats(): array {
        return ['course-view' => true, 'site' => true, 'my' => true];
    }

    public function has_config(): bool {
        return true;
    }

    public function instance_allow_multiple(): bool {
        return false;
    }
}
```

- [ ] **Step 2: Verificar que el bloque aparece en Moodle**

1. Ir a un curso en Moodle → **Activar edición**.
2. **Añadir bloque** → buscar "Asistente Académico".
3. Verificar que aparece el div `#block-chatbot-root` en el HTML de la página (inspección de elemento).

- [ ] **Step 3: Commit**

```bash
git add moodle-plugin/block_chatbot/block_chatbot.php
git commit -m "feat: Moodle block class with PHP JWT generation"
```

---

## Task 11: UI del Chat (Mustache + AMD JavaScript)

**Files:**
- Create: `moodle-plugin/block_chatbot/templates/chat.mustache`
- Create: `moodle-plugin/block_chatbot/amd/src/chat.js`

- [ ] **Step 1: Crear `templates/chat.mustache`**

```html
<div class="block-chatbot-wrap" style="font-family:inherit;">
    <div id="block-chatbot-messages"
         style="height:280px;overflow-y:auto;border:1px solid #dee2e6;border-radius:4px;padding:8px;background:#fafafa;margin-bottom:8px;">
        <div class="text-center text-muted" style="margin-top:100px;font-size:0.9em;">
            ¡Hola! Soy tu asistente académico.<br>¿En qué puedo ayudarte?
        </div>
    </div>

    <div style="display:flex;gap:6px;margin-bottom:6px;">
        <input id="block-chatbot-input"
               type="text"
               class="form-control form-control-sm"
               placeholder="Escribe tu pregunta..."
               style="flex:1;" />
        <button id="block-chatbot-send" class="btn btn-primary btn-sm">Enviar</button>
    </div>

    <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
        <select id="block-chatbot-subject" class="form-control form-control-sm" style="width:auto;">
            <option value="">-- Materia --</option>
            <option value="Matemáticas">Matemáticas</option>
            <option value="Física">Física</option>
            <option value="Química">Química</option>
            <option value="Biología">Biología</option>
            <option value="Lengua">Lengua</option>
            <option value="Literatura">Literatura</option>
            <option value="Inglés">Inglés</option>
            <option value="Historia">Historia</option>
            <option value="Ciencias Sociales">Ciencias Sociales</option>
        </select>
        <button id="block-chatbot-exercise-btn"
                class="btn btn-outline-secondary btn-sm"
                style="display:none;">
            Practicar ejercicio
        </button>
        <button id="block-chatbot-progress-toggle"
                class="btn btn-outline-info btn-sm">
            Mi progreso
        </button>
    </div>

    <div id="block-chatbot-progress-panel"
         style="display:none;margin-top:8px;padding:8px;border:1px solid #dee2e6;border-radius:4px;background:#fff;font-size:0.85em;">
    </div>
</div>
```

- [ ] **Step 2: Actualizar `block_chatbot.php` para usar el template**

Reemplazar el método `render_container` en `block_chatbot.php`:

```php
private function render_container(string $token, string $backend_url): string {
    global $OUTPUT;
    return $OUTPUT->render_from_template('block_chatbot/chat', []);
}
```

- [ ] **Step 3: Crear `amd/src/chat.js`**

```javascript
define([], function() {

    var token = '';
    var backendUrl = '';
    var userId = 0;
    var lastSubject = null;
    var lastTopic = null;

    function escapeHtml(text) {
        var d = document.createElement('div');
        d.appendChild(document.createTextNode(text));
        return d.innerHTML;
    }

    function appendMessage(role, content) {
        var container = document.getElementById('block-chatbot-messages');
        var isUser = role === 'user';
        var div = document.createElement('div');
        div.style.cssText = 'margin:4px 0;text-align:' + (isUser ? 'right' : 'left') + ';';
        var span = document.createElement('span');
        span.style.cssText = 'display:inline-block;padding:6px 10px;border-radius:12px;max-width:90%;word-wrap:break-word;'
            + 'background:' + (isUser ? '#cce5ff' : '#e2e3e5') + ';font-size:0.9em;';
        span.innerHTML = escapeHtml(content).replace(/\n/g, '<br>');
        div.appendChild(span);
        // Limpiar mensaje de bienvenida inicial
        var welcome = container.querySelector('.text-muted');
        if (welcome) welcome.remove();
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function setLoading(loading) {
        var btn = document.getElementById('block-chatbot-send');
        var input = document.getElementById('block-chatbot-input');
        btn.disabled = loading;
        input.disabled = loading;
        btn.textContent = loading ? '...' : 'Enviar';
    }

    async function sendMessage() {
        var input = document.getElementById('block-chatbot-input');
        var subject = document.getElementById('block-chatbot-subject').value;
        var message = input.value.trim();
        if (!message) return;

        lastSubject = subject || null;
        input.value = '';
        appendMessage('user', message);
        setLoading(true);

        try {
            var response = await fetch(backendUrl + '/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token: token, message: message, subject: lastSubject})
            });

            if (response.status === 429) {
                appendMessage('assistant', 'Has alcanzado el límite diario de mensajes. ¡Vuelve mañana!');
            } else if (!response.ok) {
                appendMessage('assistant', 'El asistente está ocupado, inténtalo en unos segundos.');
            } else {
                var data = await response.json();
                appendMessage('assistant', data.response);
                lastTopic = message.substring(0, 60);
                if (data.suggest_exercise) {
                    document.getElementById('block-chatbot-exercise-btn').style.display = 'inline-block';
                }
            }
        } catch (e) {
            appendMessage('assistant', 'No se pudo conectar con el asistente.');
        }

        setLoading(false);
    }

    async function loadProgress() {
        var panel = document.getElementById('block-chatbot-progress-panel');
        try {
            var r = await fetch(backendUrl + '/progress/' + userId + '?token=' + encodeURIComponent(token));
            var data = await r.json();
            panel.innerHTML = '<strong>Tu progreso:</strong><br>'
                + 'Preguntas realizadas: ' + data.total_questions + '<br>'
                + 'Ejercicios completados: ' + data.total_exercises + '<br>'
                + 'Ejercicios correctos: ' + data.correct_exercises + '<br>'
                + 'Mensajes hoy: ' + data.messages_today;
        } catch (e) {
            panel.innerHTML = '<em>No se pudo cargar el progreso.</em>';
        }
    }

    return {
        init: function(params) {
            token      = params.token;
            backendUrl = params.backendUrl;
            userId     = params.userId;

            document.getElementById('block-chatbot-send').addEventListener('click', sendMessage);
            document.getElementById('block-chatbot-input').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') sendMessage();
            });

            document.getElementById('block-chatbot-progress-toggle').addEventListener('click', function() {
                var panel = document.getElementById('block-chatbot-progress-panel');
                if (panel.style.display === 'none') {
                    panel.style.display = 'block';
                    loadProgress();
                } else {
                    panel.style.display = 'none';
                }
            });

            document.getElementById('block-chatbot-exercise-btn').addEventListener('click', async function() {
                if (!lastTopic) return;
                this.disabled = true;
                try {
                    var r = await fetch(backendUrl + '/exercise', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({token: token, topic: lastTopic, subject: lastSubject})
                    });
                    var data = await r.json();
                    appendMessage('assistant', 'Ejercicio: ' + data.question);
                    this.style.display = 'none';
                } catch (e) {
                    appendMessage('assistant', 'No se pudo generar el ejercicio.');
                }
                this.disabled = false;
            });
        }
    };
});
```

- [ ] **Step 4: Construir el módulo AMD**

En Moodle, los módulos AMD necesitan ser "compilados" (minificados). Para desarrollo se puede usar el modo no-minificado:

1. Ir a **Administración del sitio → Desarrollo → Purgar todas las cachés**.
2. Activar **Depuración de JavaScript** en Administración del sitio → Desarrollo → JavaScript.
3. Recargar la página con el bloque — el navegador cargará `amd/src/chat.js` directamente.

- [ ] **Step 5: Prueba manual de la UI**

1. Login como estudiante en Moodle (`http://localhost:8080`).
2. Navegar a un curso con el bloque añadido.
3. Escribir "¿Cuánto es la derivada de x²?" y enviar.
4. Verificar que aparece respuesta del LLM.
5. Hacer clic en "Practicar ejercicio" (si aparece).
6. Hacer clic en "Mi progreso" y verificar que muestra datos.

- [ ] **Step 6: Commit**

```bash
git add moodle-plugin/block_chatbot/templates/ moodle-plugin/block_chatbot/amd/
git commit -m "feat: chat UI with Mustache template and AMD JavaScript"
```

---

## Task 12: PHPUnit Tests del Plugin

**Files:**
- Create: `moodle-plugin/block_chatbot/tests/phpunit/block_chatbot_test.php`

- [ ] **Step 1: Crear `tests/phpunit/block_chatbot_test.php`**

```php
<?php
namespace block_chatbot\tests;

defined('MOODLE_INTERNAL') || die();

global $CFG;
require_once($CFG->dirroot . '/blocks/chatbot/block_chatbot.php');

class block_chatbot_test extends \advanced_testcase {

    protected function setUp(): void {
        parent::setUp();
        $this->resetAfterTest(true);
    }

    public function test_jwt_has_three_parts(): void {
        $block  = new \block_chatbot();
        $method = new \ReflectionMethod($block, 'generate_jwt');
        $method->setAccessible(true);

        $token = $method->invoke($block, 42, 'test-secret');
        $parts = explode('.', $token);

        $this->assertCount(3, $parts, 'JWT debe tener exactamente 3 partes separadas por punto');
    }

    public function test_jwt_payload_contains_user_id(): void {
        $block  = new \block_chatbot();
        $method = new \ReflectionMethod($block, 'generate_jwt');
        $method->setAccessible(true);

        $token   = $method->invoke($block, 99, 'test-secret');
        $parts   = explode('.', $token);
        $padding = strlen($parts[1]) % 4;
        if ($padding) {
            $parts[1] .= str_repeat('=', 4 - $padding);
        }
        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+/')), true);

        $this->assertEquals(99, $payload['user_id']);
        $this->assertGreaterThan(time(), $payload['exp']);
    }

    public function test_jwt_different_users_produce_different_tokens(): void {
        $block  = new \block_chatbot();
        $method = new \ReflectionMethod($block, 'generate_jwt');
        $method->setAccessible(true);

        $token1 = $method->invoke($block, 1, 'secret');
        $token2 = $method->invoke($block, 2, 'secret');

        $this->assertNotEquals($token1, $token2);
    }

    public function test_block_empty_content_for_guest(): void {
        $this->setGuestUser();
        $block = new \block_chatbot();
        $block->init();
        $content = $block->get_content();

        $this->assertEmpty($content->text, 'Usuarios invitados no deben ver el chatbot');
    }

    public function test_applicable_formats_includes_course(): void {
        $block   = new \block_chatbot();
        $formats = $block->applicable_formats();

        $this->assertArrayHasKey('course-view', $formats);
        $this->assertTrue($formats['course-view']);
    }
}
```

- [ ] **Step 2: Ejecutar los tests PHPUnit**

```bash
# Desde la raíz de Moodle (dentro del contenedor Docker):
docker exec -it <moodle-container> bash
cd /bitnami/moodle
php admin/tool/phpunit/cli/init.php
vendor/bin/phpunit blocks/chatbot/tests/phpunit/block_chatbot_test.php --testdox
```

Expected:
```
block_chatbot
 ✓ Jwt has three parts
 ✓ Jwt payload contains user id
 ✓ Jwt different users produce different tokens
 ✓ Block empty content for guest
 ✓ Applicable formats includes course
```

- [ ] **Step 3: Commit final**

```bash
git add moodle-plugin/block_chatbot/tests/
git commit -m "test: PHPUnit tests for block_chatbot JWT and content rendering"
```

---

## Task 13: Verificación End-to-End

- [ ] **Step 1: Arrancar todos los servicios**

```bash
# Terminal 1 — Moodle + DB
cd chatbot-moodle && docker compose up

# Terminal 2 — Backend FastAPI
cd chatbot-moodle/backend
uvicorn main:app --reload --port 8000

# Terminal 3 — Ollama (si no está ya corriendo)
ollama serve
```

- [ ] **Step 2: Test manual del flujo completo**

1. Login en Moodle como estudiante.
2. Ir a un curso con el bloque activo.
3. Enviar pregunta: `"¿Cuál es la fórmula de la energía cinética?"` con materia `Física`.
4. Verificar respuesta del LLM en el chat.
5. Hacer clic en "Practicar ejercicio" y verificar que aparece un ejercicio de Física.
6. Abrir "Mi progreso" y verificar contadores.
7. Login como diferente usuario y verificar que el historial está separado.

- [ ] **Step 3: Test de límite de mensajes**

Cambiar temporalmente `daily_limit` a `2` en la configuración del plugin.
Enviar 3 mensajes. El tercero debe mostrar "Has alcanzado el límite diario".
Restaurar el límite a 50.

- [ ] **Step 4: Test de Ollama caído**

```bash
# Parar Ollama
pkill ollama
```

Enviar un mensaje en el chatbot. Debe aparecer "El asistente está ocupado, inténtalo en unos segundos." sin que Moodle falle.

Reiniciar Ollama: `ollama serve`

- [ ] **Step 5: Ejecutar suite completa de tests del backend**

```bash
cd chatbot-moodle/backend
pytest tests/ -v
```

Expected: Todos los tests en verde.

- [ ] **Step 6: Commit final del proyecto**

```bash
git add .
git commit -m "feat: complete academic chatbot Moodle plugin v1.0.0"
```

---

## Resumen de Comandos Útiles

```bash
# Arrancar entorno de desarrollo
docker compose up -d
uvicorn main:app --reload --port 8000

# Tests backend
cd backend && pytest tests/ -v

# Tests PHP (dentro del contenedor Moodle)
docker exec -it <container> vendor/bin/phpunit blocks/chatbot/tests/

# Purgar caché de Moodle (después de cambios en JS/templates)
# Administración del sitio → Desarrollo → Purgar todas las cachés

# Ver logs del backend
uvicorn main:app --reload --port 8000 --log-level debug
```
