"""
API Routes for Automation Dashboard
Comprehensive REST endpoints for test case generation, scenarios, and Jira sync
"""

import json
import logging
from uuid import UUID
from datetime import datetime
from typing import Dict, Any, Tuple
from urllib.parse import parse_qs, urlparse

from database.models import db_manager
from database.repositories import (
    RepositoryFactory, SessionRepository, GenerationRepository,
    ScenarioRepository, SyncRepository, JiraIssueRepository,
    ProjectSettingsRepository
)
from sync.jira_sync import sync_engine

logger = logging.getLogger(__name__)


class APIRoutes:
    """API route handlers for dashboard endpoints"""

    def __init__(self):
        """Initialize database connection"""
        self.db_manager = db_manager

    def _get_repositories(self):
        """Get repository factory"""
        db_session = self.db_manager.get_session()
        return RepositoryFactory(db_session), db_session

    def _parse_json_body(self, body: str) -> Dict[str, Any]:
        """Parse JSON request body"""
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise ValueError("Invalid JSON in request body")

    def _send_response(self, data: Dict[str, Any], status_code: int = 200) -> Tuple[str, int, str]:
        """Format response"""
        return json.dumps(data), status_code, 'application/json'

    # ==================== SESSION ENDPOINTS ====================

    def POST_api_sessions(self, body: str) -> Tuple[str, int, str]:
        """POST /api/sessions - Create user session"""
        try:
            request_data = self._parse_json_body(body)
            repos, db_session = self._get_repositories()

            user_email = request_data.get('user_email', '').strip()
            jira_base_url = request_data.get('jira_base_url', '').strip()
            jira_email = request_data.get('jira_email', '').strip()
            jira_api_token = request_data.get('jira_api_token', '').strip()
            ai_provider = request_data.get('ai_provider', '').strip()
            hours = request_data.get('session_hours', 2)

            if not all([user_email, jira_base_url, jira_email, jira_api_token, ai_provider]):
                return self._send_response({"error": "Missing required fields"}, 400)

            session_repo = repos.get_session_repo()
            session = session_repo.create_session(
                user_email=user_email,
                jira_base_url=jira_base_url,
                jira_email=jira_email,
                jira_api_token=jira_api_token,
                ai_provider=ai_provider,
                hours=hours,
                anthropic_api_key=request_data.get('anthropic_api_key'),
                openai_api_key=request_data.get('openai_api_key'),
                openai_api_base=request_data.get('openai_api_base')
            )

            db_session.close()
            return self._send_response({
                "status": "success",
                "session": {
                    "user_email": session.user_email,
                    "expires_at": session.session_expiry.isoformat(),
                    "created_at": session.created_at.isoformat()
                }
            }, 201)
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return self._send_response({"error": str(e)}, 500)

    def GET_api_sessions_email(self, user_email: str) -> Tuple[str, int, str]:
        """GET /api/sessions/{email} - Get user session"""
        try:
            repos, db_session = self._get_repositories()
            session_repo = repos.get_session_repo()
            session = session_repo.get_session_by_email(user_email)

            if not session:
                return self._send_response({"error": "Session not found or expired"}, 404)

            db_session.close()
            return self._send_response({
                "user_email": session.user_email,
                "expires_at": session.session_expiry.isoformat(),
                "is_valid": session.is_valid()
            })
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return self._send_response({"error": str(e)}, 500)

    def POST_api_sessions_refresh(self, body: str) -> Tuple[str, int, str]:
        """POST /api/sessions/refresh - Refresh session expiry"""
        try:
            request_data = self._parse_json_body(body)
            repos, db_session = self._get_repositories()

            user_email = request_data.get('user_email', '').strip()
            hours = request_data.get('hours', 2)

            session_repo = repos.get_session_repo()
            success = session_repo.update_session_expiry(user_email, hours)

            db_session.close()

            if success:
                return self._send_response({"status": "refreshed", "hours": hours})
            else:
                return self._send_response({"error": "Session not found"}, 404)
        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return self._send_response({"error": str(e)}, 500)

    # ==================== GENERATION ENDPOINTS ====================

    def POST_api_generations(self, body: str) -> Tuple[str, int, str]:
        """POST /api/generations - Create test case generation"""
        try:
            request_data = self._parse_json_body(body)
            repos, db_session = self._get_repositories()

            user_email = request_data.get('user_email', '').strip()
            jira_issue_key = request_data.get('jira_issue_key', '').strip()
            jira_instance_url = request_data.get('jira_instance_url', '').strip()
            ai_provider = request_data.get('ai_provider', '').strip()
            ai_model = request_data.get('ai_model', '').strip()

            if not all([user_email, jira_issue_key, jira_instance_url, ai_provider, ai_model]):
                return self._send_response({"error": "Missing required fields"}, 400)

            gen_repo = repos.get_generation_repo()
            generation = gen_repo.create_generation(
                user_email=user_email,
                jira_issue_key=jira_issue_key,
                jira_instance_url=jira_instance_url,
                ai_provider=ai_provider,
                ai_model=ai_model,
                temperature=request_data.get('temperature', 0.3)
            )

            db_session.close()
            return self._send_response({
                "status": "created",
                "generation_id": str(generation.generation_id),
                "created_at": generation.created_at.isoformat()
            }, 201)
        except Exception as e:
            logger.error(f"Error creating generation: {e}")
            return self._send_response({"error": str(e)}, 500)

    def GET_api_generations_id(self, generation_id: str) -> Tuple[str, int, str]:
        """GET /api/generations/{id} - Get generation details"""
        try:
            repos, db_session = self._get_repositories()
            gen_repo = repos.get_generation_repo()

            try:
                gen_uuid = UUID(generation_id)
            except ValueError:
                return self._send_response({"error": "Invalid generation ID"}, 400)

            generation = gen_repo.get_generation(gen_uuid)
            if not generation:
                return self._send_response({"error": "Generation not found"}, 404)

            db_session.close()
            return self._send_response({
                "generation_id": str(generation.generation_id),
                "user_email": generation.user_email,
                "jira_issue_key": generation.jira_issue_key,
                "status": generation.generation_status,
                "total_scenarios": generation.total_scenarios,
                "successful_scenarios": generation.successful_scenarios,
                "failed_scenarios": generation.failed_scenarios,
                "created_at": generation.created_at.isoformat(),
                "completed_at": generation.completed_at.isoformat() if generation.completed_at else None
            })
        except Exception as e:
            logger.error(f"Error getting generation: {e}")
            return self._send_response({"error": str(e)}, 500)

    def GET_api_generations_user(self, user_email: str, limit: int = 50) -> Tuple[str, int, str]:
        """GET /api/generations/user/{email} - List user generations"""
        try:
            repos, db_session = self._get_repositories()
            gen_repo = repos.get_generation_repo()

            generations = gen_repo.list_generations_for_user(user_email, limit)
            results = [
                {
                    "generation_id": str(g.generation_id),
                    "jira_issue_key": g.jira_issue_key,
                    "status": g.generation_status,
                    "total_scenarios": g.total_scenarios,
                    "created_at": g.created_at.isoformat()
                }
                for g in generations
            ]

            db_session.close()
            return self._send_response({"generations": results, "total": len(results)})
        except Exception as e:
            logger.error(f"Error listing generations: {e}")
            return self._send_response({"error": str(e)}, 500)

    def PUT_api_generations_id_status(self, generation_id: str, body: str) -> Tuple[str, int, str]:
        """PUT /api/generations/{id}/status - Update generation status"""
        try:
            request_data = self._parse_json_body(body)
            repos, db_session = self._get_repositories()

            status = request_data.get('status', '').strip()
            if not status:
                return self._send_response({"error": "Status required"}, 400)

            try:
                gen_uuid = UUID(generation_id)
            except ValueError:
                return self._send_response({"error": "Invalid generation ID"}, 400)

            gen_repo = repos.get_generation_repo()
            success = gen_repo.update_generation_status(gen_uuid, status, request_data.get('notes'))

            db_session.close()

            if success:
                return self._send_response({"status": "updated", "generation_id": generation_id})
            else:
                return self._send_response({"error": "Generation not found"}, 404)
        except Exception as e:
            logger.error(f"Error updating generation status: {e}")
            return self._send_response({"error": str(e)}, 500)

    def DELETE_api_generations_id(self, generation_id: str) -> Tuple[str, int, str]:
        """DELETE /api/generations/{id} - Delete generation"""
        try:
            repos, db_session = self._get_repositories()

            try:
                gen_uuid = UUID(generation_id)
            except ValueError:
                return self._send_response({"error": "Invalid generation ID"}, 400)

            gen_repo = repos.get_generation_repo()
            generation = gen_repo.get_generation(gen_uuid)

            if not generation:
                return self._send_response({"error": "Generation not found"}, 404)

            db_session.delete(generation)
            db_session.commit()
            db_session.close()

            return self._send_response({"status": "deleted"})
        except Exception as e:
            logger.error(f"Error deleting generation: {e}")
            return self._send_response({"error": str(e)}, 500)

    # ==================== SCENARIO ENDPOINTS ====================

    def POST_api_scenarios(self, body: str) -> Tuple[str, int, str]:
        """POST /api/scenarios - Create test scenario"""
        try:
            request_data = self._parse_json_body(body)
            repos, db_session = self._get_repositories()

            generation_id = request_data.get('generation_id', '').strip()
            jira_issue_key = request_data.get('jira_issue_key', '').strip()
            jira_instance_url = request_data.get('jira_instance_url', '').strip()
            title = request_data.get('title', '').strip()
            scenario_type = request_data.get('scenario_type', '').strip()

            if not all([generation_id, jira_issue_key, jira_instance_url, title, scenario_type]):
                return self._send_response({"error": "Missing required fields"}, 400)

            try:
                gen_uuid = UUID(generation_id)
            except ValueError:
                return self._send_response({"error": "Invalid generation ID"}, 400)

            scenario_repo = repos.get_scenario_repo()
            scenario = scenario_repo.create_scenario(
                generation_id=gen_uuid,
                jira_issue_key=jira_issue_key,
                jira_instance_url=jira_instance_url,
                title=title,
                scenario_type=scenario_type,
                category=request_data.get('category'),
                priority=request_data.get('priority'),
                preconditions=request_data.get('preconditions'),
                steps=request_data.get('steps'),
                expected_result=request_data.get('expected_result'),
                automation_hint=request_data.get('automation_hint'),
                tags=request_data.get('tags'),
                scenario_number=request_data.get('scenario_number')
            )

            db_session.close()
            return self._send_response({
                "status": "created",
                "scenario_id": str(scenario.scenario_id),
                "created_at": scenario.created_at.isoformat()
            }, 201)
        except Exception as e:
            logger.error(f"Error creating scenario: {e}")
            return self._send_response({"error": str(e)}, 500)

    def GET_api_scenarios_id(self, scenario_id: str) -> Tuple[str, int, str]:
        """GET /api/scenarios/{id} - Get scenario details"""
        try:
            repos, db_session = self._get_repositories()

            try:
                scenario_uuid = UUID(scenario_id)
            except ValueError:
                return self._send_response({"error": "Invalid scenario ID"}, 400)

            scenario_repo = repos.get_scenario_repo()
            scenario = scenario_repo.get_scenario(scenario_uuid)

            if not scenario:
                return self._send_response({"error": "Scenario not found"}, 404)

            db_session.close()
            return self._send_response({
                "scenario_id": str(scenario.scenario_id),
                "title": scenario.title,
                "scenario_type": scenario.scenario_type,
                "status": scenario.status,
                "jira_sync_status": scenario.jira_sync_status,
                "jira_child_issue_key": scenario.jira_child_issue_key,
                "preconditions": scenario.preconditions,
                "steps": scenario.steps,
                "expected_result": scenario.expected_result,
                "approved_by": scenario.approved_by,
                "approved_at": scenario.approved_at.isoformat() if scenario.approved_at else None,
                "created_at": scenario.created_at.isoformat()
            })
        except Exception as e:
            logger.error(f"Error getting scenario: {e}")
            return self._send_response({"error": str(e)}, 500)

    def GET_api_scenarios_issue(self, jira_issue_key: str, limit: int = 100) -> Tuple[str, int, str]:
        """GET /api/scenarios/issue/{key} - List scenarios for issue"""
        try:
            repos, db_session = self._get_repositories()
            scenario_repo = repos.get_scenario_repo()

            scenarios = scenario_repo.list_scenarios_for_issue(jira_issue_key, limit)
            results = [
                {
                    "scenario_id": str(s.scenario_id),
                    "title": s.title,
                    "scenario_type": s.scenario_type,
                    "status": s.status,
                    "jira_sync_status": s.jira_sync_status,
                    "created_at": s.created_at.isoformat()
                }
                for s in scenarios
            ]

            db_session.close()
            return self._send_response({"scenarios": results, "total": len(results)})
        except Exception as e:
            logger.error(f"Error listing scenarios: {e}")
            return self._send_response({"error": str(e)}, 500)

    def POST_api_scenarios_id_approve(self, scenario_id: str, body: str) -> Tuple[str, int, str]:
        """POST /api/scenarios/{id}/approve - Approve scenario"""
        try:
            request_data = self._parse_json_body(body)
            repos, db_session = self._get_repositories()

            approved_by = request_data.get('approved_by', '').strip()
            if not approved_by:
                return self._send_response({"error": "approved_by required"}, 400)

            try:
                scenario_uuid = UUID(scenario_id)
            except ValueError:
                return self._send_response({"error": "Invalid scenario ID"}, 400)

            scenario_repo = repos.get_scenario_repo()
            success = scenario_repo.approve_scenario(scenario_uuid, approved_by)

            if success:
                # Record sync event
                sync_repo = repos.get_sync_repo()
                sync_repo.record_sync(
                    scenario_id=scenario_uuid,
                    sync_direction='internal',
                    sync_type='approve',
                    sync_status='success',
                    synced_by=approved_by
                )

            db_session.close()

            if success:
                return self._send_response({"status": "approved"})
            else:
                return self._send_response({"error": "Scenario not found"}, 404)
        except Exception as e:
            logger.error(f"Error approving scenario: {e}")
            return self._send_response({"error": str(e)}, 500)

    def POST_api_scenarios_id_reject(self, scenario_id: str, body: str) -> Tuple[str, int, str]:
        """POST /api/scenarios/{id}/reject - Reject scenario"""
        try:
            request_data = self._parse_json_body(body)
            repos, db_session = self._get_repositories()

            reason = request_data.get('reason', '').strip()
            if not reason:
                return self._send_response({"error": "reason required"}, 400)

            try:
                scenario_uuid = UUID(scenario_id)
            except ValueError:
                return self._send_response({"error": "Invalid scenario ID"}, 400)

            scenario_repo = repos.get_scenario_repo()
            success = scenario_repo.reject_scenario(scenario_uuid, reason)

            if success:
                sync_repo = repos.get_sync_repo()
                sync_repo.record_sync(
                    scenario_id=scenario_uuid,
                    sync_direction='internal',
                    sync_type='reject',
                    sync_status='success',
                    synced_by=request_data.get('rejected_by')
                )

            db_session.close()

            if success:
                return self._send_response({"status": "rejected"})
            else:
                return self._send_response({"error": "Scenario not found"}, 404)
        except Exception as e:
            logger.error(f"Error rejecting scenario: {e}")
            return self._send_response({"error": str(e)}, 500)

    def PUT_api_scenarios_id(self, scenario_id: str, body: str) -> Tuple[str, int, str]:
        """PUT /api/scenarios/{id} - Update scenario"""
        try:
            request_data = self._parse_json_body(body)
            repos, db_session = self._get_repositories()

            try:
                scenario_uuid = UUID(scenario_id)
            except ValueError:
                return self._send_response({"error": "Invalid scenario ID"}, 400)

            # Remove internal fields
            updates = {k: v for k, v in request_data.items()
                      if k not in ['scenario_id', 'generation_id', 'created_at']}

            scenario_repo = repos.get_scenario_repo()
            success = scenario_repo.update_scenario(scenario_uuid, updates)

            db_session.close()

            if success:
                return self._send_response({"status": "updated"})
            else:
                return self._send_response({"error": "Scenario not found"}, 404)
        except Exception as e:
            logger.error(f"Error updating scenario: {e}")
            return self._send_response({"error": str(e)}, 500)

    def DELETE_api_scenarios_id(self, scenario_id: str) -> Tuple[str, int, str]:
        """DELETE /api/scenarios/{id} - Delete scenario"""
        try:
            repos, db_session = self._get_repositories()

            try:
                scenario_uuid = UUID(scenario_id)
            except ValueError:
                return self._send_response({"error": "Invalid scenario ID"}, 400)

            scenario_repo = repos.get_scenario_repo()
            success = scenario_repo.delete_scenario(scenario_uuid)

            db_session.close()

            if success:
                return self._send_response({"status": "deleted"})
            else:
                return self._send_response({"error": "Scenario not found"}, 404)
        except Exception as e:
            logger.error(f"Error deleting scenario: {e}")
            return self._send_response({"error": str(e)}, 500)

    # ==================== JIRA SYNC ENDPOINTS ====================

    def GET_api_scenarios_id_history(self, scenario_id: str, limit: int = 50) -> Tuple[str, int, str]:
        """GET /api/scenarios/{id}/history - Get sync history"""
        try:
            repos, db_session = self._get_repositories()

            try:
                scenario_uuid = UUID(scenario_id)
            except ValueError:
                return self._send_response({"error": "Invalid scenario ID"}, 400)

            sync_repo = repos.get_sync_repo()
            history = sync_repo.get_sync_history(scenario_uuid, limit)

            results = [
                {
                    "sync_type": h.sync_type,
                    "sync_direction": h.sync_direction,
                    "status": h.sync_status,
                    "error": h.error_message,
                    "synced_at": h.synced_at.isoformat(),
                    "synced_by": h.synced_by
                }
                for h in history
            ]

            db_session.close()
            return self._send_response({"history": results, "total": len(results)})
        except Exception as e:
            logger.error(f"Error getting sync history: {e}")
            return self._send_response({"error": str(e)}, 500)

    def GET_api_jira_pending_syncs(self, limit: int = 100) -> Tuple[str, int, str]:
        """GET /api/jira/pending-syncs - Get scenarios pending Jira sync"""
        try:
            repos, db_session = self._get_repositories()
            scenario_repo = repos.get_scenario_repo()

            pending = scenario_repo.list_pending_scenarios(limit)
            results = [
                {
                    "scenario_id": str(s.scenario_id),
                    "title": s.title,
                    "jira_issue_key": s.jira_issue_key,
                    "status": s.status,
                    "created_at": s.created_at.isoformat()
                }
                for s in pending
            ]

            db_session.close()
            return self._send_response({"pending_scenarios": results, "total": len(results)})
        except Exception as e:
            logger.error(f"Error getting pending syncs: {e}")
            return self._send_response({"error": str(e)}, 500)

    def POST_api_jira_sync_scenario(self, scenario_id: str, body: str) -> Tuple[str, int, str]:
        """POST /api/jira/sync/{scenario_id} - Sync scenario to Jira"""
        try:
            request_data = self._parse_json_body(body)
            repos, db_session = self._get_repositories()

            try:
                scenario_uuid = UUID(scenario_id)
            except ValueError:
                return self._send_response({"error": "Invalid scenario ID"}, 400)

            # Get Jira credentials
            jira_base_url = request_data.get('jira_base_url', '').strip()
            jira_email = request_data.get('jira_email', '').strip()
            jira_token = request_data.get('jira_api_token', '').strip()

            if not all([jira_base_url, jira_email, jira_token]):
                return self._send_response({"error": "Missing Jira credentials"}, 400)

            db_session.close()

            # Trigger sync via engine
            success, child_key = sync_engine.sync_scenario_to_jira(
                scenario_uuid, jira_base_url, jira_email, jira_token
            )

            if success:
                return self._send_response({
                    "status": "synced",
                    "jira_child_issue_key": child_key
                })
            else:
                return self._send_response({
                    "status": "error",
                    "error": child_key  # Error message
                }, 500)
        except Exception as e:
            logger.error(f"Error syncing scenario: {e}")
            return self._send_response({"error": str(e)}, 500)

    def POST_api_jira_sync_batch(self, body: str) -> Tuple[str, int, str]:
        """POST /api/jira/sync-batch - Sync multiple scenarios to Jira"""
        try:
            request_data = self._parse_json_body(body)

            scenario_ids = request_data.get('scenario_ids', [])
            jira_base_url = request_data.get('jira_base_url', '').strip()
            jira_email = request_data.get('jira_email', '').strip()
            jira_token = request_data.get('jira_api_token', '').strip()

            if not all([scenario_ids, jira_base_url, jira_email, jira_token]):
                return self._send_response({"error": "Missing required fields"}, 400)

            # Convert string IDs to UUIDs
            try:
                scenario_uuids = [UUID(s) for s in scenario_ids]
            except ValueError:
                return self._send_response({"error": "Invalid scenario IDs"}, 400)

            # Trigger batch sync
            results = sync_engine.sync_batch_scenarios(
                scenario_uuids, jira_base_url, jira_email, jira_token
            )

            return self._send_response({
                "status": "completed",
                "results": results
            })
        except Exception as e:
            logger.error(f"Error in batch sync: {e}")
            return self._send_response({"error": str(e)}, 500)

    def POST_api_jira_sync_pending(self, body: str) -> Tuple[str, int, str]:
        """POST /api/jira/sync-pending - Sync all pending scenarios to Jira"""
        try:
            request_data = self._parse_json_body(body)

            jira_base_url = request_data.get('jira_base_url', '').strip()
            jira_email = request_data.get('jira_email', '').strip()
            jira_token = request_data.get('jira_api_token', '').strip()
            limit = request_data.get('limit', 50)

            if not all([jira_base_url, jira_email, jira_token]):
                return self._send_response({"error": "Missing Jira credentials"}, 400)

            # Trigger sync
            results = sync_engine.sync_pending_scenarios(
                jira_base_url, jira_email, jira_token, limit
            )

            return self._send_response({
                "status": "completed",
                "results": results
            })
        except Exception as e:
            logger.error(f"Error syncing pending: {e}")
            return self._send_response({"error": str(e)}, 500)

    def POST_api_jira_webhook(self, body: str) -> Tuple[str, int, str]:
        """POST /api/jira/webhook - Handle Jira webhook events"""
        try:
            webhook_data = self._parse_json_body(body)

            success = sync_engine.handle_jira_webhook(webhook_data)

            if success:
                return self._send_response({"status": "processed"})
            else:
                return self._send_response({"status": "error"}, 400)
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return self._send_response({"error": str(e)}, 500)

    # ==================== ANALYTICS ENDPOINTS ====================

    def GET_api_reports_coverage(self, jira_instance_url: str = None) -> Tuple[str, int, str]:
        """GET /api/reports/coverage - Test coverage by issue"""
        try:
            repos, db_session = self._get_repositories()
            scenario_repo = repos.get_scenario_repo()

            # TODO: Implement coverage calculations
            coverage_data = {
                "coverage_summary": {
                    "total_issues": 0,
                    "covered_issues": 0,
                    "partial_coverage": 0,
                    "uncovered_issues": 0
                },
                "by_issue": []
            }

            db_session.close()
            return self._send_response(coverage_data)
        except Exception as e:
            logger.error(f"Error getting coverage: {e}")
            return self._send_response({"error": str(e)}, 500)

    def GET_api_reports_sync_status(self, days: int = 30) -> Tuple[str, int, str]:
        """GET /api/reports/sync-status - Sync statistics"""
        try:
            repos, db_session = self._get_repositories()
            sync_repo = repos.get_sync_repo()

            stats = sync_repo.get_sync_statistics(days)

            db_session.close()
            return self._send_response({
                "statistics": stats,
                "period_days": days
            })
        except Exception as e:
            logger.error(f"Error getting sync stats: {e}")
            return self._send_response({"error": str(e)}, 500)

    def GET_api_reports_generations(self, user_email: str = None, limit: int = 50) -> Tuple[str, int, str]:
        """GET /api/reports/generations - Generation history"""
        try:
            repos, db_session = self._get_repositories()
            gen_repo = repos.get_generation_repo()

            if user_email:
                generations = gen_repo.list_generations_for_user(user_email, limit)
            else:
                # TODO: Implement pagination for all generations
                generations = []

            results = [
                {
                    "generation_id": str(g.generation_id),
                    "user_email": g.user_email,
                    "jira_issue_key": g.jira_issue_key,
                    "status": g.generation_status,
                    "total_scenarios": g.total_scenarios,
                    "successful_scenarios": g.successful_scenarios,
                    "failed_scenarios": g.failed_scenarios,
                    "created_at": g.created_at.isoformat()
                }
                for g in generations
            ]

            db_session.close()
            return self._send_response({
                "generations": results,
                "total": len(results)
            })
        except Exception as e:
            logger.error(f"Error getting generation reports: {e}")
            return self._send_response({"error": str(e)}, 500)

    # ==================== UTILITY METHODS ====================

    def route(self, method: str, path: str, body: str = "") -> Tuple[str, int, str]:
        """Route request to appropriate handler"""
        path_parts = path.strip('/').split('/')
        handler_name = f"{method}_{'_'.join(path_parts)}"

        # Try to find handler method
        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            try:
                return handler(body)
            except TypeError:
                # Handler might need path parameters
                if len(path_parts) > 1:
                    param = path_parts[-1]
                    handler_base = f"{method}_{path_parts[0]}_{path_parts[1]}"
                    if hasattr(self, handler_base):
                        handler = getattr(self, handler_base)
                        return handler(param, body) if method == "PUT" or method == "POST" else handler(param)

        return json.dumps({"error": "Endpoint not found"}), 404, 'application/json'


# Global API instance
api_routes = APIRoutes()
