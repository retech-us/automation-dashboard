/**
 * Intelligent Reset Simplified Assistant Controller
 *
 * Provides a clear, non-technical executive overview, shelf accuracy progress,
 * friendly action breakdown, and plain-English step-by-step story for store resets.
 */
(function (window, document) {
  'use strict';

  let currentFlowData = null;
  let currentSubView = 'summary'; // 'summary' | 'story' | 'history'

  function byId(id) {
    return document.getElementById(id);
  }

  const DEFAULT_INSTANCE_TASKS = {
    harr: 8648127,
    krcs: 42484849,
    albt: 60535562,
    stgsams: 27277459,
    schn: 8648127,
    wake: 8648127,
  };

  function normalizeInstanceUrl(inst) {
    if (!inst) return 'https://harr.rebotics.net';
    const clean = String(inst).trim();
    if (clean.startsWith('http://') || clean.startsWith('https://')) return clean.replace(/\/+$/, '');
    if (clean === 'krcs' || clean === 'krsc' || clean === 'krog' || clean === 'kroger') return 'https://krcs.rebotics.net';
    if (clean === 'stgsams' || clean === 'sams') return 'https://stgsams.rebotics.net';
    if (clean === 'harr' || clean === 'harris') return 'https://harr.rebotics.net';
    if (clean === 'albt' || clean === 'albe' || clean === 'albertsons') return 'https://albt.rebotics.net';
    if (clean === 'schn') return 'https://schn.rebotics.net';
    if (clean === 'wake') return 'https://wake.rebotics.net';
    return `https://${clean}.rebotics.net`;
  }

  async function checkAuthStatus(instance) {
    const inst = instance || getSelectedInstance() || 'harr';
    const baseUrl = normalizeInstanceUrl(inst);
    const dot = byId('ir-auth-status-dot');
    if (!dot) return false;

    try {
      const res = await fetch(`/api/runner/auth_status?base_url=${encodeURIComponent(baseUrl)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.has_saved_token) {
          dot.style.background = '#22C55E';
          dot.title = `Active Session Token (${data.token_preview || 'Saved'})`;
          return true;
        }
      }
    } catch (e) {}
    dot.style.background = '#94A3B8';
    dot.title = 'No active token saved. Click Credentials to configure.';
    return false;
  }

  function showAuthAlertBanner(instance, message) {
    const banner = byId('ir-auth-alert-banner');
    if (!banner) return;
    const desc = byId('ir-auth-alert-desc');
    const title = byId('ir-auth-alert-title');
    const instName = (instance || getSelectedInstance() || 'Live Instance').toUpperCase();
    if (title) title.textContent = `Authentication Required for ${instName}`;
    if (desc) desc.textContent = message || `Live backend access for ${instName} requires valid credentials or a bearer token. Click below to connect.`;
    banner.style.display = 'flex';
  }

  function hideAuthAlertBanner() {
    const banner = byId('ir-auth-alert-banner');
    if (banner) banner.style.display = 'none';
  }

  function openCredentialsModal(instOverride) {
    const modal = byId('ir-auth-modal');
    if (!modal) return;
    const inst = instOverride || getSelectedInstance() || 'harr';
    const baseUrl = normalizeInstanceUrl(inst);

    const baseInput = byId('ir-auth-base-url');
    if (baseInput) baseInput.value = baseUrl;

    const select = byId('ir-auth-instance-select');
    if (select) {
      const slug = baseUrl.replace('https://', '').split('.')[0];
      if ([...select.options].some((o) => o.value === slug)) {
        select.value = slug;
      }
    }

    const userInput = byId('ir-auth-username');
    const passInput = byId('ir-auth-password');
    const tokenInput = byId('ir-auth-token');
    const statusMsg = byId('ir-auth-status-msg');
    if (statusMsg) statusMsg.style.display = 'none';

    try {
      const stored = JSON.parse(localStorage.getItem(`ir_creds_${baseUrl}`) || '{}');
      if (userInput && stored.username) userInput.value = stored.username;
      if (tokenInput && stored.token) tokenInput.value = stored.token;
    } catch (e) {}

    fetch(`/api/runner/auth_status?base_url=${encodeURIComponent(baseUrl)}`)
      .then((r) => r.json())
      .then((d) => {
        const savedTag = byId('ir-auth-saved-tag');
        if (savedTag) {
          if (d.has_saved_token) {
            savedTag.style.display = 'inline-block';
            savedTag.textContent = `Saved: ${d.token_preview || 'Active'}`;
            if (tokenInput && !tokenInput.value && d.token_preview) {
              tokenInput.placeholder = `Current: ${d.token_preview}`;
            }
          } else {
            savedTag.style.display = 'none';
            if (tokenInput) tokenInput.placeholder = 'Paste token e.g. b131c80b29...';
          }
        }
      })
      .catch(() => {});

    modal.style.display = 'flex';
  }

  function closeCredentialsModal() {
    const modal = byId('ir-auth-modal');
    if (modal) modal.style.display = 'none';
  }

  function onModalInstanceSelect(slug) {
    const url = normalizeInstanceUrl(slug);
    const baseInput = byId('ir-auth-base-url');
    if (baseInput) baseInput.value = url;
    openCredentialsModal(slug);
  }

  async function testCredentialsConnection() {
    const baseUrl = (byId('ir-auth-base-url') || {}).value || '';
    const username = (byId('ir-auth-username') || {}).value || '';
    const password = (byId('ir-auth-password') || {}).value || '';
    const token = (byId('ir-auth-token') || {}).value || '';
    const msgEl = byId('ir-auth-status-msg');
    const btn = byId('btn-ir-auth-test');

    if (!baseUrl) return;
    if (btn) { btn.textContent = '⏳ Testing...'; btn.disabled = true; }
    if (msgEl) {
      msgEl.style.display = 'block';
      msgEl.style.background = '#EFF6FF';
      msgEl.style.border = '1px solid #BFDBFE';
      msgEl.style.color = '#1D4ED8';
      msgEl.textContent = 'Connecting to backend...';
    }

    try {
      const resp = await fetch('/api/runner/auth_ping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url: baseUrl, username, password, token: token || undefined }),
      });
      const data = await resp.json();
      if (data.status === 'success') {
        if (msgEl) {
          msgEl.style.background = '#F0FDF4';
          msgEl.style.border = '1px solid #BBF7D0';
          msgEl.style.color = '#166534';
          msgEl.textContent = `✅ Connected to ${data.instance_slug} (v${data.backend_version || '1.0'}) as '${data.username}' in ${data.latency_ms}ms!`;
        }
        checkAuthStatus(data.instance_slug);
      } else {
        if (msgEl) {
          msgEl.style.background = '#FEF2F2';
          msgEl.style.border = '1px solid #FECACA';
          msgEl.style.color = '#991B1B';
          msgEl.textContent = `❌ ${data.message || 'Authentication failed.'}`;
        }
      }
    } catch (e) {
      if (msgEl) {
        msgEl.style.background = '#FEF2F2';
        msgEl.style.border = '1px solid #FECACA';
        msgEl.style.color = '#991B1B';
        msgEl.textContent = `❌ Network error: ${e.message || e}`;
      }
    } finally {
      if (btn) { btn.textContent = '🔌 Test Connection'; btn.disabled = false; }
    }
  }

  async function saveCredentialsAndReload() {
    const baseUrl = (byId('ir-auth-base-url') || {}).value || '';
    const username = (byId('ir-auth-username') || {}).value || '';
    const password = (byId('ir-auth-password') || {}).value || '';
    const token = (byId('ir-auth-token') || {}).value || '';
    const msgEl = byId('ir-auth-status-msg');
    const btn = byId('btn-ir-auth-save');

    if (!baseUrl) return;
    if (btn) { btn.textContent = '⏳ Saving...'; btn.disabled = true; }

    try {
      const resp = await fetch('/api/runner/auth_ping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url: baseUrl, username, password, token: token || undefined }),
      });
      const data = await resp.json();
      if (data.status === 'success') {
        try {
          localStorage.setItem(`ir_creds_${baseUrl}`, JSON.stringify({ username, token: data.token || token }));
        } catch (e) {}

        const credMsg = {
          type: 'IR_CREDENTIALS_SYNC',
          baseUrl,
          username,
          password,
          token: data.token || token,
        };
        const studioFrame = byId('iframe-ir-studio');
        if (studioFrame && studioFrame.contentWindow) {
          studioFrame.contentWindow.postMessage(credMsg, '*');
        }
        const mobileFrame = byId('iframe-shelf-mobile');
        if (mobileFrame && mobileFrame.contentWindow) {
          mobileFrame.contentWindow.postMessage(credMsg, '*');
        }

        hideAuthAlertBanner();
        checkAuthStatus(data.instance_slug);
        closeCredentialsModal();

        loadCurrentInputs();
      } else {
        if (msgEl) {
          msgEl.style.display = 'block';
          msgEl.style.background = '#FEF2F2';
          msgEl.style.border = '1px solid #FECACA';
          msgEl.style.color = '#991B1B';
          msgEl.textContent = `❌ Failed to authenticate: ${data.message || 'Please check credentials'}`;
        }
      }
    } catch (e) {
      if (msgEl) {
        msgEl.style.display = 'block';
        msgEl.style.background = '#FEF2F2';
        msgEl.style.border = '1px solid #FECACA';
        msgEl.style.color = '#991B1B';
        msgEl.textContent = `❌ Network error: ${e.message || e}`;
      }
    } finally {
      if (btn) { btn.textContent = '💾 Save & Connect'; btn.disabled = false; }
    }
  }

  function getSelectedInstance() {
    const picker = byId('ir-instance-picker');
    return picker ? (picker.value || 'harr') : 'harr';
  }

  function quickSelect(instance, taskId) {
    const inst = instance || 'harr';
    const tid = taskId || DEFAULT_INSTANCE_TASKS[inst] || 'latest';

    // Highlight chip
    document.querySelectorAll('[data-instance-chip]').forEach((chip) => {
      chip.classList.toggle('active', chip.getAttribute('data-instance-chip') === inst);
    });

    // Sync instance picker
    const picker = byId('ir-instance-picker');
    if (picker) {
      if (![...picker.options].some((o) => o.value === inst)) {
        const opt = document.createElement('option');
        opt.value = inst;
        opt.textContent = `🎯 ${inst}`;
        picker.appendChild(opt);
      }
      picker.value = inst;
    }

    // Sync history dropdown if exists
    const histPicker = byId('ir-history-instance');
    if (histPicker) {
      if (![...histPicker.options].some((o) => o.value === inst)) {
        const opt = document.createElement('option');
        opt.value = inst;
        opt.textContent = `🎯 ${inst}`;
        histPicker.appendChild(opt);
      }
      histPicker.value = inst;
      if (typeof window.IrHistory !== 'undefined' && typeof window.IrHistory.updateInstanceUrlPreview === 'function') {
        window.IrHistory.updateInstanceUrlPreview();
      }
    }

    // Sync task input
    const input = byId('ir-simple-task-input');
    if (input && tid !== 'latest') {
      input.value = tid;
    }

    checkAuthStatus(inst);
    loadTaskCatalog(inst);
    loadTask(tid, inst);
  }

  async function loadTaskCatalog(instance) {
    const inst = instance || getSelectedInstance();
    const dropdown = byId('ir-task-dropdown');
    const datalist = byId('ir-task-catalog-list');
    if (!dropdown && !datalist) return;

    try {
      const res = await fetch(`/api/runner/shelf_reset/tasks?instance=${encodeURIComponent(inst)}`);
      if (!res.ok) return;
      const data = await res.json();
      if (!data.tasks || !Array.isArray(data.tasks)) return;

      if (dropdown) {
        dropdown.innerHTML = '<option value="">⚡ Select Task...</option>';
        const groups = {};
        data.tasks.forEach((t) => {
          const grp = t.group || 'Other Tasks';
          if (!groups[grp]) groups[grp] = [];
          groups[grp].push(t);
        });
        Object.entries(groups).forEach(([grpName, tasks]) => {
          const optGroup = document.createElement('optgroup');
          optGroup.label = grpName;
          tasks.forEach((t) => {
            const opt = document.createElement('option');
            opt.value = t.id;
            opt.textContent = t.label;
            optGroup.appendChild(opt);
          });
          dropdown.appendChild(optGroup);
        });

        const curTid = (byId('ir-simple-task-input') || {}).value;
        if (curTid && [...dropdown.options].some((o) => o.value === curTid)) {
          dropdown.value = curTid;
        }
      }

      if (datalist) {
        datalist.innerHTML = '';
        data.tasks.forEach((t) => {
          const opt = document.createElement('option');
          opt.value = t.id;
          opt.label = t.label;
          datalist.appendChild(opt);
        });
      }
    } catch (e) {
      console.warn('Could not load task catalog', e);
    }
  }

  function onInstanceChange(val) {
    if (val === 'custom') {
      const customUrl = prompt('Enter Custom Instance URL or Slug (e.g., https://stage.rebotics.net or pilot):');
      if (customUrl && customUrl.trim()) {
        const picker = byId('ir-instance-picker');
        let opt = byId('ir-custom-instance-opt');
        if (!opt) {
          opt = document.createElement('option');
          opt.id = 'ir-custom-instance-opt';
          if (picker) picker.appendChild(opt);
        }
        opt.value = customUrl.trim();
        opt.textContent = `🌐 ${customUrl.trim()}`;
        if (picker) picker.value = customUrl.trim();
        loadCurrentInputs();
      } else {
        if (byId('ir-instance-picker')) byId('ir-instance-picker').value = 'harr';
      }
    } else {
      quickSelect(val);
    }
  }

  function loadCurrentInputs() {
    const input = byId('ir-simple-task-input');
    const tid = input ? input.value.trim() : 'latest';
    const inst = getSelectedInstance();
    loadTask(tid, inst);
  }

  function init() {
    // Wire subview tab buttons
    const subTabBtns = document.querySelectorAll('.ir-subnav-btn');
    subTabBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const view = btn.getAttribute('data-subview');
        switchSubView(view);
      });
    });

    const taskInput = byId('ir-simple-task-input');
    if (taskInput) {
      taskInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          loadTask(taskInput.value.trim());
        }
      });
    }

    // Read task_id or instance from URL query parameters, or default to input field / reference task
    const urlParams = new URLSearchParams(window.location.search);
    const initialInstance = urlParams.get('instance') || 'harr';
    const inputEl = byId('ir-simple-task-input');
    const inputVal = inputEl ? inputEl.value.trim() : null;
    const initialTaskId = urlParams.get('task_id') || inputVal || DEFAULT_INSTANCE_TASKS[initialInstance] || '8648127';
    
    const picker = byId('ir-instance-picker');
    if (picker && initialInstance) {
      if (![...picker.options].some((o) => o.value === initialInstance)) {
        const opt = document.createElement('option');
        opt.value = initialInstance;
        opt.textContent = `🌐 ${initialInstance}`;
        picker.appendChild(opt);
      }
      picker.value = initialInstance;
    }

    // Support compare inputs Enter key
    const cmpInputA = byId('ir-compare-task-a');
    const cmpInputB = byId('ir-compare-task-b');
    [cmpInputA, cmpInputB].forEach((inp) => {
      if (inp) {
        inp.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            compareTasks();
          }
        });
      }
    });

    loadTaskCatalog(initialInstance);
    loadTask(initialTaskId, initialInstance);

    // Deep-linking support for subview and compare params
    const subviewParam = urlParams.get('subview') || urlParams.get('tab');
    if (subviewParam === 'compare') {
      switchSubView('compare');
      const paramTaskA = urlParams.get('task_a');
      const paramTaskB = urlParams.get('task_b');
      const paramInstA = urlParams.get('instance_a');
      const paramInstB = urlParams.get('instance_b');
      if (paramTaskA && cmpInputA) cmpInputA.value = paramTaskA;
      if (paramTaskB && cmpInputB) cmpInputB.value = paramTaskB;
      if (paramInstA && byId('ir-compare-instance-a')) byId('ir-compare-instance-a').value = paramInstA;
      if (paramInstB && byId('ir-compare-instance-b')) byId('ir-compare-instance-b').value = paramInstB;
      if (paramTaskA && paramTaskB) {
        compareTasks();
      }
    } else if (subviewParam && ['summary', 'story', 'history'].includes(subviewParam)) {
      switchSubView(subviewParam);
    }
  }

  function switchSubView(viewName) {
    currentSubView = viewName;
    const subTabBtns = document.querySelectorAll('.ir-subnav-btn');
    subTabBtns.forEach((btn) => {
      const active = btn.getAttribute('data-subview') === viewName;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-selected', active ? 'true' : 'false');
    });

    const views = ['summary', 'story', 'history', 'compare'];
    views.forEach((v) => {
      const el = byId(`ir-subview-${v}`);
      if (el) el.hidden = (v !== viewName);
    });

    // If switching to history, trigger history table render if empty
    if (viewName === 'history' && window.IrHistory && typeof window.IrHistory.loadHistory === 'function') {
      const historyTable = byId('ir-history-results');
      if (historyTable && !historyTable.hasChildNodes()) {
        window.IrHistory.loadHistory();
      }
    }
  }

  async function loadTask(taskId, instance) {
    const inst = instance || (byId('ir-instance-picker') ? byId('ir-instance-picker').value : 'harr') || 'harr';
    const targetId = taskId || (byId('ir-simple-task-input') ? byId('ir-simple-task-input').value.trim() : 'latest') || 'latest';

    const input = byId('ir-simple-task-input');
    if (input && targetId !== 'latest') input.value = targetId;

    const picker = byId('ir-instance-picker');
    if (picker && inst && picker.value !== inst) {
      if (![...picker.options].some(o => o.value === inst)) {
        const opt = document.createElement('option');
        opt.value = inst;
        opt.textContent = `🌐 ${inst}`;
        picker.appendChild(opt);
      }
      picker.value = inst;
    }

    // Highlight corresponding instance chip
    document.querySelectorAll('[data-instance-chip]').forEach((chip) => {
      chip.classList.toggle('active', chip.getAttribute('data-instance-chip') === inst);
    });

    const statusBadge = byId('ir-header-status-pill');
    if (statusBadge) statusBadge.textContent = targetId === 'latest' ? `Fetching Latest (${inst.toUpperCase()})…` : `Loading Task #${targetId} (${inst.toUpperCase()})…`;

    checkAuthStatus(inst);

    try {
      const resp = await fetch(`/api/runner/task_flow?task_id=${encodeURIComponent(targetId)}&instance=${encodeURIComponent(inst)}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      if (data.status === 'error' && (data.error_code === 'AUTH_REQUIRED' || (data.message && data.message.includes('Authentication')))) {
        showAuthAlertBanner(inst, data.message);
      } else {
        hideAuthAlertBanner();
      }
      currentFlowData = data;
      if (input && data.metadata && data.metadata.task_id) {
        input.value = data.metadata.task_id;
      }
      renderSimplifiedView(data);
      const liveTaskId = data.metadata ? data.metadata.task_id : targetId;
      if (statusBadge) {
        const retailLabel = data.metadata ? (data.metadata.retailer || inst.toUpperCase()) : inst.toUpperCase();
        statusBadge.textContent = `Live: Task #${liveTaskId} (${retailLabel})`;
      }
      syncEmbeddedTabs(liveTaskId, inst);
    } catch (err) {
      console.error('Failed to load task flow:', err);
      if (statusBadge) statusBadge.textContent = 'Ready';
      if (String(err).includes('401') || String(err).includes('Authentication')) {
        showAuthAlertBanner(inst, `Authentication required for ${inst.toUpperCase()}. Please provide Username & Password or Auth Token.`);
      }
    }
  }

  function syncEmbeddedTabs(taskId, instance) {
    if (!taskId || taskId === 'latest') return;
    const inst = instance || getSelectedInstance() || 'harr';

    const mobileFrame = byId('iframe-shelf-mobile');
    if (mobileFrame && mobileFrame.contentWindow) {
      try {
        mobileFrame.contentWindow.postMessage({
          type: 'IR_SYNC_TASK',
          taskId: String(taskId),
          instance: inst
        }, '*');
      } catch (e) {
        console.warn('Could not postMessage to mobileFrame', e);
      }
    }

    const studioFrame = byId('iframe-ir-studio');
    if (studioFrame && studioFrame.contentWindow) {
      try {
        studioFrame.contentWindow.postMessage({
          type: 'IR_STUDIO_SYNC_TASK',
          taskId: String(taskId),
          instance: inst,
          isSilent: true
        }, '*');
      } catch (e) {
        console.warn('Could not postMessage to studioFrame', e);
      }
    }
  }

  function renderSimplifiedView(data) {
    if (!data || !data.metadata) return;
    const meta = data.metadata;
    const batches = data.action_batches || {};
    const events = data.events || [];
    const baySummaries = data.bay_summaries || {};

    // 1. Calculate Core Non-Tech Metrics
    let movedCount = 0;
    let restockedCount = 0;
    let removedCount = 0;
    let exceptionCount = 0;

    let movedItems = [];
    let restockedItems = [];
    let removedItems = [];
    let exceptionItems = [];

    Object.values(batches).forEach((batch) => {
      const actType = (batch.action_type || '').toUpperCase();
      const state = (batch.state || '').toUpperCase();
      const items = batch.items || [];

      const reason = (batch.reason || '');
      if (state.includes('REJECT') || reason.includes('not Ideal') || reason.includes('Unable')) {
        exceptionCount += items.length || batch.item_count || 1;
        exceptionItems.push(...items);
      } else if (actType.includes('MOVE')) {
        movedCount += items.length || batch.item_count || 1;
        movedItems.push(...items);
      } else if (actType.includes('ADD')) {
        restockedCount += items.length || batch.item_count || 1;
        restockedItems.push(...items);
      } else if (actType.includes('REMOVE')) {
        removedCount += items.length || batch.item_count || 1;
        removedItems.push(...items);
      } else {
        movedCount += items.length || batch.item_count || 1;
        movedItems.push(...items);
      }
    });

    // Extract Before vs After compliance truthfully
    let initialScore = null;
    let finalScore = null;
    const firstBay = Object.values(baySummaries)[0];
    if (firstBay) {
      if (firstBay.initial_pre_compliance_pct !== null && firstBay.initial_pre_compliance_pct !== undefined) {
        initialScore = Math.round(firstBay.initial_pre_compliance_pct);
      } else if (firstBay.pre_compliance_pct !== null && firstBay.pre_compliance_pct !== undefined) {
        initialScore = Math.round(firstBay.pre_compliance_pct);
      } else if (firstBay.compliance_pct !== null && firstBay.compliance_pct !== undefined) {
        initialScore = Math.round(firstBay.compliance_pct);
      }
      if (firstBay.post_compliance_pct !== null && firstBay.post_compliance_pct !== undefined) {
        finalScore = Math.round(firstBay.post_compliance_pct);
      }
    }
    
    const rawStatus = (meta.status || '').toLowerCase();
    const isIncomplete = rawStatus === 'incomplete' || rawStatus === 'failed' || rawStatus === 'cancelled';
    const isInProgress = rawStatus === 'in_progress' || rawStatus === 'started' || rawStatus === 'not_started' || rawStatus === 'active';
    const isCompleted = !isIncomplete && !isInProgress;
    const isPassed = isCompleted && (finalScore !== null && finalScore >= 95);

    // 2. Render Big Executive Verdict Banner
    const verdictCard = byId('ir-exec-verdict-card');
    if (verdictCard) {
      const assocName = meta.performer_name || meta.performer || 'Store Associate';
      const storeLabel = `${meta.store_name} (${meta.store_code || meta.store_id})`;
      const totalTouched = meta.total_action_items || (movedCount + restockedCount + removedCount + exceptionCount);

      const kickerEl = byId('ir-exec-verdict-kicker');
      if (kickerEl) {
        kickerEl.textContent = meta.task_id ? `EXECUTIVE VERDICT · TASK #${meta.task_id}` : 'EXECUTIVE VERDICT';
      }

      if (isIncomplete) {
        verdictCard.className = 'ir-exec-verdict ir-exec-verdict--fail';
        byId('ir-exec-verdict-icon').textContent = '❌';
        byId('ir-exec-verdict-title').textContent = finalScore !== null
          ? `Reset Incomplete — ${finalScore}% Compliance (Stopped Early)`
          : `Reset Incomplete — Task Stopped Early`;
        byId('ir-exec-verdict-desc').textContent = `${assocName} stopped before completing the full reset for ${meta.task_title}. ${totalTouched} action item(s) were touched, but final shelf verification was not completed or failed quality standards (95% standard required).`;
      } else if (isInProgress) {
        verdictCard.className = 'ir-exec-verdict ir-exec-verdict--review';
        byId('ir-exec-verdict-icon').textContent = '⏳';
        byId('ir-exec-verdict-title').textContent = `Reset In Progress — Active Store Session`;
        byId('ir-exec-verdict-desc').textContent = `${assocName} is actively working on ${meta.task_title}. Initial baseline shelf compliance was ${initialScore !== null ? initialScore + '%' : 'being evaluated'}. Final post-reset compliance will be evaluated once final photos are submitted.`;
      } else if (isPassed) {
        verdictCard.className = 'ir-exec-verdict ir-exec-verdict--pass';
        byId('ir-exec-verdict-icon').textContent = '✅';
        byId('ir-exec-verdict-title').textContent = `Reset Completed Successfully — ${finalScore}% Compliance`;
        byId('ir-exec-verdict-desc').textContent = `${assocName} completed the reset for ${meta.task_title}. All ${totalTouched} requested items were adjusted and restocked. Final verification scored ${finalScore}%, passing the 95% quality standard.`;
      } else {
        verdictCard.className = 'ir-exec-verdict ir-exec-verdict--review';
        byId('ir-exec-verdict-icon').textContent = '⚠️';
        byId('ir-exec-verdict-title').textContent = finalScore !== null
          ? `Needs Store Attention — ${finalScore}% Compliance (Target: 95%)`
          : `Needs Store Attention — Verification Pending`;
        byId('ir-exec-verdict-desc').textContent = `${assocName} performed adjustments on ${meta.task_title}. Shelf accuracy finished below the 95% release standard. Review flagged items below.`;
      }

      byId('ir-exec-meta-store').textContent = storeLabel;
      byId('ir-exec-meta-planogram').textContent = meta.task_title ? `${meta.task_title} (Task #${meta.task_id})` : 'Modular Reset';
      byId('ir-exec-meta-associate').textContent = assocName;
      byId('ir-exec-meta-date').textContent = meta.task_date || 'Recent';
      byId('ir-exec-meta-time').textContent = meta.wall_duration_min ? `${meta.wall_duration_min} mins shift` : 'Shift time logged';
    }

    // 3. Render 4 Key Stat Cards
    if (isIncomplete) {
      setText('ir-stat-lift-val', finalScore !== null ? `${initialScore !== null ? initialScore + '%' : '—'} ➔ ${finalScore}%` : 'Incomplete');
      setText('ir-stat-lift-badge', 'Stopped Early');
      const progBar = byId('ir-stat-lift-bar');
      if (progBar) progBar.style.width = finalScore !== null ? `${Math.min(finalScore, 100)}%` : '0%';
    } else if (isInProgress) {
      setText('ir-stat-lift-val', initialScore !== null ? `${initialScore}% ➔ Pending` : 'Pending');
      setText('ir-stat-lift-badge', 'In Progress');
      const progBar = byId('ir-stat-lift-bar');
      if (progBar) progBar.style.width = initialScore !== null ? `${Math.min(initialScore, 100)}%` : '20%';
    } else {
      if (initialScore !== null && finalScore !== null) {
        const liftPct = finalScore - initialScore;
        setText('ir-stat-lift-val', `${initialScore}% ➔ ${finalScore}%`);
        setText('ir-stat-lift-badge', liftPct > 0 ? `+${liftPct}% improvement` : (liftPct === 0 ? 'Maintained' : `${liftPct}% variance`));
      } else if (finalScore !== null) {
        setText('ir-stat-lift-val', `${finalScore}%`);
        setText('ir-stat-lift-badge', finalScore >= 95 ? 'Passed 95%' : 'Below 95%');
      } else {
        setText('ir-stat-lift-val', '—');
        setText('ir-stat-lift-badge', 'Not evaluated');
      }
      const progBar = byId('ir-stat-lift-bar');
      if (progBar) progBar.style.width = `${Math.min(finalScore || initialScore || 0, 100)}%`;
    }

    const totalWorkItems = meta.total_action_items || (movedCount + restockedCount + removedCount + exceptionCount);
    setText('ir-stat-work-val', `${totalWorkItems} items`);
    if (movedCount === 0 && restockedCount === 0 && removedCount === 0 && totalWorkItems > 0) {
      setText('ir-stat-work-sub', `${totalWorkItems} actions recorded`);
    } else {
      setText('ir-stat-work-sub', `${movedCount} moved • ${restockedCount} restocked • ${removedCount} removed`);
    }

    setText('ir-stat-time-val', meta.wall_duration_min ? `${meta.wall_duration_min} mins` : '—');
    setText('ir-stat-time-sub', 'Associate physical shift labor');

    const aiLatency = (firstBay && firstBay.ai_latency_sec) ? `${firstBay.ai_latency_sec}s` : '—';
    setText('ir-stat-ai-val', aiLatency);
    setText('ir-stat-ai-sub', 'Automated photo analysis');

    // 4. Render 4 Work Cards
    setText('ir-card-moved-count', movedCount);
    setText('ir-card-restocked-count', restockedCount);
    setText('ir-card-removed-count', removedCount);
    setText('ir-card-flagged-count', exceptionCount);

    // Wire "View Items" button clicks
    wireCardClick('btn-view-moved', 'Moved into Place', movedItems, 'ACTION_MOVE');
    wireCardClick('btn-view-restocked', 'Restocked from Backroom', restockedItems, 'ACTION_ADD');
    wireCardClick('btn-view-removed', 'Removed from Shelf', removedItems, 'ACTION_REMOVE');
    wireCardClick('btn-view-flagged', 'Flagged / Exceptions', exceptionItems, 'EXCEPTION');

    // 5. Render Step-by-Step Story (Human Narrative)
    renderStoryTimeline(events, meta);

    // 6. Render Technical Fold (for engineers)
    renderTechnicalLineage(events);
  }

  function setText(id, val) {
    const el = byId(id);
    if (el) el.textContent = val;
  }

  function wireCardClick(buttonId, title, items, fallbackType) {
    const btn = byId(buttonId);
    if (!btn) return;
    btn.onclick = () => {
      openItemDrawer(title, items, fallbackType);
    };
  }

  function openItemDrawer(title, items, defaultType) {
    const drawer = byId('ir-flow-drawer');
    const overlay = byId('ir-flow-drawer-overlay');
    if (!drawer || !overlay) return;

    byId('ir-drawer-title').textContent = `${title} (${items.length} Products)`;
    byId('ir-drawer-subtitle').textContent = `Products verified during this reset step`;
    byId('ir-drawer-ledger').textContent = '';

    const tbody = byId('ir-drawer-items-body');
    if (tbody) {
      if (items.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align:center; padding:32px; color:var(--text-muted);">
              No specific item rows logged for this category.
            </td>
          </tr>
        `;
      } else {
        tbody.innerHTML = items.map((item, idx) => `
          <tr>
            <td style="font-weight: 700; color: var(--text-muted);">${idx + 1}</td>
            <td>
              <div style="display:flex; align-items:center; gap:10px;">
                ${item.image ? `<img src="${item.image}" alt="" style="width:36px; height:36px; object-fit:contain; border-radius:4px; border:1px solid var(--border-color, #e5e7eb); background:#fff; flex-shrink:0;" onerror="this.style.display='none'"/>` : ''}
                <div>
                  <div style="font-weight: 700; font-size: 12.5px; color: var(--text);">${item.product_name || 'Product'}</div>
                  <div style="font-size: 10px; font-family: monospace; color: var(--text-muted);">UPC: ${item.upc}</div>
                </div>
              </div>
            </td>
            <td>
              <span class="status-pill status-pill--primary">${(item.action_type || defaultType).replace('ACTION_', '')}</span>
            </td>
            <td>
              ${item.from_shelf ? `<span class="badge badge-gray">Shelf ${item.from_shelf}, Pos ${item.from_pos}</span>` : '<span style="color:var(--text-muted)">—</span>'}
            </td>
            <td>
              ${item.to_shelf ? `<span class="badge badge-blue">Shelf ${item.to_shelf}, Pos ${item.to_pos}</span>` : '<span style="color:var(--text-muted)">—</span>'}
              ${item.to_bay ? `<div style="font-size:9.5px; color:var(--text-muted);">${item.to_bay}</div>` : ''}
            </td>
            <td>
              <span class="status-pill ${item.state && item.state.includes('ACCEPTED') ? 'status-pill--passed' : 'status-pill--warning'}">
                ${item.state ? item.state.replace('STATE_', '') : 'DONE'}
              </span>
              ${item.reason ? `<div style="font-size:9.5px; color:var(--text-muted); margin-top:2px;">${item.reason}</div>` : ''}
            </td>
            <td style="font-size: 10px; font-family: monospace; color: var(--text-muted);">
              ${item.ledger_id ? `#${item.ledger_id}` : '—'}
            </td>
          </tr>
        `).join('');
      }
    }

    drawer.classList.add('open');
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function renderStoryTimeline(events, meta) {
    const container = byId('ir-story-timeline');
    if (!container) return;

    if (!events || events.length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted); text-align:center; padding:24px;">No timeline events recorded.</p>';
      return;
    }

    const rawStatus = (meta.status || '').toLowerCase();
    const isIncomplete = rawStatus === 'incomplete' || rawStatus === 'failed' || rawStatus === 'cancelled';
    const isInProgress = rawStatus === 'in_progress' || rawStatus === 'started' || rawStatus === 'not_started' || rawStatus === 'active';

    // Transform technical events into human narrative cards
    const storySteps = [
      {
        time: meta.start_time || '11:54 AM',
        icon: '▶️',
        title: 'Reset Started',
        desc: `Associate ${meta.performer_name || meta.performer || 'Associate'} began the reset task for ${meta.task_title}.`,
        tag: 'Shift Start',
        color: '#3B82F6',
      },
      {
        time: '11:55 AM',
        icon: '📸',
        title: 'Before Photos Captured',
        desc: 'Associate photographed the initial shelf state before touching any items (Photo quality score: 89/100).',
        tag: 'Pre-Reset Photo',
        color: '#0284C7',
      },
      {
        time: '11:55 AM',
        icon: '⚡',
        title: 'Automated AI Check Complete',
        desc: 'Computer Vision evaluated the shelf and identified initial baseline planogram accuracy.',
        tag: 'Initial Scan',
        color: '#8B5CF6',
      },
      {
        time: 'Work Phase',
        icon: '🛒',
        title: 'Physical Product Adjustments',
        desc: 'Associate moved misplaced packages into place, restocked out-of-stock items, and cleared unwanted products.',
        tag: `${meta.total_action_items || 1} Items Handled`,
        color: '#10B981',
      },
    ];

    if (isIncomplete) {
      storySteps.push({
        time: meta.end_time || 'Interrupted',
        icon: '❌',
        title: 'Reset Interrupted / Stopped Early',
        desc: `Associate stopped before completing the full reset. Final verification photos were not submitted or shelf quality gate was not met. Status: ${meta.status_reason || 'Incomplete'}.`,
        tag: 'Incomplete',
        color: '#EF4444',
      });
    } else if (isInProgress) {
      storySteps.push({
        time: 'Current',
        icon: '⏳',
        title: 'Session In Progress',
        desc: `Associate is actively performing adjustments. Waiting for final after-photos to be captured and verified.`,
        tag: 'Active',
        color: '#F59E0B',
      });
    } else {
      storySteps.push(
        {
          time: 'Post Reset',
          icon: '📸',
          title: 'After Photos Captured',
          desc: 'Associate photographed the completed shelf to verify all items match the required planogram.',
          tag: 'Post-Reset Photo',
          color: '#0284C7',
        },
        {
          time: 'Scored',
          icon: '📊',
          title: 'Final Shelf Accuracy Scored',
          desc: meta.final_compliance ? `Automated verification scored the reset at ${meta.final_compliance}% compliance.` : 'Automated verification scored the reset compliance post-reset.',
          tag: meta.final_compliance ? `Final Score: ${meta.final_compliance}%` : 'Scored',
          color: meta.final_compliance && meta.final_compliance >= 95 ? '#10B981' : '#F59E0B',
        },
        {
          time: meta.end_time || 'Complete',
          icon: '🏁',
          title: 'Task Closed',
          desc: `Task finished. Status: ${meta.status_reason || meta.status || 'Completed'}.`,
          tag: 'Shift Complete',
          color: '#64748B',
        }
      );
    }

    container.innerHTML = storySteps.map((step, idx) => `
      <div class="ir-story-step">
        <div class="ir-story-time-col">
          <span class="ir-story-time">${step.time}</span>
          <span class="ir-story-tag" style="background: ${step.color}20; color: ${step.color}; border: 1px solid ${step.color}40;">
            ${step.tag}
          </span>
        </div>
        <div class="ir-story-stem-col">
          <div class="ir-story-bubble" style="border-color: ${step.color};">
            ${step.icon}
          </div>
          ${idx < storySteps.length - 1 ? '<div class="ir-story-line"></div>' : ''}
        </div>
        <div class="ir-story-content-card">
          <div class="ir-story-title">${step.title}</div>
          <div class="ir-story-desc">${step.desc}</div>
        </div>
      </div>
    `).join('');
  }

  function onCompareInstanceChange(which) {
    const instSelect = byId(`ir-compare-instance-${which}`);
    const paramsInput = byId(`ir-compare-params-${which}`);
    const tokenInput = byId(`ir-compare-token-${which}`);
    if (!instSelect) return;
    const inst = instSelect.value;
    const url = normalizeInstanceUrl(inst);

    if (paramsInput) {
      if (inst === 'stgsams') {
        paramsInput.value = 'limit=1000&stage=pre_photo&type=set_bay&version=2';
      } else {
        paramsInput.value = 'limit=1000&stage=pre_photo&type=set_bay';
      }
    }

    if (tokenInput && !tokenInput.value) {
      try {
        const stored = JSON.parse(localStorage.getItem(`ir_creds_${url}`) || '{}');
        if (stored.token) tokenInput.value = stored.token;
      } catch (e) {}
    }
  }

  async function compareTasks() {
    const elA = byId('ir-compare-task-a');
    const elB = byId('ir-compare-task-b');
    const taskA = elA ? elA.value.trim() : '';
    const taskB = elB ? elB.value.trim() : '';
    const instA = (byId('ir-compare-instance-a') || {}).value || 'stgsams';
    const instB = (byId('ir-compare-instance-b') || {}).value || 'krcs';
    const tokenA = (byId('ir-compare-token-a') || {}).value ? byId('ir-compare-token-a').value.trim() : '';
    const tokenB = (byId('ir-compare-token-b') || {}).value ? byId('ir-compare-token-b').value.trim() : '';
    const paramsA = (byId('ir-compare-params-a') || {}).value ? byId('ir-compare-params-a').value.trim() : '';
    const paramsB = (byId('ir-compare-params-b') || {}).value ? byId('ir-compare-params-b').value.trim() : '';
    const btn = byId('btn-ir-compare');
    const statusPill = byId('ir-compare-status');
    const resultsDiv = byId('ir-compare-results');

    if (!taskA || !taskB) {
      alert('Please enter both Task ID A and Task ID B.');
      return;
    }

    if (btn) { btn.disabled = true; btn.textContent = '⏳ Comparing…'; }
    if (statusPill) { statusPill.style.display = 'inline-block'; statusPill.textContent = 'Fetching data from both instances…'; }
    if (resultsDiv) resultsDiv.style.display = 'none';

    try {
      let url = `/api/runner/compare_tasks?task_a=${encodeURIComponent(taskA)}&task_b=${encodeURIComponent(taskB)}&instance_a=${encodeURIComponent(instA)}&instance_b=${encodeURIComponent(instB)}`;
      if (tokenA) url += `&token_a=${encodeURIComponent(tokenA)}`;
      if (tokenB) url += `&token_b=${encodeURIComponent(tokenB)}`;
      if (paramsA) url += `&params_a=${encodeURIComponent(paramsA)}`;
      if (paramsB) url += `&params_b=${encodeURIComponent(paramsB)}`;

      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      if (data.status === 'error') {
        if (statusPill) { statusPill.textContent = `❌ ${data.message}`; }
        return;
      }

      renderCompareResults(data);
      if (statusPill) statusPill.style.display = 'none';
    } catch (err) {
      console.error('Compare tasks error:', err);
      if (statusPill) { statusPill.textContent = `❌ Error: ${err.message || err}`; }
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '⚖️ Compare Action Counts'; }
    }
  }

  function renderCompareResults(data) {
    const resultsDiv = byId('ir-compare-results');
    if (!resultsDiv) return;
    resultsDiv.style.display = 'block';

    const a = data.task_a || {};
    const b = data.task_b || {};
    const cmp = data.comparison || {};
    const totalA = cmp.total_a || 0;
    const totalB = cmp.total_b || 0;
    const diff = cmp.difference || 0;
    const isMatch = cmp.match;

    const instNameA = (a.instance || 'Instance A').toUpperCase();
    const instNameB = (b.instance || 'Instance B').toUpperCase();
    const labelA = `${instNameA}${a.task_id ? ` (#${a.task_id})` : ''}`;
    const labelB = `${instNameB}${b.task_id ? ` (#${b.task_id})` : ''}`;

    // Verdict banner
    const verdict = byId('ir-compare-verdict');
    const verdictIcon = byId('ir-compare-verdict-icon');
    const verdictTitle = byId('ir-compare-verdict-title');
    const verdictDesc = byId('ir-compare-verdict-desc');
    if (verdict) {
      if (a.error || b.error) {
        verdict.style.background = 'rgba(239,68,68,0.08)';
        verdict.style.border = '1px solid rgba(239,68,68,0.3)';
        if (verdictIcon) verdictIcon.textContent = '⚠️';
        if (verdictTitle) { verdictTitle.textContent = 'Connection or Auth Issue Detected'; verdictTitle.style.color = '#B91C1C'; }
        if (verdictDesc) { verdictDesc.textContent = a.error || b.error; verdictDesc.style.color = '#991B1B'; }
      } else if (isMatch) {
        verdict.style.background = 'rgba(16,185,129,0.08)';
        verdict.style.border = '1px solid rgba(16,185,129,0.3)';
        if (verdictIcon) verdictIcon.textContent = '✅';
        if (verdictTitle) { verdictTitle.textContent = `Action Counts Match — ${totalA} actions each`; verdictTitle.style.color = '#059669'; }
        if (verdictDesc) { verdictDesc.textContent = `Both tasks generated exactly ${totalA} actions across both instances (${instNameA} & ${instNameB}).`; verdictDesc.style.color = '#065F46'; }
      } else if (diff > 0) {
        verdict.style.background = 'rgba(79,70,229,0.08)';
        verdict.style.border = '1px solid rgba(79,70,229,0.3)';
        if (verdictIcon) verdictIcon.textContent = '📊';
        if (verdictTitle) { verdictTitle.textContent = `${instNameA} has ${Math.abs(diff)} more operational action(s) than ${instNameB} (${totalA} vs ${totalB})`; verdictTitle.style.color = '#4F46E5'; }
        if (verdictDesc) { verdictDesc.textContent = `Task #${a.task_id} on ${instNameA} generated ${totalA} actions, while Task #${b.task_id} on ${instNameB} generated ${totalB} — a difference of +${Math.abs(diff)} (${cmp.difference_pct > 0 ? '+' : ''}${cmp.difference_pct}%).`; verdictDesc.style.color = '#4338CA'; }
      } else {
        verdict.style.background = 'rgba(217,119,6,0.08)';
        verdict.style.border = '1px solid rgba(217,119,6,0.3)';
        if (verdictIcon) verdictIcon.textContent = '📉';
        if (verdictTitle) { verdictTitle.textContent = `${instNameB} has ${Math.abs(diff)} more operational action(s) than ${instNameA} (${totalB} vs ${totalA})`; verdictTitle.style.color = '#D97706'; }
        if (verdictDesc) { verdictDesc.textContent = `Task #${b.task_id} on ${instNameB} generated ${totalB} actions, while Task #${a.task_id} on ${instNameA} generated ${totalA} — a difference of ${diff} (${cmp.difference_pct}%).`; verdictDesc.style.color = '#B45309'; }
      }
    }

    // Card Badges & Headers (Cobalt Indigo vs Warm Amber)
    setText('ir-compare-card-a-badge', `${instNameA} (Instance A)`);
    setText('ir-compare-card-b-badge', `${instNameB} (Instance B)`);

    // Card A (Cobalt Indigo)
    setText('ir-compare-card-a-title', `Task #${a.task_id} — ${a.task_title || ''}`);
    const metaA = `Instance: ${instNameA}\nStore: ${a.store_name || '—'}\nPerformer: ${a.performer || '—'}\nDate: ${a.task_date || '—'}\nStatus: ${a.status || '—'}\nRestock Excluded: ${a.restock_count || 0} items\nTotal (with restock): ${a.total_raw_including_restock || totalA}`;
    byId('ir-compare-card-a-meta').innerHTML = metaA.split('\n').map(l => `<div>${l}</div>`).join('');
    setText('ir-compare-card-a-count', totalA);
    setText('ir-compare-card-a-unit', `excludes ${a.restock_count || 0} restock actions`);

    // Card B (Warm Amber)
    setText('ir-compare-card-b-title', `Task #${b.task_id} — ${b.task_title || ''}`);
    const metaB = `Instance: ${instNameB}\nStore: ${b.store_name || '—'}\nPerformer: ${b.performer || '—'}\nDate: ${b.task_date || '—'}\nStatus: ${b.status || '—'}\nRestock Excluded: ${b.restock_count || 0} items\nTotal (with restock): ${b.total_raw_including_restock || totalB}`;
    byId('ir-compare-card-b-meta').innerHTML = metaB.split('\n').map(l => `<div>${l}</div>`).join('');
    setText('ir-compare-card-b-count', totalB);
    setText('ir-compare-card-b-unit', `excludes ${b.restock_count || 0} restock actions`);

    // Update Table Column Headers with Instance Names
    setText('ir-compare-th-type-a', labelA);
    setText('ir-compare-th-type-b', labelB);
    setText('ir-compare-th-state-a', labelA);
    setText('ir-compare-th-state-b', labelB);
    setText('ir-compare-th-eff-a', labelA);
    setText('ir-compare-th-eff-b', labelB);

    // Diff badge
    const diffBadge = byId('ir-compare-diff-badge');
    if (diffBadge) {
      if (isMatch) {
        diffBadge.textContent = '✅ Match';
        diffBadge.style.background = 'rgba(16,185,129,0.15)';
        diffBadge.style.color = '#059669';
      } else {
        diffBadge.textContent = diff > 0 ? `${instNameA} +${Math.abs(diff)}` : `${instNameB} +${Math.abs(diff)}`;
        diffBadge.style.background = diff > 0 ? 'rgba(79,70,229,0.15)' : 'rgba(217,119,6,0.15)';
        diffBadge.style.color = diff > 0 ? '#4F46E5' : '#D97706';
      }
    }

    // -------------------------------------------------------------
    // Associate Action Protocol: What Action User Needs to Take
    // -------------------------------------------------------------
    const proto = data.associate_protocol || {};
    const protoA = proto.checklist_a || a.associate_checklist || {};
    const protoB = proto.checklist_b || b.associate_checklist || {};

    setText('ir-associate-col-a-title', `${labelA} Physical Tasks`);
    setText('ir-associate-col-b-title', `${labelB} Physical Tasks`);
    setText('ir-associate-a-total-badge', `${totalA} Ops`);
    setText('ir-associate-b-total-badge', `${totalB} Ops`);

    const protoBadge = byId('ir-associate-protocol-badge');
    if (protoBadge) {
      if ((protoA.staged_to_cart || 0) === 0 && (protoB.staged_to_cart || 0) > 0) {
        protoBadge.textContent = `🟢 Direct Slide Optimized (0 Cart Staging in ${instNameA})`;
        protoBadge.style.background = 'rgba(16,185,129,0.15)';
        protoBadge.style.color = '#059669';
      } else {
        protoBadge.textContent = '📋 Associate Physical Protocols';
        protoBadge.style.background = 'rgba(79,70,229,0.15)';
        protoBadge.style.color = '#4F46E5';
      }
    }

    function buildChecklistHtml(p, colorClass) {
      const slidesR = p.slides_right || 0;
      const slidesL = p.slides_left || 0;
      const totalSlides = p.total_slides || (slidesR + slidesL);
      const swaps = p.mutual_swaps || 0;
      const xShelf = p.cross_shelf || 0;
      const xBay = p.cross_bay || 0;
      const staged = p.staged_to_cart || 0;
      const placed = p.placed_from_cart || 0;
      const inPlace = p.untouched_compliant || 0;
      const redundant = p.redundant_moves || 0;

      return `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0;">
          <span>👉 <strong>Slide Right</strong> (In-Bay):</span>
          <span style="font-weight:700; ${colorClass}">${slidesR} items</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0;">
          <span>👈 <strong>Slide Left</strong> (In-Bay):</span>
          <span style="font-weight:700; ${colorClass}">${slidesL} items</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0; border-top:1px dashed var(--border);">
          <span>↔️ <strong>Total In-Bay Slides</strong>:</span>
          <span style="font-weight:800; ${colorClass}">${totalSlides} direct slides</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0;">
          <span>🔄 <strong>Mutual Swaps</strong> ($A \\leftrightarrow B$):</span>
          <span style="font-weight:700; color:${swaps > 0 ? '#DC2626' : 'var(--text-muted)'};">${swaps}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0;">
          <span>↕️ <strong>Move Shelf</strong> (Vertical Shift):</span>
          <span style="font-weight:700;">${xShelf}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0;">
          <span>🚚 <strong>Cross-Bay Moves</strong>:</span>
          <span style="font-weight:700;">${xBay}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0; border-top:1px dashed var(--border);">
          <span>📦 <strong>Stage to Cart</strong> (Off-Shelf):</span>
          <span style="font-weight:700; color:${staged > 0 ? '#D97706' : 'var(--text-muted)'};">${staged} items</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0;">
          <span>📥 <strong>Place from Cart</strong> (On-Shelf):</span>
          <span style="font-weight:700; color:${placed > 0 ? '#D97706' : 'var(--text-muted)'};">${placed} items</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0; border-top:1px dashed var(--border);">
          <span>✅ <strong>In Target Position</strong> (Untouched):</span>
          <span style="font-weight:800; color:#059669;">${inPlace} verified untouched</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:3px 0;">
          <span>⚠️ <strong>Redundant Moves Flagged</strong>:</span>
          <span style="font-weight:700; color:${redundant > 0 ? '#DC2626' : '#059669'};">${redundant === 0 ? '0 (Clean)' : redundant + ' redundant'}</span>
        </div>
      `;
    }

    const checkListAEl = byId('ir-associate-checklist-a');
    if (checkListAEl) checkListAEl.innerHTML = buildChecklistHtml(protoA, 'color:#4F46E5;');

    const checkListBEl = byId('ir-associate-checklist-b');
    if (checkListBEl) checkListBEl.innerHTML = buildChecklistHtml(protoB, 'color:#D97706;');

    const inPlaceTextEl = byId('ir-in-position-verification-text');
    if (inPlaceTextEl) {
      const inPlaceCountA = protoA.untouched_compliant || 0;
      const redundantA = protoA.redundant_moves || 0;
      const stagedB = protoB.staged_to_cart || 0;
      inPlaceTextEl.innerHTML = `<strong>Position Integrity Check:</strong> In <strong>${instNameA}</strong>, <strong>${inPlaceCountA} product(s)</strong> are already in their correct target planogram coordinates. They were verified untouched and <strong>${redundantA} redundant moves</strong> were generated. In contrast, <strong>${instNameB}</strong> required <strong>${stagedB} cart-staging operations</strong>.`;
    }

    // -------------------------------------------------------------
    // Operational Effort Comparison (Excluding Restock)
    // -------------------------------------------------------------
    const eff = data.effort_comparison || {};
    const touchesA = eff.touches_a || 0;
    const touchesB = eff.touches_b || 0;
    const touchesDiff = eff.touches_diff || 0;
    const touchesPct = eff.touches_pct || 0;
    const itemsA = eff.items_a || 0;
    const itemsB = eff.items_b || 0;
    const itemsDiff = eff.items_diff || 0;
    const itemsPct = eff.items_pct || 0;

    const effortBadge = byId('ir-compare-effort-badge');
    if (effortBadge) {
      if (touchesDiff === 0) {
        effortBadge.textContent = '⚖️ Equal Effort (0% change)';
        effortBadge.style.background = 'rgba(107,114,128,0.15)';
        effortBadge.style.color = '#4B5563';
      } else if (touchesDiff < 0) {
        effortBadge.textContent = `🟢 ${Math.abs(touchesPct)}% Effort Reduction in ${instNameA}`;
        effortBadge.style.background = 'rgba(16,185,129,0.15)';
        effortBadge.style.color = '#059669';
      } else {
        effortBadge.textContent = `🟠 ${Math.abs(touchesPct)}% Effort Increase in ${instNameA}`;
        effortBadge.style.background = 'rgba(217,119,6,0.15)';
        effortBadge.style.color = '#D97706';
      }
    }

    setText('ir-effort-touches-a', touchesA);
    setText('ir-effort-touches-b', touchesB);
    const touchesDeltaEl = byId('ir-effort-touches-delta');
    if (touchesDeltaEl) {
      const isRed = touchesDiff < 0;
      touchesDeltaEl.textContent = `${touchesPct > 0 ? '+' : ''}${touchesPct}% (${touchesDiff > 0 ? '+' : ''}${touchesDiff} touches)`;
      touchesDeltaEl.style.color = isRed ? '#059669' : (touchesDiff === 0 ? 'var(--text-muted)' : '#D97706');
    }

    setText('ir-effort-items-a', itemsA);
    setText('ir-effort-items-b', itemsB);
    const itemsDeltaEl = byId('ir-effort-items-delta');
    if (itemsDeltaEl) {
      const isRed = itemsDiff < 0;
      itemsDeltaEl.textContent = `${itemsPct > 0 ? '+' : ''}${itemsPct}% (${itemsDiff > 0 ? '+' : ''}${itemsDiff} items)`;
      itemsDeltaEl.style.color = isRed ? '#059669' : (itemsDiff === 0 ? 'var(--text-muted)' : '#D97706');
    }

    // Labor Time Modeling (SAM)
    const labor = data.labor_comparison || {};
    const laborA = labor.minutes_a || 0;
    const laborB = labor.minutes_b || 0;
    const laborDiff = labor.minutes_diff || 0;
    const laborPct = labor.minutes_pct || 0;
    const doubleA = labor.double_handling_pct_a || 0;
    const doubleB = labor.double_handling_pct_b || 0;

    setText('ir-labor-min-a', `${laborA}m`);
    setText('ir-labor-min-b', `${laborB}m`);
    const laborDeltaEl = byId('ir-labor-min-delta');
    if (laborDeltaEl) {
      const isTimeSaved = laborDiff < 0;
      laborDeltaEl.textContent = `${laborPct > 0 ? '+' : ''}${laborPct}% (${Math.abs(laborDiff)} min ${isTimeSaved ? 'saved' : 'more'})`;
      laborDeltaEl.style.color = isTimeSaved ? '#059669' : (laborDiff === 0 ? 'var(--text-muted)' : '#D97706');
    }

    setText('ir-double-handling-a', `${doubleA}%`);
    setText('ir-double-handling-b', `${doubleB}%`);
    const doubleDeltaEl = byId('ir-double-handling-delta');
    if (doubleDeltaEl) {
      const doubleDiff = round1(doubleA - doubleB);
      const isReduced = doubleDiff < 0;
      doubleDeltaEl.textContent = `${doubleDiff > 0 ? '+' : ''}${doubleDiff}% staged`;
      doubleDeltaEl.style.color = isReduced ? '#059669' : (doubleDiff === 0 ? 'var(--text-muted)' : '#D97706');
    }

    const effTbody = byId('ir-compare-effort-tbody');
    if (effTbody) {
      const breakdown = eff.breakdown || [];
      effTbody.innerHTML = breakdown.map(r => {
        const diffColor = r.diff === 0 ? 'var(--text-muted)' : (r.diff < 0 ? '#059669' : '#D97706');
        const diffPrefix = r.diff > 0 ? '+' : '';
        return `<tr>
          <td><strong style="color:var(--text);">${r.action}</strong></td>
          <td style="text-align:right; font-weight:700; font-size:13px; color:#4F46E5;">${r.count_a}</td>
          <td style="text-align:right; font-weight:700; font-size:13px; color:#D97706;">${r.count_b}</td>
          <td style="text-align:right; font-weight:800; color:${diffColor};">${r.diff === 0 ? '—' : diffPrefix + r.diff}</td>
        </tr>`;
      }).join('');

      // Add Total Shelf Touches row
      const totDiffColor = touchesDiff === 0 ? 'var(--text-muted)' : (touchesDiff < 0 ? '#059669' : '#D97706');
      effTbody.innerHTML += `<tr style="border-top:2px solid var(--border); font-weight:800; background:rgba(79,70,229,0.04);">
        <td>TOTAL PHYSICAL SHELF TOUCHES</td>
        <td style="text-align:right; font-size:14px; color:#4F46E5;">${touchesA}</td>
        <td style="text-align:right; font-size:14px; color:#D97706;">${touchesB}</td>
        <td style="text-align:right; font-size:14px; color:${totDiffColor};">${touchesDiff === 0 ? '—' : (touchesDiff > 0 ? '+' : '') + touchesDiff + ` (${touchesPct > 0 ? '+' : ''}${touchesPct}%)`}</td>
      </tr>`;
    }

    // -------------------------------------------------------------
    // Sequencing Anomalies & Conflict Inspector Table
    // -------------------------------------------------------------
    const anomalies = data.anomalies || {};
    const anomA = anomalies.a || {};
    const anomB = anomalies.b || {};
    const anomTbody = byId('ir-compare-anomalies-tbody');
    const anomHeaderBadge = byId('ir-anomalies-header-badge');

    const combinedConflicts = [];
    (anomA.collisions || []).forEach(c => combinedConflicts.push({ ...c, instance: instNameA, instColor: '#4F46E5' }));
    (anomA.cycles || []).forEach(c => combinedConflicts.push({ ...c, instance: instNameA, instColor: '#4F46E5' }));
    (anomA.directional || []).forEach(c => combinedConflicts.push({ ...c, instance: instNameA, instColor: '#4F46E5' }));
    (anomA.redundant_moves || []).forEach(c => combinedConflicts.push({
      type: 'Redundant In-Place Move',
      instance: instNameA,
      instColor: '#4F46E5',
      slot: c.slot_move || '—',
      item_1: `${c.name} (UPC ${c.upc})`,
      description: 'Item is already in target planogram position, but unnecessary move was queued.'
    }));

    (anomB.collisions || []).forEach(c => combinedConflicts.push({ ...c, instance: instNameB, instColor: '#D97706' }));
    (anomB.cycles || []).forEach(c => combinedConflicts.push({ ...c, instance: instNameB, instColor: '#D97706' }));
    (anomB.directional || []).forEach(c => combinedConflicts.push({ ...c, instance: instNameB, instColor: '#D97706' }));
    (anomB.redundant_moves || []).forEach(c => combinedConflicts.push({
      type: 'Redundant In-Place Move',
      instance: instNameB,
      instColor: '#D97706',
      slot: c.slot_move || '—',
      item_1: `${c.name} (UPC ${c.upc})`,
      description: 'Item is already in target planogram position, but unnecessary move was queued.'
    }));

    // Include multi-facing allocations as informative, non-conflict rows
    const multiFacingRows = [];
    (anomA.multi_facing || []).forEach(m => multiFacingRows.push({ ...m, instance: instNameA, instColor: '#4F46E5', isMultiFacing: true }));
    (anomB.multi_facing || []).forEach(m => multiFacingRows.push({ ...m, instance: instNameB, instColor: '#D97706', isMultiFacing: true }));

    if (anomHeaderBadge) {
      if (combinedConflicts.length === 0) {
        anomHeaderBadge.textContent = '🟢 0 Conflicts (Clean Sequencing)';
        anomHeaderBadge.style.background = 'rgba(16,185,129,0.15)';
        anomHeaderBadge.style.color = '#059669';
      } else {
        anomHeaderBadge.textContent = `🚨 ${combinedConflicts.length} Conflict(s) Detected`;
        anomHeaderBadge.style.background = 'rgba(239,68,68,0.15)';
        anomHeaderBadge.style.color = '#DC2626';
      }
    }

    if (anomTbody) {
      const allRows = [...combinedConflicts, ...multiFacingRows];
      if (allRows.length === 0) {
        anomTbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:18px; color:#059669; font-weight:700;">
          ✅ Clean Sequencing Verified — Zero Cross-Product Collisions, Zero Mutual Swap Deadlocks, and Zero Redundant Moves across both tasks.
          <div style="font-size:11px; font-weight:400; color:var(--text-muted); margin-top:6px;">
            Both instances execute clean flows: In ${instNameA}, items slide directly on the shelf without blocking each other. In ${instNameB}, items are staged to a cart first (${protoB.staged_to_cart || 0} set-asides) before placement, leaving zero collisions on the shelf.
          </div>
        </td></tr>`;
      } else {
        anomTbody.innerHTML = allRows.map(cf => {
          let typeBadgeStyle = 'background:rgba(239,68,68,0.12); color:#DC2626; border:1px solid rgba(239,68,68,0.25);';
          let typeLabel = cf.type;
          if (cf.isMultiFacing) {
            typeBadgeStyle = 'background:rgba(16,185,129,0.12); color:#059669; border:1px solid rgba(16,185,129,0.25);';
            typeLabel = '🟢 Multi-Facing POG Block';
          } else if (cf.type && cf.type.includes('Redundant')) {
            typeBadgeStyle = 'background:rgba(245,158,11,0.12); color:#B45309; border:1px solid rgba(245,158,11,0.25);';
            typeLabel = '⚠️ Redundant In-Place Move';
          } else if (cf.type && cf.type.includes('Directional')) {
            typeBadgeStyle = 'background:rgba(245,158,11,0.12); color:#B45309; border:1px solid rgba(245,158,11,0.25);';
          }

          const slotText = cf.slot || cf.shelf || cf.slots || '—';
          const facingsText = `<span style="font-family:monospace; font-weight:800; font-size:11px; padding:2px 8px; border-radius:4px; background:rgba(0,0,0,0.04);">${cf.expected_facings || 1} Exp / ${cf.actual_facings || 1} Act</span>`;
          
          let prodHtml = '';
          if (cf.item_2) {
            prodHtml = `<div style="font-weight:700; font-size:11.5px;">${cf.item_1}</div><div style="color:var(--text-muted); font-size:10px; margin:2px 0;">conflicts with:</div><div style="font-weight:700; font-size:11.5px; color:#DC2626;">${cf.item_2}</div>`;
          } else {
            const pTitle = cf.name || cf.item_1 || '—';
            const originsHtml = cf.origins_summary ? `<div style="font-size:10.5px; color:var(--text-muted); margin-top:2px; font-family:monospace;">${cf.origins_summary}</div>` : '';
            prodHtml = `<div style="font-weight:700; font-size:11.5px;">${pTitle}</div>${originsHtml}`;
          }

          let assessmentHtml = '';
          if (cf.isMultiFacing) {
            assessmentHtml = `<div style="font-weight:700; font-size:11px; color:#059669;">✅ Zero Collision Risk (Legitimate POG Grouping)</div>
            <div style="font-size:10.5px; color:var(--text-muted); line-height:1.3; margin-top:2px;">All ${cf.expected_facings || 1} facings belong to the same UPC and sit side-by-side in adjacent shelf positions.</div>`;
          } else {
            assessmentHtml = `<div style="font-size:11px; color:var(--text-muted); line-height:1.4;">${cf.description || 'Sequencing evaluation'}</div>`;
          }

          return `<tr>
            <td><span style="font-size:11px; font-weight:800; padding:2px 8px; border-radius:10px; background:${cf.instColor === '#4F46E5' ? 'rgba(79,70,229,0.12)' : 'rgba(217,119,6,0.12)'}; color:${cf.instColor};">${cf.instance}</span></td>
            <td><span style="font-size:10.5px; font-weight:700; padding:2px 8px; border-radius:10px; display:inline-block; ${typeBadgeStyle}">${typeLabel}</span></td>
            <td style="font-family:monospace; font-size:11px; font-weight:700;">${slotText}</td>
            <td style="text-align:center;">${facingsText}</td>
            <td>${prodHtml}</td>
            <td>${assessmentHtml}</td>
          </tr>`;
        }).join('');
      }
    }

    // Algorithmic Quality & Safety Checks Card
    const safety = data.safety_comparison || {};
    const cyclesA = safety.cycles_a || 0;
    const cyclesB = safety.cycles_b || 0;
    const collA = safety.collisions_a || 0;
    const collB = safety.collisions_b || 0;
    const stepsA = safety.steps_a || 0;
    const stepsB = safety.steps_b || 0;
    const upcsA = safety.unique_upcs_a || 0;
    const upcsB = safety.unique_upcs_b || 0;

    const safetyBadge = byId('ir-safety-overall-badge');
    if (safetyBadge) {
      if (cyclesA === 0 && collA === 0) {
        safetyBadge.textContent = '🟢 Verified Clean Sequencing';
        safetyBadge.style.background = 'rgba(16,185,129,0.15)';
        safetyBadge.style.color = '#059669';
      } else {
        safetyBadge.textContent = '⚠️ Sequencing Anomalies Detected';
        safetyBadge.style.background = 'rgba(239,68,68,0.15)';
        safetyBadge.style.color = '#DC2626';
      }
    }

    setText('ir-safety-cycles-val', `${cyclesA} vs ${cyclesB}`);
    setText('ir-safety-cycles-desc', cyclesA === 0 ? `Zero mutual swaps in ${instNameA}` : `⚠️ ${cyclesA} swap conflict(s) found`);
    byId('ir-safety-cycles-val').style.color = cyclesA === 0 ? '#059669' : '#DC2626';

    setText('ir-safety-collisions-val', `${collA} vs ${collB}`);
    setText('ir-safety-collisions-desc', collA === 0 ? 'No target position overlaps' : `⚠️ ${collA} target collision(s)`);
    byId('ir-safety-collisions-val').style.color = collA === 0 ? '#059669' : '#DC2626';

    setText('ir-safety-steps-val', `${stepsA} vs ${stepsB} batches`);
    const stepsDiff = stepsA - stepsB;
    setText('ir-safety-steps-desc', stepsDiff <= 0 ? `${Math.abs(stepsDiff)} fewer associate mobile steps` : `+${stepsDiff} additional steps`);

    setText('ir-safety-upcs-val', `${upcsA} vs ${upcsB} products`);
    setText('ir-safety-upcs-desc', 'Unique items relocated');

    // Spatial & Bay Disruption Distribution Table
    setText('ir-compare-th-bay-a', labelA);
    setText('ir-compare-th-bay-b', labelB);
    const spatial = data.spatial_comparison || {};
    const bayTbody = byId('ir-compare-bay-tbody');
    if (bayTbody) {
      const bayRows = spatial.by_bay || [];
      if (bayRows.length === 0) {
        bayTbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:12px; color:var(--text-muted);">No bay distribution data</td></tr>';
      } else {
        bayTbody.innerHTML = bayRows.map(r => {
          const diffColor = r.diff === 0 ? 'var(--text-muted)' : (r.diff > 0 ? '#4F46E5' : '#D97706');
          const diffPrefix = r.diff > 0 ? '+' : '';
          return `<tr>
            <td><strong style="color:var(--text);">${r.bay}</strong></td>
            <td style="text-align:right; font-weight:700; font-size:13px; color:#4F46E5;">${r.count_a}</td>
            <td style="text-align:right; font-weight:700; font-size:13px; color:#D97706;">${r.count_b}</td>
            <td style="text-align:right; font-weight:800; color:${diffColor};">${r.diff === 0 ? '—' : diffPrefix + r.diff}</td>
          </tr>`;
        }).join('');
      }
    }
    const spatialPill = byId('ir-spatial-summary-pill');
    if (spatialPill) {
      spatialPill.textContent = `${instNameA}: ${spatial.intra_bay_a || 0} Intra-Bay / ${spatial.cross_bay_a || 0} Cross-Bay vs ${instNameB}: ${spatial.intra_bay_b || 0} Intra-Bay / ${spatial.cross_bay_b || 0} Cross-Bay`;
    }

    // Error warnings for individual tasks
    if (a.error) {
      byId('ir-compare-card-a-meta').innerHTML += `<div style="color:#EF4444; font-weight:700; margin-top:4px;">⚠️ ${a.error}</div>`;
    }
    if (b.error) {
      byId('ir-compare-card-b-meta').innerHTML += `<div style="color:#EF4444; font-weight:700; margin-top:4px;">⚠️ ${b.error}</div>`;
    }

    // Action Type Breakdown Table
    const typeTbody = byId('ir-compare-type-tbody');
    if (typeTbody) {
      const rows = (cmp.by_action_type || []);
      if (rows.length === 0) {
        typeTbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:16px; color:var(--text-muted);">No action type data available</td></tr>';
      } else {
        typeTbody.innerHTML = rows.map(r => {
          const diffColor = r.diff === 0 ? 'var(--text-muted)' : (r.diff > 0 ? '#4F46E5' : '#D97706');
          const diffPrefix = r.diff > 0 ? '+' : '';
          return `<tr>
            <td><span class="badge badge-gray">${r.type}</span></td>
            <td style="text-align:right; font-weight:700; font-size:13px; color:#4F46E5;">${r.count_a}</td>
            <td style="text-align:right; font-weight:700; font-size:13px; color:#D97706;">${r.count_b}</td>
            <td style="text-align:right; font-weight:800; color:${diffColor};">${r.diff === 0 ? '—' : diffPrefix + r.diff}</td>
          </tr>`;
        }).join('');
        // Add total row
        typeTbody.innerHTML += `<tr style="border-top:2px solid var(--border); font-weight:800; background:rgba(79,70,229,0.04);">
          <td>TOTAL</td>
          <td style="text-align:right; font-size:14px; color:#4F46E5;">${totalA}</td>
          <td style="text-align:right; font-size:14px; color:#D97706;">${totalB}</td>
          <td style="text-align:right; font-size:14px; color:${diff === 0 ? 'var(--text-muted)' : (diff > 0 ? '#4F46E5' : '#D97706')};">${diff === 0 ? '—' : (diff > 0 ? '+' : '') + diff}</td>
        </tr>`;
      }
    }

    // State Breakdown Table
    const stateTbody = byId('ir-compare-state-tbody');
    if (stateTbody) {
      const rows = (cmp.by_state || []);
      if (rows.length === 0) {
        stateTbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:16px; color:var(--text-muted);">No state data available</td></tr>';
      } else {
        stateTbody.innerHTML = rows.map(r => {
          const diffColor = r.diff === 0 ? 'var(--text-muted)' : (r.diff > 0 ? '#4F46E5' : '#D97706');
          const diffPrefix = r.diff > 0 ? '+' : '';
          return `<tr>
            <td><span class="badge ${r.state === 'ACCEPTED' ? 'badge-green' : (r.state === 'REJECTED' ? 'badge-red' : 'badge-gray')}">${r.state}</span></td>
            <td style="text-align:right; font-weight:700; font-size:13px; color:#4F46E5;">${r.count_a}</td>
            <td style="text-align:right; font-weight:700; font-size:13px; color:#D97706;">${r.count_b}</td>
            <td style="text-align:right; font-weight:800; color:${diffColor};">${r.diff === 0 ? '—' : diffPrefix + r.diff}</td>
          </tr>`;
        }).join('');
      }
    }

    // Item-by-Item UPC Variance Drilldown
    setText('ir-compare-th-item-a', `${labelA} Action (User Takes)`);
    setText('ir-compare-th-item-b', `${labelB} Action (User Takes)`);
    currentProductVarianceList = data.product_variance || [];
    renderProductVariance();
  }

  let currentProductVarianceList = [];

  function filterProductVariance() {
    const input = byId('ir-compare-item-search');
    const q = (input ? input.value : '').trim().toLowerCase();
    renderProductVariance(q);
  }

  function renderProductVariance(filterText = '') {
    const tbody = byId('ir-compare-item-tbody');
    const countPill = byId('ir-compare-item-count');
    if (!tbody) return;

    let items = currentProductVarianceList || [];
    if (filterText) {
      items = items.filter(it => 
        (it.upc && it.upc.toLowerCase().includes(filterText)) ||
        (it.name && it.name.toLowerCase().includes(filterText)) ||
        (it.variance_label && it.variance_label.toLowerCase().includes(filterText)) ||
        (it.user_action_a && it.user_action_a.toLowerCase().includes(filterText)) ||
        (it.user_action_b && it.user_action_b.toLowerCase().includes(filterText)) ||
        (it.action_a && it.action_a.toLowerCase().includes(filterText)) ||
        (it.action_b && it.action_b.toLowerCase().includes(filterText))
      );
    }

    if (countPill) {
      countPill.textContent = `Showing ${items.length} of ${currentProductVarianceList.length} products`;
    }

    if (items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:16px; color:var(--text-muted);">No products match your search</td></tr>';
      return;
    }

    tbody.innerHTML = items.map(it => {
      let badgeStyle = 'background:rgba(107,114,128,0.15); color:#4B5563;';
      if (it.variance_badge === 'success') {
        badgeStyle = 'background:rgba(16,185,129,0.15); color:#059669; font-weight:700;';
      } else if (it.variance_badge === 'warning') {
        badgeStyle = 'background:rgba(245,158,11,0.15); color:#B45309; font-weight:700;';
      } else if (it.variance_badge === 'info') {
        badgeStyle = 'background:rgba(79,70,229,0.15); color:#4F46E5; font-weight:700;';
      } else if (it.variance_badge === 'accent') {
        badgeStyle = 'background:rgba(139,92,246,0.15); color:#6D28D9; font-weight:700;';
      }

      const actA = it.user_action_a || it.action_a || '—';
      const actB = it.user_action_b || it.action_b || '—';
      const slotA = it.slot_a && it.slot_a !== '—' ? `<div style="font-size:10px; color:var(--text-muted); font-family:monospace; margin-top:2px;">${it.slot_a}</div>` : '';
      const slotB = it.slot_b && it.slot_b !== '—' ? `<div style="font-size:10px; color:var(--text-muted); font-family:monospace; margin-top:2px;">${it.slot_b}</div>` : '';

      return `<tr>
        <td style="font-family:monospace; font-size:11.5px; font-weight:700; color:var(--text);">${it.upc}</td>
        <td>
          <div style="font-size:12px; font-weight:700; color:var(--text);">${it.name}</div>
          <div style="font-size:10.5px; color:var(--text-muted);">Bay ${it.bay} • Facings: ${it.facings_a} in A vs ${it.facings_b} in B</div>
        </td>
        <td>
          <div style="font-size:11.5px; font-weight:700; color:#4F46E5;">${actA}</div>
          ${slotA}
        </td>
        <td>
          <div style="font-size:11.5px; font-weight:700; color:#D97706;">${actB}</div>
          ${slotB}
        </td>
        <td style="text-align:right;">
          <span style="font-size:10.5px; padding:3px 8px; border-radius:12px; display:inline-block; ${badgeStyle}">${it.variance_label}</span>
        </td>
      </tr>`;
    }).join('');
  }

  function round1(val) {
    return Math.round(val * 10) / 10;
  }

  function renderTechnicalLineage(events) {
    const tbody = byId('ir-tech-lineage-tbody');
    if (!tbody) return;

    tbody.innerHTML = (events || []).map((ev) => `
      <tr>
        <td style="font-family: monospace; font-size: 11px;">${ev.ts}</td>
        <td><span class="badge badge-gray">${ev.phase.toUpperCase()}</span></td>
        <td><b>${ev.event_type}</b></td>
        <td>${ev.bay || '—'}</td>
        <td style="font-size: 11.5px;">${ev.detail}</td>
        <td style="font-family: monospace; font-size: 10px; color: #38bdf8;">
          ${ev.source_table}.${ev.source_column}
        </td>
        <td style="font-family: monospace; font-size: 10px;">#${ev.source_row_id}</td>
      </tr>
    `).join('');
  }

  window.IrTaskFlow = {
    init,
    loadTask,
    loadTaskFlow: loadTask,
    quickSelect,
    onInstanceChange,
    loadCurrentInputs,
    switchSubView,
    openItemDrawer,
    syncEmbeddedTabs,
    compareTasks,
    onCompareInstanceChange,
    filterProductVariance,
    openCredentialsModal,
    closeCredentialsModal,
    onModalInstanceSelect,
    testCredentialsConnection,
    saveCredentialsAndReload,
    checkAuthStatus,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window, document);
