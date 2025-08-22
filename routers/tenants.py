# backend/routers/tenants.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/")
def create_tenant():
    return {"message": "Tenant creation placeholder"}