"""
Day 1: Jira Integration Tests
Tests for JiraClient.fetch_issues() and download_attachment()
"""

import pytest
import responses
import json
import os
import importlib.util
from unittest.mock import Mock, patch

# Load generate_test_cases.py dynamically (module name has hyphen)
spec = importlib.util.spec_from_file_location(
    "generate_test_cases",
    os.path.join(os.path.dirname(__file__), '..', 'scripts', 'generate-test-cases.py')
)
generate_test_cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_test_cases)


class TestJiraClientFetchIssues:
    """Tests for fetching issues from Jira"""

    @responses.activate
    def test_fetch_issues_success(self, mock_jira_issue):
        """Test successful issue fetch"""
        responses.add(
            responses.POST,
            "https://test.atlassian.net/rest/api/3/search/jql",
            json={
                "issues": [mock_jira_issue],
                "total": 1,
                "startAt": 0,
                "maxResults": 1
            },
            status=200
        )

        config = generate_test_cases.ConfigManager()
        config.jira_base_url = "https://test.atlassian.net"
        config.jira_user_email = "test@example.com"
        config.jira_api_token = "test-token"

        client = generate_test_cases.JiraClient(config)
        issues = client.fetch_issues(limit=10)

        assert len(issues) > 0
        assert issues[0]['key'] == 'TEST-001'

    @responses.activate
    def test_fetch_issues_empty(self):
        """Test handling of empty results"""
        responses.add(
            responses.POST,
            "https://test.atlassian.net/rest/api/3/search/jql",
            json={"issues": [], "total": 0},
            status=200
        )

        config = generate_test_cases.ConfigManager()
        config.jira_base_url = "https://test.atlassian.net"
        config.jira_api_token = "test-token"

        client = generate_test_cases.JiraClient(config)
        issues = client.fetch_issues(limit=10)

        assert len(issues) == 0

    @responses.activate
    def test_fetch_issues_pagination(self):
        """Test pagination of issue results"""
        # First page
        responses.add(
            responses.POST,
            "https://test.atlassian.net/rest/api/3/search/jql",
            json={
                "issues": [{"key": f"TEST-{i}", "fields": {}} for i in range(100)],
                "total": 150,
                "maxResults": 100
            },
            status=200
        )

        # Second page
        responses.add(
            responses.POST,
            "https://test.atlassian.net/rest/api/3/search/jql",
            json={
                "issues": [{"key": f"TEST-{i}", "fields": {}} for i in range(100, 150)],
                "total": 150,
                "maxResults": 50
            },
            status=200
        )

        config = generate_test_cases.ConfigManager()
        config.jira_base_url = "https://test.atlassian.net"
        config.jira_api_token = "test-token"

        client = generate_test_cases.JiraClient(config)
        issues = client.fetch_issues(limit=150)

        assert len(issues) == 150


class TestJiraClientDownloadAttachment:
    """Tests for downloading attachments"""

    @responses.activate
    def test_download_attachment_success(self):
        """Test successful attachment download"""
        test_content = b"PDF content here"

        responses.add(
            responses.GET,
            "https://test.atlassian.net/attachment/123",
            body=test_content,
            status=200,
            headers={"content-length": str(len(test_content))}
        )

        config = generate_test_cases.ConfigManager()
        config.jira_base_url = "https://test.atlassian.net"
        config.jira_api_token = "test-token"
        config.max_attachment_mb = 10

        client = generate_test_cases.JiraClient(config)
        result = client.download_attachment("https://test.atlassian.net/attachment/123")

        assert result == test_content

    def test_download_attachment_size_limit(self):
        """Test rejection of oversized attachments"""
        config = generate_test_cases.ConfigManager()
        config.jira_base_url = "https://test.atlassian.net"
        config.jira_api_token = "test-token"
        config.max_attachment_mb = 10

        client = generate_test_cases.JiraClient(config)

        # Mock response with large content-length
        with patch('urllib.request.urlopen') as mock_open:
            mock_response = Mock()
            mock_response.headers.get.return_value = str(50 * 1024 * 1024)  # 50MB
            mock_open.return_value.__enter__.return_value = mock_response

            result = client.download_attachment("https://test.atlassian.net/attachment/999")

            assert result is None

    @responses.activate
    def test_download_attachment_timeout(self):
        """Test timeout handling"""
        config = generate_test_cases.ConfigManager()
        config.jira_base_url = "https://test.atlassian.net"
        config.jira_api_token = "test-token"

        client = generate_test_cases.JiraClient(config)

        with patch('urllib.request.urlopen', side_effect=TimeoutError):
            result = client.download_attachment("https://test.atlassian.net/attachment/123")
            assert result is None


class TestPreconditionExtraction:
    """Tests for extracting preconditions from issues"""

    def test_extract_from_description(self, mock_jira_issue):
        """Test extracting preconditions from description"""
        issue = {
            "fields": {
                "description": "Users must be authenticated. System should have database configured. AC1: User is logged in"
            }
        }

        preconditions = generate_test_cases.PreconditionExtractor.extract(issue)

        assert len(preconditions) > 0
        assert any("authenticated" in p.lower() for p in preconditions)

    def test_extract_empty_description(self):
        """Test handling of empty description"""
        issue = {"fields": {"description": ""}}
        preconditions = generate_test_cases.PreconditionExtractor.extract(issue)

        assert len(preconditions) == 0

    def test_extract_with_attachment_content(self):
        """Test extracting from attachment content"""
        issue = {"fields": {"description": ""}}
        attachment_content = "System requires database configured and API endpoint available"

        preconditions = generate_test_cases.PreconditionExtractor.extract(issue, attachment_content)

        assert len(preconditions) > 0
