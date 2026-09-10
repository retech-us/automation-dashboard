"""
Data Access Object (DAO) Layer for Automation Dashboard
Provides CRUD operations and common queries for all database entities
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy import desc, and_, or_

from database.models import (
    Session, JiraIssue, TestCaseGeneration, TestScenario,
    SyncHistory, AcceptanceCriteriaCoverage, ProjectSettings, JiraCustomFields
)

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common CRUD operations"""

    def __init__(self, db_session: SQLSession):
        self.db = db_session

    def commit(self):
        """Commit current transaction"""
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Commit failed: {e}")
            raise

    def rollback(self):
        """Rollback current transaction"""
        self.db.rollback()


class SessionRepository(BaseRepository):
    """Repository for managing user sessions"""

    def create_session(self, user_email: str, jira_base_url: str, jira_email: str,
                      jira_api_token: str, ai_provider: str, hours: int = 2,
                      anthropic_api_key: Optional[str] = None,
                      openai_api_key: Optional[str] = None,
                      openai_api_base: Optional[str] = None) -> Session:
        """Create a new user session"""
        try:
            # Delete expired sessions for this user
            self.delete_expired_sessions(user_email)

            session = Session(
                user_email=user_email,
                jira_base_url=jira_base_url,
                jira_email=jira_email,
                jira_api_token=jira_api_token,
                ai_provider=ai_provider,
                anthropic_api_key=anthropic_api_key,
                openai_api_key=openai_api_key,
                openai_api_base=openai_api_base,
                session_expiry=datetime.utcnow() + timedelta(hours=hours)
            )
            self.db.add(session)
            self.commit()
            logger.info(f"Created session for {user_email} (expires in {hours}h)")
            return session
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to create session for {user_email}: {e}")
            raise

    def get_session_by_email(self, user_email: str) -> Optional[Session]:
        """Get active session by user email"""
        try:
            session = self.db.query(Session).filter_by(user_email=user_email).first()
            if session and session.is_valid():
                return session
            return None
        except Exception as e:
            logger.error(f"Failed to get session for {user_email}: {e}")
            return None

    def update_session_expiry(self, user_email: str, hours: int = 2) -> bool:
        """Refresh session expiry"""
        try:
            session = self.db.query(Session).filter_by(user_email=user_email).first()
            if session:
                session.refresh_expiry(hours)
                self.commit()
                logger.info(f"Refreshed session for {user_email}")
                return True
            return False
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to refresh session for {user_email}: {e}")
            return False

    def is_session_valid(self, user_email: str) -> bool:
        """Check if user session is still valid"""
        session = self.get_session_by_email(user_email)
        return session is not None

    def delete_expired_sessions(self, user_email: Optional[str] = None) -> int:
        """Delete expired sessions"""
        try:
            query = self.db.query(Session).filter(Session.session_expiry < datetime.utcnow())
            if user_email:
                query = query.filter_by(user_email=user_email)

            count = query.count()
            query.delete()
            self.commit()

            if count > 0:
                logger.info(f"Deleted {count} expired sessions")
            return count
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to delete expired sessions: {e}")
            return 0

    def get_session_expiry(self, user_email: str) -> Optional[datetime]:
        """Get session expiry time"""
        session = self.db.query(Session).filter_by(user_email=user_email).first()
        return session.session_expiry if session else None


