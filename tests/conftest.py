"""
Pytest configuration and shared fixtures for Test Case Creator plugin tests
"""

import pytest
import os
import sys
import json
from unittest.mock import Mock, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_jira_issue():
    """Mock Jira issue for testing"""
    return {
        "key": "TEST-001",
        "summary": "User login functionality",
        "description": """
        Users should be able to log in with valid credentials.

        System must validate username and password format.
        API authentication requires JWT token.
        Multi-store configuration must be enabled.
        """,
        "fields": {
            "issuetype": {"name": "Story"},
            "status": {"name": "In Progress"},
            "attachment": [
                {
                    "id": "123",
                    "filename": "requirements.pdf",
                    "mimeType": "application/pdf",
                    "size": 102400,
                    "content": "http://jira.example.com/attachment/123"
                }
            ],
            "customfield_10014": "Epic Link"  # Jira epic
        }
    }


@pytest.fixture
def mock_bdd_scenario():
    """Mock BDD scenario output for testing"""
    return {
        "id": "TEST-001-001",
        "title": "Valid credentials login successfully",
        "type": "positive",
        "category": "functional",
        "priority": "P1",
        "preconditions": [
            "User is on login page",
            "Database has test account",
            "JWT authentication is enabled"
        ],
        "steps": [
            {
                "stepNumber": 1,
                "action": "User enters valid username",
                "expectedResult": "Username field populated"
            },
            {
                "stepNumber": 2,
                "action": "User enters valid password",
                "expectedResult": "Password field populated"
            },
            {
                "stepNumber": 3,
                "action": "User clicks login button",
                "expectedResult": "Login API called with JWT token"
            }
        ],
        "expectedResult": "User successfully logged in and redirected to dashboard",
        "automationHint": "Use Selenium WebDriver, locate elements by id/xpath",
        "tags": ["@positive", "@smoke", "@critical"],
        "coverage": ["AC1", "AC2"]
    }


@pytest.fixture
def mock_claude_response():
    """Mock Claude API response"""
    return {
        "id": "msg_123abc",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": json.dumps([
                    {
                        "id": "SC-001",
                        "title": "Valid login scenario",
                        "preconditions": ["Given user is on login page"],
                        "steps": [
                            {"step": "When user enters credentials", "expected": "Login succeeds"}
                        ]
                    }
                ])
            }
        ],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 500, "output_tokens": 300}
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
    monkeypatch.setenv("JIRA_USER_EMAIL", "test@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "test-token-12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-12345")
    monkeypatch.setenv("TEST_CASE_CREATOR_ENABLED", "true")


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing attachment parsing"""
    # Minimal PDF structure for testing
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Content) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000227 00000 n
0000000327 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
422
%%EOF"""
