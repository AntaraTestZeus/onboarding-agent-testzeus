# backend/routers/chatbot.py
from fastapi import APIRouter, Request
from openai import OpenAI
import os
import random
import traceback
import json
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import openai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path

# Add the new modules to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import the new modules
try:
    from modules.screenshot import capture_screenshot_sync
    from modules.gpt5_gherkin import GPT5GherkinGenerator
    from modules.ocr_utils import Qwen2VLOCR
    from modules.prompts import (
        GHERKIN_PROMPT, 
        LOGIN_GHERKIN_PROMPT, 
        DASHBOARD_GHERKIN_PROMPT,
        FORM_GHERKIN_PROMPT,
        ECOMMERCE_GHERKIN_PROMPT
    )
    NEW_FEATURES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: New features not available: {e}")
    NEW_FEATURES_AVAILABLE = False

# Add URL validation imports
import re
import requests
from urllib.parse import urlparse, urljoin

def validate_and_extract_url_info(url: str, company_name: str) -> Tuple[bool, str, str, str]:
    """
    Validate URL and extract domain + company info for screenshot naming.
    
    Args:
        url: The URL to validate
        company_name: Company name for organization
        
    Returns:
        Tuple of (is_valid, clean_url, domain, screenshot_name)
    """
    try:
        # Clean and normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Parse URL
        parsed = urlparse(url)
        domain = parsed.netloc
        
        if not domain:
            return False, "", "", "Invalid URL format"
        
        # Check if site exists
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code >= 400:
                return False, "", "", f"Site returned error {response.status_code}"
        except requests.RequestException as e:
            return False, "", "", f"Site not accessible: {str(e)}"
        
        # Generate screenshot name: domain_company_timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_name = f"{domain.replace('.', '_')}_{company_name}_{timestamp}"
        
        return True, url, domain, screenshot_name
        
    except Exception as e:
        return False, "", "", f"URL validation error: {str(e)}"


router = APIRouter(prefix="/v1", tags=["chat"])

# Simple in-memory storage for demo accounts
DEMO_ACCOUNTS = []

# Initialize OpenAI client with fallback
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠️ WARNING: OPENAI_API_KEY not set. Chat functionality will be limited.")
    client = None
else:
    client = OpenAI(api_key=api_key)

# --- Dynamic Conversation Starters ---
CONVERSATION_STARTERS = [
    "🚀 Simplify your QA game — what's your biggest testing challenge?",
    "💡 Tired of manual testing? Let's automate 70% of your QA work",
    "🔧 Struggling with test maintenance? I've got the solution",
    "📊 Need faster test execution? Tell me about your current setup",
    "🎯 Want to scale your testing without scaling your team?",
    "⚡ Slow test runs killing your CI/CD? I can help",
    "🔄 Manual regression testing taking forever? Let's fix that",
    "🌐 Cross-browser testing headaches? I know the feeling"
]

# --- GPT-5 Tools (Free-Form) ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "testzeus_knowledge",
            "description": "Retrieve information about TestZeus features, benefits, pricing, and how things work",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to search for in TestZeus knowledge base"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_email",
            "description": "Validate if a single email address is valid and properly formatted",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "The email address to validate"
                    }
                },
                "required": ["email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_tenant_and_team",
            "description": "Create a new TestZeus tenant and team account",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_text": {
                        "type": "string",
                        "description": "Text containing admin_email, plan, and teammate_emails in the format: admin_email: email@domain.com\nplan: oss or enterprise\nteammate_emails: email1@domain.com, email2@domain.com"
                    }
                },
                "required": ["input_text"]
            }
        }
    }
]

# Add new tools if available
if NEW_FEATURES_AVAILABLE:
    TOOLS.extend([
        {
            "type": "function",
            "function": {
                "name": "capture_website_screenshot",
                "description": "Capture a screenshot from a website URL for test case generation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The website URL to capture"
                        },
                        "company_name": {
                            "type": "string",
                            "description": "Company name for organizing screenshots"
                        },
                        "wait_time": {
                            "type": "integer",
                            "description": "Time to wait after page load in milliseconds (default: 3000)",
                            "default": 3000
                        }
                    },
                    "required": ["url", "company_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_gherkin_from_screenshot",
                "description": "Generate Gherkin test cases from a screenshot using GPT-5 Vision",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "screenshot_path": {
                            "type": "string",
                            "description": "Path to the screenshot file"
                        },
                        "prompt_type": {
                            "type": "string",
                            "description": "Type of prompt to use: general, login, dashboard, form, or ecommerce",
                            "enum": ["general", "login", "dashboard", "form", "ecommerce"]
                        },
                        "company_context": {
                            "type": "string",
                            "description": "Additional context about the company or application"
                        }
                    },
                    "required": ["screenshot_path", "prompt_type"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "extract_text_from_screenshot",
                "description": "Extract text and UI elements from a screenshot using OCR",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "screenshot_path": {
                            "type": "string",
                            "description": "Path to the screenshot file"
                        },
                        "custom_prompt": {
                            "type": "string",
                            "description": "Custom prompt for text extraction (optional)"
                        }
                    },
                    "required": ["screenshot_path"]
                }
            }
        }
    ])

# --- Tool Implementations ---
def tool_testzeus_knowledge(query: str) -> str:
    try:
        from services.rag_service import RAGService
        rag = RAGService()
        results = rag.retrieve(query)
        return "\n\n".join(results) if results else "I don't have detailed info on that."
    except Exception as e:
        return f"ERROR: Failed to retrieve knowledge: {str(e)}"

def tool_validate_email(input_text: str) -> str:
    try:
        import re
        from services.email_validator import email_validator
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', input_text)
        if not email_match:
            return "ERROR: no email found in input"
        email = email_match.group()
        validation = email_validator.validate_email(email)
        if validation["is_valid"]:
            return f"VALID: {email}"
        else:
            return f"INVALID: {email} - {validation['reason']}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def tool_create_tenant_and_team(input_text: str) -> str:
    try:
        # Parse the input text
        lines = [line.strip() for line in input_text.split("\n") if ":" in line]
        params = {}
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                params[k.strip().lower()] = v.strip()

        admin_email = params.get("admin_email")
        plan = params.get("plan", "oss")
        teammate_emails = [e.strip() for e in params.get("teammate_emails", "").split(",") if e.strip()]

        if not admin_email:
            return "ERROR: missing admin_email"

        # For demo purposes, simulate account creation with detailed logging
        print("=" * 50)
        print("🔐 CREATING TESTZEUS ACCOUNT")
        print("=" * 50)
        print(f"📧 Admin Email: {admin_email}")
        print(f"📋 Plan: {plan.upper()}")
        print(f"👥 Teammates: {teammate_emails}")
        print(f"⏰ Timestamp: {__import__('datetime').datetime.now()}")
        print("=" * 50)
        
        # Actually store the account in our demo storage
        account_data = {
            "admin_email": admin_email,
            "plan": plan.upper(),
            "teammates": teammate_emails,
            "created_at": str(__import__('datetime').datetime.now()),
            "status": "Active",
            "account_id": f"ACC_{len(DEMO_ACCOUNTS) + 1:04d}"
        }
        DEMO_ACCOUNTS.append(account_data)
        
        # Simulate success with detailed response
        response = f"""✅ ACCOUNT CREATED SUCCESSFULLY!

📊 Account Details:
• Account ID: {account_data['account_id']}
• Admin: {admin_email}
• Plan: {plan.upper()}
• Team Size: {len(teammate_emails) + 1} members
• Status: Active
• Created: {account_data['created_at']}

🎯 Next Steps:
1. Check your email for login credentials
2. Complete your profile setup
3. Start creating your first test cases

🚀 Welcome to TestZeus! Your QA automation journey begins now."""
        
        print("✅ Account creation completed successfully!")
        print(f"📊 Total accounts created: {len(DEMO_ACCOUNTS)}")
        print("=" * 50)
        
        return response
        
    except Exception as e:
        print(f"❌ Error in account creation: {str(e)}")
        return f"ERROR: {str(e)}"

# Add new tool implementations after the existing ones
def tool_capture_website_screenshot(url: str, company_name: str, wait_time: int = 3000) -> str:
    """Enhanced screenshot capture with URL validation"""
    try:
        print(f"🔍 Validating URL: {url}")
        print(f"🏢 Company: {company_name}")
        
        # Validate URL and extract info
        is_valid, clean_url, domain, screenshot_name = validate_and_extract_url_info(url, company_name)
        
        if not is_valid:
            error_msg = f"❌ **URL Validation Failed**\n\n**Issue**: {clean_url}\n\n**Please provide**:\n- A valid, accessible website URL\n- Correct company name\n\n**Examples of valid URLs**:\n- `https://example.com`\n- `https://app.company.com/login`\n- `https://dashboard.testcorp.com`"
            print(error_msg)
            return error_msg
        
        print(f"✅ URL validated successfully!")
        print(f"🌐 Domain: {domain}")
        print(f"📸 Screenshot name: {screenshot_name}")
        print(f"⏱️ Wait time: {wait_time}ms")
        
        # Capture screenshot
        screenshot_path, filename = capture_screenshot_sync(clean_url, company_name, wait_time)
        
        print(f"✅ Screenshot captured successfully!")
        print(f"📁 Saved to: {screenshot_path}")
        print(f"📄 Filename: {filename}")
        
        return f"""✅ **Screenshot Captured Successfully!**

📸 **Screenshot Details:**
- **URL**: {clean_url}
- **Domain**: {domain}
- **Company**: {company_name}
- **File**: {filename}
- **Path**: {screenshot_path}

🚀 **Next Steps Available:**
1. **Generate Gherkin test cases** from this screenshot
2. **Extract text and UI elements** using OCR
3. **Use for visual testing** and documentation

💡 **Recommendation**: 
I can now generate comprehensive test cases for this website. What type of functionality would you like me to focus on?

**Prompt Types Available:**
- `login` - Authentication and login flows
- `dashboard` - Navigation and data display
- `form` - Form validation and submission
- `ecommerce` - Shopping and checkout flows
- `general` - Overall website functionality

**Example**: "Generate Gherkin test cases for the login functionality using the login prompt type"

Would you like me to proceed with test case generation?"""
        
    except Exception as e:
        error_msg = f"❌ **Screenshot Capture Failed**\n\n**Error**: {str(e)}\n\n**Troubleshooting**:\n- Check if the URL is accessible\n- Verify the company name is correct\n- Try a different wait time if the site loads slowly\n\n**Common Issues**:\n- Site requires authentication\n- Heavy JavaScript applications need longer wait times\n- Some sites block automated access"
        print(error_msg)
        return error_msg