class GenerationRepository(BaseRepository):
    """Repository for managing test case generations"""

    def create_generation(self, user_email: str, jira_issue_key: str,
                         jira_instance_url: str, ai_provider: str,
                         ai_model: str, **kwargs) -> TestCaseGeneration:
        """Create a new test case generation record"""
        try:
            generation = TestCaseGeneration(
                user_email=user_email,
                jira_issue_key=jira_issue_key,
                jira_instance_url=jira_instance_url,
                ai_provider=ai_provider,
                ai_model=ai_model,
                generation_status='pending',
                started_at=datetime.utcnow(),
                **kwargs
            )
            self.db.add(generation)
            self.commit()
            logger.info(f"Created generation {generation.generation_id} for {jira_issue_key}")
            return generation
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to create generation: {e}")
            raise

    def get_generation(self, generation_id: UUID) -> Optional[TestCaseGeneration]:
        """Get generation by ID"""
        try:
            return self.db.query(TestCaseGeneration).filter_by(
                generation_id=generation_id
            ).first()
        except Exception as e:
            logger.error(f"Failed to get generation {generation_id}: {e}")
            return None

    def list_generations_for_user(self, user_email: str, limit: int = 50) -> List[TestCaseGeneration]:
        """List all generations for a user"""
        try:
            return self.db.query(TestCaseGeneration).filter_by(
                user_email=user_email
            ).order_by(desc(TestCaseGeneration.created_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to list generations for {user_email}: {e}")
            return []

    def list_generations_for_issue(self, jira_issue_key: str, limit: int = 50) -> List[TestCaseGeneration]:
        """List all generations for a Jira issue"""
        try:
            return self.db.query(TestCaseGeneration).filter_by(
                jira_issue_key=jira_issue_key
            ).order_by(desc(TestCaseGeneration.created_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to list generations for {jira_issue_key}: {e}")
            return []

    def update_generation_status(self, generation_id: UUID, status: str,
                                notes: Optional[str] = None) -> bool:
        """Update generation status"""
        try:
            generation = self.get_generation(generation_id)
            if not generation:
                return False

            generation.generation_status = status
            if notes:
                generation.generation_notes = notes
            if status == 'completed':
                generation.completed_at = datetime.utcnow()

            self.commit()
            logger.info(f"Updated generation {generation_id} status to {status}")
            return True
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to update generation {generation_id}: {e}")
            return False

    def update_generation_stats(self, generation_id: UUID, total: int,
                               successful: int, failed: int) -> bool:
        """Update generation scenario statistics"""
        try:
            generation = self.get_generation(generation_id)
            if not generation:
                return False

            generation.total_scenarios = total
            generation.successful_scenarios = successful
            generation.failed_scenarios = failed
            self.commit()
            return True
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to update stats for generation {generation_id}: {e}")
            return False


class ScenarioRepository(BaseRepository):
    """Repository for managing test scenarios"""

    def create_scenario(self, generation_id: UUID, jira_issue_key: str,
                       jira_instance_url: str, title: str,
                       scenario_type: str, **kwargs) -> TestScenario:
        """Create a new test scenario"""
        try:
            scenario = TestScenario(
                generation_id=generation_id,
                jira_issue_key=jira_issue_key,
                jira_instance_url=jira_instance_url,
                title=title,
                scenario_type=scenario_type,
                status='draft',
                jira_sync_status='pending',
                **kwargs
            )
            self.db.add(scenario)
            self.commit()
            logger.info(f"Created scenario {scenario.scenario_id}")
            return scenario
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to create scenario: {e}")
            raise

    def get_scenario(self, scenario_id: UUID) -> Optional[TestScenario]:
        """Get scenario by ID"""
        try:
            return self.db.query(TestScenario).filter_by(scenario_id=scenario_id).first()
        except Exception as e:
            logger.error(f"Failed to get scenario {scenario_id}: {e}")
            return None

    def list_scenarios_for_issue(self, jira_issue_key: str,
                                limit: int = 100) -> List[TestScenario]:
        """List all scenarios for a Jira issue"""
        try:
            return self.db.query(TestScenario).filter_by(
                jira_issue_key=jira_issue_key
            ).order_by(TestScenario.scenario_number).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to list scenarios for {jira_issue_key}: {e}")
            return []

    def list_scenarios_for_generation(self, generation_id: UUID,
                                     limit: int = 100) -> List[TestScenario]:
        """List all scenarios for a generation"""
        try:
            return self.db.query(TestScenario).filter_by(
                generation_id=generation_id
            ).order_by(TestScenario.scenario_number).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to list scenarios for generation {generation_id}: {e}")
            return []

    def approve_scenario(self, scenario_id: UUID, approved_by: str) -> bool:
        """Approve a scenario"""
        try:
            scenario = self.get_scenario(scenario_id)
            if not scenario:
                return False

            scenario.approve(approved_by)
            self.commit()
            logger.info(f"Approved scenario {scenario_id} by {approved_by}")
            return True
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to approve scenario {scenario_id}: {e}")
            return False

    def reject_scenario(self, scenario_id: UUID, reason: str) -> bool:
        """Reject a scenario"""
        try:
            scenario = self.get_scenario(scenario_id)
            if not scenario:
                return False

            scenario.reject(reason)
            self.commit()
            logger.info(f"Rejected scenario {scenario_id}")
            return True
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to reject scenario {scenario_id}: {e}")
            return False

    def update_scenario(self, scenario_id: UUID, updates: Dict[str, Any]) -> bool:
        """Update scenario fields"""
        try:
            scenario = self.get_scenario(scenario_id)
            if not scenario:
                return False

            for key, value in updates.items():
                if hasattr(scenario, key):
                    setattr(scenario, key, value)

            self.commit()
            logger.info(f"Updated scenario {scenario_id}")
            return True
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to update scenario {scenario_id}: {e}")
            return False

    def update_scenario_sync_status(self, scenario_id: UUID, sync_status: str,
                                   jira_child_issue_key: Optional[str] = None,
                                   jira_child_issue_url: Optional[str] = None) -> bool:
        """Update scenario Jira sync status"""
        try:
            scenario = self.get_scenario(scenario_id)
            if not scenario:
                return False

            scenario.jira_sync_status = sync_status
            if jira_child_issue_key:
                scenario.jira_child_issue_key = jira_child_issue_key
            if jira_child_issue_url:
                scenario.jira_child_issue_url = jira_child_issue_url
            scenario.jira_last_sync_at = datetime.utcnow()

            self.commit()
            logger.info(f"Updated sync status for {scenario_id} to {sync_status}")
            return True
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to update sync status for {scenario_id}: {e}")
            return False

    def list_pending_scenarios(self, limit: int = 100) -> List[TestScenario]:
        """List scenarios pending Jira sync"""
        try:
            return self.db.query(TestScenario).filter_by(
                jira_sync_status='pending'
            ).filter(TestScenario.status == 'approved').limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to list pending scenarios: {e}")
            return []

    def list_approved_scenarios_for_issue(self, jira_issue_key: str) -> List[TestScenario]:
        """List approved scenarios for an issue"""
        try:
            return self.db.query(TestScenario).filter(
                and_(
                    TestScenario.jira_issue_key == jira_issue_key,
                    TestScenario.status == 'approved'
                )
            ).order_by(TestScenario.scenario_number).all()
        except Exception as e:
            logger.error(f"Failed to list approved scenarios for {jira_issue_key}: {e}")
            return []

    def delete_scenario(self, scenario_id: UUID) -> bool:
        """Delete a scenario"""
        try:
            scenario = self.get_scenario(scenario_id)
            if not scenario:
                return False

            self.db.delete(scenario)
            self.commit()
            logger.info(f"Deleted scenario {scenario_id}")
            return True
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to delete scenario {scenario_id}: {e}")
            return False


class SyncRepository(BaseRepository):
    """Repository for managing sync history and tracking"""

    def record_sync(self, scenario_id: UUID, sync_direction: str,
                   sync_type: str, previous_state: Optional[Dict] = None,
                   new_state: Optional[Dict] = None, sync_status: str = 'success',
                   error_message: Optional[str] = None,
                   synced_by: Optional[str] = None) -> SyncHistory:
        """Record a sync event"""
        try:
            sync = SyncHistory(
                scenario_id=scenario_id,
                sync_direction=sync_direction,
                sync_type=sync_type,
                previous_state=previous_state,
                new_state=new_state,
                sync_status=sync_status,
                error_message=error_message,
                synced_by=synced_by
            )
            self.db.add(sync)
            self.commit()
            logger.info(f"Recorded sync for {scenario_id}: {sync_type} -> {sync_status}")
            return sync
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to record sync for {scenario_id}: {e}")
            raise

    def get_sync_history(self, scenario_id: UUID, limit: int = 50) -> List[SyncHistory]:
        """Get sync history for a scenario"""
        try:
            return self.db.query(SyncHistory).filter_by(
                scenario_id=scenario_id
            ).order_by(desc(SyncHistory.synced_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get sync history for {scenario_id}: {e}")
            return []

    def get_pending_syncs(self, limit: int = 100) -> List[SyncHistory]:
        """Get pending syncs"""
        try:
            return self.db.query(SyncHistory).filter_by(
                sync_status='pending'
            ).order_by(SyncHistory.synced_at).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get pending syncs: {e}")
            return []

    def mark_sync_complete(self, scenario_id: UUID) -> bool:
        """Mark sync as complete for a scenario"""
        try:
            sync = self.db.query(SyncHistory).filter_by(
                scenario_id=scenario_id,
                sync_status='pending'
            ).first()

            if sync:
                sync.sync_status = 'success'
                self.commit()
                return True
            return False
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to mark sync complete for {scenario_id}: {e}")
            return False

    def get_sync_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get sync statistics for the last N days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            syncs = self.db.query(SyncHistory).filter(
                SyncHistory.synced_at >= cutoff_date
            ).all()

            total = len(syncs)
            successful = sum(1 for s in syncs if s.sync_status == 'success')
            failed = sum(1 for s in syncs if s.sync_status == 'failed')

            return {
                'total': total,
                'successful': successful,
                'failed': failed,
                'success_rate': (successful / total * 100) if total > 0 else 0,
                'period_days': days
            }
        except Exception as e:
            logger.error(f"Failed to get sync statistics: {e}")
            return {}


class JiraIssueRepository(BaseRepository):
    """Repository for managing cached Jira issues"""

    def create_or_update_issue(self, jira_instance_url: str, issue_key: str,
                              summary: str, **kwargs) -> JiraIssue:
        """Create or update a Jira issue cache"""
        try:
            issue = self.db.query(JiraIssue).filter(
                and_(
                    JiraIssue.jira_instance_url == jira_instance_url,
                    JiraIssue.issue_key == issue_key
                )
            ).first()

            if issue:
                for key, value in kwargs.items():
                    if hasattr(issue, key):
                        setattr(issue, key, value)
            else:
                issue = JiraIssue(
                    jira_instance_url=jira_instance_url,
                    issue_key=issue_key,
                    summary=summary,
                    **kwargs
                )
                self.db.add(issue)

            self.commit()
            logger.info(f"Cached Jira issue {issue_key}")
            return issue
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to cache Jira issue {issue_key}: {e}")
            raise

    def get_issue(self, jira_instance_url: str, issue_key: str) -> Optional[JiraIssue]:
        """Get cached Jira issue"""
        try:
            return self.db.query(JiraIssue).filter(
                and_(
                    JiraIssue.jira_instance_url == jira_instance_url,
                    JiraIssue.issue_key == issue_key
                )
            ).first()
        except Exception as e:
            logger.error(f"Failed to get Jira issue {issue_key}: {e}")
            return None


class ProjectSettingsRepository(BaseRepository):
    """Repository for managing project settings"""

    def get_settings(self, jira_instance_url: str) -> Optional[ProjectSettings]:
        """Get project settings for Jira instance"""
        try:
            return self.db.query(ProjectSettings).filter_by(
                jira_instance_url=jira_instance_url
            ).first()
        except Exception as e:
            logger.error(f"Failed to get settings for {jira_instance_url}: {e}")
            return None

    def update_settings(self, jira_instance_url: str, **kwargs) -> bool:
        """Update project settings"""
        try:
            settings = self.get_settings(jira_instance_url)
            if not settings:
                return False

            for key, value in kwargs.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)

            self.commit()
            logger.info(f"Updated settings for {jira_instance_url}")
            return True
        except Exception as e:
            self.rollback()
            logger.error(f"Failed to update settings for {jira_instance_url}: {e}")
            return False


# Repository Factory
class RepositoryFactory:
    """Factory for creating repository instances"""

    def __init__(self, db_session: SQLSession):
        self.db = db_session

    def get_session_repo(self) -> SessionRepository:
        return SessionRepository(self.db)

    def get_generation_repo(self) -> GenerationRepository:
        return GenerationRepository(self.db)

    def get_scenario_repo(self) -> ScenarioRepository:
        return ScenarioRepository(self.db)

    def get_sync_repo(self) -> SyncRepository:
        return SyncRepository(self.db)

    def get_issue_repo(self) -> JiraIssueRepository:
        return JiraIssueRepository(self.db)

    def get_settings_repo(self) -> ProjectSettingsRepository:
        return ProjectSettingsRepository(self.db)
