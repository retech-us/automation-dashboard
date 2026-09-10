/**
 * Scenario Manager - Frontend for test scenario approval and Jira sync
 * Handles scenario review, approval/rejection, and synchronization to Jira
 */

class ScenarioManager {
    constructor() {
        this.currentScenarios = [];
        this.selectedScenarios = new Set();
        this.syncInProgress = false;
        this.refreshInterval = null;
        this.init();
    }

    init() {
        console.log('📋 ScenarioManager: Initializing');
        this.setupEventListeners();
        this.createUIElements();
    }

    setupEventListeners() {
        // Listen for scenario generation completion
        document.addEventListener('scenarios-generated', (e) => {
            console.log('📋 scenarios-generated event received');
            if (e.detail.testCases) {
                const scenarios = this.processScenarios(e.detail.testCases);
                this.displayScenarios(scenarios);
            }
        });
    }

    processScenarios(testCases) {
        // Get approvals from session storage
        const approvals = JSON.parse(sessionStorage.getItem('scenario_approvals') || '{}');

        // Convert testCases format to flat scenarios array
        return testCases.flatMap(tc =>
            (tc.scenarios || []).map(s => {
                const approval = approvals[s.title];
                let status = 'draft';
                if (approval?.status === 'approved') {
                    status = 'approved';
                } else if (approval?.status === 'rejected') {
                    status = 'rejected';
                }

                return {
                    id: s.id || Math.random().toString(36).substr(2, 9),
                    title: s.title,
                    type: s.type || 'positive',
                    status: status,
                    priority: s.priority || 'medium',
                    category: s.category || '',
                    preconditions: s.preconditions || [],
                    steps: s.steps || [],
                    expected_result: s.expectedResult || s.expected_result || '',
                    automation_hint: s.automationHint || s.automation_hint || '',
                    tags: s.tags || [],
                    jira_issue_key: tc.issueKey || '',
                    jira_sync_status: 'pending',
                    jira_child_issue_key: null,
                    rejection_reason: approval?.reason || null
                };
            })
        );
    }

    createUIElements() {
        // Create scenario review panel
        const panel = `
            <div id="scenario-review-panel" class="scenario-review-panel">
                <div class="panel-header">
                    <h3>🧪 Test Scenarios</h3>
                    <div class="panel-controls">
                        <button id="batch-sync-btn" class="btn btn-primary btn-sm" title="Sync all approved scenarios to Jira">
                            <span class="sync-icon">🔗</span> Sync to Jira
                        </button>
                        <button id="refresh-scenarios-btn" class="btn btn-secondary btn-sm" title="Refresh scenario list">
                            <span>🔄</span>
                        </button>
                    </div>
                </div>

                <div class="panel-filters">
                    <div class="filter-group">
                        <input type="checkbox" id="filter-approved" class="filter-checkbox">
                        <label for="filter-approved">Approved</label>
                    </div>
                    <div class="filter-group">
                        <input type="checkbox" id="filter-pending-sync" class="filter-checkbox">
                        <label for="filter-pending-sync">Pending Sync</label>
                    </div>
                    <div class="filter-group">
                        <input type="checkbox" id="filter-synced" class="filter-checkbox">
                        <label for="filter-synced">Synced</label>
                    </div>
                </div>

                <div id="scenarios-container" class="scenarios-container">
                    <p class="empty-state">No scenarios generated yet</p>
                </div>

                <div id="sync-progress-container" class="sync-progress-container hidden">
                    <div class="progress-header">
                        <h4>Syncing to Jira...</h4>
                        <span id="sync-progress-text">0/0</span>
                    </div>
                    <div class="progress-bar">
                        <div id="sync-progress-fill" class="progress-fill"></div>
                    </div>
                </div>

                <div id="sync-results-container" class="sync-results-container hidden">
                    <div class="results-header">
                        <h4>Sync Complete</h4>
                        <button class="btn-close" onclick="this.parentElement.parentElement.classList.add('hidden')">×</button>
                    </div>
                    <div id="sync-results-content" class="results-content"></div>
                </div>
            </div>
        `;

        // Insert into the Generate Test Cases tab container
        const scenarioContainer = document.getElementById('scenario-manager-container');
        if (scenarioContainer) {
            scenarioContainer.innerHTML = panel;
            console.log('✓ Panel inserted into scenario-manager-container');
            this.attachPanelListeners();
        } else {
            console.warn('⚠️ scenario-manager-container not found, panel will be inserted when tab loads');
            // Fallback: wait for container and insert when available
            const tryInsert = () => {
                const container = document.getElementById('scenario-manager-container');
                if (container) {
                    container.innerHTML = panel;
                    console.log('✓ Panel inserted into scenario-manager-container (delayed)');
                    this.attachPanelListeners();
                } else {
                    setTimeout(tryInsert, 500);
                }
            };
            tryInsert();
        }
    }

