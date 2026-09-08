#!/usr/bin/env python3
"""
Test Case Creator Plugin - BDD Scenario Generator
Generates Behavior-Driven Development test scenarios from Jira issues using Claude AI

Environment Variables (required):
  - JIRA_BASE_URL: Jira Cloud instance URL (e.g., https://your-domain.atlassian.net)
  - JIRA_USER_EMAIL: Email for Jira API authentication
  - JIRA_API_TOKEN: Jira API token (generate from account settings)
  - ANTHROPIC_API_KEY: Claude API key (from https://console.anthropic.com/)

Optional Environment Variables:
  - TEST_CASE_CREATOR_ENABLED: true/false (default: true)
  - GENERATION_MODEL: claude-3-5-sonnet-20241022, claude-3-opus-20250219, claude-3-haiku-20250307
  - MAX_ISSUES_PER_RUN: Max issues to process (default: 50)
  - MAX_ATTACHMENT_SIZE_MB: Max attachment file size (default: 10)
  - DEBUG: true/false for verbose logging (default: false)
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import base64
import urllib.request
import urllib.error

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables

# Configure logging with UTF-8 encoding
class UTF8StreamHandler(logging.StreamHandler):
    """Stream handler that supports UTF-8 encoding"""
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # Handle both Windows and Unix systems
            if hasattr(stream, 'buffer'):
                stream.buffer.write((msg + '\n').encode('utf-8'))
            else:
                stream.write(msg + '\n')
            stream.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        UTF8StreamHandler(sys.stdout),
        logging.FileHandler('scripts/logs/generate-test-cases.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages environment configuration and validation"""

    def __init__(self):
        self.jira_base_url = os.getenv('JIRA_BASE_URL', '').rstrip('/')
        self.jira_user_email = os.getenv('JIRA_USER_EMAIL', '')
        self.jira_api_token = os.getenv('JIRA_API_TOKEN', '')

        # AI Provider Configuration
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.ai_provider = self._determine_provider()

        self.enabled = os.getenv('TEST_CASE_CREATOR_ENABLED', 'true').lower() == 'true'
        self.model = os.getenv('GENERATION_MODEL', 'claude-3-5-sonnet-20241022')
        self.max_issues = int(os.getenv('MAX_ISSUES_PER_RUN', '50'))
        self.max_attachment_mb = int(os.getenv('MAX_ATTACHMENT_SIZE_MB', '10'))
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'

    def _determine_provider(self) -> str:
        """Determine which AI provider to use (anthropic or openai)"""
        if self.anthropic_api_key:
            return 'anthropic'
        elif self.openai_api_key:
            return 'openai'
        return None

    def validate(self) -> bool:
        """Validate all required configuration is present"""
        if not self.enabled:
            logger.info("Test Case Creator plugin is disabled")
            return False

        missing = []
        if not self.jira_base_url:
            missing.append("JIRA_BASE_URL")
        if not self.jira_user_email:
            missing.append("JIRA_USER_EMAIL")
        if not self.jira_api_token:
            missing.append("JIRA_API_TOKEN")

        # Check for at least one AI provider
        if not self.ai_provider:
            missing.append("ANTHROPIC_API_KEY or OPENAI_API_KEY")

        if missing:
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            return False

        logger.info(f"Configuration validated successfully (AI Provider: {self.ai_provider})")
        return True

    def log_config(self):
        """Log current configuration (without sensitive values)"""
        logger.debug(f"Jira URL: {self.jira_base_url}")
        logger.debug(f"Jira User: {self.jira_user_email}")
        logger.debug(f"AI Provider: {self.ai_provider}")
        logger.debug(f"AI Model: {self.model}")
        logger.debug(f"Max Issues: {self.max_issues}")
        logger.debug(f"Max Attachment Size: {self.max_attachment_mb}MB")


