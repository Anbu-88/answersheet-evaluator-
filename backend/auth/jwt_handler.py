"""
ExamAI - JWT Token Handler
Creates and verifies JWT tokens with role-based claims.
"""

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS


def create_access_token(user_id: int, email: str, role: str) -> str:
    """Create a JWT token with user claims."""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """
    Verify and decode a JWT token.
    Returns the payload dict or None if invalid.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