    attachPanelListeners() {
        const batchSyncBtn = document.getElementById('batch-sync-btn');
        const refreshBtn = document.getElementById('refresh-scenarios-btn');

        if (batchSyncBtn) {
            batchSyncBtn.addEventListener('click', () => this.showSyncModal());
        }
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshScenarioList());
        }

        // Filter listeners
        document.getElementById('filter-approved')?.addEventListener('change', () => this.applyFilters());
        document.getElementById('filter-pending-sync')?.addEventListener('change', () => this.applyFilters());
        document.getElementById('filter-synced')?.addEventListener('change', () => this.applyFilters());
    }

    displayScenarios(scenarios) {
        console.log(`📋 Displaying ${scenarios.length} scenarios`);
        this.currentScenarios = scenarios;
        this.renderScenarioList(scenarios);
    }

    renderScenarioList(scenarios) {
        const container = document.getElementById('scenarios-container');
        if (!container) return;

        if (scenarios.length === 0) {
            container.innerHTML = '<p class="empty-state">No scenarios available</p>';
            return;
        }

        container.innerHTML = scenarios.map((scenario, idx) => `
            <div class="scenario-card" data-scenario-id="${scenario.id}" data-index="${idx}">
                <div class="scenario-header">
                    <div class="scenario-title">
                        <input type="checkbox" class="scenario-checkbox" value="${scenario.id}">
                        <h4>${scenario.title}</h4>
                    </div>
                    <div class="scenario-badges">
                        ${this.getBadge(scenario.type, 'type')}
                        ${this.getBadge(scenario.status, 'status')}
                        ${scenario.jira_sync_status ? this.getBadge(scenario.jira_sync_status, 'sync') : ''}
                    </div>
                </div>

                <div class="scenario-details">
                    <div class="detail-group">
                        <strong>Type:</strong> ${scenario.type || 'N/A'}
                    </div>
                    ${scenario.priority ? `<div class="detail-group"><strong>Priority:</strong> ${scenario.priority}</div>` : ''}
                    ${scenario.category ? `<div class="detail-group"><strong>Category:</strong> ${scenario.category}</div>` : ''}
                </div>

                ${scenario.preconditions ? `
                    <div class="scenario-section">
                        <strong>Preconditions:</strong>
                        <ul class="preconditions-list">
                            ${(Array.isArray(scenario.preconditions) ? scenario.preconditions : [scenario.preconditions])
                                .map(p => `<li>${p}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}

                ${scenario.steps ? `
                    <div class="scenario-section">
                        <strong>Steps:</strong>
                        <ol class="steps-list">
                            ${(Array.isArray(scenario.steps) ? scenario.steps : [scenario.steps])
                                .map((step, i) => {
                                    if (typeof step === 'object' && step.action) {
                                        return `<li>${step.action}</li>`;
                                    }
                                    return `<li>${step}</li>`;
                                }).join('')}
                        </ol>
                    </div>
                ` : ''}

                ${scenario.expected_result ? `
                    <div class="scenario-section">
                        <strong>Expected Result:</strong>
                        <p>${scenario.expected_result}</p>
                    </div>
                ` : ''}

                ${scenario.tags && scenario.tags.length > 0 ? `
                    <div class="scenario-tags">
                        ${scenario.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                    </div>
                ` : ''}

                ${scenario.jira_child_issue_key ? `
                    <div class="jira-link-box">
                        <span class="jira-icon">🔗</span>
                        <a href="${scenario.jira_child_issue_url}" target="_blank" rel="noopener">
                            View in Jira: ${scenario.jira_child_issue_key}
                        </a>
                    </div>
                ` : ''}

                <div class="scenario-actions">
                    ${scenario.status !== 'approved' ? `
                        <button class="btn btn-success btn-sm approve-btn" data-id="${scenario.id}">
                            ✓ Approve
                        </button>
                    ` : ''}
                    ${scenario.status !== 'rejected' && scenario.status !== 'approved' ? `
                        <button class="btn btn-danger btn-sm reject-btn" data-id="${scenario.id}">
                            ✗ Reject
                        </button>
                    ` : ''}
                    ${scenario.status === 'approved' && !scenario.jira_child_issue_key ? `
                        <button class="btn btn-primary btn-sm sync-single-btn" data-id="${scenario.id}">
                            🔗 Sync to Jira
                        </button>
                    ` : ''}
                    ${scenario.status === 'approved' && scenario.jira_child_issue_key ? `
                        <span class="badge badge-success">✓ Synced</span>
                    ` : ''}
                </div>

                ${scenario.rejection_reason ? `
                    <div class="rejection-notice">
                        <strong>Rejection Reason:</strong> ${scenario.rejection_reason}
                    </div>
                ` : ''}
            </div>
        `).join('');

        this.attachScenarioListeners();
    }

    attachScenarioListeners() {
        // Checkbox listeners
        document.querySelectorAll('.scenario-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.selectedScenarios.add(e.target.value);
                } else {
                    this.selectedScenarios.delete(e.target.value);
                }
                this.updateBatchSyncButton();
            });
        });

        // Approve listeners
        document.querySelectorAll('.approve-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const scenarioId = e.target.getAttribute('data-id');
                this.approveScenario(scenarioId);
            });
        });

        // Reject listeners
        document.querySelectorAll('.reject-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const scenarioId = e.target.getAttribute('data-id');
                this.showRejectModal(scenarioId);
            });
        });

        // Single sync listeners
        document.querySelectorAll('.sync-single-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const scenarioId = e.target.getAttribute('data-id');
                this.syncSingleScenario(scenarioId);
            });
        });
    }

    getBadge(value, type) {
        const badges = {
            type: {
                positive: '<span class="badge badge-blue">Positive</span>',
                negative: '<span class="badge badge-red">Negative</span>',
                'edge-case': '<span class="badge badge-yellow">Edge Case</span>',
                default: `<span class="badge badge-gray">${value}</span>`
            },
            status: {
                draft: '<span class="badge badge-gray">Draft</span>',
                approved: '<span class="badge badge-green">✓ Approved</span>',
                rejected: '<span class="badge badge-red">✗ Rejected</span>',
                default: `<span class="badge">${value}</span>`
            },
            sync: {
                pending: '<span class="badge badge-yellow">Pending Sync</span>',
                synced: '<span class="badge badge-green">✓ Synced</span>',
                failed: '<span class="badge badge-red">Sync Failed</span>',
                default: `<span class="badge">${value}</span>`
            }
        };

        return (badges[type] && badges[type][value]) || badges[type].default;
    }

    approveScenario(scenarioId) {
        const userEmail = document.body.getAttribute('data-user-email') || 'unknown@example.com';

        fetch('/api/scenarios/' + scenarioId + '/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ approved_by: userEmail })
        })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'approved') {
                console.log(`✓ Scenario approved: ${scenarioId}`);
                this.showNotification('Scenario approved! Ready to sync to Jira.', 'success');
                this.refreshScenarioList();
            } else {
                this.showNotification('Failed to approve scenario', 'error');
            }
        })
        .catch(e => {
            console.error('❌ Error approving scenario:', e);
            this.showNotification('Error approving scenario', 'error');
        });
    }

    showRejectModal(scenarioId) {
        const modal = document.createElement('div');
        modal.className = 'modal modal-overlay';
        modal.innerHTML = `
            <div class="modal-content modal-md">
                <div class="modal-header">
                    <h3>Reject Scenario</h3>
                    <button class="btn-close">&times;</button>
                </div>
                <div class="modal-body">
                    <label for="reject-reason">Reason for rejection:</label>
                    <textarea id="reject-reason" placeholder="Explain why this scenario needs revision..." rows="4"></textarea>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button class="btn btn-danger" onclick="this.dispatchEvent(new CustomEvent('confirm-reject', {detail: '${scenarioId}'}))">Reject</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.classList.add('is-open');

        const confirmBtn = modal.querySelector('[onclick*="dispatchEvent"]');
        confirmBtn.addEventListener('click', () => {
            const reason = document.getElementById('reject-reason').value;
            if (!reason.trim()) {
                this.showNotification('Please provide a reason', 'warning');
                return;
            }

            this.rejectScenario(scenarioId, reason);
            modal.remove();
        });

        modal.querySelector('.btn-close').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    rejectScenario(scenarioId, reason) {
        const userEmail = document.body.getAttribute('data-user-email') || 'unknown@example.com';

        fetch('/api/scenarios/' + scenarioId + '/reject', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason, rejected_by: userEmail })
        })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'rejected') {
                console.log(`✗ Scenario rejected: ${scenarioId}`);
                this.showNotification('Scenario rejected', 'info');
                this.refreshScenarioList();
            } else {
                this.showNotification('Failed to reject scenario', 'error');
            }
        })
        .catch(e => {
            console.error('❌ Error rejecting scenario:', e);
            this.showNotification('Error rejecting scenario', 'error');
        });
    }

    showSyncModal() {
        const approvedPending = this.currentScenarios.filter(s =>
            s.status === 'approved' && !s.jira_child_issue_key
        );

        if (approvedPending.length === 0) {
            this.showNotification('No approved scenarios pending sync', 'info');
            return;
        }

        const modal = document.createElement('div');
        modal.className = 'modal modal-overlay';
        modal.innerHTML = `
            <div class="modal-content modal-md">
                <div class="modal-header">
                    <h3>🔗 Sync Scenarios to Jira</h3>
                    <button class="btn-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="sync-info">
                        <p><strong>Ready to sync ${approvedPending.length} approved scenario(s) to Jira</strong></p>
                        ${approvedPending.length > 1 ? `
                            <p class="text-muted">The following scenarios will be created as child issues:</p>
                            <ul>
                                ${approvedPending.slice(0, 5).map(s => `<li>${s.title}</li>`).join('')}
                                ${approvedPending.length > 5 ? `<li>... and ${approvedPending.length - 5} more</li>` : ''}
                            </ul>
                        ` : ''}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button class="btn btn-primary" id="confirm-sync-btn">
                        🔗 Sync Now
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.classList.add('is-open');

        modal.querySelector('#confirm-sync-btn').addEventListener('click', () => {
            modal.remove();
            this.syncPendingScenarios();
        });

        modal.querySelector('.btn-close').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    syncSingleScenario(scenarioId) {
        const credentials = window.credentialsManager?.getSession();
        if (!credentials) {
            this.showNotification('Session expired. Please enter credentials again.', 'error');
            window.credentialsManager?.openModal();
            return;
        }

        const scenario = this.currentScenarios.find(s => s.id === scenarioId);
        if (!scenario) {
            this.showNotification('Scenario not found', 'error');
            return;
        }

        this.syncInProgress = true;
        this.updateBatchSyncButton();

        fetch('/api/jira/sync/' + scenarioId, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jira_base_url: credentials.jira_base_url,
                jira_email: credentials.jira_email,
                jira_api_token: credentials.jira_api_token
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'synced') {
                console.log(`✓ Scenario synced: ${data.jira_child_issue_key}`);
                this.showNotification(`✓ Synced to ${data.jira_child_issue_key}`, 'success');
                this.refreshScenarioList();
            } else {
                this.showNotification(`Sync failed: ${data.error}`, 'error');
            }
        })
        .catch(e => {
            console.error('❌ Error syncing:', e);
            this.showNotification('Error syncing to Jira', 'error');
        })
        .finally(() => {
            this.syncInProgress = false;
            this.updateBatchSyncButton();
        });
    }

    syncPendingScenarios() {
        const credentials = window.credentialsManager?.getSession();
        if (!credentials) {
            this.showNotification('Session expired. Please enter credentials again.', 'error');
            window.credentialsManager?.openModal();
            return;
        }

        this.syncInProgress = true;
        this.selectedScenarios.clear();
        this.updateBatchSyncButton();
        this.showSyncProgress();

        const payload = {
            jira_base_url: credentials.jira_base_url,
            jira_email: credentials.jira_email,
            jira_api_token: credentials.jira_api_token,
            limit: 100
        };

        fetch('/api/jira/sync-pending', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'completed') {
                const results = data.results;
                console.log(`✓ Sync complete: ${results.successful}/${results.total}`);
                this.showSyncResults(results);
                this.refreshScenarioList();
            } else {
                this.showNotification('Sync failed', 'error');
                this.hideSyncProgress();
            }
        })
        .catch(e => {
            console.error('❌ Error syncing:', e);
            this.showNotification('Error syncing to Jira', 'error');
            this.hideSyncProgress();
        })
        .finally(() => {
            this.syncInProgress = false;
            this.updateBatchSyncButton();
        });
    }

    showSyncProgress() {
        const container = document.getElementById('sync-progress-container');
        if (container) {
            container.classList.remove('hidden');
        }
    }

    hideSyncProgress() {
        const container = document.getElementById('sync-progress-container');
        if (container) {
            container.classList.add('hidden');
        }
    }

    showSyncResults(results) {
        this.hideSyncProgress();

        const resultsContainer = document.getElementById('sync-results-container');
        const contentDiv = document.getElementById('sync-results-content');

        if (resultsContainer && contentDiv) {
            contentDiv.innerHTML = `
                <div class="results-grid">
                    <div class="result-stat">
                        <div class="stat-number">${results.successful}</div>
                        <div class="stat-label">Successful</div>
                    </div>
                    <div class="result-stat">
                        <div class="stat-number">${results.failed}</div>
                        <div class="stat-label">Failed</div>
                    </div>
                    <div class="result-stat">
                        <div class="stat-number">${((results.successful / results.total) * 100).toFixed(0)}%</div>
                        <div class="stat-label">Success Rate</div>
                    </div>
                </div>

                ${results.synced_issues && results.synced_issues.length > 0 ? `
                    <div class="synced-issues">
                        <strong>✓ Created as Child Issues in Jira:</strong>
                        <ul>
                            ${results.synced_issues.map(key => `
                                <li>
                                    <a href="https://retech.atlassian.net/browse/${key}" target="_blank">
                                        ${key} →
                                    </a>
                                </li>
                            `).join('')}
                        </ul>
                        <p style="font-size: 12px; color: #666; margin-top: 10px;">
                            These scenarios are now linked to your Jira ticket as child issues and have been removed from the pending list.
                        </p>
                    </div>
                ` : ''}
            `;

            resultsContainer.classList.remove('hidden');
        }

        // Remove synced scenarios from the display
        if (results.synced_issues && results.synced_issues.length > 0) {
            setTimeout(() => {
                this.removeSyncedScenariosFromUI(results.synced_issues);
                this.updateBatchSyncButton();
            }, 1000);
        }

        // Show success notification
        this.showNotification(`✓ Successfully synced ${results.successful} scenario(s) to Jira!`, 'success');
    }

    removeSyncedScenariosFromUI(syncedIssueKeys) {
        const container = document.getElementById('scenarios-container');
        if (!container) return;

        // Filter out synced scenarios from current scenarios
        this.currentScenarios = this.currentScenarios.filter(scenario => {
            // Keep scenarios that don't have a Jira child issue key yet
            return !scenario.jira_child_issue_key;
        });

        // Re-render the list (will now exclude synced scenarios)
        if (this.currentScenarios.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="padding: 60px 20px; text-align: center;">
                    <p style="font-size: 18px; margin-bottom: 10px;">✓ All scenarios synced!</p>
                    <p style="color: #666;">All approved scenarios have been successfully added to Jira as child issues.</p>
                    <p style="color: #999; font-size: 12px; margin-top: 15px;">
                        To view them, open your Jira ticket and check the child issues section.
                    </p>
                </div>
            `;
        } else {
            this.renderScenarioList(this.currentScenarios);
        }

        console.log(`✓ Removed ${syncedIssueKeys.length} synced scenarios from UI`);
    }

    updateBatchSyncButton() {
        const btn = document.getElementById('batch-sync-btn');
        if (btn) {
            const approvedPending = this.currentScenarios.filter(s =>
                s.status === 'approved' && !s.jira_child_issue_key
            ).length;

            btn.disabled = approvedPending === 0 || this.syncInProgress;
            btn.textContent = this.syncInProgress
                ? '⏳ Syncing...'
                : `🔗 Sync to Jira (${approvedPending})`;
        }
    }

    applyFilters() {
        // TODO: Implement filtering
    }

    refreshScenarioList() {
        // Refresh is handled by scenario generation
        // This is a placeholder for manual refresh
        console.log('🔄 Scenario list refresh triggered');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        const container = document.querySelector('.notification-container') || document.body;
        container.appendChild(notification);

        setTimeout(() => notification.remove(), 4000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.scenarioManager === undefined) {
        window.scenarioManager = new ScenarioManager();
        console.log('✓ ScenarioManager initialized');
    }
});
