# backend/routers/tenants.py
from fastapi import APIRouter, Depends, HTTPException
from models.tenant import TenantCreate, TenantResponse
from services.pocketbase import pb_service

router = APIRouter(prefix="/tenants", tags=["tenants"])

@router.post("/", response_model=dict)
async def create_tenant(tenant: TenantCreate):
    try:
        # 1. Create tenant
        tenant_record = await pb_service.create_tenant(tenant)
        tenant_id = tenant_record["id"]

        # 2. Create user with verification email
        user_record = await pb_service.create_user(tenant.admin_email, tenant_id)

        return {
            "success": True,
            "tenant": tenant_record,
            "user": user_record,
            "message": "Tenant created and verification email sent!"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))