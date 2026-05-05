from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from backend.database import get_db
from backend.models.user import User, UserRole
from backend.models.patient import PatientProfile
from backend.utils.security import hash_password, verify_password, create_access_token
from backend.utils.logging import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ActivateRequest(BaseModel):
    access_code: str
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str


@router.post("/register", response_model=TokenResponse)
async def register_patient(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=req.email,
        phone=req.phone,
        hashed_password=hash_password(req.password),
        role=UserRole.patient,
    )
    db.add(user)
    await db.flush()

    profile = PatientProfile(user_id=user.id, full_name=req.name)
    db.add(profile)
    
    await log_action(db, user.id, "register", "auth", f"Registered new patient: {req.email}")
    await db.commit()

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return TokenResponse(access_token=token, role=user.role.value, user_id=user.id)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token({"sub": user.id, "role": user.role.value})
    await log_action(db, user.id, "login", "auth", f"Successful login for {req.email}")
    await db.commit()
    return TokenResponse(access_token=token, role=user.role.value, user_id=user.id)


@router.post("/activate", response_model=TokenResponse)
async def activate_account(req: ActivateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.access_code == req.access_code))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid access code")

    existing_email = await db.execute(
        select(User).where(User.email == req.email, User.id != user.id)
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already in use")

    user.email = req.email
    user.hashed_password = hash_password(req.password)
    user.access_code = None
    
    await log_action(db, user.id, "activate", "auth", f"Activated account for {req.email}")
    await db.commit()

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return TokenResponse(access_token=token, role=user.role.value, user_id=user.id)


@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    return {"status": "ok", "service": "HospitalIQ API"}
