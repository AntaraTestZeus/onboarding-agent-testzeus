# backend/routers/verify.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/verify-email")
def verify_email(token: str):
    return {"token": token, "message": "Email verification placeholder"}