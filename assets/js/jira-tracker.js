/**
 * Jira Quality & Defect Tracker for Store Intell QA Dashboard.
 * Renders defect lifecycle, blocker metrics, and automation-linked Jira tickets.
 */

(function (window) {
  'use strict';

  class JiraTracker {
    constructor() {
      this.data = null;
      this.activeFilter = 'all'; // 'all', 'blockers', 'progress', 'qa', 'resolved'
      this.activeComponent = 'all';
      this.searchQuery = '';
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
      // 1. Try bundled bootstrap snapshots first
      if (window.DASHBOARD_SNAPSHOTS?.snapshots?.jira) {
        this.data = window.DASHBOARD_SNAPSHOTS.snapshots.jira;
      }

      // 2. Fetch fresh data/jira.json
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

    filterIssues(issues) {
      return issues.filter((issue) => {
        // Priority / Status Filter
        if (this.activeFilter === 'blockers') {
          const p = (issue.priority || '').toLowerCase();
          if (!p.includes('highest') && !p.includes('blocker') && !p.includes('p0')) return false;
        } else if (this.activeFilter === 'progress') {
          const s = (issue.status || '').toLowerCase();
          if (!s.includes('progress') && !s.includes('dev')) return false;
        } else if (this.activeFilter === 'qa') {
          const s = (issue.status || '').toLowerCase();
          if (!s.includes('qa') && !s.includes('review') && !s.includes('testing')) return false;
        } else if (this.activeFilter === 'resolved') {
          const s = (issue.statusCategory || '').toLowerCase();
          const sn = (issue.status || '').toLowerCase();
          if (s !== 'done' && !sn.includes('closed') && !sn.includes('resolved')) return false;
        }

        // Component Filter
        if (this.activeComponent !== 'all' && issue.component !== this.activeComponent) {
          return false;
        }

        // Search Query
        if (this.searchQuery.trim()) {
          const q = this.searchQuery.toLowerCase();
          const matchKey = (issue.key || '').toLowerCase().includes(q);
          const matchSum = (issue.summary || '').toLowerCase().includes(q);
          const matchAss = (issue.assignee || '').toLowerCase().includes(q);
          const matchComp = (issue.component || '').toLowerCase().includes(q);
          const matchLabels = (issue.labels || []).some(l => l.toLowerCase().includes(q));
          if (!matchKey && !matchSum && !matchAss && !matchComp && !matchLabels) return false;
        }

        return true;
      });
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

      const { summary = {}, issues = [], jiraUrl, projectKey, status, lastUpdated, byComponent = {} } = this.data;
      const filtered = this.filterIssues(issues);
      const isLive = status === 'live';

      // Update status pill
      if (statusPill) {
        statusPill.innerHTML = isLive
          ? `<span style="color:#10b981;">●</span> Live Jira Sync`
          : `<span>ℹ️</span> Sample Dataset`;
        statusPill.title = `Last synchronized: ${lastUpdated ? new Date(lastUpdated).toLocaleString() : 'N/A'}`;
      }

      // Update header action button
      if (headerActions && jiraUrl) {
        headerActions.innerHTML = `
          <a href="${jiraUrl}" target="_blank" rel="noopener noreferrer" class="btn btn--ghost" style="font-size:13px;display:inline-flex;align-items:center;gap:6px;">
            <span>Open Jira Project (${this.escapeHtml(projectKey || 'Jira')})</span> ↗
          </a>
        `;
      }

      // Collect unique components
      const components = ['all', ...Object.keys(byComponent)];

      container.innerHTML = `
        <!-- KPI Metrics Grid -->
        <div class="jira-kpi-grid">
          <div class="jira-kpi-card ${this.activeFilter === 'all' ? 'jira-kpi-card--active' : ''}" data-filter="all">
            <div class="jira-kpi-label">Tracked Defects</div>
            <div class="jira-kpi-val">${summary.totalDefects || issues.length}</div>
            <div class="jira-kpi-sub">Total active &amp; tracked</div>
          </div>

          <div class="jira-kpi-card jira-kpi-card--blocker ${this.activeFilter === 'blockers' ? 'jira-kpi-card--active' : ''}" data-filter="blockers">
            <div class="jira-kpi-label">🚨 Critical Blockers</div>
            <div class="jira-kpi-val" style="color:var(--fail);">${summary.blockers || 0}</div>
            <div class="jira-kpi-sub">Highest / P0 Priority</div>
          </div>

          <div class="jira-kpi-card ${this.activeFilter === 'progress' ? 'jira-kpi-card--active' : ''}" data-filter="progress">
            <div class="jira-kpi-label">⚡ In Progress</div>
            <div class="jira-kpi-val" style="color:var(--warn);">${summary.inProgress || 0}</div>
            <div class="jira-kpi-sub">Active developer fixes</div>
          </div>

          <div class="jira-kpi-card ${this.activeFilter === 'qa' ? 'jira-kpi-card--active' : ''}" data-filter="qa">
            <div class="jira-kpi-label">🔍 Ready for QA</div>
            <div class="jira-kpi-val" style="color:#38bdf8;">${summary.inQa || 0}</div>
            <div class="jira-kpi-sub">Ready for test verification</div>
          </div>

          <div class="jira-kpi-card ${this.activeFilter === 'resolved' ? 'jira-kpi-card--active' : ''}" data-filter="resolved">
            <div class="jira-kpi-label">✅ Resolved Recently</div>
            <div class="jira-kpi-val" style="color:var(--pass);">${summary.resolvedThisWeek || summary.resolvedTotal || 0}</div>
            <div class="jira-kpi-sub">Closed / Verified</div>
          </div>
        </div>

        <!-- Filter & Search Bar -->
        <div class="jira-toolbar">
          <div class="jira-filter-chips">
            <button type="button" class="jira-chip ${this.activeFilter === 'all' ? 'jira-chip--active' : ''}" data-filter="all">All (${issues.length})</button>
            <button type="button" class="jira-chip ${this.activeFilter === 'blockers' ? 'jira-chip--active' : ''}" data-filter="blockers">Blockers (${summary.blockers || 0})</button>
            <button type="button" class="jira-chip ${this.activeFilter === 'progress' ? 'jira-chip--active' : ''}" data-filter="progress">In Progress (${summary.inProgress || 0})</button>
            <button type="button" class="jira-chip ${this.activeFilter === 'qa' ? 'jira-chip--active' : ''}" data-filter="qa">In QA (${summary.inQa || 0})</button>
            <button type="button" class="jira-chip ${this.activeFilter === 'resolved' ? 'jira-chip--active' : ''}" data-filter="resolved">Resolved</button>
          </div>

          <div class="jira-toolbar-right">
            <select id="jira-component-select" class="jira-select" aria-label="Filter by Component">
              ${components.map(c => `<option value="${this.escapeHtml(c)}" ${this.activeComponent === c ? 'selected' : ''}>${c === 'all' ? 'All Components' : this.escapeHtml(c)}</option>`).join('')}
            </select>
            <div class="jira-search-wrapper">
              <input type="text" id="jira-search-input" class="jira-search-input" placeholder="Search ticket key, summary, assignee..." value="${this.escapeHtml(this.searchQuery)}" />
              ${this.searchQuery ? `<button type="button" id="jira-search-clear" class="jira-search-clear">✕</button>` : ''}
            </div>
          </div>
        </div>

        <!-- Issues List Table -->
        <div class="jira-table-container">
          ${filtered.length === 0 ? `
            <div class="jira-empty-state" style="padding:40px 20px;">
              <p style="font-size:16px;color:var(--muted);">No Jira tickets match the selected filters or search query.</p>
              <button type="button" class="btn btn--ghost" id="jira-reset-filters" style="margin-top:12px;">Reset Filters</button>
            </div>
          ` : `
            <table class="jira-table">
              <thead>
                <tr>
                  <th style="width:120px;">Key</th>
                  <th style="width:100px;">Priority</th>
                  <th>Summary</th>
                  <th style="width:130px;">Component</th>
                  <th style="width:130px;">Status</th>
                  <th style="width:150px;">Assignee</th>
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
                      <span class="jira-component-tag">${this.escapeHtml(issue.component || 'General')}</span>
                    </td>
                    <td>
                      <span class="jira-status-pill ${this.getStatusBadgeClass(issue.statusCategory, issue.status)}">
                        ${this.escapeHtml(issue.status)}
                      </span>
                    </td>
                    <td>
                      <div class="jira-assignee-box">
                        ${issue.assigneeAvatar ? `<img src="${this.escapeHtml(issue.assigneeAvatar)}" class="jira-avatar" alt="" />` : `<span class="jira-avatar-placeholder">👤</span>`}
                        <span class="jira-assignee-name">${this.escapeHtml(issue.assignee || 'Unassigned')}</span>
                      </div>
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
          const filter = card.getAttribute('data-filter');
          if (filter) {
            this.activeFilter = filter;
            this.render();
          }
        });
      });

      // Filter Chips
      document.querySelectorAll('.jira-chip').forEach((chip) => {
        chip.addEventListener('click', () => {
          const filter = chip.getAttribute('data-filter');
          if (filter) {
            this.activeFilter = filter;
            this.render();
          }
        });
      });

      // Component Dropdown
      const compSelect = document.getElementById('jira-component-select');
      if (compSelect) {
        compSelect.addEventListener('change', (e) => {
          this.activeComponent = e.target.value;
          this.render();
        });
      }

      // Search Input
      const searchInput = document.getElementById('jira-search-input');
      if (searchInput) {
        searchInput.addEventListener('input', (e) => {
          this.searchQuery = e.target.value;
          this.render();
          // refocus
          const newEl = document.getElementById('jira-search-input');
          if (newEl) {
            newEl.focus();
            newEl.setSelectionRange(newEl.value.length, newEl.value.length);
          }
        });
      }

      // Search Clear
      const searchClear = document.getElementById('jira-search-clear');
      if (searchClear) {
        searchClear.addEventListener('click', () => {
          this.searchQuery = '';
          this.render();
        });
      }

      // Reset Filters
      const resetBtn = document.getElementById('jira-reset-filters');
      if (resetBtn) {
        resetBtn.addEventListener('click', () => {
          this.activeFilter = 'all';
          this.activeComponent = 'all';
          this.searchQuery = '';
          this.render();
        });
      }
    }
  }

  window.JiraTracker = new JiraTracker();
})(window);
