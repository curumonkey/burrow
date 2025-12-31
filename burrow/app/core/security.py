from datetime import datetime, timedelta
from typing import Optional, Tuple
import os

from fastapi import Security, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.api_key import APIKeyHeader
from jose import jwt, JWTError
from passlib.context import CryptContext
import logging

# ---- Logging setup ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_env_file_if_present() -> None:
    """Attempt to load environment variables from a .env file.

    Prefer `python-dotenv` if installed; otherwise fall back to a tiny parser.
    This lets developers set `SECRET_KEY` in a local `.env` file without
    adding a hard dependency.
    """
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
        logger.info("Loaded environment from .env using python-dotenv")
        return
    except Exception:
        # fallback to manual loader
        env_path = os.path.join(os.getcwd(), ".env")
        if not os.path.exists(env_path):
            return
        try:
            logger.info("Loading .env from %s", env_path)
            with open(env_path, "r", encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('\"').strip("\'")
                    if k and v:
                        os.environ.setdefault(k, v)
        except Exception:
            logger.exception("Failed to load .env file")


# Try to load .env before reading SECRET_KEY
_load_env_file_if_present()

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
# Load secret from environment. In production you should set SECRET_KEY.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Allow an explicit dev override to avoid failing in local dev: set DEV_INSECURE_KEY=1
    if os.getenv("DEV_INSECURE_KEY", "0") == "1":
        logging.getLogger(__name__).warning(
            "SECRET_KEY not set; using insecure fallback for development (DEV_INSECURE_KEY=1)."
        )
        SECRET_KEY = "change-this-in-.env"
    else:
        raise RuntimeError(
            "SECRET_KEY is not set. Set the SECRET_KEY environment variable or set DEV_INSECURE_KEY=1 for local development."
        )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Demo user store (use a real DB in production). Keep plaintext here for convenience
# but hash only when first used to avoid hashing at import-time.
_DEMO_USERS_PLAINTEXT = {
    "solo": "burrow-secret",
    "monkey": "banana123",
}
_DEMO_USERS_HASHED: dict[str, str] = {}

def _get_hashed_password(username: str) -> Optional[str]:
    """Return cached hashed password for `username`, computing and caching it on first access."""
    if username in _DEMO_USERS_HASHED:
        return _DEMO_USERS_HASHED[username]
    plain = _DEMO_USERS_PLAINTEXT.get(username)
    if plain is None:
        return None
    hashed = pwd_context.hash(plain)
    _DEMO_USERS_HASHED[username] = hashed
    return hashed

def authenticate_user(username: str, password: str) -> Optional[str]:
    logger.info(f"Authenticating user: {username}")
    hashed = _get_hashed_password(username)
    if not hashed:
        logger.warning(f"User '{username}' not found")
        return None
    if not pwd_context.verify(password, hashed):
        logger.warning(f"Password verification failed for user '{username}'")
        return None
    logger.info(f"User '{username}' authenticated successfully")
    return username

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None, client: Optional[str] = None) -> str:
    """Create a JWT access token. If `client` is provided, include it in the token payload
    so tokens can be bound to a specific client application.
    """
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": subject, "exp": expire}
    if client:
        to_encode["client"] = client
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Access token created for user '{subject}', client='{client}', expires at {expire}")
    return token


def require_current_user_for_client(client: str = Depends(require_app_key), token: str = Depends(oauth2_scheme)) -> Tuple[str, str]:
    """Dependency which validates a JWT and ensures it was issued for the provided `client`.

    Returns a tuple `(client, subject)` on success. Raises HTTP errors on failure.
    """
    logger.info("Validating JWT token for client '%s'", client)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject: str = payload.get("sub")
        token_client: Optional[str] = payload.get("client")
        if subject is None:
            logger.error("JWT payload missing subject")
            raise JWTError("No subject")
        if token_client is None:
            logger.error("JWT token missing client claim")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token not bound to any client",
            )
        if token_client != client:
            logger.warning("Token client '%s' does not match request client '%s'", token_client, client)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token not valid for this client",
            )
        logger.info("Token valid for user '%s' and client '%s'", subject, client)
        return (client, subject)
    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

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
