from fastapi import APIRouter, Depends
from burrow.app.core.security import require_app_key, require_current_user

router = APIRouter(tags=["hello"])

@router.get("/")
def say_hello(
    client: str = Depends(require_app_key),
    user: str = Depends(require_current_user),
):
    return {"message": f"Welcome to Burrow, {user}!", "client": client}
