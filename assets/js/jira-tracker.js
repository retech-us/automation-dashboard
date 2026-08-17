/**
 * Jira Quality & Defect Tracker for Store Intell QA Dashboard.
 * Supports multi-axis filtering (Project, Fix Version, Type, Assignee, Tester, Status, Priority)
 * and interactive column & dropdown sorting.
 */

(function (window) {
  'use strict';

  const PRIORITY_RANKS = {
    'highest': 5,
    'blocker': 5,
    'p0': 5,
    'high': 4,
    'p1': 4,
    'medium': 3,
    'p2': 3,
    'low': 2,
    'p3': 2,
    'lowest': 1,
    'p4': 1
  };

  class JiraTracker {
    constructor() {
      this.data = null;
      this.filters = {
        kpi: 'all',          // 'all', 'blockers', 'progress', 'qa', 'resolved'
        project: 'all',
        fixVersion: 'all',
        type: 'all',
        assignee: 'all',
        tester: 'all',
        priority: 'all',
        component: 'all',
        searchQuery: ''
      };
      this.sort = {
        field: 'priority',  // 'priority', 'key', 'summary', 'fixVersion', 'status', 'assignee', 'tester', 'created', 'updated'
        dir: 'desc'         // 'asc' or 'desc'
      };
      this.initialized = false;
    }

    async init() {
      if (this.initialized && this.data) {
        this.render();
        return;
      }
      await this.loadData();
      this.render();
      this.initialized = true;
    }

    async loadData() {
      if (window.DASHBOARD_SNAPSHOTS?.snapshots?.jira) {
        this.data = window.DASHBOARD_SNAPSHOTS.snapshots.jira;
      }

      try {
        const res = await fetch(`data/jira.json?_=${Date.now()}`);
        if (res.ok) {
          this.data = await res.json();
        }
      } catch (err) {
        console.warn('[Jira Tracker] Could not fetch fresh data/jira.json:', err);
      }
    }

    escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    getPriorityClass(priority) {
      const p = (priority || '').toLowerCase();
      if (p.includes('highest') || p.includes('blocker') || p.includes('p0')) return 'jira-priority--highest';
      if (p.includes('high') || p.includes('p1')) return 'jira-priority--high';
      if (p.includes('medium') || p.includes('p2')) return 'jira-priority--medium';
      if (p.includes('low') || p.includes('p3')) return 'jira-priority--low';
      return 'jira-priority--lowest';
    }

    getStatusBadgeClass(statusCategory, statusName) {
      const cat = (statusCategory || '').toLowerCase();
      const name = (statusName || '').toLowerCase();
      if (cat === 'done' || name.includes('closed') || name.includes('resolved')) return 'jira-status--done';
      if (name.includes('qa') || name.includes('testing') || name.includes('review')) return 'jira-status--qa';
      if (cat === 'indeterminate' || name.includes('progress') || name.includes('dev')) return 'jira-status--prog';
      return 'jira-status--open';
    }

    getPriorityRank(priority) {
      const p = (priority || '').toLowerCase().trim();
      return PRIORITY_RANKS[p] || 3;
    }

    filterAndSortIssues(issues) {
      // 1. Filtering
      let filtered = issues.filter((issue) => {
        // KPI Card Quick Filters
        if (this.filters.kpi === 'blockers') {
          const p = (issue.priority || '').toLowerCase();
          if (!p.includes('highest') && !p.includes('blocker') && !p.includes('p0')) return false;
        } else if (this.filters.kpi === 'progress') {
          const s = (issue.status || '').toLowerCase();
          if (!s.includes('progress') && !s.includes('dev')) return false;
        } else if (this.filters.kpi === 'qa') {
          const s = (issue.status || '').toLowerCase();
          if (!s.includes('qa') && !s.includes('review') && !s.includes('testing')) return false;
        } else if (this.filters.kpi === 'resolved') {
          const s = (issue.statusCategory || '').toLowerCase();
          const sn = (issue.status || '').toLowerCase();
          if (s !== 'done' && !sn.includes('closed') && !sn.includes('resolved')) return false;
        }

        // Project Filter
        if (this.filters.project !== 'all' && (issue.project !== this.filters.project && issue.projectKey !== this.filters.project)) {
          return false;
        }

        // Fix Version Filter
        if (this.filters.fixVersion !== 'all' && issue.fixVersion !== this.filters.fixVersion) {
          return false;
        }

        // Type Filter
        if (this.filters.type !== 'all' && issue.type !== this.filters.type) {
          return false;
        }

        // Assignee Filter
        if (this.filters.assignee !== 'all' && issue.assignee !== this.filters.assignee) {
          return false;
        }

        // Tester Filter
        if (this.filters.tester !== 'all' && (issue.tester !== this.filters.tester && issue.reporter !== this.filters.tester)) {
          return false;
        }

        // Priority Filter
        if (this.filters.priority !== 'all' && issue.priority !== this.filters.priority) {
          return false;
        }

        // Component Filter
        if (this.filters.component !== 'all' && issue.component !== this.filters.component) {
          return false;
        }

        // Search Query
        if (this.filters.searchQuery.trim()) {
          const q = this.filters.searchQuery.toLowerCase();
          const matchKey = (issue.key || '').toLowerCase().includes(q);
          const matchSum = (issue.summary || '').toLowerCase().includes(q);
          const matchAss = (issue.assignee || '').toLowerCase().includes(q);
          const matchTest = (issue.tester || '').toLowerCase().includes(q);
          const matchProj = (issue.project || '').toLowerCase().includes(q);
          const matchVer = (issue.fixVersion || '').toLowerCase().includes(q);
          const matchComp = (issue.component || '').toLowerCase().includes(q);
          const matchLabels = (issue.labels || []).some(l => l.toLowerCase().includes(q));
          if (!matchKey && !matchSum && !matchAss && !matchTest && !matchProj && !matchVer && !matchComp && !matchLabels) {
            return false;
          }
        }

        return true;
      });

      // 2. Sorting
      filtered.sort((a, b) => {
        let valA, valB;
        const field = this.sort.field;

        if (field === 'priority') {
          valA = this.getPriorityRank(a.priority);
          valB = this.getPriorityRank(b.priority);
        } else if (field === 'created' || field === 'updated') {
          valA = new Date(a[field] || 0).getTime();
          valB = new Date(b[field] || 0).getTime();
        } else if (field === 'key') {
          // Extract numeric ID if possible for natural sort
          const numA = parseInt(a.key?.split('-')[1] || '0', 10);
          const numB = parseInt(b.key?.split('-')[1] || '0', 10);
          if (numA && numB) {
            valA = numA;
            valB = numB;
          } else {
            valA = (a.key || '').toLowerCase();
            valB = (b.key || '').toLowerCase();
          }
        } else {
          valA = (a[field] || '').toString().toLowerCase();
          valB = (b[field] || '').toString().toLowerCase();
        }

        let res = 0;
        if (valA > valB) res = 1;
        else if (valA < valB) res = -1;

        return this.sort.dir === 'desc' ? -res : res;
      });

      return filtered;
    }

    countActiveFilters() {
      let count = 0;
      if (this.filters.kpi !== 'all') count++;
      if (this.filters.project !== 'all') count++;
      if (this.filters.fixVersion !== 'all') count++;
      if (this.filters.type !== 'all') count++;
      if (this.filters.assignee !== 'all') count++;
      if (this.filters.tester !== 'all') count++;
      if (this.filters.priority !== 'all') count++;
      if (this.filters.component !== 'all') count++;
      if (this.filters.searchQuery.trim()) count++;
      return count;
    }

    resetFilters() {
      this.filters = {
        kpi: 'all',
        project: 'all',
        fixVersion: 'all',
        type: 'all',
        assignee: 'all',
        tester: 'all',
        priority: 'all',
        component: 'all',
        searchQuery: ''
      };
      this.render();
    }

    renderSortHeader(field, label, width = '') {
      const isCurrent = this.sort.field === field;
      const arrow = isCurrent ? (this.sort.dir === 'asc' ? ' ▲' : ' ▼') : ' ↕';
      const style = width ? `style="width:${width};"` : '';
      return `
        <th ${style} class="jira-sortable-th ${isCurrent ? 'jira-sortable-th--active' : ''}" data-sort-field="${field}">
          <span>${label}</span><span class="jira-sort-indicator">${arrow}</span>
        </th>
      `;
    }

    render() {
      const container = document.getElementById('jira-content');
      const statusPill = document.getElementById('jira-status-pill');
      const headerActions = document.getElementById('jira-header-actions');
      if (!container) return;

      if (!this.data) {
        container.innerHTML = `
          <div class="jira-empty-state">
            <div class="jira-empty-icon">⏳</div>
            <h3>No Jira Data Available Yet</h3>
            <p>Jira data will appear here once the scheduled sync runs or workflow is triggered.</p>
          </div>
        `;
        if (statusPill) statusPill.textContent = 'No Data';
        return;
      }

      const { summary = {}, issues = [], jiraUrl, projectKey, status, lastUpdated, filterOptions = {}, lastError } = this.data;
      const filtered = this.filterAndSortIssues(issues);
      const isLive = status === 'live';
      const isError = status === 'error';
      const activeFilterCount = this.countActiveFilters();

      // Extract unique lists dynamically if not in filterOptions
      const projects = filterOptions.projects || Array.from(new Set(issues.map(i => i.project || i.projectKey).filter(Boolean)));
      const fixVersions = filterOptions.fixVersions || Array.from(new Set(issues.map(i => i.fixVersion).filter(Boolean)));
      const types = filterOptions.types || Array.from(new Set(issues.map(i => i.type).filter(Boolean)));
      const assignees = filterOptions.assignees || Array.from(new Set(issues.map(i => i.assignee).filter(Boolean)));
      const testers = filterOptions.testers || Array.from(new Set(issues.map(i => i.tester || i.reporter).filter(Boolean)));
      const priorities = ['Highest', 'High', 'Medium', 'Low', 'Lowest'];

      // Update status pill
      if (statusPill) {
        if (isLive) {
          statusPill.innerHTML = `<span style="color:#10b981;">●</span> Live Jira (${this.escapeHtml(projectKey || 'Connected')})`;
        } else if (isError) {
          statusPill.innerHTML = `<span style="color:#f59e0b;">⏳</span> Pending CI Jira Sync`;
        } else {
          statusPill.innerHTML = `<span>ℹ️</span> Sample Dataset`;
        }
        statusPill.title = isError && lastError ? `Sync info: ${lastError}` : `Last synchronized: ${lastUpdated ? new Date(lastUpdated).toLocaleString() : 'N/A'}`;
      }

      // Update header action button
      if (headerActions && jiraUrl) {
        headerActions.innerHTML = `
          <a href="${jiraUrl}" target="_blank" rel="noopener noreferrer" class="btn btn--ghost" style="font-size:13px;display:inline-flex;align-items:center;gap:6px;">
            <span>Open Jira (${this.escapeHtml(projectKey || 'Jira')})</span> ↗
          </a>
        `;
      }

      container.innerHTML = `
        <!-- KPI Metrics Grid -->
        <div class="jira-kpi-grid">
          <div class="jira-kpi-card ${this.filters.kpi === 'all' ? 'jira-kpi-card--active' : ''}" data-kpi="all">
            <div class="jira-kpi-label">Tracked Defects</div>
            <div class="jira-kpi-val">${summary.totalDefects || issues.length}</div>
            <div class="jira-kpi-sub">Total active &amp; tracked</div>
          </div>

          <div class="jira-kpi-card jira-kpi-card--blocker ${this.filters.kpi === 'blockers' ? 'jira-kpi-card--active' : ''}" data-kpi="blockers">
            <div class="jira-kpi-label">🚨 Critical Blockers</div>
            <div class="jira-kpi-val" style="color:var(--fail);">${summary.blockers || 0}</div>
            <div class="jira-kpi-sub">Highest / P0 Priority</div>
          </div>

          <div class="jira-kpi-card ${this.filters.kpi === 'progress' ? 'jira-kpi-card--active' : ''}" data-kpi="progress">
            <div class="jira-kpi-label">⚡ In Progress</div>
            <div class="jira-kpi-val" style="color:var(--warn);">${summary.inProgress || 0}</div>
            <div class="jira-kpi-sub">Active developer fixes</div>
          </div>

          <div class="jira-kpi-card ${this.filters.kpi === 'qa' ? 'jira-kpi-card--active' : ''}" data-kpi="qa">
            <div class="jira-kpi-label">🔍 Ready for QA</div>
            <div class="jira-kpi-val" style="color:#38bdf8;">${summary.inQa || 0}</div>
            <div class="jira-kpi-sub">Ready for test verification</div>
          </div>

          <div class="jira-kpi-card ${this.filters.kpi === 'resolved' ? 'jira-kpi-card--active' : ''}" data-kpi="resolved">
            <div class="jira-kpi-label">✅ Resolved Recently</div>
            <div class="jira-kpi-val" style="color:var(--pass);">${summary.resolvedThisWeek || summary.resolvedTotal || 0}</div>
            <div class="jira-kpi-sub">Closed / Verified</div>
          </div>
        </div>

        <!-- Comprehensive Multi-Filter Bar -->
        <div class="jira-filter-section">
          <div class="jira-filter-header">
            <div class="jira-filter-title">
              <span>⚡ Filters &amp; Sorting</span>
              <span class="jira-filter-count-badge">${filtered.length} of ${issues.length} shown</span>
              ${activeFilterCount > 0 ? `<button type="button" class="jira-clear-btn" id="jira-btn-clear-filters">✕ Clear Filters (${activeFilterCount})</button>` : ''}
            </div>
            
            <div class="jira-sort-control">
              <label for="jira-sort-select">Sort By:</label>
              <select id="jira-sort-select" class="jira-select">
                <option value="priority-desc" ${this.sort.field === 'priority' && this.sort.dir === 'desc' ? 'selected' : ''}>Priority (Highest → Lowest)</option>
                <option value="priority-asc" ${this.sort.field === 'priority' && this.sort.dir === 'asc' ? 'selected' : ''}>Priority (Lowest → Highest)</option>
                <option value="created-desc" ${this.sort.field === 'created' && this.sort.dir === 'desc' ? 'selected' : ''}>Created Date (Newest First)</option>
                <option value="created-asc" ${this.sort.field === 'created' && this.sort.dir === 'asc' ? 'selected' : ''}>Created Date (Oldest First)</option>
                <option value="updated-desc" ${this.sort.field === 'updated' && this.sort.dir === 'desc' ? 'selected' : ''}>Recently Updated</option>
                <option value="key-asc" ${this.sort.field === 'key' && this.sort.dir === 'asc' ? 'selected' : ''}>Ticket Key (A → Z)</option>
                <option value="fixVersion-desc" ${this.sort.field === 'fixVersion' && this.sort.dir === 'desc' ? 'selected' : ''}>Fix Version</option>
                <option value="assignee-asc" ${this.sort.field === 'assignee' && this.sort.dir === 'asc' ? 'selected' : ''}>Assignee Name</option>
              </select>
            </div>
          </div>

          <div class="jira-filter-grid">
            <!-- Project Filter -->
            <div class="jira-filter-field">
              <label>📁 Project</label>
              <select class="jira-select" id="filter-project">
                <option value="all">All Projects</option>
                ${projects.map(p => `<option value="${this.escapeHtml(p)}" ${this.filters.project === p ? 'selected' : ''}>${this.escapeHtml(p)}</option>`).join('')}
              </select>
            </div>

            <!-- Fix Version Filter -->
            <div class="jira-filter-field">
              <label>🎯 Fix Version</label>
              <select class="jira-select" id="filter-fix-version">
                <option value="all">All Versions</option>
                ${fixVersions.map(v => `<option value="${this.escapeHtml(v)}" ${this.filters.fixVersion === v ? 'selected' : ''}>${this.escapeHtml(v)}</option>`).join('')}
              </select>
            </div>

            <!-- Issue Type Filter -->
            <div class="jira-filter-field">
              <label>🏷️ Issue Type</label>
              <select class="jira-select" id="filter-type">
                <option value="all">All Types</option>
                ${types.map(t => `<option value="${this.escapeHtml(t)}" ${this.filters.type === t ? 'selected' : ''}>${this.escapeHtml(t)}</option>`).join('')}
              </select>
            </div>

            <!-- Assignee Filter -->
            <div class="jira-filter-field">
              <label>👤 Assignee (Dev)</label>
              <select class="jira-select" id="filter-assignee">
                <option value="all">All Assignees</option>
                ${assignees.map(a => `<option value="${this.escapeHtml(a)}" ${this.filters.assignee === a ? 'selected' : ''}>${this.escapeHtml(a)}</option>`).join('')}
              </select>
            </div>

            <!-- Tester / QA Filter -->
            <div class="jira-filter-field">
              <label>🧪 Tester / QA</label>
              <select class="jira-select" id="filter-tester">
                <option value="all">All Testers</option>
                ${testers.map(t => `<option value="${this.escapeHtml(t)}" ${this.filters.tester === t ? 'selected' : ''}>${this.escapeHtml(t)}</option>`).join('')}
              </select>
            </div>

            <!-- Priority Filter -->
            <div class="jira-filter-field">
              <label>📶 Priority</label>
              <select class="jira-select" id="filter-priority">
                <option value="all">All Priorities</option>
                ${priorities.map(pr => `<option value="${this.escapeHtml(pr)}" ${this.filters.priority === pr ? 'selected' : ''}>${this.escapeHtml(pr)}</option>`).join('')}
              </select>
            </div>

            <!-- Search Field -->
            <div class="jira-filter-field jira-filter-field--search">
              <label>🔍 Live Search</label>
              <div class="jira-search-wrapper">
                <input type="text" id="jira-search-input" class="jira-search-input" placeholder="Search key, summary, label..." value="${this.escapeHtml(this.filters.searchQuery)}" />
                ${this.filters.searchQuery ? `<button type="button" id="jira-search-clear" class="jira-search-clear">✕</button>` : ''}
              </div>
            </div>
          </div>
        </div>

        <!-- Issues List Table -->
        <div class="jira-table-container">
          ${filtered.length === 0 ? `
            <div class="jira-empty-state" style="padding:48px 20px;">
              <div class="jira-empty-icon">${issues.length === 0 ? (isError ? '⚙️' : '📁') : '🔍'}</div>
              <h3 style="margin-bottom:8px;">${issues.length === 0 ? (isError ? 'Jira Project Sync' : 'No Jira Tickets Found') : 'No Matching Tickets'}</h3>
              <p style="font-size:14px;color:var(--muted);max-width:540px;margin:0 auto 16px;">
                ${issues.length === 0 
                  ? (isError 
                      ? 'Live tickets from your Jira Project will appear here once the GitHub Actions workflow runs with your configured secrets.' 
                      : `No active tickets returned for Jira Project <strong>${this.escapeHtml(projectKey || '')}</strong>.`)
                  : 'No Jira tickets match the selected filters or search criteria.'}
              </p>
              ${activeFilterCount > 0 ? `<button type="button" class="btn btn--ghost" id="jira-empty-reset">Reset All Filters</button>` : ''}
            </div>
          ` : `
            <table class="jira-table">
              <thead>
                <tr>
                  ${this.renderSortHeader('key', 'Key', '110px')}
                  ${this.renderSortHeader('type', 'Type', '90px')}
                  ${this.renderSortHeader('priority', 'Priority', '100px')}
                  ${this.renderSortHeader('summary', 'Summary')}
                  ${this.renderSortHeader('project', 'Project', '140px')}
                  ${this.renderSortHeader('fixVersion', 'Fix Version', '110px')}
                  ${this.renderSortHeader('status', 'Status', '125px')}
                  ${this.renderSortHeader('assignee', 'Assignee', '140px')}
                  ${this.renderSortHeader('tester', 'Tester / QA', '140px')}
                  ${this.renderSortHeader('created', 'Created', '105px')}
                </tr>
              </thead>
              <tbody>
                ${filtered.map(issue => `
                  <tr>
                    <td>
                      <a href="${this.escapeHtml(issue.url)}" target="_blank" rel="noopener noreferrer" class="jira-issue-key">
                        ${this.escapeHtml(issue.key)} ↗
                      </a>
                    </td>
                    <td>
                      <span class="jira-type-tag">${this.escapeHtml(issue.type || 'Bug')}</span>
                    </td>
                    <td>
                      <span class="jira-priority-badge ${this.getPriorityClass(issue.priority)}">
                        ${this.escapeHtml(issue.priority)}
                      </span>
                    </td>
                    <td>
                      <div class="jira-issue-summary">
                        <a href="${this.escapeHtml(issue.url)}" target="_blank" rel="noopener noreferrer" class="jira-summary-link">
                          ${this.escapeHtml(issue.summary)}
                        </a>
                        ${(issue.labels && issue.labels.length > 0) ? `
                          <div class="jira-labels-row">
                            ${issue.labels.slice(0, 3).map(l => `<span class="jira-label-tag">${this.escapeHtml(l)}</span>`).join('')}
                          </div>
                        ` : ''}
                      </div>
                    </td>
                    <td>
                      <span class="jira-project-tag">${this.escapeHtml(issue.project || issue.projectKey || 'Project')}</span>
                    </td>
                    <td>
                      <span class="jira-version-badge">${this.escapeHtml(issue.fixVersion || 'Unversioned')}</span>
                    </td>
                    <td>
                      <span class="jira-status-pill ${this.getStatusBadgeClass(issue.statusCategory, issue.status)}">
                        ${this.escapeHtml(issue.status)}
                      </span>
                    </td>
                    <td>
                      <div class="jira-assignee-box">
                        ${issue.assigneeAvatar ? `<img src="${this.escapeHtml(issue.assigneeAvatar)}" class="jira-avatar" alt="" />` : `<span class="jira-avatar-placeholder">👤</span>`}
                        <span class="jira-assignee-name" title="${this.escapeHtml(issue.assignee)}">${this.escapeHtml(issue.assignee || 'Unassigned')}</span>
                      </div>
                    </td>
                    <td>
                      <div class="jira-assignee-box">
                        <span class="jira-tester-icon">🧪</span>
                        <span class="jira-assignee-name" title="${this.escapeHtml(issue.tester)}">${this.escapeHtml(issue.tester || 'Unknown')}</span>
                      </div>
                    </td>
                    <td>
                      <span class="jira-date-tag">${issue.created ? new Date(issue.created).toLocaleDateString() : 'N/A'}</span>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          `}
        </div>
      `;

      this.wireEvents();
    }

    wireEvents() {
      // KPI Card Clicks
      document.querySelectorAll('.jira-kpi-card').forEach((card) => {
        card.addEventListener('click', () => {
          const kpi = card.getAttribute('data-kpi');
          if (kpi) {
            this.filters.kpi = (this.filters.kpi === kpi && kpi !== 'all') ? 'all' : kpi;
            this.render();
          }
        });
      });

      // Filter Dropdown Change Handlers
      const bindSelect = (id, filterKey) => {
        const el = document.getElementById(id);
        if (el) {
          el.addEventListener('change', (e) => {
            this.filters[filterKey] = e.target.value;
            this.render();
          });
        }
      };

      bindSelect('filter-project', 'project');
      bindSelect('filter-fix-version', 'fixVersion');
      bindSelect('filter-type', 'type');
      bindSelect('filter-assignee', 'assignee');
      bindSelect('filter-tester', 'tester');
      bindSelect('filter-priority', 'priority');

      // Sort Select Dropdown
      const sortSelect = document.getElementById('jira-sort-select');
      if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
          const [field, dir] = e.target.value.split('-');
          this.sort.field = field;
          this.sort.dir = dir || 'asc';
          this.render();
        });
      }

      // Column Header Sort Clicks
      document.querySelectorAll('.jira-sortable-th').forEach((th) => {
        th.addEventListener('click', () => {
          const field = th.getAttribute('data-sort-field');
          if (field) {
            if (this.sort.field === field) {
              this.sort.dir = this.sort.dir === 'asc' ? 'desc' : 'asc';
            } else {
              this.sort.field = field;
              this.sort.dir = (field === 'priority' || field === 'created' || field === 'updated') ? 'desc' : 'asc';
            }
            this.render();
          }
        });
      });

      // Live Search Input
      const searchInput = document.getElementById('jira-search-input');
      if (searchInput) {
        searchInput.addEventListener('input', (e) => {
          this.filters.searchQuery = e.target.value;
          this.render();
          const newEl = document.getElementById('jira-search-input');
          if (newEl) {
            newEl.focus();
            newEl.setSelectionRange(newEl.value.length, newEl.value.length);
          }
        });
      }

      // Search Clear Button
      const searchClear = document.getElementById('jira-search-clear');
      if (searchClear) {
        searchClear.addEventListener('click', () => {
          this.filters.searchQuery = '';
          this.render();
        });
      }

      // Clear / Reset All Filters
      const clearBtn = document.getElementById('jira-btn-clear-filters');
      if (clearBtn) {
        clearBtn.addEventListener('click', () => this.resetFilters());
      }
      const emptyReset = document.getElementById('jira-empty-reset');
      if (emptyReset) {
        emptyReset.addEventListener('click', () => this.resetFilters());
      }
    }
  }

  window.JiraTracker = new JiraTracker();
})(window);
