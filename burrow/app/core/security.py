from datetime import datetime, timedelta
from typing import Optional

from fastapi import Security, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.api_key import APIKeyHeader
from jose import jwt, JWTError
from passlib.context import CryptContext
import logging

# ---- Logging setup ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- App API keys (per-client) ----
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# In production, store hashed keys in a DB and load into memory/cache.
APP_KEYS = {
    "app1-key-123": "App One",
    "app2-key-456": "App Two",
}

def require_app_key(api_key: str = Security(api_key_header)) -> str:
    logger.info(f"Checking API key: {api_key}")
    if api_key in APP_KEYS:
        logger.info(f"API key valid for client: {APP_KEYS[api_key]}")
        return APP_KEYS[api_key]
    logger.warning("Invalid or missing API Key")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )

# ---- User JWTs (per-user) ----
SECRET_KEY = "change-this-in-.env"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Demo user store (use a real DB in production)
# Pre-hash the password once and paste the hash here.
# Example Argon2 hash for "burrow-secret"
DEMO_USERS = {
    "solo": pwd_context.hash("burrow-secret"),  # <-- pre-hash once, not on every run in prod
    "monkey": pwd_context.hash("banana123")
}

def authenticate_user(username: str, password: str) -> Optional[str]:
    logger.info(f"Authenticating user: {username}")
    hashed = DEMO_USERS.get(username)
    if not hashed:
        logger.warning(f"User '{username}' not found")
        return None
    if not pwd_context.verify(password, hashed):
        logger.warning(f"Password verification failed for user '{username}'")
        return None
    logger.info(f"User '{username}' authenticated successfully")
    return username

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": subject, "exp": expire}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Access token created for user '{subject}', expires at {expire}")
    return token

def require_current_user(token: str = Depends(oauth2_scheme)) -> str:
    logger.info("Validating JWT token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject: str = payload.get("sub")
        if subject is None:
            logger.error("JWT payload missing subject")
            raise JWTError("No subject")
        logger.info(f"Token valid for user '{subject}'")
        return subject
    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