class JiraClient:
    """Handles Jira API interactions"""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.base_url = config.jira_base_url
        self.auth_header = self._create_auth_header()

    def _create_auth_header(self) -> Dict[str, str]:
        """Create authorization header for Jira API"""
        credentials = f"{self.config.jira_user_email}:{self.config.jira_api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def validate_credentials(self) -> bool:
        """Validate Jira credentials by calling /myself endpoint"""
        try:
            url = f"{self.base_url}/rest/api/3/myself"
            req = urllib.request.Request(url, headers=self.auth_header)
            with urllib.request.urlopen(req, timeout=5) as response:
                user = json.loads(response.read())
                logger.info(f"✓ Jira auth OK: {user.get('displayName', 'Unknown')}")
                return True
        except urllib.error.HTTPError as e:
            if e.code == 401:
                logger.error("✗ Jira authentication failed: Invalid credentials")
            else:
                logger.error(f"✗ Jira API error: {e.code}")
            return False
        except Exception as e:
            logger.error(f"✗ Jira connectivity failed: {e}")
            return False

    def _api_call(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make API call to Jira with error handling"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET" and data:
                from urllib.parse import urlencode
                query_string = urlencode(data)
                url = f"{url}?{query_string}"
                logger.debug(f"Calling Jira API: {method} {url}")
                req = urllib.request.Request(url, headers=self.auth_header, method=method)
            elif method == "POST":
                payload = json.dumps(data).encode('utf-8') if data else None
                req = urllib.request.Request(url, data=payload, headers=self.auth_header, method=method)
            else:
                req = urllib.request.Request(url, headers=self.auth_header, method=method)

            with urllib.request.urlopen(req, timeout=10) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                return response_data
        except urllib.error.HTTPError as e:
            error_msg = f"Jira API error {e.code}: {e.reason} - URL: {url}"
            logger.error(error_msg)
            if self.config.debug:
                try:
                    error_body = e.read().decode('utf-8')
                    logger.debug(f"Error response: {error_body}")
                except:
                    pass
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise

    def fetch_issues(self, limit: int = 50, jql: str = None) -> List[Dict[str, Any]]:
        """Fetch Jira issues for test case generation"""
        logger.info(f"Fetching up to {limit} issues from Jira...")

        # Default JQL query
        if not jql:
            jql = "type in (Story, Task) ORDER BY updated DESC"

        issues = []
        start_at = 0

        try:
            while len(issues) < limit:
                # Query Jira API
                params = {
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": min(100, limit - len(issues)),
                    "fields": "key,summary,description,issuetype,status,attachment"
                }

                response = self._api_call("GET", "/rest/api/3/search", params)
                fetched_issues = response.get("issues", [])

                if not fetched_issues:
                    break

                issues.extend(fetched_issues)
                start_at += len(fetched_issues)

                logger.info(f"  Fetched {len(fetched_issues)} issues (total: {len(issues)})")

        except Exception as e:
            logger.error(f"Failed to fetch issues: {e}")
            return issues[:limit]

        logger.info(f"✓ Total issues fetched: {len(issues)}")
        return issues[:limit]

    def download_attachment(self, attachment_url: str) -> Optional[bytes]:
        """Download attachment safely with size limits"""
        try:
            req = urllib.request.Request(attachment_url, headers=self.auth_header)

            # Check content-length header
            with urllib.request.urlopen(req, timeout=5) as response:
                content_length = int(response.headers.get('content-length', 0))
                max_bytes = self.config.max_attachment_mb * 1024 * 1024

                if content_length > max_bytes:
                    logger.warning(f"Attachment too large: {content_length} bytes (max: {max_bytes})")
                    return None

                # Download with size limit
                data = response.read(max_bytes + 1)

                if len(data) > max_bytes:
                    logger.warning("Attachment download exceeded size limit")
                    return None

                logger.info(f"✓ Downloaded attachment: {len(data)} bytes")
                return data

        except Exception as e:
            logger.warning(f"Attachment download failed: {e}")
            return None


class AttachmentParser:
    """Parses attachment content (PDF, DOCX) (PLACEHOLDER - Phase 1)"""

    @staticmethod
    def parse_pdf(content: bytes) -> Optional[str]:
        """Extract text from PDF"""
        # Phase 1 Implementation:
        # 1. Import pdfplumber
        # 2. Parse PDF bytes
        # 3. Extract text with timeout (3s)
        # 4. Return None on failure
        return None

    @staticmethod
    def parse_docx(content: bytes) -> Optional[str]:
        """Extract text from DOCX"""
        # Phase 1 Implementation:
        # 1. Import python-docx
        # 2. Parse DOCX bytes
        # 3. Extract text from paragraphs
        # 4. Return None on failure
        return None

    @staticmethod
    def parse(content: bytes, mime_type: str) -> Optional[str]:
        """Parse attachment based on MIME type"""
        if mime_type == "application/pdf":
            return AttachmentParser.parse_pdf(content)
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return AttachmentParser.parse_docx(content)
        else:
            logger.warning(f"Unsupported MIME type: {mime_type}")
            return None


class PreconditionExtractor:
    """Extracts preconditions from Jira issue content"""

    @staticmethod
    def extract(issue: Dict[str, Any], attachment_content: Optional[str] = None) -> List[str]:
        """Extract preconditions from issue description and acceptance criteria"""
        import re

        preconditions = []
        description = issue.get("fields", {}).get("description", "") or ""

        # Extract from description - look for patterns
        patterns = [
            r"(?:must|should)\s+be\s+([^.\n;]+)",
            r"requires?\s+([^.\n;]+)",
            r"configured\s+(?:as|to)\s+([^.\n;]+)",
            r"(?:Given|And)\s+([^.\n;]+)"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 10:
                    preconditions.append(f"Given {match.strip()}")

        # Extract acceptance criteria
        ac_matches = re.findall(r"AC\d+:\s*([^\n]+)", description)
        for ac in ac_matches:
            if ac.strip():
                preconditions.append(f"And {ac.strip()}")

        # Extract from attachment if provided
        if attachment_content:
            att_matches = re.findall(r"(?:must|should|requires?)\s+([^.\n]+)", attachment_content, re.IGNORECASE)
            for match in att_matches[:3]:  # Limit to 3 from attachments
                if len(match.strip()) > 10:
                    preconditions.append(f"And {match.strip()}")

        # Deduplicate and clean
        seen = set()
        unique = []
        for pre in preconditions:
            normalized = pre.lower()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(pre)

        logger.info(f"  Extracted {len(unique)} preconditions")
        return unique[:10]  # Limit to 10 preconditions


class BDDGenerator:
    """Generates BDD scenarios using Claude AI or OpenAI"""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.client = None
        self.provider = config.ai_provider

        if self.provider == 'anthropic':
            self._init_anthropic()
        elif self.provider == 'openai':
            self._init_openai()
        else:
            logger.error("✗ No AI provider configured (set ANTHROPIC_API_KEY or OPENAI_API_KEY)")

    def _init_anthropic(self):
        """Initialize Anthropic/Claude client"""
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
            logger.info(f"✓ Claude client initialized (model: {self.config.model})")
        except ImportError:
            logger.error("✗ anthropic SDK not installed: pip install anthropic")
            self.client = None
        except Exception as e:
            logger.error(f"✗ Failed to initialize Claude client: {e}")
            self.client = None

    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.config.openai_api_key)
            logger.info(f"✓ OpenAI client initialized (model: {self.config.model})")
        except ImportError:
            logger.error("✗ openai SDK not installed: pip install openai")
            self.client = None
        except Exception as e:
            logger.error(f"✗ Failed to initialize OpenAI client: {e}")
            self.client = None

    def _call_anthropic(self, user_prompt: str) -> Optional[str]:
        """Call Anthropic Claude API"""
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"  Anthropic API error: {e}")
            return None

    def _call_openai(self, user_prompt: str) -> Optional[str]:
        """Call OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"  OpenAI API error: {e}")
            return None

    def _load_system_prompt(self) -> str:
        """Load BDD generation system prompt from file"""
        try:
            prompt_file = os.path.join(os.path.dirname(__file__), 'prompts', 'bdd-generation.txt')
            with open(prompt_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"BDD prompt file not found: {prompt_file}")
            return ""

    def _extract_ac(self, issue: Dict[str, Any]) -> str:
        """Extract acceptance criteria from issue"""
        import re
        description = issue.get("fields", {}).get("description", "") or ""
        ac_matches = re.findall(r"AC\d+:\s*([^\n]+)", description)
        if ac_matches:
            return "\n".join([f"  {ac}" for ac in ac_matches])
        return "Not specified"

    def _validate_scenario(self, scenario: Dict[str, Any]) -> bool:
        """Validate BDD scenario structure and content"""
        required_fields = ['id', 'title', 'type', 'preconditions', 'steps', 'expectedResult']

        # Check required fields
        for field in required_fields:
            if field not in scenario or not scenario[field]:
                logger.warning(f"  Scenario missing field: {field}")
                return False

        # Validate preconditions
        preconditions = scenario.get('preconditions', [])
        if not isinstance(preconditions, list) or not preconditions:
            logger.warning(f"  Invalid preconditions format")
            return False

        for pre in preconditions:
            if not pre.startswith(('Given', 'And')):
                logger.warning(f"  Precondition doesn't start with Given/And: {pre}")
                return False

        # Validate steps
        steps = scenario.get('steps', [])
        if not isinstance(steps, list) or not steps:
            logger.warning(f"  Invalid steps format")
            return False

        for step in steps:
            if not isinstance(step, dict):
                logger.warning(f"  Step is not a dict")
                return False
            if 'action' not in step or 'expectedResult' not in step:
                logger.warning(f"  Step missing action or expectedResult")
                return False

        # Validate priority
        priority = scenario.get('priority', '')
        if priority not in ['P1', 'P2', 'P3']:
            logger.warning(f"  Invalid priority: {priority}")
            return False

        # Validate type
        valid_types = ['positive', 'negative', 'edge-case', 'performance', 'security', 'usability', 'design']
        if scenario.get('type') not in valid_types:
            logger.warning(f"  Invalid type: {scenario.get('type')}")
            return False

        # Validate expected result length
        expected = scenario.get('expectedResult', '')
        if len(expected) < 20:
            logger.warning(f"  Expected result too short: {expected}")
            return False

        return True

    def generate_scenarios(
        self,
        issue: Dict[str, Any],
        preconditions: List[str],
        test_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate BDD scenarios using Claude"""
        if not self.client:
            logger.error("Claude client not initialized")
            return []

        if test_types is None:
            test_types = ['positive', 'negative', 'edge-case']

        try:
            # Load system prompt
            system_prompt = self._load_system_prompt()
            if not system_prompt:
                return []

            # Build user prompt
            issue_summary = issue.get('summary', 'No summary')
            issue_desc = issue.get('fields', {}).get('description', 'No description') or 'No description'
            acceptance_criteria = self._extract_ac(issue)

            # Sanitize content
            issue_summary = PIISanitizer.sanitize(issue_summary)
            issue_desc = PIISanitizer.sanitize(issue_desc)

            user_prompt = f"""
Issue Summary: {issue_summary}
Issue Type: {issue.get('fields', {}).get('issuetype', {}).get('name', 'Unknown')}

Description:
{issue_desc}

Acceptance Criteria:
{acceptance_criteria}

Preconditions:
{chr(10).join([f"  - {pre}" for pre in preconditions])}

Test Types Requested: {', '.join(test_types)}

Generate comprehensive BDD test scenarios for this issue.
"""

            logger.info(f"  Calling {self.provider.upper()} ({self.config.model}) for BDD generation...")

            # Call AI provider
            if self.provider == 'anthropic':
                response_text = self._call_anthropic(user_prompt)
            elif self.provider == 'openai':
                response_text = self._call_openai(user_prompt)
            else:
                logger.error("No AI provider initialized")
                return []

            if not response_text:
                return []

            # Parse JSON response
            try:
                scenarios = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"  Failed to parse Claude response as JSON: {e}")
                logger.debug(f"  Response: {response_text[:200]}...")
                return []

            if not isinstance(scenarios, list):
                logger.error(f"  Expected JSON array, got {type(scenarios)}")
                return []

            # Validate scenarios
            validated = []
            for scenario in scenarios:
                if self._validate_scenario(scenario):
                    validated.append(scenario)
                else:
                    logger.warning(f"  Skipping invalid scenario: {scenario.get('id', '?')}")

            logger.info(f"  ✓ Generated {len(validated)}/{len(scenarios)} valid scenarios")
            return validated

        except Exception as e:
            logger.error(f"  Error generating scenarios: {e}")
            return []


