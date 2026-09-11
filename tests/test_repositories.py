"""
Unit tests for database repositories
Tests CRUD operations and error handling
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from database.models import db_manager, Session as SessionModel
from database.repositories import (
    SessionRepository, GenerationRepository, ScenarioRepository,
    SyncRepository, RepositoryFactory
)


@pytest.fixture
def db_session():
    """Create test database session"""
    db_manager.database_url = "sqlite:///:memory:"
    db_manager.initialize()
    session = db_manager.get_session()
    yield session
    session.close()


@pytest.fixture
def repo_factory(db_session):
    """Create repository factory"""
    return RepositoryFactory(db_session)


class TestSessionRepository:
    """Tests for SessionRepository"""

    def test_create_session(self, repo_factory):
        """Test creating a user session"""
        repo = repo_factory.get_session_repo()

        session = repo.create_session(
            user_email='test@example.com',
            jira_base_url='https://jira.test.com',
            jira_email='jira@test.com',
            jira_api_token='token123',
            ai_provider='anthropic',
            anthropic_api_key='key123',
            hours=2
        )

        assert session is not None
        assert session.user_email == 'test@example.com'
        assert session.is_valid()

    def test_get_session_by_email(self, repo_factory):
        """Test retrieving session by email"""
        repo = repo_factory.get_session_repo()

        created = repo.create_session(
            user_email='test@example.com',
            jira_base_url='https://jira.test.com',
            jira_email='jira@test.com',
            jira_api_token='token123',
            ai_provider='anthropic',
            anthropic_api_key='key123'
        )

        retrieved = repo.get_session_by_email('test@example.com')
        assert retrieved is not None
        assert retrieved.user_email == 'test@example.com'

    def test_session_expiry(self, repo_factory):
        """Test session expiry validation"""
        repo = repo_factory.get_session_repo()

        session = repo.create_session(
            user_email='test@example.com',
            jira_base_url='https://jira.test.com',
            jira_email='jira@test.com',
            jira_api_token='token123',
            ai_provider='anthropic',
            anthropic_api_key='key123',
            hours=0  # Expire immediately
        )

        assert session is not None
        assert not session.is_valid()

    def test_refresh_session_expiry(self, repo_factory):
        """Test refreshing session expiry"""
        repo = repo_factory.get_session_repo()

        repo.create_session(
            user_email='test@example.com',
            jira_base_url='https://jira.test.com',
            jira_email='jira@test.com',
            jira_api_token='token123',
            ai_provider='anthropic',
            anthropic_api_key='key123',
            hours=1
        )

        success = repo.update_session_expiry('test@example.com', hours=4)
        assert success is True

        session = repo.get_session_by_email('test@example.com')
        assert session.is_valid()

    def test_delete_expired_sessions(self, repo_factory):
        """Test deleting expired sessions"""
        repo = repo_factory.get_session_repo()

        # Create expired session
        repo.create_session(
            user_email='expired@example.com',
            jira_base_url='https://jira.test.com',
            jira_email='jira@test.com',
            jira_api_token='token123',
            ai_provider='anthropic',
            anthropic_api_key='key123',
            hours=0
        )

        # Create valid session
        repo.create_session(
            user_email='valid@example.com',
            jira_base_url='https://jira.test.com',
            jira_email='jira@test.com',
            jira_api_token='token123',
            ai_provider='anthropic',
            anthropic_api_key='key123',
            hours=2
        )

        deleted = repo.delete_expired_sessions()
        assert deleted >= 1


class TestGenerationRepository:
    """Tests for GenerationRepository"""

    def test_create_generation(self, repo_factory):
        """Test creating a generation record"""
        repo = repo_factory.get_generation_repo()

        generation = repo.create_generation(
            user_email='test@example.com',
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            ai_provider='anthropic',
            ai_model='claude-3-sonnet'
        )

        assert generation is not None
        assert generation.jira_issue_key == 'TEST-101'
        assert generation.generation_status == 'pending'

    def test_get_generation(self, repo_factory):
        """Test retrieving generation by ID"""
        repo = repo_factory.get_generation_repo()

        created = repo.create_generation(
            user_email='test@example.com',
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            ai_provider='anthropic',
            ai_model='claude-3-sonnet'
        )

        retrieved = repo.get_generation(created.generation_id)
        assert retrieved is not None
        assert retrieved.generation_id == created.generation_id

    def test_list_generations_for_user(self, repo_factory):
        """Test listing generations for a user"""
        repo = repo_factory.get_generation_repo()

        repo.create_generation(
            user_email='test@example.com',
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            ai_provider='anthropic',
            ai_model='claude-3-sonnet'
        )

        repo.create_generation(
            user_email='test@example.com',
            jira_issue_key='TEST-102',
            jira_instance_url='https://jira.test.com',
            ai_provider='anthropic',
            ai_model='claude-3-sonnet'
        )

        generations = repo.list_generations_for_user('test@example.com')
        assert len(generations) == 2

    def test_update_generation_status(self, repo_factory):
        """Test updating generation status"""
        repo = repo_factory.get_generation_repo()

        generation = repo.create_generation(
            user_email='test@example.com',
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            ai_provider='anthropic',
            ai_model='claude-3-sonnet'
        )

        success = repo.update_generation_status(
            generation.generation_id,
            'completed',
            'Test generation complete'
        )

        assert success is True
        updated = repo.get_generation(generation.generation_id)
        assert updated.generation_status == 'completed'


class TestScenarioRepository:
    """Tests for ScenarioRepository"""

    def test_create_scenario(self, repo_factory):
        """Test creating a scenario"""
        gen_repo = repo_factory.get_generation_repo()
        scenario_repo = repo_factory.get_scenario_repo()

        generation = gen_repo.create_generation(
            user_email='test@example.com',
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            ai_provider='anthropic',
            ai_model='claude-3-sonnet'
        )

        scenario = scenario_repo.create_scenario(
            generation_id=generation.generation_id,
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            title='Test scenario',
            scenario_type='positive'
        )

        assert scenario is not None
        assert scenario.title == 'Test scenario'
        assert scenario.status == 'draft'

    def test_approve_scenario(self, repo_factory):
        """Test approving a scenario"""
        gen_repo = repo_factory.get_generation_repo()
        scenario_repo = repo_factory.get_scenario_repo()

        generation = gen_repo.create_generation(
            user_email='test@example.com',
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            ai_provider='anthropic',
            ai_model='claude-3-sonnet'
        )

        scenario = scenario_repo.create_scenario(
            generation_id=generation.generation_id,
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            title='Test scenario',
            scenario_type='positive'
        )

        success = scenario_repo.approve_scenario(scenario.scenario_id, 'reviewer@test.com')
        assert success is True

        updated = scenario_repo.get_scenario(scenario.scenario_id)
        assert updated.status == 'approved'
        assert updated.approved_by == 'reviewer@test.com'

    def test_reject_scenario(self, repo_factory):
        """Test rejecting a scenario"""
        gen_repo = repo_factory.get_generation_repo()
        scenario_repo = repo_factory.get_scenario_repo()

        generation = gen_repo.create_generation(
            user_email='test@example.com',
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            ai_provider='anthropic',
            ai_model='claude-3-sonnet'
        )

        scenario = scenario_repo.create_scenario(
            generation_id=generation.generation_id,
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            title='Test scenario',
            scenario_type='positive'
        )

        success = scenario_repo.reject_scenario(scenario.scenario_id, 'Not detailed enough')
        assert success is True

        updated = scenario_repo.get_scenario(scenario.scenario_id)
        assert updated.status == 'rejected'
        assert updated.rejection_reason == 'Not detailed enough'

    def test_list_pending_scenarios(self, repo_factory):
        """Test listing scenarios pending Jira sync"""
        gen_repo = repo_factory.get_generation_repo()
        scenario_repo = repo_factory.get_scenario_repo()

        generation = gen_repo.create_generation(
            user_email='test@example.com',
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            ai_provider='anthropic',
            ai_model='claude-3-sonnet'
        )

        scenario = scenario_repo.create_scenario(
            generation_id=generation.generation_id,
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            title='Test scenario',
            scenario_type='positive'
        )

        # Approve scenario
        scenario_repo.approve_scenario(scenario.scenario_id, 'reviewer@test.com')

        # Get pending
        pending = scenario_repo.list_pending_scenarios(limit=10)
        assert len(pending) == 1
        assert pending[0].scenario_id == scenario.scenario_id


class TestSyncRepository:
    """Tests for SyncRepository"""

    def test_record_sync(self, repo_factory, db_session):
        """Test recording a sync event"""
        gen_repo = repo_factory.get_generation_repo()
        scenario_repo = repo_factory.get_scenario_repo()
        sync_repo = repo_factory.get_sync_repo()

        generation = gen_repo.create_generation(
            user_email='test@example.com',
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            ai_provider='anthropic',
            ai_model='claude-3-sonnet'
        )

        scenario = scenario_repo.create_scenario(
            generation_id=generation.generation_id,
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            title='Test scenario',
            scenario_type='positive'
        )

        sync = sync_repo.record_sync(
            scenario_id=scenario.scenario_id,
            sync_direction='to_jira',
            sync_type='create',
            sync_status='success',
            synced_by='sync-engine'
        )

        assert sync is not None
        assert sync.sync_status == 'success'

    def test_get_sync_history(self, repo_factory):
        """Test retrieving sync history"""
        gen_repo = repo_factory.get_generation_repo()
        scenario_repo = repo_factory.get_scenario_repo()
        sync_repo = repo_factory.get_sync_repo()

        generation = gen_repo.create_generation(
            user_email='test@example.com',
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            ai_provider='anthropic',
            ai_model='claude-3-sonnet'
        )

        scenario = scenario_repo.create_scenario(
            generation_id=generation.generation_id,
            jira_issue_key='TEST-101',
            jira_instance_url='https://jira.test.com',
            title='Test scenario',
            scenario_type='positive'
        )

        sync_repo.record_sync(
            scenario_id=scenario.scenario_id,
            sync_direction='to_jira',
            sync_type='create',
            sync_status='success',
            synced_by='sync-engine'
        )

        history = sync_repo.get_sync_history(scenario.scenario_id)
        assert len(history) == 1
        assert history[0].sync_type == 'create'

    def test_get_sync_statistics(self, repo_factory):
        """Test getting sync statistics"""
        sync_repo = repo_factory.get_sync_repo()

        stats = sync_repo.get_sync_statistics(days=30)
        assert 'total' in stats
        assert 'successful' in stats
        assert 'failed' in stats
        assert 'success_rate' in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
