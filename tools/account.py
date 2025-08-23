# tools/account.py
"""
GPT-5 Custom Tool: create_tenant_and_team
Purpose: Create tenant + users via account_manager.py
Input: Raw text in format:
    admin_email: alice@acme.com
    plan: enterprise
    teammate_emails: bob@acme.com, carol@acme.com
Output: "SUCCESS: ..." or "ERROR: ..."
"""

from typing import Dict, List
import re


# Import your real account manager
try:
    from account_manager import create_account, user_exists
except ImportError:
    # Mock for demo
    def create_account(org_email, user_name, user_email, user_role, password, password_confirm):
        return True, f"Mock: {user_name} created"
    def user_exists(email):
        return False


def parse_input(input_text: str) -> Dict[str, str]:
    """Parse raw input text into dict"""
    lines = [line.strip() for line in input_text.split("\n") if ":" in line]
    params = {}
    for line in lines:
        k, v = line.split(":", 1)
        params[k.strip().lower()] = v.strip()
    return params


def tool_create_tenant_and_team(input_text: str) -> str:
    """
    Called by GPT-5 via free-form tool call.
    Input: 
        admin_email: alice@acme.com
        plan: enterprise
        teammate_emails: bob@acme.com, carol@acme.com
    Output: "SUCCESS: ..." or "ERROR: ..."
    """
    try:
        params = parse_input(input_text)
        admin_email = params.get("admin_email")
        plan = params.get("plan", "oss")
        teammate_emails = [e.strip() for e in params.get("teammate_emails", "").split(",") if e.strip()]

        if not admin_email:
            return "ERROR: Missing admin_email"

        # Create admin
        success, msg = create_account(
            org_email=admin_email,
            user_name=admin_email.split("@")[0].title(),
            user_email=admin_email,
            user_role="admin",
            password="temp_pass_123!",
            password_confirm="temp_pass_123!"
        )
        if not success:
            return f"ERROR: {msg}"

        # Add teammates
        invited = 0
        for te_email in teammate_emails:
            if not user_exists(te_email):
                _, _ = create_account(
                    org_email=admin_email,
                    user_name=te_email.split("@")[0].title(),
                    user_email=te_email,
                    user_role="member",
                    password="temp_pass_123!",
                    password_confirm="temp_pass_123!"
                )
                invited += 1

        return f"SUCCESS: Tenant created for {admin_email}. {invited} teammates invited."

    except Exception as e:
        return f"ERROR: Failed to parse or execute: {str(e)}"