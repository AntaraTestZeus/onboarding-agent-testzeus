# services/email_validator.py
from openai import OpenAI
import os
import re

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class EmailValidator:
    def __init__(self):
        self.blocklist = {"tempmail.com", "10minutemail.net", "mailinator.com"}
        self.personal_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}

    def validate_email(self, email: str) -> dict:
        # 1. Basic format check
        if not re.match(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
            return {"is_valid": False, "reason": "Invalid format"}

        domain = email.split("@")[1].lower()

        # 2. Blocklist check (fast)
        if domain in self.blocklist:
            return {"is_valid": False, "reason": "Disposable email not allowed"}

        # 3. Personal domain? (warn, don't block)
        if domain in self.personal_domains:
            return {"is_valid": True, "warning": "Personal email — use company email if possible"}

        # 4. Unknown domain? Ask GPT-5
        if not self.is_domain_known(domain):
            return self.llm_validate_email(email)

        return {"is_valid": True, "reason": "Valid business email"}

    def is_domain_known(self, domain: str) -> bool:
        """Check if domain is in your known list (or via WHOIS, DNS, etc.)"""
        # In prod: call DNS lookup or company DB
        # For hackathon: mock
        known_domains = {"acme.com", "testzeus.com", "google.com"}
        return domain in known_domains or domain.endswith(".com")

    def llm_validate_email(self, email: str) -> dict:
        """Use GPT-5 to validate ambiguous emails"""
        try:
            response = client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are an email validation assistant. Answer only YES or NO."},
                    {"role": "user", "content": f"Is '{email}' a valid business/work email address? Answer only YES or NO."}
                ],
                max_tokens=10
            )

            # Extract YES/NO
            content = response.choices[0].message.content.strip().lower()
            is_valid = "yes" in content

            return {
                "is_valid": is_valid,
                "reason": "LLM validated" if is_valid else "LLM flagged as suspicious"
            }
        except Exception as e:
            return {"is_valid": False, "reason": f"Validation failed: {str(e)}"}

# Create an instance for the chatbot to use
email_validator = EmailValidator()