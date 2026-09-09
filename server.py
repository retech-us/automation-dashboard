#!/usr/bin/env python3
"""
Local development server for automation-dashboard
Serves on localhost:6060

Usage:
    python3 server.py
    Then visit: http://localhost:6060
"""

import http.server
import socketserver
import os
import json
import logging
import sys
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables

# Configuration
PORT = 6060
HOST = 'localhost'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DashboardHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler for dashboard"""

    def do_GET(self):
        """Handle GET requests"""
        # Log request
        logger.info(f"GET {self.path} - {self.client_address[0]}")

        # API endpoints
        if self.path == '/api/jira-issues':
            return self._handle_get_jira_issues()
        elif self.path == '/api/test-cases':
            return self._handle_get_test_cases()
        elif self.path.startswith('/api/test-cases/'):
            issue_key = self.path.split('/')[-1]
            return self._handle_get_test_case_for_issue(issue_key)

        # Serve static files from current directory
        if self.path == '/' or self.path == '/index.html':
            self.path = '/index.html'

        # Try to serve the file
        try:
            return super().do_GET()
        except Exception as e:
            logger.error(f"Error serving {self.path}: {e}")
            self.send_error(500, str(e))

    def do_POST(self):
        """Handle POST requests"""
        logger.info(f"POST {self.path} - {self.client_address[0]}")

        # API endpoints
        if self.path == '/api/verify-credentials':
            return self._handle_verify_credentials()
        elif self.path == '/api/generate-test-cases':
            return self._handle_generate_test_cases()
        else:
            self.send_error(404, "Not Found")

    def _handle_verify_credentials(self):
        """POST /api/verify-credentials - Verify user credentials"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            if not body:
                return self._send_json_response({"valid": False, "error": "No credentials provided"}, 400)

            request_data = json.loads(body)

            # Extract credentials
            jira_url = request_data.get('jira_base_url', '').strip()
            jira_email = request_data.get('jira_user_email', '').strip()
            jira_token = request_data.get('jira_api_token', '').strip()
            ai_provider = request_data.get('ai_provider', '').strip()

            # Validate Jira credentials
            if not all([jira_url, jira_email, jira_token]):
                return self._send_json_response({"valid": False, "error": "Missing Jira credentials"}, 400)

            # Validate AI provider credentials
            if ai_provider == 'anthropic':
                anthropic_key = request_data.get('anthropic_api_key', '').strip()
                if not anthropic_key:
                    return self._send_json_response({"valid": False, "error": "Missing Claude API key"}, 400)
                if not anthropic_key.startswith('sk-ant-'):
                    return self._send_json_response({"valid": False, "error": "Invalid Claude API key format"}, 400)
            elif ai_provider == 'openai':
                openai_key = request_data.get('openai_api_key', '').strip()
                if not openai_key:
                    return self._send_json_response({"valid": False, "error": "Missing OpenAI API key"}, 400)
                if not openai_key.startswith('sk-'):
                    return self._send_json_response({"valid": False, "error": "Invalid OpenAI API key format"}, 400)
            else:
                return self._send_json_response({"valid": False, "error": "Invalid AI provider"}, 400)

            # Test Jira connection
            import base64
            import urllib.request
            import urllib.error

            credentials = f"{jira_email}:{jira_token}"
            encoded = base64.b64encode(credentials.encode()).decode()
            url = f"{jira_url}/rest/api/3/myself"

            try:
                headers = {
                    'Authorization': f'Basic {encoded}',
                    'Content-Type': 'application/json'
                }
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as response:
                    jira_user = json.loads(response.read().decode('utf-8'))
                    logger.info(f"✓ Credentials verified for {jira_user.get('displayName', 'User')}")
                    return self._send_json_response({"valid": True, "user": jira_user.get('displayName', 'User')})
            except Exception as e:
                logger.error(f"Jira verification failed: {e}")
                return self._send_json_response({"valid": False, "error": f"Jira verification failed: {str(e)}"}, 400)

        except json.JSONDecodeError:
            return self._send_json_response({"valid": False, "error": "Invalid JSON"}, 400)
        except Exception as e:
            logger.error(f"Error verifying credentials: {e}")
            return self._send_json_response({"valid": False, "error": str(e)}, 500)

    def _handle_get_jira_issues(self):
        """GET /api/jira-issues - Return all Jira issues from mock data"""
        try:
            jira_file = Path('data/jira.json')
            if jira_file.exists():
                with open(jira_file, 'r') as f:
                    data = json.load(f)
                return self._send_json_response(data)
            else:
                return self._send_json_response({"issues": [], "total": 0})
        except Exception as e:
            logger.error(f"Error loading Jira issues: {e}")
            return self._send_json_response({"error": str(e)}, 500)

    def _handle_get_test_cases(self):
        """GET /api/test-cases - Return generated test cases"""
        try:
            tc_file = Path('data/test-cases.json')
            if tc_file.exists():
                with open(tc_file, 'r') as f:
                    data = json.load(f)
                return self._send_json_response(data)
            else:
                return self._send_json_response({"testCases": [], "totalIssues": 0})
        except Exception as e:
            logger.error(f"Error loading test cases: {e}")
            return self._send_json_response({"error": str(e)}, 500)

    def _handle_get_test_case_for_issue(self, issue_key):
        """GET /api/test-cases/:issueKey - Return test cases for specific issue"""
        try:
            tc_file = Path('data/test-cases.json')
            if tc_file.exists():
                with open(tc_file, 'r') as f:
                    data = json.load(f)
                    for tc in data.get('testCases', []):
                        if tc.get('issueKey') == issue_key:
                            return self._send_json_response(tc)
            return self._send_json_response({"error": "Not found"}, 404)
        except Exception as e:
            logger.error(f"Error loading test case for {issue_key}: {e}")
            return self._send_json_response({"error": str(e)}, 500)

    def _handle_generate_test_cases(self):
        """POST /api/generate-test-cases - Trigger test case generation with user credentials"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            if body:
                request_data = json.loads(body)
            else:
                request_data = {}

            # Get parameters
            issue_keys = request_data.get('issueKeys', [])
            max_issues = request_data.get('maxIssues', 50)

            logger.info(f"Generating test cases for {len(issue_keys)} issues...")

            # Set up environment with user credentials
            env = os.environ.copy()

            # Jira credentials (required)
            jira_url = request_data.get('jira_base_url', '').strip()
            jira_email = request_data.get('jira_user_email', '').strip()
            jira_token = request_data.get('jira_api_token', '').strip()
            ai_provider = request_data.get('ai_provider', '').strip()

            if not all([jira_url, jira_email, jira_token, ai_provider]):
                logger.error("Missing required credentials")
                return self._send_json_response({
                    "status": "error",
                    "message": "Missing required credentials"
                }, 400)

            # Set Jira environment variables
            env['JIRA_BASE_URL'] = jira_url
            env['JIRA_USER_EMAIL'] = jira_email
            env['JIRA_API_TOKEN'] = jira_token

            # Set AI provider credentials
            if ai_provider == 'anthropic':
                anthropic_key = request_data.get('anthropic_api_key', '').strip()
                if not anthropic_key:
                    return self._send_json_response({
                        "status": "error",
                        "message": "Missing Claude API key"
                    }, 400)
                env['ANTHROPIC_API_KEY'] = anthropic_key
                # Remove OpenAI key if set
                env.pop('OPENAI_API_KEY', None)
                logger.info(f"Using Claude (Anthropic) provider")
            elif ai_provider == 'openai':
                openai_key = request_data.get('openai_api_key', '').strip()
                if not openai_key:
                    return self._send_json_response({
                        "status": "error",
                        "message": "Missing OpenAI API key"
                    }, 400)
                env['OPENAI_API_KEY'] = openai_key
                # Set custom endpoint if provided
                openai_base = request_data.get('openai_api_base', '').strip()
                if openai_base:
                    env['OPENAI_API_BASE'] = openai_base
                    logger.info(f"Using OpenAI with custom endpoint: {openai_base}")
                else:
                    logger.info(f"Using OpenAI provider")
            else:
                return self._send_json_response({
                    "status": "error",
                    "message": "Invalid AI provider"
                }, 400)

            # Build command to run generator
            cmd = [
                sys.executable,
                'scripts/generate-test-cases.py'
            ]

            # Add issue keys if provided
            if issue_keys:
                cmd.append('--issues')
                cmd.append(','.join(issue_keys))

            logger.info(f"Running generator with command: {' '.join(cmd)}")

            # Run generator with credentials
            try:
                logger.info(f"Running command: {' '.join(cmd)}")
                logger.info(f"Environment: JIRA_BASE_URL={env.get('JIRA_BASE_URL')}, AI_PROVIDER={ai_provider}")

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)

                if result.returncode == 0:
                    # Load generated test cases
                    tc_file = Path('data/test-cases.json')
                    if tc_file.exists():
                        with open(tc_file, 'r') as f:
                            data = json.load(f)
                        logger.info(f"✓ Successfully generated test cases for {data.get('totalIssues', 0)} issues")
                        return self._send_json_response({
                            "status": "success",
                            "message": f"Generated test cases for {data.get('totalIssues', 0)} issues",
                            "data": data
                        })
                    else:
                        logger.warning("Generation complete but no results file found")
                        return self._send_json_response({
                            "status": "success",
                            "message": "Generation complete but no results file found"
                        })
                else:
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    logger.error(f"❌ Generator failed with return code {result.returncode}")
                    logger.error(f"STDOUT: {result.stdout[:500]}")
                    logger.error(f"STDERR: {result.stderr[:500]}")
                    return self._send_json_response({
                        "status": "error",
                        "message": f"Test case generation failed: {error_msg[:200]}"
                    }, 500)
            except subprocess.TimeoutExpired:
                logger.error("❌ Test case generation timed out (5 minutes)")
                return self._send_json_response({
                    "status": "error",
                    "message": "Test case generation timed out (5 minutes)"
                }, 500)
            except Exception as e:
                logger.error(f"❌ Error running generator: {str(e)}", exc_info=True)
                return self._send_json_response({
                    "status": "error",
                    "message": f"Failed to run generator: {str(e)[:200]}"
                }, 500)

        except json.JSONDecodeError:
            return self._send_json_response({"error": "Invalid JSON"}, 400)
        except Exception as e:
            logger.error(f"Error in generate handler: {e}")
            return self._send_json_response({"error": str(e)}, 500)

    def _send_json_response(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        response = json.dumps(data).encode('utf-8')
        self.wfile.write(response)

    def end_headers(self):
        """Add custom headers for development"""
        # Allow CORS for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')

        # Add content-type headers
        if self.path.endswith('.js'):
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
        elif self.path.endswith('.json'):
            self.send_header('Content-Type', 'application/json; charset=utf-8')
        elif self.path.endswith('.html'):
            self.send_header('Content-Type', 'text/html; charset=utf-8')
        elif self.path.endswith('.css'):
            self.send_header('Content-Type', 'text/css; charset=utf-8')

        super().end_headers()

    def log_message(self, format, *args):
        """Suppress default logging (we use our own)"""
        pass


def run_server():
    """Start the development server"""
    # Change to project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Create server
    handler = DashboardHTTPHandler
    httpd = socketserver.TCPServer((HOST, PORT), handler)

    # Print startup info
    logger.info("=" * 70)
    logger.info("Automation Dashboard - Local Development Server")
    logger.info("=" * 70)
    logger.info(f"✓ Server running on: http://{HOST}:{PORT}")
    logger.info(f"✓ Dashboard available at: http://{HOST}:{PORT}/index.html")
    logger.info(f"✓ Press CTRL+C to stop server")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Tips:")
    logger.info("  • Open DevTools (F12) to see console output")
    logger.info("  • Check 'Network' tab to see API calls")
    logger.info("  • Refresh page (Ctrl+R) to reload dashboard")
    logger.info("  • Hard refresh (Ctrl+Shift+R) to clear cache")
    logger.info("")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\n✓ Server stopped")
        httpd.server_close()
        exit(0)


if __name__ == '__main__':
    run_server()
