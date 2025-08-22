# backend/services/pocketbase.py
import httpx
from typing import Dict, Any, Optional
from utils.config import settings
from models.tenant import TenantCreate

# PocketBase Collections (adjust if different)
TENANT_COLLECTION = "tenants"
USER_COLLECTION = "users"

class PocketBaseService:
    def __init__(self):
        self.base_url = settings.pb_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=10.0)

    async def create_tenant(self, tenant_data: TenantCreate) -> Dict[str, Any]:
        """
        Create a new tenant in PocketBase
        """
        tenant_payload = {
            "name": tenant_data.name,
            "plan": tenant_data.plan,
            "testing_types": ",".join(tenant_data.testing_types),  # CSV string
            "team_size": tenant_data.team_size,
            "admin_email": tenant_data.admin_email,
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/collections/{TENANT_COLLECTION}/records",
                json=tenant_payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json()
            raise Exception(f"PocketBase tenant creation failed: {error_detail}")
        except httpx.RequestError as e:
            raise Exception(f"Request error connecting to PocketBase: {str(e)}")

    async def create_user(self, email: str, tenant_id: str) -> Dict[str, Any]:
        """
        Create a user in PocketBase and send email verification
        """
        user_payload = {
            "email": email,
            "tenant_id": tenant_id,
            "sendEmailVerification": True  # PocketBase auto-sends verification
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/collections/{USER_COLLECTION}/records",
                json=user_payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json()
            # If user already exists, return existing user
            if e.response.status_code == 409:
                return await self.get_user_by_email(email)
            raise Exception(f"User creation failed: {error_detail}")
        except httpx.RequestError as e:
            raise Exception(f"Request error: {str(e)}")

    async def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """
        Fetch user by email
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/collections/{USER_COLLECTION}/records",
                params={"filter": f'email="{email}"'}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("items"):
                return data["items"][0]
            raise Exception("User not found")
        except Exception as e:
            raise Exception(f"Error fetching user: {str(e)}")

    async def close(self):
        await self.client.aclose()

# Global instance
pb_service = PocketBaseService()