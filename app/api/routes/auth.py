from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service, get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenOut, UserOut
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest, service: AuthService = Depends(get_auth_service)):
    return service.signup(data)


@router.post("/login", response_model=TokenOut)
def login(data: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return TokenOut(access_token=service.login(data))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user