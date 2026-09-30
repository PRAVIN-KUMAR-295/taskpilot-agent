import datetime
import sqlite3
from typing import Optional, Dict, Any
import bcrypt
import jwt
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES
    from database.connection import get_db
    from database.repositories import UserRepository
except ImportError:
    from backend.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES
    from backend.database.connection import get_db
    from backend.database.repositories import UserRepository


security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: int, email: str) -> str:
    """Generates a signed JWT access token."""
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=JWT_EXPIRATION_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.datetime.now(datetime.timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    conn: sqlite3.Connection = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """
    Returns authenticated user if token is valid.
    If no token is supplied, returns the default demo user (ID 1) to enable seamless hackathon demo experience.
    """
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and "sub" in payload:
            user = UserRepository.get_by_id(conn, int(payload["sub"]))
            if user:
                return user

    # Fallback to demo user for seamless UX/testing
    demo_user = UserRepository.get_by_email(conn, "demo@taskpilot.ai")
    if demo_user:
        return demo_user
    # If not found, retrieve first user
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY id ASC LIMIT 1")
    row = cursor.fetchone()
    return dict(row) if row else None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    conn: sqlite3.Connection = Depends(get_db)
) -> Dict[str, Any]:
    """Strict authentication dependency returning 401 if unauthenticated."""
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication credentials were not provided.")

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")

    user = UserRepository.get_by_id(conn, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User account not found.")

    return user
