import jwt
import logging
from os import getenv
from datetime import datetime, timedelta
from fastapi import HTTPException

SECRET = getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
EXPIRES = getenv("JWT_TOKEN_EXPIRES_MINUTES") if getenv("JWT_TOKEN_EXPIRES_MINUTES") is not None else 500


def generate_token(payload: dict = {}, set_expiry: bool = False):
    if set_expiry:
        payload.update({
            "exp": datetime.utcnow() + timedelta(minutes=EXPIRES)
        })
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    return token


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET, algorithm=ALGORITHM)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )
