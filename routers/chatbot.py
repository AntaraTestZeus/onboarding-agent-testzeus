# backend/routers/chatbot.py
from fastapi import APIRouter, Request
from openai import OpenAI
import os
import random
import traceback

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
            "description": "Call this to answer questions about TestZeus using internal docs. Input: the user's question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user's question about TestZeus"
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
            "description": "Call this to validate an email address. Input: 'email: user@company.com'",
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
            "description": "Call this to create a tenant and team. Input format:\nadmin_email: ...\nplan: oss|enterprise\nteammate_emails: ...",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_text": {
                        "type": "string",
                        "description": "The input text containing admin_email, plan, and teammate_emails"
                    }
                },
                "required": ["input_text"]
            }
        }
    }
]

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

**When Using testzeus_knowledge:**
- The tool will provide you with structured information from our knowledge base
- Process this information and present it in a conversational, engaging way
- Don't just repeat the raw content - make it engaging and easy to understand
- Focus on what's most relevant to the user's specific question
- Add your own insights and recommendations when appropriate
- Keep responses concise but comprehensive
- Personalize the response based on the user's context (company, role, current situation)
- If the information is long, summarize the key points and offer to elaborate on specific areas

**Conversation Flow:**
1. Greet users warmly and ask about their testing challenges
2. Listen to their needs and provide relevant information
3. When they're ready to onboard, guide them through the process
4. Always be helpful and encouraging

**For Account Creation:**
Users should provide:
admin_email: [their email]
plan: oss or enterprise  
teammate_emails: [comma-separated list, optional]

Keep responses conversational, helpful, and not too long. Build rapport and guide users naturally through the onboarding process.
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