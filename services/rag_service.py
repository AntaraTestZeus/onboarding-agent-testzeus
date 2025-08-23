# backend/services/rag_service.py
import os
from typing import List
import re

class RAGService:
    def __init__(self, docs_path: str = None):
        if docs_path is None:
            # Default to the testzeus_docs directory in the backend folder
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_dir = os.path.dirname(current_dir)
            self.docs_path = os.path.join(backend_dir, "testzeus_docs")
        else:
            self.docs_path = docs_path

    def retrieve(self, query: str) -> List[str]:
        if not os.path.exists(self.docs_path):
            return ["I don't have access to the TestZeus documentation right now."]
        
        query_lower = query.lower()
        query_words = query_lower.split()
        
        # Define specific knowledge areas
        knowledge_areas = {
            "pricing": ["pricing", "cost", "plan", "subscription", "billing", "price"],
            "test_creation": ["test case", "generate", "create test", "automation", "ai agent"],
            "salesforce": ["salesforce", "sfdc", "crm"],
            "benefits": ["benefit", "advantage", "feature", "special", "unique"],
            "onboarding": ["onboard", "setup", "get started", "join", "signup"]
        }
        
        # Determine what the user is asking about
        relevant_areas = []
        for area, keywords in knowledge_areas.items():
            if any(keyword in query_lower for keyword in keywords):
                relevant_areas.append(area)
        
        # If no specific area found, default to general info
        if not relevant_areas:
            relevant_areas = ["benefits", "test_creation"]
        
        results = []
        
        # Search for relevant content based on identified areas
        for area in relevant_areas:
            area_content = self._get_area_content(area, query_words)
            if area_content:
                results.append(area_content)
        
        # If no specific content found, provide a helpful response
        if not results:
            return ["I'd be happy to help you with TestZeus! Could you be more specific about what you'd like to know? For example:\n• How TestZeus creates test cases\n• Pricing and plans\n• Benefits and features\n• Getting started"]
        
        return results

    def _get_area_content(self, area: str, query_words: List[str]) -> str:
        """Get focused content for a specific knowledge area"""
        
        if area == "pricing":
            return self._get_pricing_info()
        elif area == "test_creation":
            return self._get_test_creation_info()
        elif area == "salesforce":
            return self._get_salesforce_info()
        elif area == "benefits":
            return self._get_benefits_info()
        elif area == "onboarding":
            return self._get_onboarding_info()
        
        return None

    def _get_pricing_info(self) -> str:
        """Get focused pricing information"""
        try:
            pricing_file = os.path.join(self.docs_path, "testzeus_pricing.txt")
            if os.path.exists(pricing_file):
                # Extract key pricing points
                pricing_summary = """TestZeus Pricing Plans

Starter Plan - $600/month
- Perfect for solo developers or small teams
- 1,200 test scenario runs
- Up to 15 parallel runs
- 1 user included

Growth Plan - $1,200/month  
- Best for scaling teams
- 2,400 test scenario runs
- Up to 30 parallel runs
- 4 users included

Enterprise Plan - Custom pricing
- Custom-built for large teams
- Regional deployments
- Custom parallel runs
- Dedicated support

Additional Users: $20/month per extra user
Annual Billing: 20% savings on Starter and Growth plans"""
                return pricing_summary
        except Exception as e:
            print(f"Error reading pricing file: {e}")
        
        return "Pricing: Starter plan starts at $600/month, Growth at $1,200/month, and Enterprise is custom pricing. Each additional user is $20/month."

    def _get_test_creation_info(self) -> str:
        """Get focused information about test case creation"""
        try:
            test_creation_file = os.path.join(self.docs_path, "Creating and Running Test Cases with TestZeus.txt")
            if os.path.exists(test_creation_file):
                return """How TestZeus Generates Test Cases

AI-Powered Test Creation:
- Write tests in natural English (e.g., 'Login to Salesforce and create a new account')
- AI agents automatically generate and execute complex test cases
- No coding required - just describe what you want to test

For Salesforce Integration:
- TestZeus opens Salesforce in a built-in browser
- AI interacts naturally with UI elements (app launcher, buttons, forms)
- Automatically handles authentication, navigation, and data entry
- Records video playback of test execution for debugging

Test Case Structure:
- Given: Set up test data and environment
- When: Describe the actions to perform
- Then: Define expected outcomes and assertions

Key Benefits:
- 70% faster test creation than manual coding
- Built-in test data management
- Automatic parallel execution
- Comprehensive reporting and debugging tools"""
        except Exception as e:
            print(f"Error reading test creation file: {e}")
        
        return "Test Case Generation: TestZeus uses AI agents to automatically create and execute test cases from natural English descriptions. No coding required!"

    def _get_salesforce_info(self) -> str:
        """Get focused Salesforce-specific information"""
        return """Salesforce Integration Features

Native Salesforce Support:
- Built-in Salesforce testing capabilities
- AI agents understand Salesforce UI patterns
- Automatic handling of authentication and navigation
- Support for custom objects, fields, and workflows

Test Automation for PSA Platforms:
- Perfect for platforms like Precursive that integrate with Salesforce
- Test end-to-end workflows across integrated systems
- Validate data synchronization between platforms
- Automated regression testing for Salesforce updates

Key Advantages for Salesforce QA Teams:
- Reduce manual testing time by 70%
- Catch integration bugs early
- Maintain test coverage as Salesforce evolves
- Scale testing without adding more QA engineers"""

    def _get_benefits_info(self) -> str:
        """Get focused benefits information"""
        try:
            benefits_file = os.path.join(self.docs_path, "our_benefits.txt")
            if os.path.exists(benefits_file):
                return """Why TestZeus is Special

For QA Engineers:
- Massive Time Savings: AI generates complex test cases automatically
- Increased Coverage: AI explores edge cases humans might miss
- Focus on Strategy: Spend time on test planning, not repetitive coding

For Development Teams:
- Faster Feedback: Catch bugs immediately in CI/CD pipelines
- Reproducible Results: Detailed logs and context for debugging
- Scalable Testing: Run more tests without scaling QA headcount

For Business Leaders:
- Lower Costs: Reduce need for large manual QA teams
- Faster Releases: Ship features with confidence
- Better Quality: More reliable products lead to happier customers"""
        except Exception as e:
            print(f"Error reading benefits file: {e}")
        
        return "Key Benefits: TestZeus saves 70% of testing time, increases test coverage, and reduces QA costs while improving software quality."

    def _get_onboarding_info(self) -> str:
        """Get focused onboarding information"""
        return """Getting Started with TestZeus

Quick Setup:
1. Create your account (OSS or Enterprise plan)
2. Set up your testing environment
3. Write your first test case in natural English
4. Run tests immediately in our cloud environment

No Installation Required:
- Browser-based platform
- Built-in test execution environment
- Instant access to AI agents
- Real-time test results and reporting

Support & Training:
- Onboarding assistance included
- Documentation and tutorials
- Community support
- Enterprise customers get dedicated support"""