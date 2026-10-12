from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead
from fastapi import Request
from app import ratelimit
from app.security import create_token, fake_verify, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    ratelimit.register_limiter.check(ratelimit.client_ip(request))
    email = payload.email.strip().lower()
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not register with these details")
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ratelimit.login_ip_limiter.check(ratelimit.client_ip(request))
    ratelimit.login_email_limiter.check(payload.email.strip().lower())
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None:
        fake_verify()
        ok = False
    else:
        ok = verify_password(payload.password, user.password_hash)
    if not ok:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return TokenResponse(access_token=create_token(user.id))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user
