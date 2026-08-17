/**
 * Jira Quality & Sprint Delivery Tracker for Store Intell QA Dashboard.
 * Supports dynamic interactive pie/donut charts, Ticket Type / Epic tracking,
 * clean multi-axis filtering at the top, Created + Updated dates, and CSV export.
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

  const STATUS_COLORS = {
    'open': '#38bdf8',
    'to do': '#38bdf8',
    'new': '#38bdf8',
    'in progress': '#fbbf24',
    'in dev': '#fbbf24',
    'development': '#fbbf24',
    'code review': '#fbbf24',
    'in review': '#fbbf24',
    'review': '#fbbf24',
    'in qa': '#a855f7',
    'ready for qa': '#a855f7',
    'qa': '#a855f7',
    'testing': '#a855f7',
    'verified': '#a855f7',
    'blocked': '#f43f5e',
    'on hold': '#f43f5e',
    'done': '#10b981',
    'closed': '#10b981',
    'resolved': '#10b981'
  };

  const PRIORITY_COLORS = {
    'highest': '#f43f5e',
    'blocker': '#f43f5e',
    'high': '#fb923c',
    'medium': '#f59e0b',
    'low': '#60a5fa',
    'lowest': '#94a3b8'
  };

  const COMPONENT_COLORS = ['#3b82f6', '#a855f7', '#10b981', '#f59e0b', '#06b6d4', '#ec4899'];

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
        status: 'all',
        component: 'all',
        searchQuery: ''
      };
      this.sort = {
        field: 'updated',
        dir: 'desc'
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

    formatDate(dateStr) {
      if (!dateStr) return 'N/A';
      try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      } catch {
        return dateStr;
      }
    }

    formatRelativeTime(dateStr) {
      if (!dateStr) return '';
      try {
        const d = new Date(dateStr);
        const diffMs = Date.now() - d.getTime();
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 30) return `${diffDays}d ago`;
        return this.formatDate(dateStr);
      } catch {
        return '';
      }
    }

    getPriorityClass(priority) {
      const p = (priority || '').toLowerCase();
      if (p.includes('highest') || p.includes('blocker') || p.includes('p0')) return 'jira-priority--highest';
      if (p.includes('high') || p.includes('p1')) return 'jira-priority--high';
      if (p.includes('medium') || p.includes('p2')) return 'jira-priority--medium';
      if (p.includes('low') || p.includes('p3')) return 'jira-priority--low';
      return 'jira-priority--lowest';
    }

    isQaStatus(statusName) {
      const s = (statusName || '').toLowerCase().trim();
      const isCodeReview = s.includes('code review') || s.includes('pr review') || s.includes('peer review') || s === 'in review' || s === 'review';
      if (isCodeReview) return false;
      return s.includes('qa') || s.includes('testing') || s.includes('verified');
    }

    isDevStatus(statusName, statusCategory) {
      const s = (statusName || '').toLowerCase().trim();
      const cat = (statusCategory || '').toLowerCase();
      if (this.isQaStatus(statusName)) return false;
      if (cat === 'done' || ['closed', 'done', 'resolved'].includes(s)) return false;
      return cat === 'indeterminate' || s.includes('progress') || s.includes('dev') || s.includes('review') || s.includes('draft') || s.includes('working');
    }

    getStatusBadgeClass(statusCategory, statusName) {
      const cat = (statusCategory || '').toLowerCase();
      const name = (statusName || '').toLowerCase();
      if (cat === 'done' || name.includes('closed') || name.includes('resolved')) return 'jira-status--done';
      if (this.isQaStatus(statusName)) return 'jira-status--qa';
      if (this.isDevStatus(statusName, statusCategory)) return 'jira-status--prog';
      return 'jira-status--open';
    }

    getPriorityRank(priority) {
      const p = (priority || '').toLowerCase().trim();
      return PRIORITY_RANKS[p] || 3;
    }

    getStatusColor(statusName) {
      const s = (statusName || '').toLowerCase().trim();
      if (this.isQaStatus(statusName)) return '#a855f7';
      if (this.isDevStatus(statusName, 'indeterminate')) return '#fbbf24';
      if (['done', 'closed', 'resolved'].includes(s)) return '#10b981';
      return '#38bdf8';
    }

    getPriorityColor(priorityName) {
      const p = (priorityName || '').toLowerCase().trim();
      for (const [k, color] of Object.entries(PRIORITY_COLORS)) {
        if (p.includes(k)) return color;
      }
      return '#94a3b8';
    }

    matchesTicketType(issue, filterType) {
      if (!filterType || filterType === 'all') return true;
      const tIssue = (issue.type || issue.issuetype || '').toLowerCase().trim();
      const tFilter = filterType.toLowerCase().trim();

      if (tFilter === 'epic') {
        return tIssue === 'epic' || tIssue.includes('epic');
      }
      if (tFilter === 'bug' || tFilter === 'defect') {
        return tIssue === 'bug' || tIssue.includes('bug') || tIssue.includes('defect') || tIssue.includes('incident');
      }
      if (tFilter === 'story' || tFilter === 'feature') {
        return tIssue === 'story' || tIssue.includes('story') || tIssue.includes('feature');
      }
      if (tFilter === 'task') {
        return (tIssue === 'task' || tIssue.includes('task')) && !tIssue.includes('sub');
      }
      if (tFilter.includes('sub')) {
        return tIssue.includes('sub');
      }
      return tIssue === tFilter || tIssue.includes(tFilter) || tFilter.includes(tIssue);
    }

    filterAndSortIssues(issues) {
      // 1. Filtering
      let filtered = issues.filter((issue) => {
        // KPI Card Quick Filters
        if (this.filters.kpi === 'blockers') {
          const p = (issue.priority || '').toLowerCase();
          if (!p.includes('highest') && !p.includes('blocker') && !p.includes('p0') && !p.includes('p1')) return false;
        } else if (this.filters.kpi === 'progress') {
          if (!this.isDevStatus(issue.status, issue.statusCategory)) return false;
        } else if (this.filters.kpi === 'qa') {
          if (!this.isQaStatus(issue.status)) return false;
        } else if (this.filters.kpi === 'resolved') {
          const s = (issue.statusCategory || '').toLowerCase();
          const sn = (issue.status || '').toLowerCase();
          if (s !== 'done' && !sn.includes('closed') && !sn.includes('resolved')) return false;
        }

        // Project Filter
        if (this.filters.project !== 'all') {
          const pIssue = (issue.project || issue.projectKey || '').toLowerCase();
          const pFilter = this.filters.project.toLowerCase();
          if (pIssue !== pFilter && !pIssue.includes(pFilter)) return false;
        }

        // Fix Version Filter
        if (this.filters.fixVersion !== 'all') {
          const vIssue = (issue.fixVersion || 'Unversioned').toLowerCase();
          const vFilter = this.filters.fixVersion.toLowerCase();
          if (vIssue !== vFilter && !vIssue.includes(vFilter)) return false;
        }

        // Ticket Type Filter (Strict matching)
        if (!this.matchesTicketType(issue, this.filters.type)) {
          return false;
        }

        // Assignee Filter
        if (this.filters.assignee !== 'all') {
          const aFilter = this.filters.assignee.toLowerCase().trim();
          const aIssue = (issue.assignee || 'Unassigned').toLowerCase().trim();
          if (aFilter === 'unassigned') {
            if (aIssue !== 'unassigned' && aIssue !== '' && aIssue !== 'none' && aIssue !== 'null') return false;
          } else {
            if (aIssue !== aFilter && !aIssue.includes(aFilter)) return false;
          }
        }

        // Tester Filter
        if (this.filters.tester !== 'all') {
          const tFilter = this.filters.tester.toLowerCase().trim();
          const tIssue = (issue.tester || 'Unassigned').toLowerCase().trim();
          const rIssue = (issue.reporter || 'Unassigned').toLowerCase().trim();
          if (tFilter.includes('unassigned') || tFilter.includes('unknown')) {
            const isUnassigned = ['unassigned', 'unknown', 'none', '', 'null'].includes(tIssue) && ['unassigned', 'unknown', 'none', '', 'null'].includes(rIssue);
            if (!isUnassigned && tIssue !== 'unassigned' && tIssue !== 'unknown' && tIssue !== '') return false;
          } else {
            if (tIssue !== tFilter && !tIssue.includes(tFilter) && rIssue !== tFilter && !rIssue.includes(tFilter)) return false;
          }
        }

        // Priority Filter
        if (this.filters.priority !== 'all') {
          const prIssue = (issue.priority || 'Medium').toLowerCase();
          const prFilter = this.filters.priority.toLowerCase();
          if (prIssue !== prFilter) return false;
        }

        // Status Filter
        if (this.filters.status !== 'all') {
          const stFilter = this.filters.status.toLowerCase().trim();
          const stIssue = (issue.status || '').toLowerCase().trim();
          const catIssue = (issue.statusCategory || '').toLowerCase().trim();
          if (stFilter === 'done' || stFilter === 'closed' || stFilter === 'resolved') {
            if (catIssue !== 'done' && stIssue !== 'done' && stIssue !== 'closed' && stIssue !== 'resolved' && !stIssue.includes('done') && !stIssue.includes('closed') && !stIssue.includes('resolved')) {
              return false;
            }
          } else {
            if (stIssue !== stFilter && !stIssue.includes(stFilter)) return false;
          }
        }

        // Component Filter
        if (this.filters.component !== 'all') {
          const cIssue = (issue.component || 'General').toLowerCase();
          const cFilter = this.filters.component.toLowerCase();
          if (cIssue !== cFilter) return false;
        }

        // Search Query
        if (this.filters.searchQuery && this.filters.searchQuery.trim()) {
          const q = this.filters.searchQuery.toLowerCase().trim();
          const matchKey = (issue.key || '').toLowerCase().includes(q);
          const matchSum = (issue.summary || '').toLowerCase().includes(q);
          const matchAss = (issue.assignee || '').toLowerCase().includes(q);
          const matchTest = (issue.tester || '').toLowerCase().includes(q);
          const matchRep = (issue.reporter || '').toLowerCase().includes(q);
          const matchProj = (issue.project || issue.projectKey || '').toLowerCase().includes(q);
          const matchVer = (issue.fixVersion || '').toLowerCase().includes(q);
          const matchEpic = (issue.epic || '').toLowerCase().includes(q);
          const matchType = (issue.type || '').toLowerCase().includes(q);
          const matchComp = (issue.component || '').toLowerCase().includes(q);
          const matchLabels = (issue.labels || []).some(l => l.toLowerCase().includes(q));
          if (!matchKey && !matchSum && !matchAss && !matchTest && !matchRep && !matchProj && !matchVer && !matchEpic && !matchType && !matchComp && !matchLabels) {
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
      if (this.filters.status !== 'all') count++;
      if (this.filters.component !== 'all') count++;
      if (this.filters.searchQuery && this.filters.searchQuery.trim()) count++;
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
        status: 'all',
        component: 'all',
        searchQuery: ''
      };
      this.render();
    }

    exportCsv(filteredIssues) {
      if (!filteredIssues || filteredIssues.length === 0) {
        alert('No Jira tickets to export.');
        return;
      }
      const headers = ['Key', 'Ticket Type', 'Priority', 'Summary', 'Project', 'Fix Version', 'Release Status', 'Epic', 'Status', 'Assignee', 'Tester', 'Created', 'Updated', 'URL'];
      const rows = filteredIssues.map(i => [
        `"${i.key || ''}"`,
        `"${i.type || ''}"`,
        `"${i.priority || ''}"`,
        `"${(i.summary || '').replace(/"/g, '""')}"`,
        `"${i.project || ''}"`,
        `"${i.fixVersion || ''}"`,
        `"${i.releaseStatus || (i.isReleased ? 'Released' : 'Unreleased')}"`,
        `"${(i.epic || '').replace(/"/g, '""')}"`,
        `"${i.status || ''}"`,
        `"${i.assignee || ''}"`,
        `"${i.tester || ''}"`,
        `"${i.created || ''}"`,
        `"${i.updated || ''}"`,
        `"${i.url || ''}"`
      ]);

      const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', `jira_work_items_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
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

    generateSvgDonut(slices, total, centerNumber, centerSubtitle, filterKey) {
      if (total === 0) {
        return `
          <div class="jira-donut-empty">
            <svg viewBox="0 0 160 160" width="130" height="130">
              <circle cx="80" cy="80" r="54" fill="none" stroke="var(--border)" stroke-width="16" />
              <text x="80" y="77" text-anchor="middle" font-size="18" font-weight="700" fill="var(--muted)">0</text>
              <text x="80" y="93" text-anchor="middle" font-size="9" fill="var(--muted)">Tickets</text>
            </svg>
          </div>
        `;
      }

      const radius = 54;
      const circumference = 2 * Math.PI * radius;
      let currentOffset = 0;

      const circlePaths = slices.map((slice) => {
        const fraction = slice.count / total;
        const strokeDash = `${fraction * circumference} ${circumference}`;
        const strokeOffset = -currentOffset;
        currentOffset += fraction * circumference;
        const isSelected = (this.filters[filterKey] || '').toLowerCase() === slice.label.toLowerCase();

        return `
          <circle class="jira-donut-slice ${isSelected ? 'jira-donut-slice--active' : ''}"
            cx="80" cy="80" r="${radius}"
            fill="none"
            stroke="${slice.color}"
            stroke-width="${isSelected ? '20' : '16'}"
            stroke-dasharray="${strokeDash}"
            stroke-dashoffset="${strokeOffset}"
            data-filter-key="${filterKey}"
            data-filter-val="${this.escapeHtml(slice.label)}"
            style="transform: rotate(-90deg); transform-origin: 50% 50%;"
          >
            <title>${this.escapeHtml(slice.label)}: ${slice.count} (${Math.round(fraction * 100)}%)</title>
          </circle>
        `;
      }).join('');

      return `
        <div class="jira-donut-wrapper">
          <svg class="jira-donut-svg" viewBox="0 0 160 160" width="140" height="140">
            ${circlePaths}
            <text x="80" y="76" text-anchor="middle" class="jira-donut-center-num">${centerNumber}</text>
            <text x="80" y="93" text-anchor="middle" class="jira-donut-center-sub">${centerSubtitle}</text>
          </svg>
        </div>
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

      // Extract unique lists dynamically across both filterOptions and actual issue records
      const projects = Array.from(new Set([].concat(filterOptions.projects || []).concat(issues.map(i => i.project || i.projectKey)).filter(Boolean))).sort();
      const fixVersions = Array.from(new Set([].concat(filterOptions.fixVersions || []).concat(issues.map(i => i.fixVersion)).filter(Boolean))).sort();
      
      const standardTypes = ['Epic', 'Story', 'Bug', 'Task', 'Sub-task'];
      const types = Array.from(new Set(['Epic'].concat(filterOptions.types || []).concat(issues.map(i => i.type)).concat(standardTypes).filter(Boolean)));

      // Full dynamic extraction of all assignees (including Unassigned)
      const rawAssignees = [].concat(filterOptions.assignees || []).concat(issues.map(i => i.assignee || 'Unassigned')).filter(Boolean);
      const hasUnassignedDev = rawAssignees.some(a => (a || '').toLowerCase() === 'unassigned') || issues.some(i => !i.assignee || i.assignee.toLowerCase() === 'unassigned');
      const uniqueAssigneeSet = new Set(rawAssignees.filter(a => (a || '').toLowerCase() !== 'unassigned'));
      const sortedNamedAssignees = Array.from(uniqueAssigneeSet).sort((a, b) => a.localeCompare(b));
      const assignees = hasUnassignedDev ? ['Unassigned', ...sortedNamedAssignees] : sortedNamedAssignees;

      // Full dynamic extraction of all testers & reporters (including Unassigned / Unknown)
      const rawTesters = [].concat(filterOptions.testers || []).concat(issues.flatMap(i => [i.tester, i.reporter])).filter(Boolean);
      const hasUnassignedQa = rawTesters.some(t => ['unassigned', 'unknown', 'none'].includes((t || '').toLowerCase())) || issues.some(i => !i.tester || ['unassigned', 'unknown', 'none'].includes(i.tester.toLowerCase()));
      const uniqueTesterSet = new Set(rawTesters.filter(t => !['unassigned', 'unknown', 'none'].includes((t || '').toLowerCase())));
      const sortedNamedTesters = Array.from(uniqueTesterSet).sort((a, b) => a.localeCompare(b));
      const testers = hasUnassignedQa ? ['Unassigned', ...sortedNamedTesters] : sortedNamedTesters;

      const rawStatuses = [].concat(issues.map(i => i.status)).filter(Boolean);
      if (!rawStatuses.some(s => s.toLowerCase() === 'done' || s.toLowerCase() === 'closed')) {
        rawStatuses.push('Done');
      }
      const allStatuses = Array.from(new Set(rawStatuses));
      const priorities = ['Highest', 'High', 'Medium', 'Low', 'Lowest'];

      // --- 1. Compute Dynamic Status Distribution for Filtered Tickets ---
      const STATUS_PALETTE = ['#38bdf8', '#fbbf24', '#a855f7', '#06b6d4', '#10b981', '#ec4899', '#f97316', '#6366f1'];
      const statusCounts = {};
      filtered.forEach((i) => {
        const s = i.status || 'Unknown';
        statusCounts[s] = (statusCounts[s] || 0) + 1;
      });
      const statusSlices = Object.entries(statusCounts).map(([label, count], idx) => {
        let col = this.getStatusColor(label);
        const lLow = label.toLowerCase();
        if (lLow === 'uat') col = '#06b6d4';
        else if (lLow.includes('dev complete')) col = '#6366f1';
        else if (col === '#38bdf8' && lLow !== 'to do' && lLow !== 'open' && lLow !== 'new') {
          col = STATUS_PALETTE[idx % STATUS_PALETTE.length];
        }
        return {
          label,
          count,
          color: col
        };
      }).sort((a, b) => b.count - a.count);

      // --- 2. Compute Dynamic Priority Distribution ---
      const priorityCounts = {};
      filtered.forEach((i) => {
        const p = i.priority || 'Medium';
        priorityCounts[p] = (priorityCounts[p] || 0) + 1;
      });
      const prioritySlices = Object.entries(priorityCounts).map(([label, count]) => ({
        label,
        count,
        color: this.getPriorityColor(label)
      })).sort((a, b) => this.getPriorityRank(b.label) - this.getPriorityRank(a.label));

      // --- 3. Compute Dynamic Ticket Type Distribution ---
      const typeCounts = {};
      filtered.forEach((i) => {
        let t = i.type || 'Story';
        if ((i.type || '').toLowerCase() === 'epic') t = 'Epic';
        typeCounts[t] = (typeCounts[t] || 0) + 1;
      });
      const typeSlices = Object.entries(typeCounts).map(([label, count], idx) => ({
        label,
        count,
        color: COMPONENT_COLORS[idx % COMPONENT_COLORS.length]
      })).sort((a, b) => b.count - a.count);

      // --- 4. Compute Dynamic KPI Metrics based on Active Filters ---
      const activeNonKpiFilters = (
        this.filters.project !== 'all' ||
        this.filters.fixVersion !== 'all' ||
        this.filters.type !== 'all' ||
        this.filters.assignee !== 'all' ||
        this.filters.tester !== 'all' ||
        this.filters.priority !== 'all' ||
        this.filters.status !== 'all' ||
        this.filters.component !== 'all' ||
        (this.filters.searchQuery && this.filters.searchQuery.trim() !== '')
      );

      const baseForKpi = activeNonKpiFilters ? issues.filter(i => {
        if (this.filters.project !== 'all') {
          const pIssue = (i.project || i.projectKey || '').toLowerCase();
          const pFilter = this.filters.project.toLowerCase();
          if (pIssue !== pFilter && !pIssue.includes(pFilter)) return false;
        }
        if (this.filters.fixVersion !== 'all') {
          const vIssue = (i.fixVersion || 'Unversioned').toLowerCase();
          const vFilter = this.filters.fixVersion.toLowerCase();
          if (vIssue !== vFilter && !vIssue.includes(vFilter)) return false;
        }
        if (!this.matchesTicketType(i, this.filters.type)) return false;
        if (this.filters.assignee !== 'all') {
          const aFilter = this.filters.assignee.toLowerCase().trim();
          const aIssue = (i.assignee || 'Unassigned').toLowerCase().trim();
          if (aFilter === 'unassigned') {
            if (aIssue !== 'unassigned' && aIssue !== '' && aIssue !== 'none' && aIssue !== 'null') return false;
          } else {
            if (aIssue !== aFilter && !aIssue.includes(aFilter)) return false;
          }
        }
        if (this.filters.tester !== 'all') {
          const tFilter = this.filters.tester.toLowerCase().trim();
          const tIssue = (i.tester || 'Unassigned').toLowerCase().trim();
          const rIssue = (i.reporter || 'Unassigned').toLowerCase().trim();
          if (tFilter.includes('unassigned') || tFilter.includes('unknown')) {
            const isUnassigned = ['unassigned', 'unknown', 'none', '', 'null'].includes(tIssue) && ['unassigned', 'unknown', 'none', '', 'null'].includes(rIssue);
            if (!isUnassigned && tIssue !== 'unassigned' && tIssue !== 'unknown' && tIssue !== '') return false;
          } else {
            if (tIssue !== tFilter && !tIssue.includes(tFilter) && rIssue !== tFilter && !rIssue.includes(tFilter)) return false;
          }
        }
        if (this.filters.priority !== 'all' && (i.priority || 'Medium').toLowerCase() !== this.filters.priority.toLowerCase()) return false;
        if (this.filters.status !== 'all') {
          const stFilter = this.filters.status.toLowerCase().trim();
          const stIssue = (i.status || '').toLowerCase().trim();
          const catIssue = (i.statusCategory || '').toLowerCase().trim();
          if (stFilter === 'done' || stFilter === 'closed' || stFilter === 'resolved') {
            if (catIssue !== 'done' && stIssue !== 'done' && stIssue !== 'closed' && stIssue !== 'resolved' && !stIssue.includes('done') && !stIssue.includes('closed') && !stIssue.includes('resolved')) {
              return false;
            }
          } else {
            if (stIssue !== stFilter && !stIssue.includes(stFilter)) return false;
          }
        }
        if (this.filters.component !== 'all' && (i.component || 'General').toLowerCase() !== this.filters.component.toLowerCase()) return false;
        if (this.filters.searchQuery && this.filters.searchQuery.trim()) {
          const q = this.filters.searchQuery.toLowerCase().trim();
          const matchKey = (i.key || '').toLowerCase().includes(q);
          const matchSum = (i.summary || '').toLowerCase().includes(q);
          const matchAss = (i.assignee || '').toLowerCase().includes(q);
          const matchTest = (i.tester || '').toLowerCase().includes(q);
          const matchRep = (i.reporter || '').toLowerCase().includes(q);
          const matchProj = (i.project || i.projectKey || '').toLowerCase().includes(q);
          const matchVer = (i.fixVersion || '').toLowerCase().includes(q);
          const matchEpic = (i.epic || '').toLowerCase().includes(q);
          const matchType = (i.type || '').toLowerCase().includes(q);
          const matchComp = (i.component || '').toLowerCase().includes(q);
          const matchLabels = (i.labels || []).some(l => l.toLowerCase().includes(q));
          if (!matchKey && !matchSum && !matchAss && !matchTest && !matchRep && !matchProj && !matchVer && !matchEpic && !matchType && !matchComp && !matchLabels) return false;
        }
        return true;
      }) : issues;

      const dynamicKpiTotal = baseForKpi.length;
      const dynamicKpiBlockers = baseForKpi.filter(i => {
        const p = (i.priority || '').toLowerCase();
        return p.includes('highest') || p.includes('blocker') || p.includes('p0') || p.includes('p1');
      }).length;
      const dynamicKpiInProgress = baseForKpi.filter(i => this.isDevStatus(i.status, i.statusCategory)).length;
      const dynamicKpiInQa = baseForKpi.filter(i => this.isQaStatus(i.status)).length;
      const dynamicKpiResolved = baseForKpi.filter(i => {
        const s = (i.status || '').toLowerCase();
        const cat = (i.statusCategory || '').toLowerCase();
        return cat === 'done' || ['closed', 'done', 'resolved'].includes(s);
      }).length;

      // --- 5. Compute Sprint & Milestone Delivery Progress (Scoped to Sprint / Version / Project) ---
      const milestoneIssues = issues.filter(i => {
        if (this.filters.project !== 'all') {
          const pIssue = (i.project || i.projectKey || '').toLowerCase();
          const pFilter = this.filters.project.toLowerCase();
          if (pIssue !== pFilter && !pIssue.includes(pFilter)) return false;
        }
        if (this.filters.fixVersion !== 'all') {
          const vIssue = (i.fixVersion || 'Unversioned').toLowerCase();
          const vFilter = this.filters.fixVersion.toLowerCase();
          if (vIssue !== vFilter && !vIssue.includes(vFilter)) return false;
        }
        return true;
      });

      const milestoneTotal = milestoneIssues.length || issues.length;
      const doneCount = milestoneIssues.filter(i => (i.statusCategory || '').toLowerCase() === 'done' || ['closed', 'done', 'resolved'].includes((i.status || '').toLowerCase())).length;
      const inQaCount = milestoneIssues.filter(i => this.isQaStatus(i.status)).length;
      const inDevCount = milestoneIssues.filter(i => this.isDevStatus(i.status, i.statusCategory)).length;
      const todoCount = Math.max(0, milestoneTotal - doneCount - inQaCount - inDevCount);

      const donePct = milestoneTotal ? Math.round((doneCount / milestoneTotal) * 100) : 0;
      const qaPct = milestoneTotal ? Math.round((inQaCount / milestoneTotal) * 100) : 0;
      const devPct = milestoneTotal ? Math.round((inDevCount / milestoneTotal) * 100) : 0;
      const todoPct = milestoneTotal ? Math.max(0, 100 - donePct - qaPct - devPct) : 0;

      // --- 6. Compute Defect vs Story Ratio (Quality Index) ---
      const bugCount = milestoneIssues.filter(i => {
        const t = (i.type || '').toLowerCase();
        return t.includes('bug') || t.includes('defect') || t.includes('incident');
      }).length;
      const storyCount = Math.max(0, milestoneTotal - bugCount);
      const defectRatio = milestoneTotal ? Math.round((bugCount / milestoneTotal) * 100) : 0;
      const qualityScore = milestoneTotal ? Math.max(0, 100 - defectRatio) : 100;

      let qualityBadge = { label: '🟢 Healthy Sprint (<15% defects)', bg: 'rgba(16,185,129,0.15)', color: '#10b981' };
      if (defectRatio > 30) {
        qualityBadge = { label: '🔴 High Defect Influx (>30%)', bg: 'rgba(244,63,94,0.15)', color: '#f43f5e' };
      } else if (defectRatio > 15) {
        qualityBadge = { label: '🟡 Moderate Defect Load (15-30%)', bg: 'rgba(245,158,11,0.15)', color: '#fbbf24' };
      }

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

      // Header actions: CSV Export & Direct Jira Link
      if (headerActions) {
        headerActions.innerHTML = `
          <button type="button" class="btn btn--ghost" id="jira-btn-export-csv" style="font-size:13px;display:inline-flex;align-items:center;gap:6px;">
            <span>📥 Export CSV</span>
          </button>
          ${jiraUrl ? `
            <a href="${jiraUrl}" target="_blank" rel="noopener noreferrer" class="btn btn--ghost" style="font-size:13px;display:inline-flex;align-items:center;gap:6px;">
              <span>Open Jira (${this.escapeHtml(projectKey || 'Jira')})</span> ↗
            </a>
          ` : ''}
        `;
      }

      container.innerHTML = `
        <!-- Comprehensive Multi-Filter Bar (At Top) -->
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
                <option value="updated-desc" ${this.sort.field === 'updated' && this.sort.dir === 'desc' ? 'selected' : ''}>Updated Date (Recently Updated)</option>
                <option value="updated-asc" ${this.sort.field === 'updated' && this.sort.dir === 'asc' ? 'selected' : ''}>Updated Date (Oldest Updated)</option>
                <option value="created-desc" ${this.sort.field === 'created' && this.sort.dir === 'desc' ? 'selected' : ''}>Created Date (Newest First)</option>
                <option value="created-asc" ${this.sort.field === 'created' && this.sort.dir === 'asc' ? 'selected' : ''}>Created Date (Oldest First)</option>
                <option value="priority-desc" ${this.sort.field === 'priority' && this.sort.dir === 'desc' ? 'selected' : ''}>Priority (Highest → Lowest)</option>
                <option value="priority-asc" ${this.sort.field === 'priority' && this.sort.dir === 'asc' ? 'selected' : ''}>Priority (Lowest → Highest)</option>
                <option value="key-asc" ${this.sort.field === 'key' && this.sort.dir === 'asc' ? 'selected' : ''}>Ticket Key (A → Z)</option>
                <option value="type-asc" ${this.sort.field === 'type' && this.sort.dir === 'asc' ? 'selected' : ''}>Ticket Type (A → Z)</option>
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
                ${projects.map(p => `<option value="${this.escapeHtml(p)}" ${(this.filters.project || '').toLowerCase() === p.toLowerCase() ? 'selected' : ''}>${this.escapeHtml(p)}</option>`).join('')}
              </select>
            </div>

            <!-- Status Filter -->
            <div class="jira-filter-field">
              <label>🔄 Status</label>
              <select class="jira-select" id="filter-status">
                <option value="all">All Statuses</option>
                ${allStatuses.map(s => `<option value="${this.escapeHtml(s)}" ${(this.filters.status || '').toLowerCase() === s.toLowerCase() ? 'selected' : ''}>${this.escapeHtml(s)}</option>`).join('')}
              </select>
            </div>

            <!-- Priority Filter -->
            <div class="jira-filter-field">
              <label>📶 Priority</label>
              <select class="jira-select" id="filter-priority">
                <option value="all">All Priorities</option>
                ${priorities.map(pr => `<option value="${this.escapeHtml(pr)}" ${(this.filters.priority || '').toLowerCase() === pr.toLowerCase() ? 'selected' : ''}>${this.escapeHtml(pr)}</option>`).join('')}
              </select>
            </div>

            <!-- Ticket Type Filter (Epic, Story, Bug, Task, Sub-task) -->
            <div class="jira-filter-field">
              <label>🏷️ Ticket Type</label>
              <select class="jira-select" id="filter-type">
                <option value="all">All Ticket Types</option>
                ${types.map(t => `<option value="${this.escapeHtml(t)}" ${(this.filters.type || '').toLowerCase() === t.toLowerCase() ? 'selected' : ''}>${this.escapeHtml(t)}</option>`).join('')}
              </select>
            </div>

            <!-- Fix Version Filter -->
            <div class="jira-filter-field">
              <label>🎯 Fix Version</label>
              <select class="jira-select" id="filter-fix-version">
                <option value="all">All Fix Versions</option>
                ${fixVersions.map(v => `<option value="${this.escapeHtml(v)}" ${(this.filters.fixVersion || '').toLowerCase() === v.toLowerCase() ? 'selected' : ''}>${this.escapeHtml(v)}</option>`).join('')}
              </select>
            </div>

            <!-- Assignee Filter -->
            <div class="jira-filter-field">
              <label>👤 Assignee (Dev)</label>
              <select class="jira-select" id="filter-assignee">
                <option value="all">All Assignees</option>
                ${assignees.map(a => `<option value="${this.escapeHtml(a)}" ${(this.filters.assignee || '').toLowerCase() === a.toLowerCase() ? 'selected' : ''}>${this.escapeHtml(a)}</option>`).join('')}
              </select>
            </div>

            <!-- Tester / QA Filter -->
            <div class="jira-filter-field">
              <label>🧪 Tester / QA</label>
              <select class="jira-select" id="filter-tester">
                <option value="all">All Testers</option>
                ${testers.map(t => `<option value="${this.escapeHtml(t)}" ${(this.filters.tester || '').toLowerCase() === t.toLowerCase() ? 'selected' : ''}>${this.escapeHtml(t)}</option>`).join('')}
              </select>
            </div>

            <!-- Search Field -->
            <div class="jira-filter-field jira-filter-field--search">
              <label>🔍 Live Search</label>
              <div class="jira-search-wrapper">
                <input type="text" id="jira-search-input" class="jira-search-input" placeholder="Search key, summary, epic, label, assignee..." value="${this.escapeHtml(this.filters.searchQuery)}" />
                ${this.filters.searchQuery ? `<button type="button" id="jira-search-clear" class="jira-search-clear">✕</button>` : ''}
              </div>
            </div>
          </div>
        </div>

        <!-- KPI Metrics Grid (100% Dynamically Reactive) -->
        <div class="jira-kpi-grid">
          <div class="jira-kpi-card ${this.filters.kpi === 'all' ? 'jira-kpi-card--active' : ''}" data-kpi="all">
            <div class="jira-kpi-label">Tracked Work Items</div>
            <div class="jira-kpi-val">${dynamicKpiTotal}</div>
            <div class="jira-kpi-sub">Total in filtered scope</div>
          </div>

          <div class="jira-kpi-card jira-kpi-card--blocker ${this.filters.kpi === 'blockers' ? 'jira-kpi-card--active' : ''}" data-kpi="blockers">
            <div class="jira-kpi-label">🚨 Critical Blockers</div>
            <div class="jira-kpi-val" style="color:var(--fail);">${dynamicKpiBlockers}</div>
            <div class="jira-kpi-sub">Highest / P0 Priority</div>
          </div>

          <div class="jira-kpi-card ${this.filters.kpi === 'progress' ? 'jira-kpi-card--active' : ''}" data-kpi="progress">
            <div class="jira-kpi-label">⚡ In Progress &amp; Review</div>
            <div class="jira-kpi-val" style="color:var(--warn);">${dynamicKpiInProgress}</div>
            <div class="jira-kpi-sub">Active fixes &amp; code reviews</div>
          </div>

          <div class="jira-kpi-card ${this.filters.kpi === 'qa' ? 'jira-kpi-card--active' : ''}" data-kpi="qa">
            <div class="jira-kpi-label">🔍 In QA &amp; Testing</div>
            <div class="jira-kpi-val" style="color:#38bdf8;">${dynamicKpiInQa}</div>
            <div class="jira-kpi-sub">QA verification &amp; testing</div>
          </div>

          <div class="jira-kpi-card ${this.filters.kpi === 'resolved' ? 'jira-kpi-card--active' : ''}" data-kpi="resolved">
            <div class="jira-kpi-label">✅ Resolved Recently</div>
            <div class="jira-kpi-val" style="color:var(--pass);">${dynamicKpiResolved}</div>
            <div class="jira-kpi-sub">Closed / Verified</div>
          </div>
        </div>

        <!-- Sprint Delivery Milestone & Quality Index Banner Row -->
        <div class="jira-delivery-banner">
          <!-- Widget 1: Milestone Progress -->
          <div class="jira-delivery-card">
            <div class="jira-delivery-card__header">
              <div>
                <h4>🎯 Sprint &amp; Release Milestone Progress</h4>
                <p>${this.filters.fixVersion !== 'all' ? `Version: <strong>${this.escapeHtml(this.filters.fixVersion)}</strong>` : 'Overall Release Progression'}</p>
              </div>
              <span class="jira-delivery-badge" style="background:rgba(16,185,129,0.15);color:#10b981;">
                ${donePct}% Completed
              </span>
            </div>

            <div class="jira-progress-track">
              <div class="jira-progress-segment jira-progress--done" style="width:${donePct}%;" title="Done: ${doneCount} (${donePct}%)"></div>
              <div class="jira-progress-segment jira-progress--qa" style="width:${qaPct}%;" title="In QA: ${inQaCount} (${qaPct}%)"></div>
              <div class="jira-progress-segment jira-progress--dev" style="width:${devPct}%;" title="In Dev: ${inDevCount} (${devPct}%)"></div>
              <div class="jira-progress-segment jira-progress--todo" style="width:${todoPct}%;" title="To Do: ${todoCount} (${todoPct}%)"></div>
            </div>

            <div class="jira-progress-legend">
              <span class="jira-prog-item"><i style="background:#10b981;"></i> Done: <strong>${doneCount}</strong> (${donePct}%)</span>
              <span class="jira-prog-item"><i style="background:#a855f7;"></i> In QA: <strong>${inQaCount}</strong> (${qaPct}%)</span>
              <span class="jira-prog-item"><i style="background:#fbbf24;"></i> In Dev: <strong>${inDevCount}</strong> (${devPct}%)</span>
              <span class="jira-prog-item"><i style="background:#38bdf8;"></i> To Do: <strong>${todoCount}</strong> (${todoPct}%)</span>
            </div>
          </div>

          <!-- Widget 2: Defect vs Story Quality Index -->
          <div class="jira-delivery-card">
            <div class="jira-delivery-card__header">
              <div>
                <h4>🛡️ Defect vs Story Ratio (Quality Index)</h4>
                <p>Sprint composition balance &amp; defect density</p>
              </div>
              <span class="jira-delivery-badge" style="background:${qualityBadge.bg};color:${qualityBadge.color};">
                ${qualityBadge.label}
              </span>
            </div>

            <div class="jira-quality-score-row">
              <div class="jira-quality-score-box">
                <span class="jira-quality-score-num">${qualityScore}</span>
                <span class="jira-quality-score-label">Quality Score</span>
              </div>
              <div class="jira-quality-split-bars">
                <div class="jira-split-metric">
                  <div class="jira-split-labels">
                    <span>✨ Stories &amp; Tasks (Feature Work)</span>
                    <strong>${storyCount} (${filtered.length ? Math.round((storyCount / filtered.length) * 100) : 0}%)</strong>
                  </div>
                  <div class="jira-split-track">
                    <div class="jira-split-fill jira-split-fill--story" style="width:${filtered.length ? Math.round((storyCount / filtered.length) * 100) : 0}%;"></div>
                  </div>
                </div>

                <div class="jira-split-metric">
                  <div class="jira-split-labels">
                    <span>🐞 Defects &amp; Bugs (Defect Load)</span>
                    <strong>${bugCount} (${defectRatio}%)</strong>
                  </div>
                  <div class="jira-split-track">
                    <div class="jira-split-fill jira-split-fill--bug" style="width:${defectRatio}%;"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Interactive Visual Analytics Pie / Donut Charts Row -->
        <div class="jira-charts-grid">
          <!-- Chart 1: Status Distribution -->
          <div class="jira-chart-card">
            <div class="jira-chart-card__header">
              <div>
                <h4>🎯 Status Distribution</h4>
                <p>Workflow progression breakdown</p>
              </div>
              <span class="jira-chart-tag">${statusSlices.length} Statuses</span>
            </div>
            <div class="jira-chart-body">
              ${this.generateSvgDonut(statusSlices, filtered.length, filtered.length, 'Tickets', 'status')}
              <div class="jira-chart-legend">
                ${statusSlices.map(s => {
                  const pct = filtered.length ? Math.round((s.count / filtered.length) * 100) : 0;
                  const isAct = (this.filters.status || '').toLowerCase() === s.label.toLowerCase();
                  return `
                    <div class="jira-legend-item ${isAct ? 'jira-legend-item--active' : ''}" data-filter-key="status" data-filter-val="${this.escapeHtml(s.label)}">
                      <span class="jira-legend-dot" style="background:${s.color};"></span>
                      <span class="jira-legend-label" title="${this.escapeHtml(s.label)}">${this.escapeHtml(s.label)}</span>
                      <span class="jira-legend-num">${s.count} <small>(${pct}%)</small></span>
                    </div>
                  `;
                }).join('')}
              </div>
            </div>
          </div>

          <!-- Chart 2: Priority Severity Breakdown -->
          <div class="jira-chart-card">
            <div class="jira-chart-card__header">
              <div>
                <h4>🚨 Priority Severity</h4>
                <p>Critical vs standard items</p>
              </div>
              <span class="jira-chart-tag" style="background:rgba(244,63,94,0.15);color:var(--fail);">${priorityCounts['Highest'] || priorityCounts['Blocker'] || 0} Blockers</span>
            </div>
            <div class="jira-chart-body">
              ${this.generateSvgDonut(prioritySlices, filtered.length, filtered.length, 'Total', 'priority')}
              <div class="jira-chart-legend">
                ${prioritySlices.map(p => {
                  const pct = filtered.length ? Math.round((p.count / filtered.length) * 100) : 0;
                  const isAct = (this.filters.priority || '').toLowerCase() === p.label.toLowerCase();
                  return `
                    <div class="jira-legend-item ${isAct ? 'jira-legend-item--active' : ''}" data-filter-key="priority" data-filter-val="${this.escapeHtml(p.label)}">
                      <span class="jira-legend-dot" style="background:${p.color};"></span>
                      <span class="jira-legend-label">${this.escapeHtml(p.label)}</span>
                      <span class="jira-legend-num">${p.count} <small>(${pct}%)</small></span>
                    </div>
                  `;
                }).join('')}
              </div>
            </div>
          </div>

          <!-- Chart 3: Ticket Type Breakdown -->
          <div class="jira-chart-card">
            <div class="jira-chart-card__header">
              <div>
                <h4>🏷️ Ticket Type &amp; Epics</h4>
                <p>Bugs, Epics, Stories &amp; Tasks</p>
              </div>
              <span class="jira-chart-tag">${typeSlices.length} Types</span>
            </div>
            <div class="jira-chart-body">
              ${this.generateSvgDonut(typeSlices, filtered.length, filtered.length, 'Types', 'type')}
              <div class="jira-chart-legend">
                ${typeSlices.map(t => {
                  const pct = filtered.length ? Math.round((t.count / filtered.length) * 100) : 0;
                  const isAct = (this.filters.type || '').toLowerCase() === t.label.toLowerCase();
                  return `
                    <div class="jira-legend-item ${isAct ? 'jira-legend-item--active' : ''}" data-filter-key="type" data-filter-val="${this.escapeHtml(t.label)}">
                      <span class="jira-legend-dot" style="background:${t.color};"></span>
                      <span class="jira-legend-label" title="${this.escapeHtml(t.label)}">${this.escapeHtml(t.label)}</span>
                      <span class="jira-legend-num">${t.count} <small>(${pct}%)</small></span>
                    </div>
                  `;
                }).join('')}
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
                  ${this.renderSortHeader('type', 'Ticket Type', '105px')}
                  ${this.renderSortHeader('priority', 'Priority', '95px')}
                  ${this.renderSortHeader('summary', 'Summary & Epic')}
                  ${this.renderSortHeader('project', 'Project', '130px')}
                  ${this.renderSortHeader('fixVersion', 'Fix Version', '130px')}
                  ${this.renderSortHeader('status', 'Status', '120px')}
                  ${this.renderSortHeader('assignee', 'Assignee', '135px')}
                  ${this.renderSortHeader('tester', 'Tester / QA', '135px')}
                  ${this.renderSortHeader('created', 'Created', '105px')}
                  ${this.renderSortHeader('updated', 'Updated', '105px')}
                </tr>
              </thead>
              <tbody>
                ${filtered.map(issue => {
                  const isStale = (issue.staleDays || 0) > 14 && (issue.statusCategory || '').toLowerCase() !== 'done';
                  const isEpic = (issue.type || '').toLowerCase() === 'epic';
                  const isReleased = Boolean(issue.isReleased || (issue.releaseStatus && issue.releaseStatus.toLowerCase() === 'released') || (issue.fixVersion || '').toLowerCase().includes('released'));
                  
                  return `
                    <tr>
                      <td>
                        <a href="${this.escapeHtml(issue.url)}" target="_blank" rel="noopener noreferrer" class="jira-issue-key">
                          ${this.escapeHtml(issue.key)} ↗
                        </a>
                      </td>
                      <td>
                        <span class="jira-type-tag ${isEpic ? 'jira-type-tag--epic' : ''}">${this.escapeHtml(issue.type || 'Story')}</span>
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
                          <div class="jira-labels-row">
                            ${(issue.epic && issue.epic !== 'None' && !isEpic) ? `
                              <span class="jira-epic-badge" title="Epic: ${this.escapeHtml(issue.epic)}">⚡ ${this.escapeHtml(issue.epic)}</span>
                            ` : ''}
                            ${(issue.labels && issue.labels.length > 0) ? issue.labels.slice(0, 2).map(l => `<span class="jira-label-tag">${this.escapeHtml(l)}</span>`).join('') : ''}
                            ${isStale ? `<span class="jira-stale-tag" title="No updates in ${issue.staleDays} days">⏳ Stale (${issue.staleDays}d)</span>` : ''}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span class="jira-project-tag">${this.escapeHtml(issue.project || issue.projectKey || 'Project')}</span>
                      </td>
                      <td>
                        <div style="display:inline-flex;flex-direction:column;gap:3px;align-items:flex-start;">
                          <span class="jira-version-badge">${this.escapeHtml(issue.fixVersion || 'Unversioned')}</span>
                          <span style="font-size:10px;font-weight:600;padding:1px 6px;border-radius:4px;${isReleased ? 'background:rgba(16,185,129,0.15);color:#10b981;' : 'background:rgba(245,158,11,0.15);color:#fbbf24;'}">
                            ${isReleased ? '● Released' : '⏳ Unreleased'}
                          </span>
                        </div>
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
                        <span class="jira-date-tag" title="${this.escapeHtml(issue.created)}">${this.formatDate(issue.created)}</span>
                      </td>
                      <td>
                        <span class="jira-date-tag ${isStale ? 'jira-date-tag--stale' : ''}" title="${this.escapeHtml(issue.updated)}">${this.formatRelativeTime(issue.updated) || this.formatDate(issue.updated)}</span>
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          `}
        </div>
      `;

      this.wireEvents(filtered);
    }

    wireEvents(currentFilteredIssues) {
      // CSV Export Button
      const exportBtn = document.getElementById('jira-btn-export-csv');
      if (exportBtn) {
        exportBtn.addEventListener('click', () => {
          this.exportCsv(currentFilteredIssues);
        });
      }

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

      // Donut Slice & Legend Clicks (Interactive Chart Filtering)
      document.querySelectorAll('.jira-donut-slice, .jira-legend-item').forEach((el) => {
        el.addEventListener('click', () => {
          const key = el.getAttribute('data-filter-key');
          const val = el.getAttribute('data-filter-val');
          if (key && val) {
            this.filters[key] = (this.filters[key] || '').toLowerCase() === val.toLowerCase() ? 'all' : val;
            this.filters.kpi = 'all'; // Clear KPI card lock
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
            this.filters.kpi = 'all'; // Clear KPI card lock so dropdown filter takes precedence
            this.render();
          });
        }
      };

      bindSelect('filter-project', 'project');
      bindSelect('filter-status', 'status');
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
