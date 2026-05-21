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
