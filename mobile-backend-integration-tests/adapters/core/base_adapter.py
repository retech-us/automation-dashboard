"""
Base Mobile Adapter Interface for Headless Execution.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from adapters.core.models import ActionEvent, MobileState, PlatformType, ScenarioResult


class BaseMobileAdapter(ABC):
    """Abstract contract that both Android and iOS adapters implement."""

    @property
    @abstractmethod
    def platform(self) -> PlatformType:
        """Returns the target platform."""
        pass

    @abstractmethod
    def initialize(self, base_url: str, custom_headers: Optional[Dict[str, str]] = None):
        """Initializes the mobile network client and headless DI container."""
        pass

    @abstractmethod
    def authenticate(self, username: str, password: str, device_id: str = "HEADLESS-001") -> MobileState:
        """Executes the mobile production authentication flow."""
        pass

    @abstractmethod
    def fetch_user_profile(self) -> MobileState:
        """Executes user profile fetch (e.g. GET /api/v4/me/)."""
        pass

    @abstractmethod
    def fetch_task_details(self, task_id: int) -> MobileState:
        """Executes task details fetch and processes action metrics."""
        pass

    @abstractmethod
    def get_state(self) -> MobileState:
        """Returns the current snapshot of mobile state."""
        pass

    @abstractmethod
    def get_actions(self) -> List[ActionEvent]:
        """Returns all recorded mobile action events during the session."""
        pass

    @abstractmethod
    def clear_state(self):
        """Cleans up in-memory state and recorded actions for test isolation."""
        pass

    @abstractmethod
    def cleanup(self):
        """Releases client sessions and memory resources."""
        pass
