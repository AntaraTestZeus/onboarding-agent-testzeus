# account_manager.py
import os
from pocketbase import PocketBase
from pocketbase.utils import ClientResponseError
from dotenv import load_dotenv
import random
import string

load_dotenv()
AGENT_CONFIG_ID = os.getenv("DEFAULT_AGENT_CONFIG_ID")

# --- Configuration (Loaded from .env file) ---
POCKETBASE_URL = os.getenv("POCKETBASE_URL")
ADMIN_EMAIL = os.getenv("POCKETBASE_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("POCKETBASE_ADMIN_PASSWORD")

# --- Initialize PocketBase Client ---
try:
    client = PocketBase(POCKETBASE_URL)
    client.admins.auth_with_password(ADMIN_EMAIL, ADMIN_PASSWORD)
    print("INFO: Successfully authenticated with PocketBase admin credentials.")
except Exception as e:
    print(f"FATAL: Could not connect or authenticate with PocketBase. Please check your .env settings and that the account is a true admin. Error: {e}")
    client = None

def generate_temp_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

def create_or_get_tenant(email: str, password: str, password_confirm: str) -> str | None:
    if not client:
        return None
    try:
        existing = client.collection("tenants").get_list(1, 1, {"filter": f"email = '{email}'"}).items
        if existing:
            print(f"INFO: Found existing tenant for '{email}'")
            return existing[0].id

        print(f"INFO: Creating new tenant for '{email}'...")
        tenant = client.collection("tenants").create({
            "email": email,
            "password": password,
            "passwordConfirm": password_confirm,
            "default_agent_config": AGENT_CONFIG_ID
        })
        return tenant.id
    except ClientResponseError as e:
        print(f"PocketBase error while creating tenant: {e.data}")
        return None
    except Exception as e:
        print(f"Unexpected error creating tenant: {e}")
        return None

def user_exists(email: str) -> bool:
    try:
        users = client.collection("users").get_list(1, 1, {"filter": f"email = '{email}'"}).items
        return len(users) > 0
    except ClientResponseError as e:
        if e.status == 404:
            return False
        print(f"Error checking user: {e}")
        return True  # Assume true to avoid duplicate

def create_account(org_email: str, user_name: str, user_email: str, user_role: str, password: str, password_confirm: str) -> tuple[bool, str]:
    if not client:
        return False, "Account system unavailable."

    if password != password_confirm:
        return False, "Password and confirm password do not match."

    # ✅ Step 1: Use org_email or fallback to user_email
    tenant_email = org_email or user_email

    # ✅ Step 2: Get or create tenant
    tenant_id = create_or_get_tenant(tenant_email, password, password_confirm)
    if not tenant_id:
        return False, "Failed to setup tenant workspace."

    # ✅ Step 3: Check for duplicate user
    if user_exists(user_email):
        return False, f"User with email {user_email} already exists."

    # ✅ Step 4: Create user
    try:
        new_user = client.collection("users").create({
            "email": user_email,
            "password": password,
            "passwordConfirm": password_confirm,
            "name": user_name,
            "role": user_role,
            "tenant": tenant_id,
            "emailVisibility": True,
        })
        print(f"User '{new_user.id}' created and linked to tenant '{tenant_id}'.")
        # For now, just print instead of sending email
        print(f"Welcome email would be sent to {user_email} with password: {password}")
        return True, f"Welcome, {user_name}! Your TestZeus account is ready. Check your email: {user_email}."
    except Exception as e:
        print(f"ERROR during account creation: {e}")
        return False, "Unexpected error occurred. Our team will follow up."