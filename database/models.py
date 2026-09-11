"""
SQLAlchemy ORM Models for Automation Dashboard
Database models for sessions, test cases, Jira integration, and sync tracking
"""

from datetime import datetime, timedelta
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    JSON, ForeignKey, UniqueConstraint, Index, CheckConstraint, func, create_engine
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import uuid

Base = declarative_base()


class Session(Base):
    """User session with Jira and AI credentials"""
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), unique=True, nullable=False, index=True)
    jira_base_url = Column(String(500), nullable=False)
    jira_email = Column(String(255), nullable=False)
    jira_api_token = Column(String(500), nullable=False)
    ai_provider = Column(String(50), nullable=False)  # 'anthropic' or 'openai'
    anthropic_api_key = Column(String(500))
    openai_api_key = Column(String(500))
    openai_api_base = Column(String(500))
    session_expiry = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    generations = relationship('TestCaseGeneration', back_populates='user_session')

    def is_expired(self):
        return datetime.utcnow() > self.session_expiry

    def is_valid(self):
        return not self.is_expired()

    def refresh_expiry(self, hours=2):
        self.session_expiry = datetime.utcnow() + timedelta(hours=hours)

    def __repr__(self):
        return f'<Session {self.user_email}>'


class JiraIssue(Base):
    """Cached Jira issue for quick lookup"""
    __tablename__ = 'jira_issues'

    id = Column(Integer, primary_key=True)
    jira_instance_url = Column(String(500), nullable=False, index=True)
    issue_key = Column(String(50), nullable=False, index=True)
    summary = Column(String(500), nullable=False)
    description = Column(Text)
    issue_type = Column(String(100))
    status = Column(String(100))
    priority = Column(String(50))
    acceptance_criteria = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('jira_instance_url', 'issue_key', name='uq_jira_instance_issue'),
    )

    generations = relationship('TestCaseGeneration', back_populates='jira_issue')

    def __repr__(self):
        return f'<JiraIssue {self.issue_key}>'


class TestCaseGeneration(Base):
    """Master record for a test case generation run"""
    __tablename__ = 'test_case_generations'

    id = Column(Integer, primary_key=True)
    generation_id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    user_email = Column(String(255), ForeignKey('sessions.user_email', ondelete='CASCADE'), nullable=False, index=True)
    jira_issue_key = Column(String(50), nullable=False, index=True)
    jira_instance_url = Column(String(500), nullable=False)
    ai_provider = Column(String(50), nullable=False)
    ai_model = Column(String(100), nullable=False)
    generation_status = Column(String(50), default='completed')  # pending, generating, completed, failed
    total_scenarios = Column(Integer, default=0)
    successful_scenarios = Column(Integer, default=0)
    failed_scenarios = Column(Integer, default=0)
    generation_notes = Column(Text)
    temperature = Column(Float, default=0.3)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_session = relationship('Session', back_populates='generations')
    jira_issue = relationship('JiraIssue', back_populates='generations')
    scenarios = relationship('TestScenario', back_populates='generation', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TestCaseGeneration {self.generation_id}>'


class TestScenario(Base):
    """Individual test scenario generated from an issue"""
    __tablename__ = 'test_scenarios'

    id = Column(Integer, primary_key=True)
    scenario_id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    generation_id = Column(UUID(as_uuid=True), ForeignKey('test_case_generations.generation_id', ondelete='CASCADE'), nullable=False)
    jira_issue_key = Column(String(50), nullable=False, index=True)
    jira_instance_url = Column(String(500), nullable=False)
    scenario_number = Column(Integer)
    title = Column(String(500), nullable=False)
    scenario_type = Column(String(50), nullable=False)  # positive, negative, edge-case
    category = Column(String(100))
    priority = Column(String(50))
    preconditions = Column(JSON)
    steps = Column(JSON)
    expected_result = Column(Text)
    automation_hint = Column(Text)
    tags = Column(JSON)
    coverage = Column(JSON)

    # Jira Integration
    jira_child_issue_key = Column(String(50))
    jira_child_issue_url = Column(String(500))
    jira_sync_status = Column(String(50), default='pending')  # pending, synced, failed
    jira_last_sync_at = Column(DateTime)

    # Approval/Validation
    status = Column(String(50), default='draft')  # draft, approved, rejected, in_progress, passed, failed
    approved_by = Column(String(255))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    generation = relationship('TestCaseGeneration', back_populates='scenarios')
    sync_history = relationship('SyncHistory', back_populates='scenario', cascade='all, delete-orphan')
    ac_coverage = relationship('AcceptanceCriteriaCoverage', back_populates='scenario', cascade='all, delete-orphan')

    def approve(self, approved_by):
        self.status = 'approved'
        self.approved_by = approved_by
        self.approved_at = datetime.utcnow()

    def reject(self, reason):
        self.status = 'rejected'
        self.rejection_reason = reason

    def __repr__(self):
        return f'<TestScenario {self.scenario_id}>'


class SyncHistory(Base):
    """Audit trail for all scenario changes and syncs"""
    __tablename__ = 'sync_history'

    id = Column(Integer, primary_key=True)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey('test_scenarios.scenario_id', ondelete='CASCADE'))
    sync_direction = Column(String(50))  # to_jira, from_jira, internal
    sync_type = Column(String(100))  # create, update, delete, approve, reject, sync
    previous_state = Column(JSON)
    new_state = Column(JSON)
    sync_status = Column(String(50))  # success, failed
    error_message = Column(Text)
    synced_by = Column(String(255))
    synced_at = Column(DateTime, default=datetime.utcnow, index=True)

    scenario = relationship('TestScenario', back_populates='sync_history')

    def __repr__(self):
        return f'<SyncHistory {self.id}>'


