from fastapi import FastAPI, Depends
import logging

# Import your routers and security utilities
from burrow.app.api.v1 import hello, auth
from burrow.app.core.security import require_app_key, require_current_user

# ---- Logging setup ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("burrow")

# ---- App instance ----
app = FastAPI(title="Burrow API", version="0.2.0")

# ---- Public: health ----
@app.get("/health")
def health_check():
    logger.info("Health check called")
    return {"status": "ok", "service": "burrow"}

# ---- Auth routes (public to allow login) ----
# These endpoints handle login and token issuance
app.include_router(auth.router, prefix="/api/v1/auth")

# ---- Hello routes (require API key at router level) ----
# Each endpoint inside hello.router can still decide if it also requires JWT
app.include_router(
    hello.router,
    prefix="/api/v1/hello",
    dependencies=[Depends(require_app_key)],  # enforce API key for all hello routes
)

# ---- Example: client-only endpoint (API key required, no JWT) ----
@app.get("/api/v1/client-info")
def client_info(client: str = Depends(require_app_key)):
    logger.info(f"Client-only endpoint accessed by {client}")
    return {"client": client, "info": "This endpoint requires only an API key"}

# ---- Example: user-only endpoint (JWT required, no API key) ----
@app.get("/api/v1/profile")
def profile(user: str = Depends(require_current_user)):
    logger.info(f"Profile endpoint accessed by user {user}")
    return {"user": user, "profile": f"This is {user}'s profile data"}

# ---- Example: secure endpoint (requires BOTH API key + JWT) ----
@app.get("/api/v1/secure-data")
def secure_data(
    client: str = Depends(require_app_key),
    user: str = Depends(require_current_user),
):
    logger.info(f"Secure endpoint accessed by client={client}, user={user}")
    return {
        "message": "You passed both gates!",
        "client": client,
        "user": user,
        "data": {"secret": "🍌 jungle treasure"},
    }
