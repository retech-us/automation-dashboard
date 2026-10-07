/**
 * Bridge between automation failures and Jira, plus a local issue lifecycle.
 *
 * States: detected → investigating → linked → fixed → verified
 *         (reopened when a cleared failure comes back)
 *
 * Links and lifecycle live in one local record per failure id.
 */
(function (window) {
  'use strict';

  const STORAGE_KEY = 'dashboard.failureLifecycle.v1';
  const LEGACY_LINKS_KEY = 'dashboard.failureJiraLinks.v1';

  const STATES = {
    detected: { id: 'detected', label: 'Detected', nextHint: 'Start investigating or link a Jira ticket.' },
    investigating: { id: 'investigating', label: 'Investigating', nextHint: 'Link a Jira ticket when you have an owner.' },
    linked: { id: 'linked', label: 'Jira linked', nextHint: 'Wait for a fix, then confirm in the next green run.' },
    fixed: { id: 'fixed', label: 'Fixed', nextHint: 'Waiting for the next run to verify it stays green.' },
    verified: { id: 'verified', label: 'Verified', nextHint: 'Cleared — not in the latest failure list.' },
    reopened: { id: 'reopened', label: 'Reopened', nextHint: 'Came back after being cleared — investigate again.' },
  };

  function nowIso() {
    return new Date().toISOString();
  }

  function loadStore() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      if (parsed && typeof parsed === 'object' && parsed.records && typeof parsed.records === 'object') {
        return parsed;
      }
    } catch { /* ignore */ }

    // One-time migrate from the older links-only store.
    const migrated = { schema: 1, records: {} };
    try {
      const legacy = JSON.parse(localStorage.getItem(LEGACY_LINKS_KEY) || '{}');
      if (legacy && typeof legacy === 'object') {
        for (const [id, link] of Object.entries(legacy)) {
          if (!link || !link.key) continue;
          migrated.records[id] = {
            state: 'linked',
            key: link.key,
            url: link.url || '',
            title: link.title || '',
            updatedAt: nowIso(),
            source: 'migrate',
          };
        }
      }
    } catch { /* ignore */ }
    saveStore(migrated);
    return migrated;
  }

  function saveStore(store) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store || { schema: 1, records: {} }));
    } catch { /* ignore quota */ }
  }

  function failureId(failure) {
    const parts = [
      failure.repo || '',
      failure.name || '',
      failure.feature || '',
      failure.status || '',
      failure.category || '',
    ];
    return parts.join('|').slice(0, 280);
  }

  function jiraCatalog() {
    const tracker = window.JiraTracker;
    const live = tracker && tracker.data ? tracker.data : null;
    const bundled = window.DASHBOARD_SNAPSHOTS?.snapshots?.jira || null;
    const data = live || bundled || {};
    const issues = Array.isArray(data)
      ? data
      : (Array.isArray(data.issues) ? data.issues : []);
    return {
      issues,
      jiraUrl: (data.jiraUrl || 'https://retech.atlassian.net').replace(/\/$/, ''),
      projectKey: data.projectKey || 'REB3',
    };
  }

  function tokenize(text) {
    return String(text || '')
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter((w) => w.length >= 4);
  }

  function findMatches(failure, limit) {
    const { issues } = jiraCatalog();
    const needles = new Set(tokenize(
      `${failure.name || ''} ${failure.feature || ''} ${failure.reason || ''} ${friendlyTitle(failure)}`,
    ));
    if (!needles.size) return [];

    const scored = [];
    for (const issue of issues) {
      if (!issue || !issue.key) continue;
      const hay = `${issue.key} ${issue.summary || ''} ${issue.epic || ''} ${(issue.labels || []).join(' ')}`.toLowerCase();
      let score = 0;
      for (const word of needles) {
        if (hay.includes(word)) score += 1;
      }
      if (score > 0) scored.push({ issue, score });
    }
    scored.sort((a, b) => b.score - a.score || String(a.issue.key).localeCompare(String(b.issue.key)));
    return scored.slice(0, limit || 5).map((row) => row.issue);
  }

  function friendlyTitle(failure) {
    const raw = (failure.feature || failure.name || 'Quality check').trim();
    return raw
      .replace(/^verify\s+/i, '')
      .replace(/^validate\s+/i, '')
      .replace(/_/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function getRecord(failureOrId) {
    const id = typeof failureOrId === 'string' ? failureOrId : failureId(failureOrId);
    const store = loadStore();
    return store.records[id] || null;
  }

  function upsertRecord(id, patch) {
    const store = loadStore();
    const prev = store.records[id] || { state: 'detected', updatedAt: nowIso() };
    store.records[id] = { ...prev, ...patch, updatedAt: nowIso() };
    saveStore(store);
    return store.records[id];
  }

  function getState(failure) {
    const record = getRecord(failure);
    return (record && record.state) || 'detected';
  }

  function setState(failure, state, meta) {
    if (!STATES[state]) return getRecord(failure);
    const id = failureId(failure);
    const patch = { state, source: (meta && meta.source) || 'manual', title: friendlyTitle(failure), repo: failure.repo || '' };
    if (meta && meta.key) patch.key = meta.key;
    if (meta && meta.url) patch.url = meta.url;
    if (state === 'verified') patch.verifiedAt = nowIso();
    if (state === 'reopened') patch.reopenedAt = nowIso();
    return upsertRecord(id, patch);
  }

  function getLink(failure) {
    const record = getRecord(failure);
    if (!record || !record.key) return null;
    return { key: record.key, url: record.url || browseUrl(record.key), state: record.state };
  }

  function setLink(failure, link) {
    const id = failureId(failure);
    if (!link) {
      const store = loadStore();
      const prev = store.records[id];
      if (!prev) return null;
      delete prev.key;
      delete prev.url;
      prev.state = prev.state === 'verified' ? 'verified' : 'investigating';
      prev.source = 'manual';
      prev.updatedAt = nowIso();
      store.records[id] = prev;
      saveStore(store);
      return null;
    }
    return upsertRecord(id, {
      state: 'linked',
      key: link.key,
      url: link.url || browseUrl(link.key),
      title: friendlyTitle(failure),
      repo: failure.repo || '',
      source: 'manual',
    });
  }

  function isJiraDone(issue) {
    if (!issue) return false;
    const category = String(issue.statusCategory || '').toLowerCase();
    const status = String(issue.status || '').toLowerCase();
    if (category === 'done') return true;
    return /^(done|closed|resolved|complete|completed)$/i.test(status);
  }

  function findIssueByKey(key) {
    if (!key) return null;
    return jiraCatalog().issues.find((issue) => issue && issue.key === key) || null;
  }

  /**
   * Sync lifecycle with the current failure list + Jira statuses.
   * - Linked + Jira Done → fixed
   * - Fixed/linked and gone from current failures → verified
   * - Verified/fixed and back in failures → reopened
   */
  function reconcile(currentFailures) {
    const present = new Set((currentFailures || []).map((f) => failureId(f)));
    const store = loadStore();
    let changed = false;

    // Ensure every visible failure has at least a detected record once touched,
    // and reopen cleared ones that came back.
    for (const failure of currentFailures || []) {
      const id = failureId(failure);
      const record = store.records[id];
      if (!record) continue;
      // Only reopen after it was cleared. "Fixed" means waiting for the next green run.
      if (record.state === 'verified') {
        store.records[id] = {
          ...record,
          state: 'reopened',
          reopenedAt: nowIso(),
          updatedAt: nowIso(),
          source: 'auto',
          title: friendlyTitle(failure),
          repo: failure.repo || record.repo || '',
        };
        changed = true;
      }
    }

    for (const [id, record] of Object.entries(store.records)) {
      if (!record) continue;
      let next = { ...record };

      if (record.key) {
        const issue = findIssueByKey(record.key);
        // Do not auto-fix from reopened — a Done ticket that fails again needs eyes.
        if (issue && isJiraDone(issue) && (record.state === 'linked' || record.state === 'investigating')) {
          next.state = 'fixed';
          next.source = 'jira';
        }
      }

      const stillFailing = present.has(id);
      if (!stillFailing && (next.state === 'fixed' || (next.state === 'linked' && next.key && isJiraDone(findIssueByKey(next.key))))) {
        next.state = 'verified';
        next.verifiedAt = next.verifiedAt || nowIso();
        next.source = 'auto';
      }

      if (next.state !== record.state || next.source !== record.source) {
        next.updatedAt = nowIso();
        store.records[id] = next;
        changed = true;
      }
    }

    if (changed) saveStore(store);
    return store.records;
  }

  function listVerified(limit) {
    const store = loadStore();
    return Object.entries(store.records)
      .filter(([, record]) => record && record.state === 'verified')
      .map(([id, record]) => ({ id, ...record }))
      .sort((a, b) => String(b.verifiedAt || b.updatedAt || '').localeCompare(String(a.verifiedAt || a.updatedAt || '')))
      .slice(0, limit || 20);
  }

  function isOpenDefect(issue) {
    if (!issue || isJiraDone(issue)) return false;
    const type = String(issue.type || '').toLowerCase();
    // Bugs matter most; include Task when it looks like a defect.
    if (type === 'bug') return true;
    if (type === 'task' && /defect|fail|broken|bug|regression/i.test(issue.summary || '')) return true;
    return false;
  }

  function linkedKeysForFailures(currentFailures) {
    const keys = new Set();
    for (const failure of currentFailures || []) {
      const link = getLink(failure);
      if (link?.key) keys.add(link.key);
    }
    return keys;
  }

  /**
   * Two-way gap list:
   * - unlinkedFailures: current failures with no local Jira link
   * - orphanJira: open Bug tickets that are not linked to any current failure
   *   and do not strongly match any current failure title
   */
  function findOrphans(currentFailures) {
    const failures = currentFailures || [];
    const unlinkedFailures = failures.filter((failure) => !getLink(failure));
    const linkedKeys = linkedKeysForFailures(failures);

    // Only strong title overlap removes a bug from the orphan list; a single shared
    // word like "scan" should not hide a real gap.
    const matchedKeys = new Set(linkedKeys);
    for (const failure of failures) {
      const { issues } = jiraCatalog();
      const needles = new Set(tokenize(
        `${failure.name || ''} ${failure.feature || ''} ${failure.reason || ''} ${friendlyTitle(failure)}`,
      ));
      if (!needles.size) continue;
      for (const issue of issues) {
        if (!issue?.key || !isOpenDefect(issue)) continue;
        const hay = `${issue.key} ${issue.summary || ''}`.toLowerCase();
        let score = 0;
        for (const word of needles) {
          if (hay.includes(word)) score += 1;
        }
        if (score >= 2) matchedKeys.add(issue.key);
      }
    }

    const orphanJira = jiraCatalog().issues
      .filter((issue) => isOpenDefect(issue) && issue.key && !matchedKeys.has(issue.key))
      .map((issue) => ({
        key: issue.key,
        summary: issue.summary || issue.key,
        status: issue.status || '',
        priority: issue.priority || '',
        assignee: issue.assignee || 'Unassigned',
        url: issue.url || browseUrl(issue.key),
        type: issue.type || 'Bug',
      }))
      .sort((a, b) => String(a.key).localeCompare(String(b.key)));

    return {
      unlinkedFailures,
      orphanJira,
      counts: {
        unlinked: unlinkedFailures.length,
        orphanJira: orphanJira.length,
      },
    };
  }

  function createIssueUrl(failure) {
    const { jiraUrl, projectKey } = jiraCatalog();
    // Always target REB3 (or catalog projectKey) by key — never use pid=KEY
    // (pid requires a numeric project id and opens the wrong project when given a key).
    const key = (projectKey || 'REB3').trim() || 'REB3';
    const summary = `[Automation] ${friendlyTitle(failure)} (${failure.repo || 'suite'})`;
    const description = [
      `Detected on the Store Intell QA dashboard.`,
      `Suite: ${failure.repo || 'unknown'}`,
      `Status: ${failure.status || 'failed'}`,
      `Category: ${failure.category || 'unknown'}`,
      failure.reason ? `Detail: ${failure.reason}` : '',
      failure.reportUrl ? `Allure: ${failure.reportUrl}` : '',
      failure.ciRunUrl ? `CI: ${failure.ciRunUrl}` : '',
    ].filter(Boolean).join('\n');

    const params = new URLSearchParams({
      selectedProjectKey: key,
      summary,
      description,
    });
    return `${jiraUrl}/secure/CreateIssue!default.jspa?${params.toString()}`;
  }

  function browseUrl(key) {
    const { jiraUrl } = jiraCatalog();
    return `${jiraUrl}/browse/${encodeURIComponent(key)}`;
  }

  function readAttentionFilters() {
    const params = new URLSearchParams(window.location.search);
    return {
      suite: (params.get('suite') || '').trim(),
      bucket: (params.get('bucket') || '').trim(),
      area: (params.get('area') || '').trim(),
      q: (params.get('q') || '').trim(),
      lifecycle: (params.get('lifecycle') || '').trim(),
      orphan: (params.get('orphan') || '').trim(),
    };
  }

  function writeAttentionFilters(filters) {
    const url = new URL(window.location.href);
    const keys = ['suite', 'bucket', 'area', 'q', 'lifecycle', 'orphan'];
    for (const key of keys) {
      const value = (filters[key] || '').trim();
      if (value) url.searchParams.set(key, value);
      else url.searchParams.delete(key);
    }
    window.history.replaceState({}, '', url);
  }

  function clearAttentionFilters() {
    writeAttentionFilters({ suite: '', bucket: '', area: '', q: '', lifecycle: '', orphan: '' });
  }

  window.IssueBridge = {
    STATES,
    failureId,
    getLink,
    setLink,
    getRecord,
    getState,
    setState,
    reconcile,
    listVerified,
    findOrphans,
    findMatches,
    createIssueUrl,
    browseUrl,
    jiraCatalog,
    friendlyTitle,
    isJiraDone,
    isOpenDefect,
    readAttentionFilters,
    writeAttentionFilters,
    clearAttentionFilters,
  };
})(window);
