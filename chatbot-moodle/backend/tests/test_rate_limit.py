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
