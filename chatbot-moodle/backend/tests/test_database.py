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
        assert msg.content == "hola"

def test_exercise_model():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from database import Base, Exercise
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        ex = Exercise(user_id=2, question="¿Cuánto es 2+2?", answer="4")
        db.add(ex)
        db.commit()
        db.refresh(ex)
        assert ex.id is not None
        assert ex.correct is None
