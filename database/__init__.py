"""
Database module for Automation Dashboard
Provides ORM models, connection management, repositories, and database utilities
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

from database.repositories import (
    SessionRepository,
    GenerationRepository,
    ScenarioRepository,
    SyncRepository,
    JiraIssueRepository,
    ProjectSettingsRepository,
    RepositoryFactory,
)

__all__ = [
    # Models
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
    # Repositories
    'SessionRepository',
    'GenerationRepository',
    'ScenarioRepository',
    'SyncRepository',
    'JiraIssueRepository',
    'ProjectSettingsRepository',
    'RepositoryFactory',
]
