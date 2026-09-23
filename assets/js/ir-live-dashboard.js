/**
 * Intelligent Reset task-quality view.
 * Reads only the runner's public snapshot contract; no credentials are exposed.
 */
(function (window) {
  'use strict';

  let timer = null;

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  }

  function percent(value) {
    return typeof value === 'number' ? `${value.toFixed(1)}%` : 'Not checked';
  }

  function renderFindings(findings) {
    const container = document.getElementById('ir-quality-findings');
    if (!container) return;
    container.replaceChildren();
    if (!Array.isArray(findings) || findings.length === 0) {
      const message = document.createElement('p');
      message.className = 'data-note';
      message.textContent = '✅ No failing checks were found in the latest verified data.';
      container.appendChild(message);
      return;
    }

    const list = document.createElement('ul');
    list.className = 'ir-finding-list';
    for (const finding of findings) {
      const item = document.createElement('li');
      item.className = `ir-finding ir-finding--${finding.severity || 'warning'}`;

      const head = document.createElement('div');
      head.className = 'ir-finding-head';
      const title = document.createElement('strong');
      title.textContent = finding.title || finding.code || 'Quality check';
      const pill = document.createElement('span');
      pill.className = `ir-kpi-pill ${finding.severity === 'critical' ? 'ir-kpi-pill--fail' : 'ir-kpi-pill--warn'}`;
      pill.textContent = (finding.severity || 'WARNING').toUpperCase();
      head.append(title, pill);

      const evidence = document.createElement('div');
      evidence.className = 'ir-finding-evidence';
      evidence.textContent = finding.evidence || '';

      const reference = document.createElement('code');
      reference.className = 'ir-finding-code';
      reference.textContent = finding.jira && finding.jira.reference
        ? `Ref: ${finding.jira.reference}`
        : finding.code || '';

      item.append(head, evidence, reference);
      list.appendChild(item);
    }
    container.appendChild(list);
  }

  function renderScans(scans) {
    const container = document.getElementById('ir-quality-scans');
    if (!container) return;
    container.replaceChildren();
    if (!Array.isArray(scans) || scans.length === 0) {
      const message = document.createElement('p');
      message.className = 'data-note';
      message.textContent = 'ℹ️ No explicit scan diagnostics were returned by the backend.';
      container.appendChild(message);
      return;
    }
    const list = document.createElement('ul');
    list.className = 'ir-finding-list';
    for (const scan of scans) {
      const item = document.createElement('li');
      item.className = 'ir-finding ir-finding--info';

      const head = document.createElement('div');
      head.className = 'ir-finding-head';
      const title = document.createElement('strong');
      const stageLabel = scan.stage === 'post_photo' ? '📸 Post-Reset Scan' : scan.stage === 'pre_photo' ? '📷 Pre-Reset Scan' : '🔍 Scan';
      title.textContent = `${stageLabel} #${scan.scan_id}`;

      const badge = document.createElement('span');
      badge.className = 'ir-kpi-pill ir-kpi-pill--neutral';
      badge.textContent = scan.status || 'INGESTED';
      head.append(title, badge);

      const evidence = document.createElement('div');
      evidence.className = 'ir-finding-evidence';
      const facts = [
        typeof scan.image_quality === 'number' ? `Quality: ${scan.image_quality.toFixed(1)}` : null,
        typeof scan.blurry_pct === 'number' ? `Blurry: ${scan.blurry_pct}%` : null,
        scan.shelf_mismatch === true ? '⚠️ Shelf mismatch: Yes' : scan.shelf_mismatch === false ? '✅ Shelf match: Normal' : null,
      ].filter(Boolean);
      evidence.textContent = facts.length ? facts.join(' · ') : 'No quality fields were returned.';

      item.append(head, evidence);
      list.appendChild(item);
    }
    container.appendChild(list);
  }

  function renderActions(snapshot) {
    const container = document.getElementById('ir-quality-actions');
    if (!container) {
      // Create the actions container if it doesn't exist
      const newContainer = document.createElement('div');
      newContainer.id = 'ir-quality-actions';
      newContainer.className = 'ir-quality-actions-panel';

      // Find where to insert it - after the scans container
      const scansContainer = document.getElementById('ir-quality-scans');
      if (scansContainer && scansContainer.parentNode) {
        scansContainer.parentNode.insertBefore(newContainer, scansContainer.nextSibling);
      } else {
        // Fallback: append to body or find another suitable location
        document.body.appendChild(newContainer);
      }
      // Use the newly created container
      container = newContainer;
    }

    container.replaceChildren();

    const actionsGenerated = snapshot.actions_generated || [];
    const actionsPerformed = snapshot.actions_performed || [];
    const actionDifferences = snapshot.action_differences || [];

    if ((!actionsGenerated || actionsGenerated.length === 0) &&
        (!actionsPerformed || actionsPerformed.length === 0) &&
        (!actionDifferences || actionDifferences.length === 0)) {
      const message = document.createElement('p');
      message.className = 'data-note';
      message.textContent = 'No action data available for this task.';
      container.appendChild(message);
      return;
    }

    // Create action tracking section
    const sectionTitle = document.createElement('h3');
    sectionTitle.textContent = 'Action Tracking';
    sectionTitle.className = 'ir-action-section-title';
    container.appendChild(sectionTitle);

    // System-generated actions
    if (actionsGenerated && actionsGenerated.length > 0) {
      const generatedTitle = document.createElement('h4');
      generatedTitle.textContent = 'System-Generated Actions';
      generatedTitle.className = 'ir-action-subtitle';
      container.appendChild(generatedTitle);

      const generatedList = document.createElement('ul');
      generatedList.className = 'ir-action-list ir-action-list--generated';

      actionsGenerated.forEach((action, index) => {
        const item = document.createElement('li');
        item.className = 'ir-action-item';

        const actionNum = document.createElement('span');
        actionNum.className = 'ir-action-number';
        actionNum.textContent = `${index + 1}.`;

        const actionDesc = document.createElement('span');
        actionDesc.className = 'ir-action-description';
        actionDesc.textContent = action.description || action.action_type || 'Unknown action';

        const actionTime = document.createElement('span');
        actionTime.className = 'ir-action-time';
        actionTime.textContent = action.timestamp ?
          new Date(action.timestamp).toLocaleTimeString() :
          'Time not available';

        item.append(actionNum, actionDesc, actionTime);
        generatedList.appendChild(item);
      });

      container.appendChild(generatedList);
    }

    // User-performed actions
    if (actionsPerformed && actionsPerformed.length > 0) {
      const performedTitle = document.createElement('h4');
      performedTitle.textContent = 'User-Performed Actions';
      performedTitle.className = 'ir-action-subtitle';
      container.appendChild(performedTitle);

      const performedList = document.createElement('ul');
      performedList.className = 'ir-action-list ir-action-list--performed';

      actionsPerformed.forEach((action, index) => {
        const item = document.createElement('li');
        item.className = 'ir-action-item';

        const actionNum = document.createElement('span');
        actionNum.className = 'ir-action-number';
        actionNum.textContent = `${index + 1}.`;

        const actionDesc = document.createElement('span');
        actionDesc.className = 'ir-action-description';
        actionDesc.textContent = action.description || action.action_type || 'Unknown action';

        const actionTime = document.createElement('span');
        actionTime.className = 'ir-action-time';
        actionTime.textContent = action.timestamp ?
          new Date(action.timestamp).toLocaleTimeString() :
          'Time not available';

        // Check if this action matches a generated action
        const matchingGenerated = actionsGenerated.find(genAction =>
          genAction.action_id === action.action_id ||
          (genAction.description === action.description &&
           genAction.action_type === action.action_type));

        if (matchingGenerated) {
          item.classList.add('ir-action-item--matched');
        } else {
          item.classList.add('ir-action-item--unmatched');
        }

        item.append(actionNum, actionDesc, actionTime);
        performedList.appendChild(item);
      });

      container.appendChild(performedList);
    }

    // Action differences/mismatches
    if (actionDifferences && actionDifferences.length > 0) {
      const differencesTitle = document.createElement('h4');
      differencesTitle.textContent = 'Action Differences';
      differencesTitle.className = 'ir-action-subtitle';
      container.appendChild(differencesTitle);

      const differencesList = document.createElement('ul');
      differencesList.className = 'ir-action-list ir-action-list--differences';

      actionDifferences.forEach((diff, index) => {
        const item = document.createElement('li');
        item.className = 'ir-action-item ir-action-item--difference';

        const diffNum = document.createElement('span');
        diffNum.className = 'ir-action-number';
        diffNum.textContent = `${index + 1}.`;

        const diffDesc = document.createElement('span');
        diffDesc.className = 'ir-action-description';
        diffDesc.textContent = diff.description ||
          `Mismatch: Expected ${diff.expected_action || 'unknown'}, ` +
          `Performed ${diff.actual_action || 'unknown'}`;

        const diffTime = document.createElement('span');
        diffTime.className = 'ir-action-time';
        diffTime.textContent = diff.timestamp ?
          new Date(diff.timestamp).toLocaleTimeString() :
          'Time not available';

        const diffSeverity = document.createElement('span');
        diffSeverity.className = `ir-action-severity ir-action-severity--${diff.severity || 'warning'}`;
        diffSeverity.textContent = (diff.severity || 'warning').toUpperCase();

        item.append(diffNum, diffDesc, diffTime, diffSeverity);
        differencesList.appendChild(item);
      });

      container.appendChild(differencesList);
    }

    // Summary statistics
    const statsContainer = document.createElement('div');
    statsContainer.className = 'ir-action-stats';

    const generatedCount = actionsGenerated ? actionsGenerated.length : 0;
    const performedCount = actionsPerformed ? actionsPerformed.length : 0;
    const differencesCount = actionDifferences ? actionDifferences.length : 0;

    statsContainer.innerHTML = `
      <div class="ir-stat-item">
        <span class="ir-stat-label">System Actions:</span>
        <span class="ir-stat-value">${generatedCount}</span>
      </div>
      <div class="ir-stat-item">
        <span class="ir-stat-label">User Actions:</span>
        <span class="ir-stat-value">${performedCount}</span>
      </div>
      <div class="ir-stat-item">
        <span class="ir-stat-label">Differences:</span>
        <span class="ir-stat-value">${differencesCount}</span>
      </div>
    `;

    container.appendChild(statsContainer);
  }

  function render(snapshot, source) {
    const metrics = snapshot.metrics || {};
    const gate = snapshot.quality_gate || {};
    const post = snapshot.post_photo || {};

    const srcLabel = source === 'last_saved' ? '💾 Last saved task' : '⚡ Live runner connected';
    setText('ir-quality-source', srcLabel);
    setText('ir-quality-summary', snapshot.plain_language_summary || 'No task is loaded.');
    setText('ir-quality-gate', gate.state === 'pass' ? 'PASS' : gate.state === 'fail' ? 'NEEDS ATTENTION' : 'Not checked');
    setText('ir-quality-finished', percent(metrics.work_finished_pct));
    setText('ir-quality-alignment', percent(metrics.digital_alignment_pct));
    setText(
      'ir-quality-post',
      post.state === 'verified'
        ? percent(metrics.post_alignment_pct)
        : post.state === 'unavailable' ? 'Unavailable' : 'Not checked',
    );
    setText('ir-quality-post-help', post.explanation || 'Post photo has not been checked yet.');

    renderFindings(snapshot.findings);
    renderScans(snapshot.scan_diagnostics);
    renderActions(snapshot); // Add action rendering

    // Update KPI Card states & color indicators
    const gateCard = document.getElementById('ir-quality-gate-card');
    const gateVal = document.getElementById('ir-quality-gate');
    const gateBadge = document.getElementById('ir-quality-gate-badge');
    if (gateCard) {
      gateCard.setAttribute('data-state', gate.state || 'not_checked');
      if (gateVal) {
        gateVal.className = `ir-kpi-val ${gate.state === 'pass' ? 'ir-kpi-val--pass' : gate.state === 'fail' ? 'ir-kpi-val--fail' : ''}`;
      }
      if (gateBadge) {
        gateBadge.textContent = gate.state === 'pass' ? 'PASS ✅' : gate.state === 'fail' ? 'FAIL ⚠️' : 'PENDING';
        gateBadge.className = `ir-kpi-pill ${gate.state === 'pass' ? 'ir-kpi-pill--pass' : gate.state === 'fail' ? 'ir-kpi-pill--fail' : ''}`;
      }
    }

    const postCard = document.getElementById('ir-quality-post-card');
    const postVal = document.getElementById('ir-quality-post');
    const postBadge = document.getElementById('ir-quality-post-badge');
    if (postCard) {
      postCard.setAttribute('data-state', post.state || 'not_checked');
      if (postVal) {
        postVal.className = `ir-kpi-val ${post.state === 'verified' ? 'ir-kpi-val--pass' : post.state === 'unavailable' ? 'ir-kpi-val--fail' : ''}`;
      }
      if (postBadge) {
        postBadge.textContent = post.state === 'verified' ? 'VERIFIED ✅' : post.state === 'unavailable' ? 'UNAVAILABLE' : 'NOT CHECKED';
        postBadge.className = `ir-kpi-pill ${post.state === 'verified' ? 'ir-kpi-pill--pass' : post.state === 'unavailable' ? 'ir-kpi-pill--fail' : ''}`;
      }
    }

    // Fix evidence report button: link to real interactive E2E Audit Report
    const report = document.getElementById('ir-quality-report');
    if (report) {
      if (snapshot.report_url) {
        report.href = snapshot.report_url;
        report.target = '_blank';
        report.removeAttribute('aria-disabled');
      } else if (snapshot.task_id) {
        report.href = `/api/runner/e2e_audit_report?task_id=${encodeURIComponent(snapshot.task_id)}`;
        report.target = '_blank';
        report.removeAttribute('aria-disabled');
      } else {
        report.href = 'test_runner.html';
      }
    }
  }

  async function refresh() {
    try {
      const response = await fetch('/api/runner/ir_live_snapshot', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      render(data.snapshot || {}, data.source);
    } catch (error) {
      setText('ir-quality-source', 'Local runner offline');
      setText(
        'ir-quality-summary',
        'Start runner_server.py to see live Intelligent Reset quality. Existing suite and Jira data are unaffected.',
      );
    }
  }

  window.IrLiveDashboard = {
    init() {
      refresh();
      if (!timer) timer = window.setInterval(refresh, 5000);
    },
    refresh,
  };
})(window);

