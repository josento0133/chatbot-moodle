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
        algorithm="HS256",
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
