"""
Day 2-3: Claude AI Integration Tests
Tests for BDDGenerator and PII sanitization
"""

import pytest
import json
import sys
import os
import importlib.util
from unittest.mock import Mock, patch, MagicMock

# Load generate_test_cases.py dynamically (module name has hyphen)
spec = importlib.util.spec_from_file_location(
    "generate_test_cases",
    os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate-test-cases.py')
)
generate_test_cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_test_cases)


class TestBDDGeneratorInit:
    """Tests for BDDGenerator initialization"""

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key-12345'})
    @patch('anthropic.Anthropic')
    def test_init_success(self, mock_anthropic):
        """Test successful Claude client initialization"""
        config = generate_test_cases.ConfigManager()
        config.model = "claude-3-5-sonnet-20241022"

        generator = generate_test_cases.BDDGenerator(config)

        assert generator.client is not None
        assert generator.provider == 'anthropic'
        mock_anthropic.assert_called_once_with(api_key='test-key-12345')

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test-openai-key'})
    @patch('openai.OpenAI')
    def test_init_openai_success(self, mock_openai):
        """Test successful OpenAI client initialization"""
        config = generate_test_cases.ConfigManager()
        config.model = "gpt-4"

        generator = generate_test_cases.BDDGenerator(config)

        assert generator.client is not None
        assert generator.provider == 'openai'
        mock_openai.assert_called_once_with(api_key='sk-test-openai-key')

    @patch.dict('os.environ', {}, clear=False)
    def test_init_no_api_key(self):
        """Test initialization with no API key"""
        import os
        # Ensure both keys are missing
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ.pop('OPENAI_API_KEY', None)

        config = generate_test_cases.ConfigManager()
        generator = generate_test_cases.BDDGenerator(config)

        assert generator.client is None
        assert generator.provider is None

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-key', 'OPENAI_API_KEY': 'sk-openai-key'})
    @patch('anthropic.Anthropic')
    def test_init_anthropic_preferred(self, mock_anthropic):
        """Test that Anthropic is preferred when both keys are set"""
        config = generate_test_cases.ConfigManager()

        generator = generate_test_cases.BDDGenerator(config)

        assert generator.provider == 'anthropic'
        mock_anthropic.assert_called_once()


class TestPIISanitizer:
    """Tests for PII redaction"""

    def test_sanitize_email(self):
        """Test email redaction"""
        text = "Contact user@example.com for support"
        sanitized = generate_test_cases.PIISanitizer.sanitize(text)

        assert "[EMAIL]" in sanitized
        assert "user@example.com" not in sanitized

    def test_sanitize_api_key(self):
        """Test API key redaction"""
        text = "Use api_key: sk-1234567890abcdef"
        sanitized = generate_test_cases.PIISanitizer.sanitize(text)

        assert "[SECRET]" in sanitized
        assert "sk-1234567890abcdef" not in sanitized

    def test_sanitize_password(self):
        """Test password redaction"""
        text = "Password: MySecurePass123"
        sanitized = generate_test_cases.PIISanitizer.sanitize(text)

        assert "[SECRET]" in sanitized
        assert "MySecurePass123" not in sanitized

    def test_sanitize_ip_address(self):
        """Test IP address redaction"""
        text = "Server at 192.168.1.100 is down"
        sanitized = generate_test_cases.PIISanitizer.sanitize(text)

        assert "[IP]" in sanitized
        assert "192.168.1.100" not in sanitized