class AcceptanceCriteriaCoverage(Base):
    """Map scenarios to acceptance criteria they cover"""
    __tablename__ = 'acceptance_criteria_coverage'

    id = Column(Integer, primary_key=True)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey('test_scenarios.scenario_id', ondelete='CASCADE'))
    jira_issue_key = Column(String(50), nullable=False, index=True)
    ac_number = Column(String(10))
    ac_text = Column(Text)
    coverage_status = Column(String(50), default='covered')  # covered, partial, not_covered
    created_at = Column(DateTime, default=datetime.utcnow)

    scenario = relationship('TestScenario', back_populates='ac_coverage')

    def __repr__(self):
        return f'<AcceptanceCriteriaCoverage {self.id}>'


class ProjectSettings(Base):
    """Project-wide settings for test generation and Jira sync"""
    __tablename__ = 'project_settings'

    id = Column(Integer, primary_key=True)
    jira_instance_url = Column(String(500), unique=True, nullable=False)
    project_key = Column(String(50))
    parent_issue_key = Column(String(50))
    test_case_issue_type = Column(String(50), default='Story')
    auto_approve_enabled = Column(Boolean, default=False)
    auto_sync_enabled = Column(Boolean, default=True)
    notification_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ProjectSettings {self.project_key}>'


class JiraCustomFields(Base):
    """Mapping of custom fields in Jira for each instance"""
    __tablename__ = 'jira_custom_fields'

    id = Column(Integer, primary_key=True)
    jira_instance_url = Column(String(500), nullable=False, index=True)
    field_key = Column(String(100), nullable=False)
    field_id = Column(String(100), nullable=False)
    field_name = Column(String(255), nullable=False)
    field_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('jira_instance_url', 'field_key', name='uq_jira_field_key'),
    )

    def __repr__(self):
        return f'<JiraCustomFields {self.field_key}>'


# Database connection helpers
class DatabaseManager:
    """Manage database connections and sessions"""

    def __init__(self, database_url='postgresql://user:password@localhost/automation_dashboard'):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None

    def initialize(self):
        """Initialize database connection and create tables"""
        self.engine = create_engine(self.database_url, echo=False, pool_size=20, max_overflow=40)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """Get a new database session"""
        if self.SessionLocal is None:
            self.initialize()
        return self.SessionLocal()

    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()


# Global database manager
db_manager = DatabaseManager()
