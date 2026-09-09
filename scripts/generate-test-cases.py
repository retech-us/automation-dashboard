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
        self.openai_api_base = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
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
            logger.info(f"Testing Jira connection to: {url}")
            req = urllib.request.Request(url, headers=self.auth_header)
            with urllib.request.urlopen(req, timeout=5) as response:
                user = json.loads(response.read())
                logger.info(f"✓ Jira auth OK: {user.get('displayName', 'Unknown')}")
                return True
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode('utf-8')[:500]
            except:
                pass
            if e.code == 401:
                logger.error("✗ Jira authentication failed: Invalid credentials")
            elif e.code == 404:
                logger.error(f"✗ Jira endpoint not found (404): {url}")
            else:
                logger.error(f"✗ Jira API error {e.code}: {e.reason}")
            if error_body:
                logger.error(f"  Error response: {error_body}")
            return False
        except Exception as e:
            logger.error(f"✗ Jira connectivity failed: {e}")
            import traceback
            logger.error(f"  Traceback: {traceback.format_exc()}")
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
        """Fetch Jira issues for test case generation
        Falls back to mock data if Jira instance returns 0 issues (for local development)
        """
        logger.info(f"Fetching up to {limit} issues from Jira...")

        # Default JQL query
        if not jql:
            jql = "type in (Story, Task) ORDER BY updated DESC"

        issues = []
        start_at = 0

        try:
            while len(issues) < limit:
                # Query Jira API using JQL endpoint
                params = {
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": min(100, limit - len(issues)),
                    "fields": "key,summary,description,issuetype,status,attachment"
                }

                response = self._api_call("GET", "/rest/api/3/search/jql", params)
                fetched_issues = response.get("issues", [])

                if not fetched_issues:
                    break

                # Flatten Jira API structure for easier access
                for api_issue in fetched_issues:
                    raw_desc = api_issue.get("fields", {}).get("description", "")
                    issue = {
                        "key": api_issue.get("key"),
                        "summary": api_issue.get("fields", {}).get("summary", ""),
                        "description": DescriptionParser.to_plain_text(raw_desc),
                        "issuetype": api_issue.get("fields", {}).get("issuetype", {}),
                        "status": api_issue.get("fields", {}).get("status", {}),
                        "attachment": api_issue.get("fields", {}).get("attachment", []),
                        "fields": api_issue.get("fields", {})  # Keep full nested structure
                    }
                    issues.append(issue)
                start_at += len(fetched_issues)

                logger.info(f"  Fetched {len(fetched_issues)} issues (total: {len(issues)})")

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode('utf-8')[:500]
            except:
                pass
            logger.error(f"Failed to fetch issues (HTTP {e.code}): {e.reason}")
            if error_body:
                logger.error(f"  Error response: {error_body}")
            return issues[:limit]
        except Exception as e:
            import traceback
            logger.error(f"Failed to fetch issues: {e}")
            logger.error(f"  Traceback: {traceback.format_exc()}")
            return issues[:limit]

        logger.info(f"✓ Total issues fetched: {len(issues)}")

        # Fallback to mock data if no issues found (for local development)
        if len(issues) == 0:
            logger.warning("No issues found in Jira, trying mock data...")
            try:
                import json
                from pathlib import Path
                mock_file = Path('data/jira.json')
                if mock_file.exists():
                    with open(mock_file, 'r') as f:
                        mock_data = json.load(f)
                    mock_issues = mock_data.get('issues', [])
                    logger.info(f"Loaded {len(mock_issues)} mock issues from data/jira.json")
                    return mock_issues[:limit]
            except Exception as e:
                logger.debug(f"Could not load mock data: {e}")

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
        description = issue.get("description", "") or ""

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
            self.client = openai.OpenAI(
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_api_base
            )
            logger.info(f"✓ OpenAI client initialized (model: {self.config.model}, endpoint: {self.config.openai_api_base})")
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

    def _call_openai(self, user_prompt: str, temperature: float = None) -> Optional[str]:
        """Call OpenAI API

        Args:
            user_prompt: The user prompt for generation
            temperature: Optional temperature override (0.0-1.0)
        """
        try:
            # Use provided temperature or default
            temp = temperature if temperature is not None else 0.3

            response = self.client.chat.completions.create(
                model=self.config.model,
                max_tokens=4000,  # Increased to handle complete responses
                temperature=temp,
                messages=[
                    {"role": "system", "content": self._load_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                timeout=300  # 5 minute timeout
            )
            response_text = response.choices[0].message.content.strip()
            if not response_text:
                logger.warning("  Empty response from OpenAI API")
                return None
            logger.debug(f"  API response (first 200 chars): {response_text[:200]}")
            return response_text
        except Exception as e:
            logger.error(f"  OpenAI API error: {e}")
            if self.config.debug:
                import traceback
                logger.debug(f"  Traceback: {traceback.format_exc()}")
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
        description = issue.get("description", "") or ""
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
        test_types: List[str] = None,
        custom_requirements: str = None,
        temperature: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Generate BDD scenarios using Claude

        Args:
            issue: Jira issue data
            preconditions: List of preconditions for the scenario
            test_types: Types of scenarios to generate (positive, negative, edge-case, etc.)
            custom_requirements: Custom requirements or notes for generation
            temperature: AI temperature/creativity level (0.0-1.0)
        """
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
            issue_desc = issue.get('description', 'No description') or 'No description'
            acceptance_criteria = self._extract_ac(issue)

            # Sanitize content
            issue_summary = PIISanitizer.sanitize(issue_summary)
            issue_desc = PIISanitizer.sanitize(issue_desc)

            user_prompt = f"""
Issue Summary: {issue_summary}
Issue Type: {issue.get('issuetype', {}).get('name', 'Unknown')}

Description:
{issue_desc}

Acceptance Criteria:
{acceptance_criteria}

Preconditions:
{chr(10).join([f"  - {pre}" for pre in preconditions])}

Test Types Requested: {', '.join(test_types)}
"""

            if custom_requirements:
                user_prompt += f"\nCustom Requirements/Notes:\n{custom_requirements}\n"

            user_prompt += "\nGenerate comprehensive BDD test scenarios for this issue."

            logger.info(f"  Calling {self.provider.upper()} ({self.config.model}) for BDD generation...")
            logger.info(f"    Temperature: {temperature}, Test Types: {', '.join(test_types)}")

            # Call AI provider with temperature
            if self.provider == 'anthropic':
                response_text = self._call_anthropic(user_prompt)
            elif self.provider == 'openai':
                response_text = self._call_openai(user_prompt, temperature=temperature)
            else:
                logger.error("No AI provider initialized")
                return []

            if not response_text:
                logger.error("  Empty response from AI provider")
                return []

            # Parse JSON response
            try:
                scenarios = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"  Failed to parse response as JSON: {e}")
                logger.error(f"  Response length: {len(response_text)} chars")
                logger.error(f"  Response preview: {response_text[:300]}")

                # Try to extract JSON from markdown code blocks
                if "```json" in response_text or "```" in response_text:
                    logger.info("  Attempting to extract JSON from markdown code block...")
                    try:
                        # Find JSON start
                        json_start = response_text.find("```json")
                        if json_start == -1:
                            json_start = response_text.find("```")
                        if json_start != -1:
                            json_start = response_text.find("\n", json_start) + 1
                        else:
                            logger.error("  Could not find code block markers")
                            return []

                        # Find JSON end (look for closing ```)
                        json_end = response_text.find("```", json_start)
                        if json_end == -1:
                            json_end = len(response_text)

                        json_text = response_text[json_start:json_end].strip()

                        # Try to parse - if it fails, try to fix common issues
                        try:
                            scenarios = json.loads(json_text)
                            logger.info("  ✓ Successfully extracted JSON from markdown")
                        except json.JSONDecodeError as parse_error:
                            logger.warning(f"  JSON parsing error: {parse_error}")
                            logger.warning(f"  Response appears truncated. Attempting recovery...")

                            json_fixed = json_text.rstrip()

                            # Remove incomplete trailing object/item
                            # Find the last complete closing bracket or brace
                            last_complete_idx = -1
                            for i in range(len(json_fixed) - 1, -1, -1):
                                if json_fixed[i] in ']}':
                                    last_complete_idx = i
                                    break

                            if last_complete_idx > 0:
                                json_fixed = json_fixed[:last_complete_idx + 1]

                            # Close any remaining open structures
                            open_brackets = json_fixed.count('[') - json_fixed.count(']')
                            open_braces = json_fixed.count('{') - json_fixed.count('}')
                            open_quotes = json_fixed.count('"') % 2

                            logger.warning(f"  Missing: {open_brackets} brackets, {open_braces} braces, {'1 quote' if open_quotes else 'no quotes'}")

                            try:
                                # Close any open structures
                                if open_quotes:
                                    json_fixed += '"'
                                # Properly close arrays and objects
                                for _ in range(open_brackets):
                                    json_fixed += ']'
                                for _ in range(open_braces):
                                    json_fixed += '}'
                                json_fixed = json_fixed.rstrip(',')  # Remove trailing commas

                                scenarios = json.loads(json_fixed)
                                logger.info(f"  ✓ Successfully recovered truncated JSON ({len(scenarios)} scenarios recovered)")
                            except Exception as recovery_error:
                                logger.error(f"  Could not recover JSON: {recovery_error}")
                                logger.error(f"  Saving raw response for debugging...")
                                with open("debug_api_response.txt", "w") as f:
                                    f.write(response_text)
                                logger.error("  Full response saved to debug_api_response.txt")
                                return []

                    except Exception as inner_e:
                        logger.error(f"  Failed to extract JSON from markdown: {inner_e}")
                        return []
                else:
                    logger.error("  Response does not contain markdown code blocks")
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


class DescriptionParser:
    """Parses Jira description format to plain text"""

    @staticmethod
    def to_plain_text(description) -> str:
        """Convert Jira description to plain text
        Handles both v2 (string) and v3 (rich text object) formats"""
        if isinstance(description, str):
            return description
        if isinstance(description, dict):
            # Jira v3 rich text format
            if description.get("type") == "doc":
                return DescriptionParser._extract_text_from_doc(description)
        return ""

    @staticmethod
    def _extract_text_from_doc(doc: dict) -> str:
        """Extract plain text from Jira v3 document structure"""
        texts = []
        content = doc.get("content", [])
        for block in content:
            DescriptionParser._extract_from_block(block, texts)
        return " ".join(texts)

    @staticmethod
    def _extract_from_block(block: dict, texts: list) -> None:
        """Recursively extract text from document blocks"""
        if block.get("type") == "paragraph":
            for item in block.get("content", []):
                if item.get("type") == "text":
                    text = item.get("text", "")
                    if text.strip():
                        texts.append(text)
        elif block.get("type") in ("orderedList", "bulletList"):
            for item in block.get("content", []):
                DescriptionParser._extract_from_block(item, texts)
        elif block.get("type") == "listItem":
            for item in block.get("content", []):
                DescriptionParser._extract_from_block(item, texts)


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

    def run(self, issue_keys: List[str] = None, test_config: Dict[str, Any] = None) -> bool:
        """Execute test case generation pipeline

        Args:
            issue_keys: Optional list of specific issue keys to process (e.g., ['REB3-123', 'REB3-456'])
                       If None, processes up to max_issues
            test_config: Optional test configuration dictionary with:
                - test_types: List of test types to generate (positive, negative, edge-case, etc.)
                - priorities: List of priority levels (P1, P2, P3)
                - max_scenarios: Maximum scenarios per issue
                - custom_requirements: Custom requirements text
                - temperature: AI temperature/creativity level
        """
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

        # Use default test config if not provided
        if test_config is None:
            test_config = {
                'test_types': ['positive', 'negative', 'edge-case'],
                'priorities': ['P1', 'P2', 'P3'],
                'max_scenarios': 10,
                'custom_requirements': None,
                'temperature': 0.3
            }

        logger.info(f"Test Configuration:")
        logger.info(f"  Test Types: {', '.join(test_config['test_types'])}")
        logger.info(f"  Priorities: {', '.join(test_config['priorities'])}")
        logger.info(f"  Max Scenarios: {test_config['max_scenarios']}")
        logger.info(f"  Temperature: {test_config['temperature']}")
        if test_config.get('custom_requirements'):
            logger.info(f"  Custom Requirements: {test_config['custom_requirements']}")

        # Fetch issues
        if issue_keys:
            logger.info(f"Fetching {len(issue_keys)} specific issues: {', '.join(issue_keys)}")
            issues = []
            for key in issue_keys:
                jql = f"key = {key}"
                try:
                    fetched = self.jira.fetch_issues(limit=1, jql=jql)
                    issues.extend(fetched)
                except Exception as e:
                    logger.warning(f"Failed to fetch {key}: {e}")
            logger.info(f"Successfully fetched {len(issues)} issues")
        else:
            logger.info(f"Fetching issues (max {self.config.max_issues})...")
            issues = self.jira.fetch_issues(limit=self.config.max_issues)
            logger.info(f"Found {len(issues)} issues to process")

        # Generate test cases
        results = {
            "timestamp": datetime.now().isoformat(),
            "model": self.config.model,
            "testConfiguration": test_config,
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

                # Generate scenarios with custom configuration
                scenarios = self.generator.generate_scenarios(
                    issue,
                    preconditions,
                    test_types=test_config.get('test_types'),
                    custom_requirements=test_config.get('custom_requirements'),
                    temperature=test_config.get('temperature')
                )

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


def get_test_configuration() -> Dict[str, Any]:
    """Interactive configuration settings for test case generation"""
    print("\n" + "=" * 60)
    print("Test Generation Configuration")
    print("=" * 60)

    config = {}

    # Test types selection
    print("\nTest Types to Generate (select multiple, comma-separated):")
    print("  1. positive    - Happy path scenarios")
    print("  2. negative    - Error/failure scenarios")
    print("  3. edge-case   - Boundary conditions")
    print("  4. performance - Performance scenarios")
    print("  5. security    - Security scenarios")
    print("  6. usability   - User experience scenarios")
    print("  7. design      - Design validation scenarios")

    test_types_input = input("\nEnter options (default: 1,2,3): ").strip()
    if not test_types_input:
        test_types_input = "1,2,3"

    type_map = {
        '1': 'positive',
        '2': 'negative',
        '3': 'edge-case',
        '4': 'performance',
        '5': 'security',
        '6': 'usability',
        '7': 'design'
    }

    selected_types = []
    for t in test_types_input.split(','):
        t = t.strip()
        if t in type_map:
            selected_types.append(type_map[t])

    config['test_types'] = selected_types if selected_types else ['positive', 'negative', 'edge-case']
    print(f"✓ Selected test types: {', '.join(config['test_types'])}")

    # Priority filter
    print("\nPriority Levels (select multiple, comma-separated):")
    print("  1. P1 - Critical")
    print("  2. P2 - High")
    print("  3. P3 - Medium")

    priority_input = input("Enter options (default: 1,2,3): ").strip()
    if not priority_input:
        priority_input = "1,2,3"

    priority_map = {'1': 'P1', '2': 'P2', '3': 'P3'}
    selected_priorities = []
    for p in priority_input.split(','):
        p = p.strip()
        if p in priority_map:
            selected_priorities.append(priority_map[p])

    config['priorities'] = selected_priorities if selected_priorities else ['P1', 'P2', 'P3']
    print(f"✓ Selected priorities: {', '.join(config['priorities'])}")

    # Number of scenarios
    print("\nNumber of Scenarios per Issue (1-20):")
    scenarios_input = input("Enter number (default: 10): ").strip()
    try:
        config['max_scenarios'] = int(scenarios_input) if scenarios_input else 10
        config['max_scenarios'] = max(1, min(20, config['max_scenarios']))
    except ValueError:
        config['max_scenarios'] = 10
    print(f"✓ Max scenarios per issue: {config['max_scenarios']}")

    # Custom requirements/notes
    print("\nCustom Requirements (optional, press Enter to skip):")
    print("  Example: 'Focus on API validation', 'Include load testing', etc.")
    custom_requirements = input("Enter custom requirements: ").strip()
    config['custom_requirements'] = custom_requirements if custom_requirements else None
    if custom_requirements:
        print(f"✓ Custom requirements: {custom_requirements}")

    # Temperature (creativity level)
    print("\nCreativity Level (0.0 = Deterministic, 1.0 = Creative):")
    temp_input = input("Enter value 0.0-1.0 (default: 0.3): ").strip()
    try:
        config['temperature'] = float(temp_input) if temp_input else 0.3
        config['temperature'] = max(0.0, min(1.0, config['temperature']))
    except ValueError:
        config['temperature'] = 0.3
    print(f"✓ Temperature: {config['temperature']}")

    print("\n" + "=" * 60)
    print("Configuration Summary")
    print("=" * 60)
    print(f"Test Types: {', '.join(config['test_types'])}")
    print(f"Priorities: {', '.join(config['priorities'])}")
    print(f"Max Scenarios: {config['max_scenarios']}")
    print(f"Temperature: {config['temperature']}")
    if config['custom_requirements']:
        print(f"Requirements: {config['custom_requirements']}")
    print("=" * 60)

    return config


def select_issues_interactive(jira_client: 'JiraClient', max_issues: int = 50) -> List[str]:
    """Interactive menu to select specific Jira issues"""
    print("\n" + "=" * 60)
    print("Jira Issue Selector")
    print("=" * 60)
    print("\nOptions:")
    print("1. Generate for specific issue(s) - Enter comma-separated keys")
    print("2. Generate for all issues (up to " + str(max_issues) + ")")
    print("3. Cancel")
    print()

    choice = input("Select option (1-3): ").strip()

    if choice == "1":
        keys_input = input("\nEnter Jira issue key(s) (comma-separated, e.g., REB3-123,REB3-456): ").strip()
        issue_keys = [k.strip().upper() for k in keys_input.split(",") if k.strip()]
        if issue_keys:
            print(f"\n✓ Selected {len(issue_keys)} issue(s): {', '.join(issue_keys)}")
            return issue_keys
        else:
            print("✗ No valid issue keys provided")
            return None

    elif choice == "2":
        print(f"\n✓ Will generate for all issues (max {max_issues})")
        return []  # Empty list means fetch all

    elif choice == "3":
        print("✗ Cancelled")
        return None

    else:
        print("✗ Invalid option")
        return None


def main():
    """Entry point for the script"""
    import sys
    import traceback

    try:
        import argparse

        # Ensure logs are flushed immediately
        logging.getLogger().handlers[0].flush()
        logging.getLogger().handlers[1].flush()

        # Log environment for debugging
        logger.info("=== Script Environment ===")
        logger.info(f"JIRA_BASE_URL: {os.getenv('JIRA_BASE_URL', 'NOT SET')}")
        logger.info(f"JIRA_USER_EMAIL: {os.getenv('JIRA_USER_EMAIL', 'NOT SET')}")
        logger.info(f"JIRA_API_TOKEN: {'SET' if os.getenv('JIRA_API_TOKEN') else 'NOT SET'}")
        logger.info(f"ANTHROPIC_API_KEY: {'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")
        logger.info(f"OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
        logger.info(f"Script started with args: {sys.argv[1:]}")
        logger.info("=== End Environment ===")

        parser = argparse.ArgumentParser(
            description="Generate BDD test cases from Jira issues"
        )
        parser.add_argument(
            "--issues",
            type=str,
            help="Comma-separated list of issue keys to process (e.g., REB3-123,REB3-456)"
        )
        parser.add_argument(
            "--interactive",
            action="store_true",
            help="Show interactive menu to select issues"
        )
        parser.add_argument(
            "--skip-config",
            action="store_true",
            help="Skip configuration prompt and use defaults"
        )

        args = parser.parse_args()

        logger.info(f"Parsed args: issues={args.issues}, interactive={args.interactive}, skip_config={args.skip_config}")

        logger.info("Creating TestCaseGenerator...")
        generator = TestCaseGenerator()
        logger.info("TestCaseGenerator created successfully")

        # Determine which issues to process
        logger.info("Processing issue_keys...")
        issue_keys = None

        if args.issues:
            logger.info("Using provided issue keys")
            # Issues provided via command-line
            issue_keys = [k.strip().upper() for k in args.issues.split(",") if k.strip()]
            print(f"Processing specified issues: {', '.join(issue_keys)}\n")

        elif args.interactive or sys.stdin.isatty():
            # Interactive mode or running in terminal
            issue_keys = select_issues_interactive(generator.jira, generator.config.max_issues)
            if issue_keys is None:
                sys.exit(1)

        # Get test configuration (unless skipped)
        logger.info("Getting test configuration...")
        test_config = None
        if not args.skip_config and sys.stdin.isatty():
            logger.info("Interactive mode - getting test configuration")
            test_config = get_test_configuration()
        else:
            # Use defaults
            logger.info("Using default configuration")
            test_config = {
                'test_types': ['positive', 'negative', 'edge-case'],
                'priorities': ['P1', 'P2', 'P3'],
                'max_scenarios': 10,
                'custom_requirements': None,
                'temperature': 0.3
            }
            print("\nUsing default configuration (use --interactive to customize)")

        # Run generator with configuration
        logger.info(f"All preconditions met. Starting generator.run() with {len(issue_keys) if issue_keys else 0} issues...")
        sys.stdout.flush()
        sys.stderr.flush()
        logger.info("About to call generator.run()")
        try:
            success = generator.run(
                issue_keys=issue_keys if issue_keys else None,
                test_config=test_config
            )
            logger.info(f"generator.run() completed with success={success}")
            sys.exit(0 if success else 1)
        except Exception as e:
            logger.error(f"generator.run() failed: {e}", exc_info=True)
            raise

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        print(f"ERROR: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
