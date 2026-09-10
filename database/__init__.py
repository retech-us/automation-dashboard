"""
Database module for Automation Dashboard
Provides ORM models, connection management, and database utilities
"""

from database.models import (
    Base,
    Session,
    JiraIssue,
    TestCaseGeneration,
    TestScenario,
    SyncHistory,
    AcceptanceCriteriaCoverage,
    ProjectSettings,
    JiraCustomFields,
    DatabaseManager,
    db_manager,
)

__all__ = [
    'Base',
    'Session',
    'JiraIssue',
    'TestCaseGeneration',
    'TestScenario',
    'SyncHistory',
    'AcceptanceCriteriaCoverage',
    'ProjectSettings',
    'JiraCustomFields',
    'DatabaseManager',
    'db_manager',
]