class PIISanitizer:
    """Sanitizes PII before sending to Claude API"""

    @staticmethod
    def sanitize(text: str) -> str:
        """Remove PII from text"""
        import re

        # Redact emails
        text = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL]',
            text
        )

        # Redact IP addresses
        text = re.sub(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            '[IP]',
            text
        )

        # Redact API keys/passwords
        text = re.sub(
            r'(password|secret|token|key|api_key)\s*[:=]\s*[\S]+',
            r'\1=[SECRET]',
            text,
            flags=re.IGNORECASE
        )

        return text


class TestCaseGenerator:
    """Main orchestrator for test case generation"""

    def __init__(self):
        self.config = ConfigManager()
        self.jira = JiraClient(self.config)
        self.generator = BDDGenerator(self.config)

    def run(self) -> bool:
        """Execute test case generation pipeline"""
        logger.info("=" * 60)
        logger.info("Test Case Creator - BDD Scenario Generator")
        logger.info("=" * 60)

        # Validate configuration
        if not self.config.validate():
            return False

        if self.config.debug:
            self.config.log_config()

        # Validate Jira credentials
        if not self.jira.validate_credentials():
            return False

        # Fetch issues
        logger.info(f"Fetching issues (max {self.config.max_issues})...")
        issues = self.jira.fetch_issues(limit=self.config.max_issues)
        logger.info(f"Found {len(issues)} issues to process")

        # Generate test cases
        results = {
            "timestamp": datetime.now().isoformat(),
            "model": self.config.model,
            "totalIssues": len(issues),
            "successfulGenerations": 0,
            "failedGenerations": 0,
            "testCases": []
        }

        for i, issue in enumerate(issues, 1):
            try:
                logger.info(f"[{i}/{len(issues)}] Processing {issue['key']}: {issue['summary']}")

                # Extract preconditions
                preconditions = PreconditionExtractor.extract(issue)

                # Generate scenarios
                scenarios = self.generator.generate_scenarios(issue, preconditions)

                if scenarios:
                    results["testCases"].append({
                        "issueKey": issue["key"],
                        "summary": issue["summary"],
                        "scenarios": scenarios,
                        "generatedAt": datetime.now().isoformat()
                    })
                    results["successfulGenerations"] += 1
                    logger.info(f"✓ Generated {len(scenarios)} scenarios")
                else:
                    results["failedGenerations"] += 1
                    logger.warning(f"✗ No scenarios generated for {issue['key']}")

            except Exception as e:
                results["failedGenerations"] += 1
                logger.error(f"✗ Error processing {issue['key']}: {e}")
                continue

        # Save results
        self._save_results(results)
        return results["successfulGenerations"] > 0

    def _save_results(self, results: Dict[str, Any]):
        """Save generated test cases to JSON file"""
        output_file = "data/test-cases.json"
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"✓ Saved results to {output_file}")
            logger.info(f"Summary: {results['successfulGenerations']}/{results['totalIssues']} successful")
        except Exception as e:
            logger.error(f"✗ Failed to save results: {e}")


def main():
    """Entry point for the script"""
    try:
        generator = TestCaseGenerator()
        success = generator.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
