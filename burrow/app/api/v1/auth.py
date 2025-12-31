from datetime import timedelta
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from burrow.app.core.security import authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from burrow.app.core.security import require_app_key

router = APIRouter(tags=["auth"])

@router.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), client: str = Depends(require_app_key)
):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        return {"error": "invalid credentials"}
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(subject=user, expires_delta=access_token_expires, client=client)
    return {"access_token": token, "token_type": "bearer"}
