"""
Utility functions for Test Case Creator plugin
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class JSONValidator:
    """Validates JSON structures for test cases"""

    REQUIRED_SCENARIO_FIELDS = [
        'id', 'title', 'type', 'category', 'priority',
        'preconditions', 'steps', 'expectedResult', 'automationHint', 'coverage'
    ]

    REQUIRED_STEP_FIELDS = ['stepNumber', 'action', 'expectedResult']

    VALID_TYPES = ['positive', 'negative', 'edge-case', 'performance', 'security', 'usability', 'design']
    VALID_CATEGORIES = ['functional', 'validation', 'performance', 'security', 'ux', 'design']
    VALID_PRIORITIES = ['P1', 'P2', 'P3', 'P4', 'P5']

    @classmethod
    def validate_scenario(cls, scenario: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a single BDD scenario.

        Returns:
            (is_valid, error_message)
        """
        # Check required fields
        for field in cls.REQUIRED_SCENARIO_FIELDS:
            if field not in scenario:
                return False, f"Missing required field: {field}"

        # Validate type
        if scenario['type'] not in cls.VALID_TYPES:
            return False, f"Invalid type: {scenario['type']}. Must be one of: {', '.join(cls.VALID_TYPES)}"

        # Validate category
        if scenario['category'] not in cls.VALID_CATEGORIES:
            return False, f"Invalid category: {scenario['category']}"

        # Validate priority
        if scenario['priority'] not in cls.VALID_PRIORITIES:
            return False, f"Invalid priority: {scenario['priority']}"

        # Validate preconditions (should be list of strings starting with Given/And)
        if not isinstance(scenario['preconditions'], list):
            return False, "Preconditions must be a list"
        if len(scenario['preconditions']) == 0:
            return False, "At least one precondition required"

        for pre in scenario['preconditions']:
            if not isinstance(pre, str):
                return False, "Precondition must be string"
            if not pre.strip().lower().startswith(('given', 'and')):
                return False, f"Precondition must start with 'Given' or 'And': {pre}"

        # Validate steps
        if not isinstance(scenario['steps'], list):
            return False, "Steps must be a list"
        if len(scenario['steps']) == 0:
            return False, "At least one step required"
        if len(scenario['steps']) > 10:
            return False, "Maximum 10 steps per scenario"

        for i, step in enumerate(scenario['steps']):
            if not isinstance(step, dict):
                return False, f"Step {i} must be a dict"
            for field in cls.REQUIRED_STEP_FIELDS:
                if field not in step:
                    return False, f"Step {i} missing field: {field}"
            if not isinstance(step['stepNumber'], int):
                return False, f"Step {i} stepNumber must be int"
            if step['stepNumber'] != i + 1:
                return False, f"Step numbers must be sequential (step {i} has number {step['stepNumber']})"

        # Validate expected result
        if not isinstance(scenario['expectedResult'], str):
            return False, "Expected result must be string"
        if len(scenario['expectedResult']) < 20:
            return False, "Expected result too short (min 20 chars)"

        # Validate coverage (should be list of AC references)
        if not isinstance(scenario['coverage'], list):
            return False, "Coverage must be a list"
        if len(scenario['coverage']) == 0:
            return False, "Coverage must include at least one AC"

        return True, None

    @classmethod
    def validate_scenarios_array(cls, scenarios: List[Dict]) -> tuple[List[Dict], List[str]]:
        """
        Validate array of scenarios.

        Returns:
            (valid_scenarios, error_messages)
        """
        valid = []
        errors = []

        for i, scenario in enumerate(scenarios):
            is_valid, error = cls.validate_scenario(scenario)
            if is_valid:
                valid.append(scenario)
            else:
                errors.append(f"Scenario {i}: {error}")

        return valid, errors