def tool_generate_gherkin_from_screenshot(screenshot_path: str, prompt_type: str, company_context: str = "") -> str:
    """Generate Gherkin test cases from a screenshot"""
    try:
        print(f"🤖 Generating Gherkin from screenshot: {screenshot_path}")
        print(f"📝 Prompt type: {prompt_type}")
        print(f"🏢 Company context: {company_context}")
        
        # Initialize GPT-5 generator
        generator = GPT5GherkinGenerator()
        
        # Select appropriate prompt
        prompt_map = {
            "general": GHERKIN_PROMPT,
            "login": LOGIN_GHERKIN_PROMPT,
            "dashboard": DASHBOARD_GHERKIN_PROMPT,
            "form": FORM_GHERKIN_PROMPT,
            "ecommerce": ECOMMERCE_GHERKIN_PROMPT
        }
        
        prompt = prompt_map.get(prompt_type, GHERKIN_PROMPT)
        
        # Generate Gherkin
        result = generator.generate_gherkin(screenshot_path, prompt, company_context)
        
        if result.get("success"):
            gherkin_content = result["gherkin"]
            tokens_used = result.get("tokens_used", 0)
            response_time = result.get("response_time", 0)
            
            print(f"✅ Gherkin generated successfully!")
            print(f"🔢 Tokens used: {tokens_used}")
            print(f"⏱️ Response time: {response_time:.2f}s")
            
            return f"""✅ Gherkin test cases generated successfully!

🤖 **AI Generation Details:**
- **Model**: GPT-5 Vision
- **Prompt Type**: {prompt_type}
- **Tokens Used**: {tokens_used}
- **Response Time**: {response_time:.2f}s

📋 **Generated Test Cases:**
```gherkin
{gherkin_content}
```

💡 **Usage Tips:**
- These test cases are ready to use in TestZeus
- They cover all visible UI elements and functionality
- You can customize them further based on your needs
- Use them for automated testing and documentation

Would you like me to help you with anything else related to these test cases?"""
            
        else:
            error_msg = f"❌ Error generating Gherkin: {result.get('error', 'Unknown error')}"
            print(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"❌ Error in Gherkin generation: {str(e)}"
        print(error_msg)
        return error_msg

def tool_extract_text_from_screenshot(screenshot_path: str, custom_prompt: str = "") -> str:
    """Extract text and UI elements from a screenshot using OCR"""
    try:
        print(f"🔍 Extracting text from screenshot: {screenshot_path}")
        print(f"📝 Custom prompt: {custom_prompt if custom_prompt else 'Using default prompt'}")
        
        # Initialize OCR processor
        ocr_processor = Qwen2VLOCR()
        
        # Extract text
        result = ocr_processor.extract_text_from_image(screenshot_path, custom_prompt)
        
        if result.get("success"):
            extracted_text = result["extracted_text"]
            tokens_used = result.get("tokens_used", 0)
            image_size = result.get("image_size", "Unknown")
            
            print(f"✅ Text extraction successful!")
            print(f"🔢 Tokens used: {tokens_used}")
            print(f"🖼️ Image size: {image_size}")
            
            return f"""✅ Text extraction completed successfully!

🔍 **OCR Details:**
- **Model**: Qwen2-VL
- **Tokens Used**: {tokens_used}
- **Image Size**: {image_size}

📝 **Extracted Content:**
```
{extracted_text}
```

💡 **What This Contains:**
- All visible text on the screenshot
- UI element descriptions
- Navigation elements
- Form fields and labels
- Error messages and notifications

🚀 **Next Steps:**
You can use this extracted text to:
1. Understand the UI structure
2. Generate more accurate test cases
3. Document the application interface
4. Analyze user experience elements

Would you like me to help you analyze this content or generate test cases?"""
            
        else:
            error_msg = f"❌ Error in text extraction: {result.get('error', 'Unknown error')}"
            print(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"❌ Error in OCR processing: {str(e)}"
        print(error_msg)
        return error_msg

@router.get("/accounts")
async def list_accounts():
    """List all created demo accounts"""
    return {
        "total_accounts": len(DEMO_ACCOUNTS),
        "accounts": DEMO_ACCOUNTS
    }

@router.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    message = data.get("message", "").strip()
    session_id = data.get("session_id")
    placeholder = random.choice(CONVERSATION_STARTERS)

    # If no message, return a starter
    if not message:
        return {
            "response": "Hey, I'm Hermes — I've been in the QA trenches. What's your biggest testing headache?",
            "placeholder": placeholder
        }

    # Check if OpenAI client is available
    if not client:
        # Simple fallback responses when AI is not available
        message_lower = message.lower()
        if any(word in message_lower for word in ["test", "testing", "qa"]):
            return {
                "response": "I can help with testing challenges! While my AI is offline, here are some quick tips:\n\n• Use TestZeus for automated test creation\n• Implement CI/CD pipelines for faster feedback\n• Focus on test maintenance and flakiness reduction\n\nWhat specific testing issue are you facing?",
                "placeholder": placeholder
            }
        elif "email" in message_lower:
            return {
                "response": "I can validate emails! Just send me an email address and I'll check if it's valid.",
                "placeholder": placeholder
            }
        elif any(word in message_lower for word in ["account", "signup", "onboard", "start"]):
            return {
                "response": "Ready to get started with TestZeus? I can help you create an account and set up your team. Just let me know your admin email and plan preference (OSS or Enterprise).",
                "placeholder": placeholder
            }
        else:
            return {
                "response": "Hey! I'm Hermes, your QA testing buddy. While my AI is offline, I can still help with:\n\n• TestZeus knowledge and features\n• Email validation\n• Account creation and team setup\n\nWhat would you like to know?",
                "placeholder": placeholder
            }

    # Check if this is a Precursive/Salesforce query and handle it directly
    if "precursive" in message.lower() and "salesforce" in message.lower():
        response = """Perfect! Precursive is exactly the kind of platform where TestZeus shines. Let me break this down for you:

**How We Generate Test Cases for You:**
- Write tests in plain English like "Login to Salesforce, create a new project, assign team members"
- Our AI agents automatically generate and execute complex test cases
- No coding required - just describe your workflow and we'll test it end-to-end

**For Your Salesforce Integration:**
- TestZeus opens Salesforce in our built-in browser
- AI understands Salesforce UI patterns (app launcher, buttons, forms, custom objects)
- Automatically handles authentication, navigation, and data entry
- Records video playback for debugging and documentation

**Perfect for PSA Platforms:**
- Test end-to-end workflows across Precursive and Salesforce
- Validate data synchronization between platforms
- Automated regression testing for Salesforce updates
- Catch integration bugs early before they reach production

**Pricing for Your Team:**
- **Growth Plan**: $1,200/month (includes 4 users, perfect for your 3 QA engineers + 1 admin)
- **Enterprise Plan**: Custom pricing for larger teams with dedicated support
- Additional users: $20/month each
- Annual billing saves 20%

**Key Benefits for Your Team:**
- Reduce manual testing time by 70%
- Scale testing without adding more QA engineers
- Maintain test coverage as Salesforce evolves
- Focus on strategy, not repetitive test maintenance

Would you like to see a demo of how we'd test a specific Precursive workflow, or shall we get you set up with an account?"""
            
        return {
            "response": response,
            "session_id": session_id,
            "placeholder": "🚀 Ready to automate your Salesforce testing? Let's get started!"
        }

    # Check if this is a general product overview query and handle it directly
    if any(keyword in message.lower() for keyword in ["tell me more about your product", "how do you create test cases", "product overview", "test case creation"]):
        response = """Great question! Let me give you a comprehensive overview of TestZeus and how we revolutionize test case creation.

**What is TestZeus?**
TestZeus is an AI-powered testing platform that automatically generates, executes, and maintains test cases using natural language descriptions. No coding required!

**How We Create Test Cases:**
- **Natural Language Input**: Write tests in plain English like "Login to the app, navigate to dashboard, verify user profile loads"
- **AI-Powered Generation**: Our AI agents automatically convert your descriptions into executable test cases
- **Multiple Sources**: We can work with requirements, user stories, PR descriptions, user flows, and existing documentation
- **Smart Maintenance**: Tests automatically update when your application changes, reducing flakiness

**Key Capabilities:**
- **No-Code Testing**: Describe what you want to test, we handle the rest
- **Cross-Platform Support**: Web, mobile, desktop, and API testing
- **Real Browser Execution**: Tests run in actual browsers for accurate results
- **Video Recording**: Every test execution is recorded for debugging
- **Parallel Execution**: Run multiple tests simultaneously to speed up your pipeline

**Integration & Collaboration:**
- **CI/CD Integration**: Works with GitHub Actions, Jenkins, GitLab CI, and more
- **Team Collaboration**: Share test cases, assign test runs, and track progress
- **Existing Tools**: Import from Jira, TestRail, or other test management systems
- **Version Control**: Track test changes and rollback when needed

**AI Capabilities:**
- **Smart Element Detection**: AI automatically finds and interacts with UI elements
- **Adaptive Testing**: Tests adapt to UI changes and application updates
- **Intelligent Assertions**: AI suggests relevant checks based on your test description
- **Flakiness Reduction**: Built-in retry logic and smart waiting strategies

**Output Formats:**
- **BDD/Gherkin**: Generate human-readable test specifications
- **Test Plans**: Organized test suites with dependencies and priorities
- **Reports**: Detailed execution reports with screenshots and logs
- **Metrics**: Track test coverage, execution time, and success rates

Would you like me to show you how this works with a specific example, or do you have questions about a particular aspect of our platform?"""
            
        return {
            "response": response,
            "session_id": session_id,
            "placeholder": "🚀 Ready to see TestZeus in action? Let's dive deeper!"
        }

    # Regular AI processing for other queries
    try:
        # Build system prompt with Hermes persona
        system_prompt = """
You are Hermes, a passionate QA engineer who's been in the testing trenches. You're friendly, practical, and speak like a real engineer — no fluff.

**Your Personality:**
- Be conversational and engaging
- Remember context from the conversation
- Ask follow-up questions to understand user needs
- Be enthusiastic about helping with testing challenges
- Use emojis occasionally to keep it friendly

**Tool Usage Guidelines:**
- testzeus_knowledge: Use when users ask about TestZeus features, benefits, pricing, or how things work
- validate_email: ONLY when users want to check if a single email is valid (not during account creation)
- create_tenant_and_team: When users want to join TestZeus, create an account, or onboard their team

**NEW AI-Powered Testing Tools:**
- capture_website_screenshot: When users want to capture screenshots from websites for test case generation
- generate_gherkin_from_screenshot: When users want to generate Gherkin test cases from screenshots using AI
- extract_text_from_screenshot: When users want to extract text and UI elements from screenshots using OCR

**When Using testzeus_knowledge:**
- The tool will provide you with structured information from our knowledge base
- Process this information and present it in a conversational, engaging way
- Don't just repeat the raw content - make it engaging and easy to understand
- Focus on what's most relevant to the user's specific question
- Add your own insights and recommendations when appropriate
- Keep responses concise but comprehensive
- Personalize the response based on the user's context (company, role, current situation)
- If the information is long, summarize the key points and offer to elaborate on specific areas

**When Using AI Testing Tools - AUTONOMOUS WORKFLOW:**
🚀 **BE PROACTIVE - Don't ask multiple questions!**

1. **URL Collection**: Extract URL and company name from user message
2. **Automatic Execution**: Run the complete pipeline without asking for confirmation:
   - Validate URL accessibility
   - Capture screenshot with smart defaults
   - Extract text/UI elements via OCR
   - Generate appropriate Gherkin test cases
3. **Smart Defaults**: Use intelligent defaults for all settings:
   - Viewport: Desktop 1920x1080 (or mobile if user specifies)
   - Wait time: 5-8 seconds for dynamic content
   - Full-page capture for comprehensive testing
   - Best prompt type based on website content (ecommerce, login, dashboard, etc.)

**URL Validation Process:**
- **Wrong URL**: "This site doesn't exist" → Ask for correct URL
- **Invalid Format**: "Invalid URL format" → Provide examples
- **Site Unreachable**: "Site not accessible" → Suggest troubleshooting
- **Success**: Extract domain + company → Generate screenshot name

**When Using AI Testing Tools:**
- **BE AUTONOMOUS**: Once you have a URL, execute the complete workflow
- **Smart Prompt Selection**: Choose the best prompt type based on the website:
  - Ecommerce sites (Amazon, Shopify) → Use ecommerce prompt
  - Login/authentication pages → Use login prompt
  - Dashboards/analytics → Use dashboard prompt
  - Forms/surveys → Use form prompt
  - General websites → Use general prompt
- **No Back-and-Forth**: Execute everything in one go and present results
- **Always guide users through the complete workflow**: URL validation → screenshot → OCR → Gherkin generation

**Conversation Flow:**
1. Greet users warmly and ask about their testing challenges
2. Listen to their needs and provide relevant information
3. When they're ready to onboard, guide them through the process
4. For AI testing requests, **EXECUTE COMPLETELY**:
   - Extract URL and company info
   - Validate and capture screenshot
   - Generate test cases automatically
   - Present complete results
5. Always be helpful and encouraging

**For Account Creation:**
Users should provide:
admin_email: [their email]
plan: oss or enterprise  
teammate_emails: [comma-separated list, optional]

**For AI Testing Workflows - AUTONOMOUS EXECUTION:**
1. **URL Input**: Website URL + Company Name (extract from user message)
2. **Validation**: Check accessibility and format
3. **Screenshot Capture**: URL + Company → Screenshot saved (use smart defaults)
4. **Text Extraction**: Screenshot → OCR text and UI elements
5. **Test Generation**: Screenshot + Smart Prompt Type → Gherkin test cases

**Key Principle: BE PROACTIVE, NOT REACTIVE**
- Don't ask "What viewport do you want?" - use smart defaults
- Don't ask "What prompt type?" - choose based on website content
- Don't ask "What company name?" - extract from context or use domain
- Execute the complete workflow and present results

**Error Handling Examples:**
- "That URL doesn't exist. Can you provide the correct website address?"
- "The site seems to be down. Let's try a different URL or check back later."
- "I need both the website URL and your company name to proceed."

Keep responses conversational, helpful, and not too long. Build rapport and guide users naturally through the onboarding process or AI testing workflows. **REMEMBER: Execute workflows automatically, don't ask for confirmation!**
"""

        # Call GPT-5 with standard chat completion API (supports tool calling)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            tools=TOOLS,
            tool_choice="auto"
        )

        # Debug: print response structure
        print(f"Response type: {type(response)}")
        print(f"Response attributes: {dir(response)}")
        print(f"Response choices: {getattr(response, 'choices', 'NO_CHOICES')}")

        # ✅ Safely extract output - handle chat completion structure
        try:
            if hasattr(response, "choices") and response.choices:
                choice = response.choices[0]
                message_obj = choice.message
                
                # Check if it's a tool call
                if message_obj.tool_calls:
                    for tool_call in message_obj.tool_calls:
                        tool_name = tool_call.function.name
                        
                        # Parse the arguments JSON
                        import json
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_args = {}

                        if tool_name == "testzeus_knowledge":
                            query = tool_args.get("query", "")
                            print(f"DEBUG: AI received query: '{query}'")
                            
                            # Special handling for Precursive/Salesforce query
                            if "precursive" in query.lower() and "salesforce" in query.lower():
                                print("DEBUG: Using hardcoded Precursive response")
                                result = """Perfect! Precursive is exactly the kind of platform where TestZeus shines. Let me break this down for you:

**How We Generate Test Cases for You:**
- Write tests in plain English like "Login to Salesforce, create a new project, assign team members"
- Our AI agents automatically generate and execute complex test cases
- No coding required - just describe your workflow and we'll test it end-to-end

**For Your Salesforce Integration:**
- TestZeus opens Salesforce in our built-in browser
- AI understands Salesforce UI patterns (app launcher, buttons, forms, custom objects)
- Automatically handles authentication, navigation, and data entry
- Records video playback for debugging and documentation

**Perfect for PSA Platforms:**
- Test end-to-end workflows across Precursive and Salesforce
- Validate data synchronization between platforms
- Automated regression testing for Salesforce updates
- Catch integration bugs early before they reach production

**Pricing for Your Team:**
- **Growth Plan**: $1,200/month (includes 4 users, perfect for your 3 QA engineers + 1 admin)
- **Enterprise Plan**: Custom pricing for larger teams with dedicated support
- Additional users: $20/month each
- Annual billing saves 20%

**Key Benefits for Your Team:**
- Reduce manual testing time by 70%
- Scale testing without adding more QA engineers
- Maintain test coverage as Salesforce evolves
- Focus on strategy, not repetitive test maintenance

Would you like to see a demo of how we'd test a specific Precursive workflow, or shall we get you set up with an account?"""
                            else:
                                print(f"DEBUG: Using RAG for query: '{query}'")
                                # Use regular RAG for other queries
                                rag_results = tool_testzeus_knowledge(query)
                                
                                # Process RAG results to make them more conversational
                                if rag_results and len(rag_results) > 0:
                                    # Combine RAG results and ask AI to process them conversationally
                                    rag_content = "\n\n".join(rag_results)
                                    
                                    # Get AI to process this information conversationally
                                    try:
                                        processing_response = client.chat.completions.create(
                                            model=os.getenv("OPENAI_MODEL", "gpt-5"),
                                            messages=[
                                                {"role": "system", "content": "You are Hermes, a helpful QA engineer. Process the following information about TestZeus and present it in a conversational, engaging way. Make it personal and relevant to the user's question. Keep it concise but comprehensive."},
                                                {"role": "user", "content": f"User asked: {query}\n\nHere's the information from our knowledge base:\n{rag_content}\n\nPlease provide a conversational, helpful response based on this information."}
                                            ],
                                            max_completion_tokens=800
                                        )
                                        
                                        result = processing_response.choices[0].message.content
                                    except Exception as e:
                                        print(f"Error processing RAG response: {e}")
                                        # Fallback to raw content if processing fails
                                        result = rag_content
                                else:
                                    result = "I don't have specific information about that, but I'd be happy to help you with TestZeus! What would you like to know?"
                                
                        elif tool_name == "validate_email":
                            email = tool_args.get("email", "")
                            result = tool_validate_email(f"email: {email}")
                        elif tool_name == "create_tenant_and_team":
                            input_text = tool_args.get("input_text", "")
                            result = tool_create_tenant_and_team(input_text)
                        elif tool_name == "capture_website_screenshot":
                            url = tool_args.get("url", "")
                            company_name = tool_args.get("company_name", "")
                            wait_time = tool_args.get("wait_time", 3000)
                            result = tool_capture_website_screenshot(url, company_name, wait_time)
                        elif tool_name == "generate_gherkin_from_screenshot":
                            screenshot_path = tool_args.get("screenshot_path", "")
                            prompt_type = tool_args.get("prompt_type", "general")
                            company_context = tool_args.get("company_context", "")
                            result = tool_generate_gherkin_from_screenshot(screenshot_path, prompt_type, company_context)
                        elif tool_name == "extract_text_from_screenshot":
                            screenshot_path = tool_args.get("screenshot_path", "")
                            custom_prompt = tool_args.get("custom_prompt", "")
                            result = tool_extract_text_from_screenshot(screenshot_path, custom_prompt)
                        else:
                            result = "Unknown tool"

                        return {
                            "response": result,
                            "session_id": session_id,
                            "tool_used": tool_name,
                            "placeholder": placeholder
                        }
                
                # Check if it's a text response
                if message_obj.content:
                    return {
                        "response": message_obj.content,
                        "session_id": session_id,
                        "placeholder": placeholder
                    }
            
            # If we can't parse the response, return a helpful message
            return {
                "response": "I received your message but couldn't process the response properly. This might be a temporary issue. Try asking again!",
                "session_id": session_id,
                "placeholder": placeholder
            }
            
        except Exception as parse_error:
            print(f"Response parsing error: {parse_error}")
            return {
                "response": "I'm having trouble processing the AI response. Let me try a different approach - what specific testing challenge are you facing?",
                "session_id": session_id,
                "placeholder": placeholder
            }

    except Exception as e:
        # 🔥 Log full traceback
        traceback.print_exc()
        return {
            "response": f"⚠️ AI error: {str(e)}",
            "placeholder": placeholder
        }