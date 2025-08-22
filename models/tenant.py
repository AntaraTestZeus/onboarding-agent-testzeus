# backend/models/tenant.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional

class TenantCreate(BaseModel):
    name: str
    plan: str  # "oss" or "enterprise"
    testing_types: List[str]  # e.g., ["web", "api"]
    team_size: int
    admin_email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corp",
                "plan": "enterprise",
                "testing_types": ["web", "api"],
                "team_size": 25,
                "admin_email": "alice@acme.com"
            }
        }

class TenantResponse(BaseModel):
    id: str
    name: str
    plan: str
    team_size: int
    created: str

    class Config:
        from_attributes = True