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
def client(db):
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
