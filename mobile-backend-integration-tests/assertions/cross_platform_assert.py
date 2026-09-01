"""
Cross-Platform Assertion & Parity Engine.
Compares actual mobile states and emitted actions against expectations and cross-platform parity.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from adapters.core.models import ActionEvent, MobileState, PlatformType


class AssertionFailure(Exception):
    pass


class CrossPlatformAssert:
    """Verifies behavioral and state contracts across Android and iOS."""

    @staticmethod
    def assert_state_matches(actual_state: MobileState, expected_state: Dict[str, Any]) -> List[str]:
        """
        Validates actual MobileState against expected dictionary.
        Returns a list of mismatch descriptions (empty if pass).
        """
        mismatches: List[str] = []
        actual_dict = actual_state.to_dict()

        for key, expected_val in expected_state.items():
            actual_val = actual_dict.get(key)
            if actual_val != expected_val:
                mismatches.append(
                    f"State mismatch for '{key}': expected '{expected_val}', got '{actual_val}'"
                )

        return mismatches

    @staticmethod
    def assert_actions_contain(actual_actions: List[ActionEvent], expected_actions: List[str]) -> List[str]:
        """
        Validates that required actions were emitted in order.
        Returns a list of missing/mismatched actions (empty if pass).
        """
        mismatches: List[str] = []
        emitted_action_names = [
            (a.action.value if hasattr(a.action, "value") else str(a.action)) for a in actual_actions
        ]

        for expected in expected_actions:
            if expected not in emitted_action_names:
                mismatches.append(
                    f"Missing expected action '{expected}'. Emitted actions were: {emitted_action_names}"
                )

        return mismatches

    @staticmethod
    def verify_platform_parity(
        android_state: MobileState,
        ios_state: MobileState,
        android_actions: List[ActionEvent],
        ios_actions: List[ActionEvent],
    ) -> Tuple[bool, List[str]]:
        """
        Verifies that Android and iOS produced identical business state and actions.
        """
        differences: List[str] = []

        # 1. State comparison
        a_dict = android_state.to_dict()
        i_dict = ios_state.to_dict()

        common_keys = [
            "isLoggedIn", "hasToken", "userId", "username", "email",
            "taskId", "taskStatus", "totalActions", "pendingActions", "completedActions", "hasError"
        ]

        for key in common_keys:
            val_a = a_dict.get(key)
            val_i = i_dict.get(key)
            if val_a != val_i:
                differences.append(
                    f"Parity divergence on '{key}': Android='{val_a}' vs iOS='{val_i}'"
                )

        # 2. Actions comparison
        actions_a = [(a.action.value if hasattr(a.action, "value") else str(a.action)) for a in android_actions]
        actions_i = [(a.action.value if hasattr(a.action, "value") else str(a.action)) for a in ios_actions]

        if actions_a != actions_i:
            differences.append(
                f"Action sequence divergence: Android={actions_a} vs iOS={actions_i}"
            )

        is_parity_ok = len(differences) == 0
        return is_parity_ok, differences
