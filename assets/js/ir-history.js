/**
 * Intelligent Reset task history by instance and date range.
 * Renders whatever the runner can prove and says plainly when data is missing.
 */
(function (window, document) {
  'use strict';

  let initialised = false;

  function byId(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    const element = byId(id);
    if (element) element.textContent = value;
  }

  function score(value) {
    return typeof value === 'number' ? `${value.toFixed(1)}%` : 'Not checked';
  }

  function gateLabel(state) {
    if (state === 'pass') return 'Passed';
    if (state === 'fail') return 'Needs attention';
    return 'Not checked';
  }

  function resolveInstanceUrl(val) {
    if (!val) return 'https://harr.rebotics.net/';
    let v = val.trim().toLowerCase();
    if (v === 'krog' || v === 'kroger' || v === 'krsc') v = 'krcs';
    if (v.startsWith('http://') || v.startsWith('https://')) {
      if (v.includes('://krog.rebotics.net') || v.includes('://krsc.rebotics.net') || v.includes('://kroger.rebotics.net')) {
        v = v.replace('://krog.rebotics.net', '://krcs.rebotics.net')
             .replace('://krsc.rebotics.net', '://krcs.rebotics.net')
             .replace('://kroger.rebotics.net', '://krcs.rebotics.net');
      }
      return v.endsWith('/') ? v : `${v}/`;
    }
    if (!v.includes('.')) {
      return `https://${v}.rebotics.net/`;
    }
    return `https://${v}/`;
  }

  function setAuthFeedback(msg, type) {
    const el = byId('ir-history-auth-feedback');
    if (!el) return;
    if (!msg) {
      el.style.display = 'none';
      el.textContent = '';
      return;
    }
    el.style.display = 'block';
    el.textContent = msg;
    if (type === 'error') {
      el.style.background = 'rgba(239, 68, 68, 0.12)';
      el.style.border = '1px solid #ef4444';
      el.style.color = '#ef4444';
    } else if (type === 'success') {
      el.style.background = 'rgba(34, 197, 94, 0.12)';
      el.style.border = '1px solid #22c55e';
      el.style.color = '#22c55e';
    } else {
      el.style.background = 'rgba(56, 189, 248, 0.12)';
      el.style.border = '1px solid #0284c7';
      el.style.color = '#38bdf8';
    }
  }

  function updateInstanceUrlPreview() {
    const val = selectedInstance();
    const resolvedUrl = resolveInstanceUrl(val);
    const badge = byId('ir-instance-resolved-badge');
    if (badge) badge.textContent = resolvedUrl;
    const authTarget = byId('ir-auth-target-url');
    if (authTarget) authTarget.textContent = resolvedUrl;
  }

  function selectedInstance() {
    const choice = byId('ir-history-instance');
    if (!choice) return 'harr';
    let val = (choice.value || '').trim();
    if (val === 'custom') {
      const custom = byId('ir-history-instance-custom');
      val = custom ? custom.value.trim() : '';
    }
    if (val === 'krog' || val === 'kroger' || val === 'krsc') val = 'krcs';
    return val || 'harr';
  }

  function selectedTaskType() {
    const choice = byId('ir-history-type');
    return choice ? choice.value : '';
  }

  /** Rebuild a dropdown from the values the instance really returned, keeping the selection. */
  function fillChoices(id, items, allLabel) {
    const select = byId(id);
    if (!select || !Array.isArray(items)) return;
    const previous = select.value;
    const options = [`<option value="">${allLabel}</option>`];
    if (id === 'ir-history-status-filter') {
      options.push('<option value="in_progress,completed">Started or completed</option>');
    }
    for (const item of items) {
      const label = `${item.label} (${item.count})`;
      options.push(`<option value="${item.value}">${label}</option>`);
    }
    select.innerHTML = options.join('');
    const stillThere = [...select.options].some((option) => option.value === previous);
    select.value = stillThere ? previous : '';
  }

  function toggleConditionalFields() {
    const rangeIsCustom = byId('ir-history-range') && byId('ir-history-range').value === 'custom';
    const instanceIsCustom = byId('ir-history-instance') && byId('ir-history-instance').value === 'custom';
    for (const id of ['ir-history-from-field', 'ir-history-to-field']) {
      const field = byId(id);
      if (field) field.hidden = !rangeIsCustom;
    }
    const instanceField = byId('ir-history-instance-custom-field');
    if (instanceField) instanceField.hidden = !instanceIsCustom;
    updateInstanceUrlPreview();
  }

  function taskRow(task) {
    const row = document.createElement('tr');
    const audited = task.audited === true;

    // 1. Task ID
    const tdId = document.createElement('td');
    const linkId = document.createElement('a');
    linkId.className = 'ir-task-link';
    linkId.href = `test_runner.html?task_id=${encodeURIComponent(task.task_id)}`;
    linkId.target = '_blank';
    linkId.title = `Open Task #${task.task_id} in IR Studio`;
    linkId.textContent = `#${task.task_id}`;
    tdId.appendChild(linkId);
    row.appendChild(tdId);

    // 2. Date
    const tdDate = document.createElement('td');
    tdDate.textContent = task.task_date || 'Unknown date';
    row.appendChild(tdDate);

    // 3. Type
    const tdType = document.createElement('td');
    tdType.textContent = task.task_type || '—';
    row.appendChild(tdType);

    // 4. Title & Store Location
    const tdTitle = document.createElement('td');
    tdTitle.style.maxWidth = '300px';
    const titleEl = document.createElement('div');
    titleEl.style.fontWeight = '500';
    titleEl.textContent = task.title || '—';
    tdTitle.appendChild(titleEl);

    const storeLabel = task.store_name || (task.store_custom_id ? `Store #${task.store_custom_id}` : (task.store_id ? `Store #${task.store_id}` : null));
    if (storeLabel) {
      const storeEl = document.createElement('div');
      storeEl.style.fontSize = '11px';
      storeEl.style.color = '#0284c7';
      storeEl.style.marginTop = '2px';
      storeEl.style.display = 'flex';
      storeEl.style.alignItems = 'center';
      storeEl.style.gap = '4px';
      storeEl.innerHTML = `<span style="font-size:11px;">🏪</span> <span>${storeLabel}</span>`;
      tdTitle.appendChild(storeEl);
    }
    row.appendChild(tdTitle);

    // 5. Status
    const tdStatus = document.createElement('td');
    const rawStatus = (task.status || '').toLowerCase();
    const statusPill = document.createElement('span');
    statusPill.className = `status-pill ${rawStatus.includes('complete') ? 'status-pill--passed' : rawStatus.includes('progress') ? 'status-pill--warning' : ''}`;
    statusPill.textContent = task.status_label || task.status || 'Unknown';
    tdStatus.appendChild(statusPill);
    row.appendChild(tdStatus);

    // 6. Quality Score
    const tdScore = document.createElement('td');
    if (audited && typeof task.overall_score_pct === 'number') {
      const scoreBadge = document.createElement('span');
      const isPass = task.overall_score_pct >= 95;
      scoreBadge.className = `ir-kpi-pill ${isPass ? 'ir-kpi-pill--pass' : 'ir-kpi-pill--fail'}`;
      scoreBadge.textContent = score(task.overall_score_pct);
      tdScore.appendChild(scoreBadge);
    } else {
      tdScore.innerHTML = '<span style="color:var(--muted);font-size:12px;">Not checked</span>';
    }
    row.appendChild(tdScore);

    // 7. 95% Check Gate
    const tdGate = document.createElement('td');
    const gateBadge = document.createElement('span');
    if (task.gate_state === 'pass') {
      gateBadge.className = 'status-badge pass';
      gateBadge.textContent = 'PASSED ✅';
    } else if (task.gate_state === 'fail') {
      gateBadge.className = 'status-badge fail';
      gateBadge.textContent = 'ATTENTION ⚠️';
    } else {
      gateBadge.className = 'status-badge unknown';
      gateBadge.textContent = 'PENDING';
    }
    tdGate.appendChild(gateBadge);
    row.appendChild(tdGate);

    // 8. Actions
    const actionCell = document.createElement('td');
    actionCell.style.textAlign = 'right';
    actionCell.style.whiteSpace = 'nowrap';

    const flowBtn = document.createElement('button');
    flowBtn.type = 'button';
    flowBtn.className = 'btn btn--primary btn--sm';
    flowBtn.style.marginRight = '6px';
    flowBtn.textContent = '📊 View Summary';
    flowBtn.title = `View Executive Summary & Action Breakdown for Task #${task.task_id}`;
    flowBtn.addEventListener('click', () => {
      if (window.IrTaskFlow) {
        window.IrTaskFlow.loadTask(task.task_id, selectedInstance());
        window.IrTaskFlow.switchSubView('summary');
        const headerEl = document.querySelector('.ir-simple-header');
        if (headerEl) {
          headerEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
    actionCell.appendChild(flowBtn);

    if (audited) {
      const link = document.createElement('a');
      link.className = 'btn btn--ghost btn--sm';
      link.href = task.report_url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = '📄 Evidence ↗';
      actionCell.appendChild(link);
    } else {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn--primary btn--sm';
      button.textContent = '⚡ Run Audit';
      button.addEventListener('click', () => runFullAudit(task, button));
      actionCell.appendChild(button);
    }
    row.appendChild(actionCell);

    row.className = task.gate_state === 'fail' ? 'ir-history-row ir-history-row--fail' : 'ir-history-row';
    return row;
  }

  function renderTasks(tasks) {
    const container = byId('ir-history-results');
    if (!container) return;
    container.replaceChildren();
    if (!Array.isArray(tasks) || tasks.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'ir-empty-state';
      empty.innerHTML = `
        <div class="ir-empty-icon">📂</div>
        <p><strong>No reset tasks found</strong></p>
        <p style="font-size:12px;margin-top:4px;color:var(--muted);">No tasks matched the selected instance, date range, or filters. Try selecting a different range or instance above.</p>
      `;
      container.appendChild(empty);
      return;
    }

    const table = document.createElement('table');
    table.className = 'ir-history-table';
    const head = document.createElement('thead');
    const headRow = document.createElement('tr');
    for (const heading of ['Task', 'Date', 'Type', 'Title', 'Status', 'Quality score', '95% check', '']) {
      const cell = document.createElement('th');
      cell.textContent = heading;
      headRow.appendChild(cell);
    }
    head.appendChild(headRow);
    table.appendChild(head);

    const body = document.createElement('tbody');
    for (const task of tasks) body.appendChild(taskRow(task));
    table.appendChild(body);
    container.appendChild(table);
  }

  function showSignIn(needed) {
    const banner = byId('ir-history-auth-banner');
    if (banner) banner.hidden = !needed;
    for (const id of ['ir-history-username-field', 'ir-history-password-field']) {
      const field = byId(id);
      if (field) field.hidden = !needed;
    }
    const button = byId('ir-history-load');
    if (button) {
      const username = byId('ir-history-username');
      const password = byId('ir-history-password');
      const hasCreds = Boolean(username && username.value.trim() && password && password.value);
      button.textContent = hasCreds ? '🔐 Sign In & Load' : '🔄 Load Resets';
    }
  }

  async function signIn(instance) {
    const username = byId('ir-history-username');
    const password = byId('ir-history-password');
    if (!username || !username.value.trim() || !password || !password.value) return false;

    const fullUrl = resolveInstanceUrl(instance || selectedInstance());
    setAuthFeedback(`Connecting to ${fullUrl}…`, 'info');

    const response = await fetch('/api/runner/auth_ping', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        base_url: fullUrl,
        username: username.value.trim(),
        password: password.value,
      }),
    });
    const data = await response.json();
    if (!data.connected) {
      const errMsg = data.error || data.message || 'Sign in failed.';
      setAuthFeedback(`⚠️ Sign in failed: ${errMsg}`, 'error');
      throw new Error(errMsg);
    }
    setAuthFeedback(`✅ Successfully signed in to ${data.instance_slug || 'krcs'} as '${data.username || username.value.trim()}'!`, 'success');
    password.value = '';
    return true;
  }

  function render(view) {
    const totals = view.totals || {};
    const facets = view.facets || {};
    fillChoices('ir-history-type', facets.types, 'All task types');
    fillChoices('ir-history-status-filter', facets.statuses, 'All statuses');
    const typeHint = byId('ir-history-type-hint');
    if (typeHint) {
      const names = (facets.types || []).map((item) => item.label);
      typeHint.textContent = names.length
        ? `${names.length} type(s) found on this instance.`
        : 'No task types were returned for this range.';
    }
    setText('ir-history-summary', view.plain_language_summary || 'No summary is available.');
    setText('ir-history-status', view.range ? view.range.label : 'Loaded');
    setText('ir-history-total-tasks', String(totals.tasks != null ? totals.tasks : '—'));
    setText('ir-history-total-audited', String(totals.audited != null ? totals.audited : '—'));
    setText('ir-history-total-pass', String(totals.gate_pass != null ? totals.gate_pass : '—'));
    setText('ir-history-total-fail', String(totals.gate_fail != null ? totals.gate_fail : '—'));
    // An empty range is already explained in the summary; a row of zeros reads as real data.
    const totalsPanel = byId('ir-history-totals');
    if (totalsPanel) totalsPanel.hidden = !totals.tasks;
    renderTasks(view.tasks);
  }

  async function runFullAudit(task, button) {
    const original = button.textContent;
    button.disabled = true;
    button.textContent = 'Checking…';
    try {
      const response = await fetch('/api/runner/audit_task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: task.task_id, base_url: selectedInstance() }),
      });
      const data = await response.json();
      if (data.status !== 'success') throw new Error(data.message || 'Audit failed');
      await load();
    } catch (error) {
      button.disabled = false;
      button.textContent = original;
      setText('ir-history-summary', `Could not run the full check for task #${task.task_id}: ${error.message}`);
    }
  }

  function setLoading(active) {
    const button = byId('ir-history-load');
    if (button) button.disabled = active;
    if (!active) return;
    // Clear old rows so a slow fetch never leaves results that contradict the chosen filters.
    const totalsPanel = byId('ir-history-totals');
    if (totalsPanel) totalsPanel.hidden = true;
    const results = byId('ir-history-results');
    if (results) results.replaceChildren();
    setText('ir-history-summary', 'Reading tasks from the instance. The first load of a range can take up to a minute.');
  }

  async function load() {
    const instance = selectedInstance();
    const range = byId('ir-history-range') ? byId('ir-history-range').value : '7d';
    if (!instance) {
      setText('ir-history-summary', 'Enter an instance URL before loading history.');
      return;
    }

    const params = new URLSearchParams({ instance, range });
    const taskType = selectedTaskType();
    if (taskType) params.set('type', taskType);
    const title = byId('ir-history-title');
    if (title && title.value.trim()) params.set('title', title.value.trim());
    const status = byId('ir-history-status-filter');
    if (status && status.value) params.set('status', status.value);
    if (range === 'custom') {
      const from = byId('ir-history-from');
      const to = byId('ir-history-to');
      if (!from || !from.value || !to || !to.value) {
        setText('ir-history-summary', 'Pick both a start and an end date for a custom range.');
        return;
      }
      params.set('from', from.value);
      params.set('to', to.value);
    }

    setText('ir-history-status', 'Loading…');
    setLoading(true);
    try {
      try {
        await signIn(instance);
      } catch (authError) {
        setText('ir-history-status', 'Sign in failed');
        setText('ir-history-summary', authError.message);
        return;
      }

      const response = await fetch(`/api/runner/ir_history?${params.toString()}`, { cache: 'no-store' });
      const data = await response.json();
      if (data.status !== 'success') {
        setText('ir-history-status', 'Could not load');
        setText('ir-history-summary', data.message || 'The runner could not load history.');
        return;
      }
      showSignIn(data.signed_in === false);
      render(data);
    } catch (error) {
      setText('ir-history-status', 'Runner unavailable');
      setText(
        'ir-history-summary',
        'Start runner_server.py to load Intelligent Reset history. Other dashboard data is unaffected.',
      );
    } finally {
      setLoading(false);
    }
  }

  window.IrHistory = {
    init() {
      if (initialised) return;
      const form = byId('ir-history-form');
      if (!form) return;
      initialised = true;
      form.addEventListener('submit', (event) => {
        event.preventDefault();
        load();
      });
      for (const id of ['ir-history-range', 'ir-history-instance', 'ir-history-type']) {
        const control = byId(id);
        if (control) control.addEventListener('change', toggleConditionalFields);
      }
      const customInput = byId('ir-history-instance-custom');
      if (customInput) {
        customInput.addEventListener('input', updateInstanceUrlPreview);
      }
      const authBtn = byId('ir-history-auth-btn');
      if (authBtn) {
        authBtn.addEventListener('click', async () => {
          const inst = selectedInstance();
          setText('ir-history-status', 'Signing in…');
          authBtn.disabled = true;
          authBtn.textContent = 'Signing in…';
          try {
            await signIn(inst);
            setText('ir-history-status', 'Signed in ✅');
            showSignIn(false);
            load();
          } catch (err) {
            setText('ir-history-status', 'Sign in failed');
            setText('ir-history-summary', err.message || 'Authentication failed. Please verify credentials.');
          } finally {
            authBtn.disabled = false;
            authBtn.textContent = 'Sign In & Sync';
          }
        });
      }
      ['ir-history-username', 'ir-history-password'].forEach((id) => {
        const el = byId(id);
        if (el) {
          el.addEventListener('input', () => {
            const username = byId('ir-history-username');
            const password = byId('ir-history-password');
            const hasCreds = Boolean(username && username.value.trim() && password && password.value);
            const btn = byId('ir-history-load');
            if (btn) btn.textContent = hasCreds ? '🔐 Sign In & Load' : '🔄 Load Resets';
          });
        }
      });
      toggleConditionalFields();
      load();
    },
    load,
    loadHistory: load,
  };
})(window, document);