class PreconditionFormatter:
    """Formats preconditions for BDD scenarios"""

    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """
        Extract configuration/requirement keywords from text.

        Looks for patterns like:
        - "must be X"
        - "should be X"
        - "requires X"
        - "configured as X"
        - "enabled/disabled"
        """
        keywords = []

        # Pattern: "must be / should be / requires / configured"
        patterns = [
            r'(?:must|should)\s+be\s+([^.;,\n]+)',
            r'requires?\s+([^.;,\n]+)',
            r'configured?\s+(?:as|to)\s+([^.;,\n]+)',
            r'([^.;,\n]+?)\s+(?:must|should)\s+be\s+(?:enabled|disabled|available)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(matches)

        # Extract bullet points that look like requirements
        bullets = re.findall(r'[-•*]\s+([^.\n]+)', text)
        keywords.extend(bullets)

        return [k.strip() for k in keywords if len(k.strip()) > 10]

    @staticmethod
    def format_as_given(text: str) -> str:
        """Convert text to BDD 'Given' statement"""
        text = text.strip()

        # Remove common prefixes
        for prefix in ['Given', 'And', 'When', 'Then', '- ', '• ', '* ']:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()

        # Capitalize appropriately
        if not text[0].isupper():
            text = text[0].upper() + text[1:]

        return f"Given {text}"

    @staticmethod
    def deduplicate(preconditions: List[str]) -> List[str]:
        """Remove duplicate/similar preconditions"""
        seen = set()
        result = []

        for pre in preconditions:
            # Normalize for comparison
            normalized = pre.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                result.append(pre)

        return result


class AcceptanceCriteriaExtractor:
    """Extracts AC from Jira issue fields"""

    @staticmethod
    def extract_from_description(description: str) -> Dict[str, str]:
        """
        Extract acceptance criteria from description text.

        Looks for patterns like:
        - "AC1: Description"
        - "Acceptance Criteria: ..."
        - Numbered lists after "Acceptance Criteria" header
        """
        ac_dict = {}

        # Pattern: "AC1: ...", "AC2: ...", etc.
        ac_patterns = re.findall(r'AC(\d+):\s*([^.\n]+)', description, re.IGNORECASE)
        for ac_num, ac_text in ac_patterns:
            ac_dict[f'AC{ac_num}'] = ac_text.strip()

        # Pattern: "Acceptance Criteria:" followed by numbered list
        ac_section = re.search(
            r'(?:Acceptance Criteria|AC):\s*\n((?:[\d]+\.|[-•*])\s+[^\n]+(?:\n(?:[\d]+\.|[-•*])\s+[^\n]+)*)',
            description,
            re.IGNORECASE
        )

        if ac_section:
            ac_items = re.findall(r'(?:[\d]+\.|[-•*])\s+([^\n]+)', ac_section.group(1))
            for i, ac_text in enumerate(ac_items, 1):
                key = f'AC{i}' if f'AC{i}' not in ac_dict else f'AC{i}_{i}'
                ac_dict[key] = ac_text.strip()

        return ac_dict

    @staticmethod
    def format_for_prompt(ac_dict: Dict[str, str]) -> str:
        """Format AC dictionary for Claude prompt"""
        if not ac_dict:
            return "No explicit acceptance criteria provided"

        lines = []
        for key, value in sorted(ac_dict.items()):
            lines.append(f"  {key}: {value}")

        return "\n".join(lines)


class MarkdownExporter:
    """Exports test cases to markdown format"""

    @staticmethod
    def export(scenarios: List[Dict], issue_summary: str, issue_key: str = None) -> str:
        """
        Export scenarios to markdown.

        Format:
        # Test Cases for [Issue]

        **Issue:** KEY
        **Summary:** Title

        Generated on: Date

        ## Scenario 1: ...
        ...
        """
        lines = []

        # Header
        if issue_key:
            lines.append(f"# Test Cases for {issue_key}")
        else:
            lines.append("# Test Cases")

        lines.append(f"\n**Summary:** {issue_summary}")
        lines.append(f"\nGenerated on: {__import__('datetime').datetime.now().isoformat()}\n")

        # Scenarios
        for scenario in scenarios:
            lines.append(f"\n## Scenario {scenario['id']}: {scenario['title']}\n")
            lines.append(f"**Type:** {scenario['type']} | **Priority:** {scenario['priority']} | **Category:** {scenario['category']}\n")

            # Preconditions
            lines.append("### Preconditions\n")
            for pre in scenario['preconditions']:
                lines.append(f"- {pre}")
            lines.append("")

            # Steps
            lines.append("### Steps\n")
            for step in scenario['steps']:
                lines.append(f"{step['stepNumber']}. **Action:** {step['action']}")
                lines.append(f"   **Expected:** {step['expectedResult']}\n")

            # Expected Result
            lines.append(f"### Expected Result\n")
            lines.append(f"{scenario['expectedResult']}\n")

            # Automation Hint
            if scenario.get('automationHint'):
                lines.append(f"### Automation Hint\n")
                lines.append(f"```\n{scenario['automationHint']}\n```\n")

            # Coverage
            if scenario.get('coverage'):
                lines.append(f"### Coverage\n")
                lines.append(f"Maps to: {', '.join(scenario['coverage'])}\n")

            lines.append("---\n")

        return "\n".join(lines)


class CostTracker:
    """Tracks API usage and costs"""

    MODELS = {
        'claude-3-5-sonnet-20241022': {'input': 0.003, 'output': 0.015},  # Per 1K tokens
        'claude-3-opus-20250219': {'input': 0.015, 'output': 0.075},
        'claude-3-haiku-20250307': {'input': 0.00080, 'output': 0.0024},
    }

    @classmethod
    def calculate_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for API call"""
        if model not in cls.MODELS:
            logger.warning(f"Unknown model: {model}")
            return 0.0

        rates = cls.MODELS[model]
        input_cost = (input_tokens / 1000) * rates['input']
        output_cost = (output_tokens / 1000) * rates['output']

        return input_cost + output_cost

    @staticmethod
    def format_cost_summary(costs: List[Dict]) -> Dict[str, Any]:
        """Format cost summary for reporting"""
        total_cost = sum(c.get('cost', 0) for c in costs)
        total_input_tokens = sum(c.get('input_tokens', 0) for c in costs)
        total_output_tokens = sum(c.get('output_tokens', 0) for c in costs)

        return {
            'total_cost_usd': round(total_cost, 4),
            'total_input_tokens': total_input_tokens,
            'total_output_tokens': total_output_tokens,
            'total_tokens': total_input_tokens + total_output_tokens,
            'api_calls': len(costs),
            'average_cost_per_call': round(total_cost / len(costs), 4) if costs else 0,
        }
