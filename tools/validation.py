# tools/validation.py
"""
GPT-5 Tool: validate_email
Validates email format, disposable domains, and competitor emails using LLM
"""

import re
from openai import OpenAI
from utils.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Disposable domains (still use fast blocklist for these)
DISPOSABLE_DOMAINS = settings.blocklist


def is_valid_domain(email: str) -> str:
    # 1. Format check
    if not re.match(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
        return f"INVALID: Invalid format"

    domain = email.split("@")[1].lower()

    # 2. Disposable check (fast)
    if domain in DISPOSABLE_DOMAINS:
        return f"INVALID: Disposable domain {domain} not allowed"

    # 3. Competitor check via GPT-5
    try:
        competitor_prompt = f"""
You are an email validation expert at TestZeus. Your job is to detect if an email belongs to a competitor.

Here is the list of known competitor email domains:

| Tool / Platform         | Email Domain                       |
|-------------------------|------------------------------------|
| Tricentis Tosca         | @tricentis.com                     |
| Katalon Platform        | @katalon.com                       |
| Functionize             | @functionize.com                   |
| TestRigor               | @testrigor.com                     |
| CodiumAI (Qodo)         | @qodo.ai or @codium.ai             |
| Eggplant (Keysight)     | @keysight.com                      |
| Applitools              | @applitools.com                    |
| Testim                  | @testim.io                         |
| Mabl                    | @mabl.com                          |
| Copado                  | @copado.com                        |
| BrowserStack            | @browserstack.com                  |
| Sastra Robotics         | @sastrarobotics.com                |
| Testsigma               | @testsigma.com                     |
| QF-Test                 | @qfs.de                            |

Is '{email}' from a competitor company? Answer only YES or NO.
"""

        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=competitor_prompt,
            reasoning={"effort": "minimal"},
            text={"verbosity": "low"}
        )

        # Extract YES/NO
        content = ""
        for item in response.output:
            if hasattr(item, "content"):
                for c in item.content:
                    if hasattr(c, "text"):
                        content += c.text

        if "yes" in content.strip().lower():
            return f"INVALID: Competitor email {email} not allowed"

    except Exception as e:
        # If LLM fails, allow but log
        print(f"LLM competitor check failed: {e}")

    return f"VALID: {email}"