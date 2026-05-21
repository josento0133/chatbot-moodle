from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
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
    role      = Column(String(16), nullable=False)
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