class TestScenarioValidation:
    """Tests for BDD scenario validation"""

    @patch('anthropic.Anthropic')
    def test_validate_valid_scenario(self, mock_anthropic):
        """Test validation of a valid scenario"""
        config = generate_test_cases.ConfigManager()
        config.anthropic_api_key = "test-key"
        generator = generate_test_cases.BDDGenerator(config)

        valid_scenario = {
            "id": "SC-001",
            "title": "User logs in with valid credentials",
            "type": "positive",
            "category": "functional",
            "priority": "P1",
            "preconditions": [
                "Given user account exists",
                "And user is on login page"
            ],
            "steps": [
                {
                    "stepNumber": 1,
                    "action": "When user enters valid email",
                    "expectedResult": "Email is accepted"
                },
                {
                    "stepNumber": 2,
                    "action": "When user enters valid password",
                    "expectedResult": "Password is accepted"
                }
            ],
            "expectedResult": "User is logged in and redirected to dashboard with session stored",
            "automationHint": "Use Selenium WebDriver to find email input and password input fields",
            "coverage": ["AC1"]
        }

        assert generator._validate_scenario(valid_scenario) is True

    @patch('anthropic.Anthropic')
    def test_validate_missing_field(self, mock_anthropic):
        """Test validation fails for missing required field"""
        config = generate_test_cases.ConfigManager()
        config.anthropic_api_key = "test-key"
        generator = generate_test_cases.BDDGenerator(config)

        invalid_scenario = {
            "id": "SC-001",
            "title": "Test",
            # Missing 'type', 'preconditions', etc.
        }

        assert generator._validate_scenario(invalid_scenario) is False

    @patch('anthropic.Anthropic')
    def test_validate_invalid_priority(self, mock_anthropic):
        """Test validation fails for invalid priority"""
        config = generate_test_cases.ConfigManager()
        config.anthropic_api_key = "test-key"
        generator = generate_test_cases.BDDGenerator(config)

        scenario = {
            "id": "SC-001",
            "title": "Test scenario",
            "type": "positive",
            "category": "functional",
            "priority": "P99",  # Invalid
            "preconditions": ["Given something"],
            "steps": [{"stepNumber": 1, "action": "When user does X", "expectedResult": "Then Y happens"}],
            "expectedResult": "This is a valid expected result with enough content"
        }

        assert generator._validate_scenario(scenario) is False

    @patch('anthropic.Anthropic')
    def test_validate_invalid_precondition_format(self, mock_anthropic):
        """Test validation fails for invalid precondition format"""
        config = generate_test_cases.ConfigManager()
        config.anthropic_api_key = "test-key"
        generator = generate_test_cases.BDDGenerator(config)

        scenario = {
            "id": "SC-001",
            "title": "Test scenario",
            "type": "positive",
            "category": "functional",
            "priority": "P1",
            "preconditions": ["user is logged in"],  # Should start with Given/And
            "steps": [{"stepNumber": 1, "action": "When user does X", "expectedResult": "Then Y happens"}],
            "expectedResult": "This is a valid expected result with enough content"
        }

        assert generator._validate_scenario(scenario) is False

    @patch('anthropic.Anthropic')
    def test_validate_short_expected_result(self, mock_anthropic):
        """Test validation fails for short expected result"""
        config = generate_test_cases.ConfigManager()
        config.anthropic_api_key = "test-key"
        generator = generate_test_cases.BDDGenerator(config)

        scenario = {
            "id": "SC-001",
            "title": "Test scenario",
            "type": "positive",
            "category": "functional",
            "priority": "P1",
            "preconditions": ["Given user is logged in"],
            "steps": [{"stepNumber": 1, "action": "When user does X", "expectedResult": "Then Y happens"}],
            "expectedResult": "Short"  # Too short (< 20 chars)
        }

        assert generator._validate_scenario(scenario) is False


class TestBDDGeneratorScenarios:
    """Tests for BDD scenario generation"""

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('anthropic.Anthropic')
    def test_generate_scenarios_success(self, mock_anthropic, mock_jira_issue):
        """Test successful scenario generation"""
        config = generate_test_cases.ConfigManager()

        # Mock Claude response
        mock_instance = MagicMock()
        mock_anthropic.return_value = mock_instance

        scenarios_json = json.dumps([
            {
                "id": "SC-001",
                "title": "User logs in successfully",
                "type": "positive",
                "category": "functional",
                "priority": "P1",
                "preconditions": ["Given user account exists", "And user is on login page"],
                "steps": [
                    {"stepNumber": 1, "action": "When user enters valid email", "expectedResult": "Email accepted"},
                    {"stepNumber": 2, "action": "When user clicks login", "expectedResult": "Login successful"}
                ],
                "expectedResult": "User is logged in and redirected to dashboard successfully",
                "automationHint": "Use Selenium for automation",
                "coverage": ["AC1"]
            }
        ])

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=scenarios_json)]
        mock_instance.messages.create.return_value = mock_response

        generator = generate_test_cases.BDDGenerator(config)
        preconditions = ["Given user account exists", "And user is on login page"]

        scenarios = generator.generate_scenarios(mock_jira_issue, preconditions)

        assert len(scenarios) == 1
        assert scenarios[0]["id"] == "SC-001"
        assert scenarios[0]["type"] == "positive"

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('anthropic.Anthropic')
    def test_generate_scenarios_invalid_json(self, mock_anthropic, mock_jira_issue):
        """Test handling of invalid JSON response from Claude"""
        config = generate_test_cases.ConfigManager()

        mock_instance = MagicMock()
        mock_anthropic.return_value = mock_instance

        # Invalid JSON response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="{invalid json")]
        mock_instance.messages.create.return_value = mock_response

        generator = generate_test_cases.BDDGenerator(config)
        preconditions = ["Given something"]

        scenarios = generator.generate_scenarios(mock_jira_issue, preconditions)

        assert scenarios == []

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('anthropic.Anthropic')
    def test_generate_scenarios_custom_test_types(self, mock_anthropic, mock_jira_issue):
        """Test scenario generation with custom test types"""
        config = generate_test_cases.ConfigManager()

        mock_instance = MagicMock()
        mock_anthropic.return_value = mock_instance

        scenarios_json = json.dumps([
            {
                "id": "SC-001",
                "title": "Security test",
                "type": "security",
                "category": "security",
                "priority": "P1",
                "preconditions": ["Given user is logged in"],
                "steps": [
                    {"stepNumber": 1, "action": "When user attempts SQL injection", "expectedResult": "Attack blocked"}
                ],
                "expectedResult": "System rejects SQL injection attempt and logs security event successfully",
                "automationHint": "Test security",
                "coverage": ["AC1"]
            }
        ])

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=scenarios_json)]
        mock_instance.messages.create.return_value = mock_response

        generator = generate_test_cases.BDDGenerator(config)
        preconditions = ["Given user is logged in"]
        test_types = ["security"]

        scenarios = generator.generate_scenarios(mock_jira_issue, preconditions, test_types)

        assert len(scenarios) == 1
        assert scenarios[0]["type"] == "security"
