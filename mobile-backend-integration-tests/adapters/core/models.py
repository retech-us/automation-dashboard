"""
Data Models and Enums for the Headless Mobile Integration Test Framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PlatformType(str, Enum):
    ANDROID = "android"
    IOS = "ios"


class ActionType(str, Enum):
    AUTH_INITIATED = "AUTH_INITIATED"
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILED = "AUTH_FAILED"
    USER_PROFILE_FETCHED = "USER_PROFILE_FETCHED"
    TASK_LOADED = "TASK_LOADED"
    TASKS_LIST_LOADED = "TASKS_LIST_LOADED"
    TASK_STATUS_CHANGED = "TASK_STATUS_CHANGED"
    CATEGORIES_LOADED = "CATEGORIES_LOADED"
    PLANOGRAM_LOADED = "PLANOGRAM_LOADED"
    SHIFT_STATUS_LOADED = "SHIFT_STATUS_LOADED"
    UPLOAD_REQUESTED = "UPLOAD_REQUESTED"
    IMAGE_UPLOADED = "IMAGE_UPLOADED"
    UPLOAD_FINISHED = "UPLOAD_FINISHED"
    PROCESSING_STATUS_POLL = "PROCESSING_STATUS_POLL"
    COMPLIANCE_CALCULATED = "COMPLIANCE_CALCULATED"
    ACTION_UPDATED = "ACTION_UPDATED"
    STATE_CHANGED = "STATE_CHANGED"
    ERROR_OCCURRED = "ERROR_OCCURRED"


@dataclass
class ActionEvent:
    action: ActionType | str
    timestamp: float
    platform: PlatformType
    entity_id: Optional[str | int] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value if isinstance(self.action, ActionType) else self.action,
            "timestamp": self.timestamp,
            "platform": self.platform.value if isinstance(self.platform, PlatformType) else self.platform,
            "entityId": self.entity_id,
            "payload": self.payload,
        }


@dataclass
class MobileState:
    platform: PlatformType
    is_logged_in: bool = False
    auth_token: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    current_task_id: Optional[int] = None
    task_status: Optional[str] = None
    total_actions: Optional[int] = None
    pending_actions: Optional[int] = None
    completed_actions: Optional[int] = None
    has_categories: bool = False
    categories_count: int = 0
    pog_id: Optional[int] = None
    pog_facings_count: int = 0
    has_tasks: bool = False
    tasks_count: int = 0
    shift_is_active: bool = False
    shift_id: Optional[int] = None
    upload_id: Optional[int] = None
    processing_id: Optional[int] = None
    processing_status: Optional[str] = None
    compliance_score: Optional[float] = None
    detected_facings: Optional[int] = None
    missing_facings: Optional[int] = None
    oos_items_count: Optional[int] = None
    has_error: bool = False
    last_error: Optional[str] = None
    custom_state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform.value if isinstance(self.platform, PlatformType) else self.platform,
            "isLoggedIn": self.is_logged_in,
            "hasToken": bool(self.auth_token),
            "userId": self.user_id,
            "username": self.username,
            "email": self.email,
            "taskId": self.current_task_id,
            "taskStatus": self.task_status,
            "totalActions": self.total_actions,
            "pendingActions": self.pending_actions,
            "completedActions": self.completed_actions,
            "hasError": self.has_error,
            "lastError": self.last_error,
            "custom": self.custom_state,
        }


@dataclass
class StepResult:
    step_name: str
    status: str  # "PASS", "FAIL", "SKIPPED"
    duration_ms: float
    request_summary: Dict[str, Any]
    response_summary: Dict[str, Any]
    captured_actions: List[ActionEvent]
    resulting_state: MobileState
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None


@dataclass
class ScenarioResult:
    scenario_id: str
    scenario_name: str
    platform: PlatformType
    status: str  # "PASS", "FAIL"
    duration_ms: float
    step_results: List[StepResult] = field(default_factory=list)
    failure_reason: Optional[str] = None
