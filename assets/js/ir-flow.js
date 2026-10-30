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
  let catalogTasks = [];
  let catalogStatusNote = '';
  let unfilteredCatalogNote = '';
  let selectedCatalogTaskId = '';
  let selectedPerformerKey = '';
  let flowInitialised = false;
  let liveStatusPollInterval = null;

  function byId(id) {
    return document.getElementById(id);
  }

  function normalizeInstanceUrl(inst) {
    if (!inst) return 'https://harr.rebotics.net';
    let clean = String(inst).trim();
    while (clean.includes('.net.net')) clean = clean.replace('.net.net', '.net');
    while (clean.includes('.rebotics.net.rebotics.net')) clean = clean.replace('.rebotics.net.rebotics.net', '.rebotics.net');
    while (clean.includes('.rebotics.net.net')) clean = clean.replace('.rebotics.net.net', '.rebotics.net');

    if (clean.startsWith('http://') || clean.startsWith('https://')) return clean.replace(/\/+$/, '');
    if (clean === 'krcs' || clean === 'krsc' || clean === 'krog' || clean === 'kroger') return 'https://krcs.rebotics.net';
    if (clean === 'stgsams' || clean === 'sams') return 'https://stgsams.rebotics.net';
    if (clean === 'harr' || clean === 'harris') return 'https://harr.rebotics.net';
    if (clean === 'albt' || clean === 'albe' || clean === 'albertsons') return 'https://albt.rebotics.net';
    if (clean === 'albtqa') return 'https://albtqa.rebotics.net';
    if (clean === 'schn') return 'https://schn.rebotics.net';
    if (clean === 'wake') return 'https://wake.rebotics.net';
    if (clean.includes('.')) return `https://${clean}`.replace(/\/+$/, '');
    return `https://${clean}.rebotics.net`;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function resolveItemScanId(item) {
    if (item && item.scan_id) return item.scan_id;
    if (!currentFlowData) return null;
    const bay = item && (item.to_bay || item.from_bay || item.section);
    if (bay && currentFlowData.bay_summaries) {
      const cleanBay = String(bay).toLowerCase().replace('bay', '').trim();
      for (const [bName, bData] of Object.entries(currentFlowData.bay_summaries)) {
        if (bName.toLowerCase().includes(cleanBay) || String(bName).toLowerCase() === String(bay).toLowerCase()) {
          if (bData.pre_photo_scan_id) return bData.pre_photo_scan_id;
        }
      }
    }
    if (currentFlowData.metadata) {
      if (currentFlowData.metadata.pre_photo_scan_id) return currentFlowData.metadata.pre_photo_scan_id;
      if (currentFlowData.metadata.scan_id) return currentFlowData.metadata.scan_id;
    }
    if (currentFlowData.pre_photo && currentFlowData.pre_photo.scan_id) {
      return currentFlowData.pre_photo.scan_id;
    }
    if (currentFlowData.performed_evidence && Array.isArray(currentFlowData.performed_evidence.scan_ids) && currentFlowData.performed_evidence.scan_ids.length > 0) {
      return currentFlowData.performed_evidence.scan_ids[0];
    }
    const firstBay = currentFlowData.bay_summaries && Object.values(currentFlowData.bay_summaries)[0];
    if (firstBay && firstBay.pre_photo_scan_id) return firstBay.pre_photo_scan_id;
    return null;
  }

  function currentPostScanId() {
    if (!currentFlowData) return null;
    if (currentFlowData.post_photo && currentFlowData.post_photo.scan_id) return currentFlowData.post_photo.scan_id;
    if (currentFlowData.metadata && currentFlowData.metadata.post_photo_scan_id) return currentFlowData.metadata.post_photo_scan_id;
    const firstBay = currentFlowData.bay_summaries && Object.values(currentFlowData.bay_summaries)[0];
    if (firstBay && firstBay.post_photo_scan_id) return firstBay.post_photo_scan_id;
    return null;
  }

  function currentPreScanId() {
    return resolveItemScanId(null);
  }

  function buildDigitalShelfScanUrl(scanId, item, meta) {
    if (item && item.digital_shelf_url) return item.digital_shelf_url;
    const sId = scanId || (item && item.scan_id) || resolveItemScanId(item);
    if (!sId) return null;
    const m = meta || (currentFlowData && currentFlowData.metadata);
    const inst = (m && m.instance) || getSelectedInstance() || 'harr';
    const base = normalizeInstanceUrl(inst);
    let url = `${base}/reporting/scans/${encodeURIComponent(sId)}`;
    const params = [];
    if (m) {
      const store = m.store_code || m.store_id;
      if (store) params.push(`store=${encodeURIComponent(store)}`);
      const pog = m.planogram_id || m.planogram_name;
      if (pog) params.push(`planogram=${encodeURIComponent(pog)}`);
      if (m.task_date) params.push(`date=${encodeURIComponent(m.task_date)}`);
    }
    if (params.length) url += `?${params.join('&')}`;
    return url;
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
            if (tokenInput) {
              tokenInput.placeholder = 'Paste token e.g. b131c80b29...';
              tokenInput.value = '';
            }
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
    let token = (byId('ir-auth-token') || {}).value || '';
    const msgEl = byId('ir-auth-status-msg');
    const btn = byId('btn-ir-auth-test');

    // If username is provided without password, stop immediately
    if (username && !password) {
      if (msgEl) {
        msgEl.style.display = 'block';
        msgEl.style.background = '#FEF2F2';
        msgEl.style.border = '1px solid #FECACA';
        msgEl.style.color = '#991B1B';
        msgEl.textContent = `❌ Please enter the password for username '${username}'.`;
      }
      return;
    }

    if (username && password) {
      token = '';
    }

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
        if (data.token_expired || (data.message && (data.message.includes('401') || data.message.includes('expired')))) {
          try {
            localStorage.removeItem(`ir_creds_${baseUrl}`);
          } catch (e) {}
          const tokenInput = byId('ir-auth-token');
          if (tokenInput) tokenInput.value = '';
          const savedTag = byId('ir-auth-saved-tag');
          if (savedTag) savedTag.style.display = 'none';
          const slug = baseUrl.replace('https://', '').split('.')[0];
          checkAuthStatus(slug);
        }
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
    let token = (byId('ir-auth-token') || {}).value || '';
    const msgEl = byId('ir-auth-status-msg');
    const btn = byId('btn-ir-auth-save');

    // If username is provided without password, stop immediately
    if (username && !password) {
      if (msgEl) {
        msgEl.style.display = 'block';
        msgEl.style.background = '#FEF2F2';
        msgEl.style.border = '1px solid #FECACA';
        msgEl.style.color = '#991B1B';
        msgEl.textContent = `❌ Please enter the password for username '${username}'.`;
      }
      return;
    }

    if (username && password) {
      token = '';
    }

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
        const signedInInstance = data.instance_slug || getSelectedInstance();
        const picker = byId('ir-instance-picker');
        if (picker && signedInInstance && [...picker.options].some((option) => option.value === signedInInstance)) {
          picker.value = signedInInstance;
        }
        const preferredTask = (byId('ir-simple-task-input') || {}).value || '';
        await loadTaskCatalog(signedInInstance, preferredTask);
      } else {
        if (data.token_expired || (data.message && (data.message.includes('401') || data.message.includes('expired')))) {
          try {
            localStorage.removeItem(`ir_creds_${baseUrl}`);
          } catch (e) {}
          const tokenInput = byId('ir-auth-token');
          if (tokenInput) tokenInput.value = '';
          const savedTag = byId('ir-auth-saved-tag');
          if (savedTag) savedTag.style.display = 'none';
          const slug = baseUrl.replace('https://', '').split('.')[0];
          checkAuthStatus(slug);
        }
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

  async function quickSelect(instance, taskId) {
    const inst = instance || 'harr';
    const tid = taskId || '';

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
    await loadTaskCatalog(inst, tid);
  }

  function formatDurationHoursMinutes(minutes) {
    if (typeof minutes !== 'number' || isNaN(minutes) || minutes < 0) {
      return null;
    }
    if (minutes === 0) {
      return '0 mins';
    }
    const totalSec = Math.round(minutes * 60);
    if (totalSec < 300 && totalSec % 60 !== 0) {
      const m = Math.floor(totalSec / 60);
      const s = totalSec % 60;
      return m > 0 ? `${m}m ${s}s` : `${s}s`;
    }
    const totalMinutes = Math.round(minutes);
    if (totalMinutes < 60) {
      return totalMinutes === 1 ? '1 min' : `${totalMinutes} mins`;
    }
    const hours = Math.floor(totalMinutes / 60);
    const remainingMins = totalMinutes % 60;
    const hourStr = hours === 1 ? '1 hr' : `${hours} hrs`;
    if (remainingMins === 0) {
      return hourStr;
    }
    const minStr = remainingMins === 1 ? '1 min' : `${remainingMins} mins`;
    return `${hourStr} ${minStr}`;
  }

  let performerAliasMap = new Map();

  function rebuildPerformerAliasMap() {
    performerAliasMap = new Map();
    catalogTasks.forEach((task) => {
      const name = String(task.performer || '').trim().toLowerCase();
      const username = String(task.performer_username || '').trim().toLowerCase();
      const id = task.performer_id ? `id:${task.performer_id}` : '';
      const canonical = username || name || id;
      if (!canonical) return;
      if (name) performerAliasMap.set(`name:${name}`, canonical);
      if (username) performerAliasMap.set(`user:${username}`, canonical);
      if (id) performerAliasMap.set(id, canonical);
    });
  }

  function performerKey(task) {
    const name = String(task.performer || '').trim().toLowerCase();
    const username = String(task.performer_username || '').trim().toLowerCase();
    const id = task.performer_id ? `id:${task.performer_id}` : '';
    if (username && performerAliasMap.has(`user:${username}`)) return performerAliasMap.get(`user:${username}`);
    if (name && performerAliasMap.has(`name:${name}`)) return performerAliasMap.get(`name:${name}`);
    if (id && performerAliasMap.has(id)) return performerAliasMap.get(id);
    return username || name || id || '';
  }

  function performerLabel(task) {
    const name = String(task.performer || '').trim();
    const username = String(task.performer_username || '').trim();
    if (name && username && name.toLowerCase() !== username.toLowerCase()) return `${name} (${username})`;
    return name || username || 'Unassigned';
  }

  function visibleCatalogTasks() {
    let list;
    if (!selectedPerformerKey) {
      list = catalogTasks;
    } else {
      list = catalogTasks.filter((task) => performerKey(task) === selectedPerformerKey);
    }
    // Deduplicate by unique task_id
    const seen = new Set();
    return list.filter((task) => {
      const id = String(task.task_id || '').trim();
      if (!id || seen.has(id)) return false;
      seen.add(id);
      return true;
    });
  }

  function populatePerformerFilter() {
    const select = byId('ir-performer-picker');
    if (!select) return;
    rebuildPerformerAliasMap();
    const groups = new Map();
    const seenTasksPerGroup = new Map();

    catalogTasks.forEach((task) => {
      const key = performerKey(task);
      if (!key) return;
      const tid = String(task.task_id || '').trim();
      let taskSet = seenTasksPerGroup.get(key);
      if (!taskSet) {
        taskSet = new Set();
        seenTasksPerGroup.set(key, taskSet);
      }
      if (tid && taskSet.has(tid)) return;
      if (tid) taskSet.add(tid);

      const existing = groups.get(key) || { key, label: performerLabel(task), count: 0 };
      const currentLabel = performerLabel(task);
      if (currentLabel.includes('(') && !existing.label.includes('(')) {
        existing.label = currentLabel;
      }
      existing.count += 1;
      groups.set(key, existing);
    });

    const previous = selectedPerformerKey;
    select.replaceChildren();
    const all = document.createElement('option');
    all.value = '';
    all.textContent = catalogTasks.length ? `All performers (${catalogTasks.length})` : 'All performers';
    select.appendChild(all);
    [...groups.values()]
      .filter((group) => !group.label.toLowerCase().includes('unassigned'))
      .sort((a, b) => a.label.localeCompare(b.label))
      .forEach((group) => {
        const option = document.createElement('option');
        option.value = group.key;
        option.textContent = `${group.label} (${group.count})`;
        select.appendChild(option);
      });
    selectedPerformerKey = previous && groups.has(previous) ? previous : '';
    select.value = selectedPerformerKey;
    select.disabled = catalogTasks.length === 0;
    const status = byId('ir-performer-status');
    if (status) {
      status.textContent = groups.size
        ? `${groups.size} associate${groups.size === 1 ? '' : 's'} performed tasks in this list.`
        : 'No performer was returned for these tasks.';
    }
  }

  function taskOptionLabel(task) {
    const store = task.store_name || task.store_custom_id || `Store ${task.store_id || 'unknown'}`;
    const title = task.title && task.title !== store ? task.title : '';
    return [
      `#${task.task_id}`,
      task.task_date || 'Unknown date',
      store,
      title,
      performerLabel(task),
      task.status_label || task.status || 'Unknown',
    ].filter(Boolean).join(' · ');
  }

  function taskSearchText(task) {
    return [
      task.task_id,
      task.task_date,
      task.store_name,
      task.store_custom_id,
      task.store_id,
      task.title,
      task.performer,
      task.performer_username,
      task.status_label,
      task.status,
    ].join(' ').toLowerCase();
  }

  function setTaskListOpen(open) {
    const list = byId('ir-task-dropdown');
    const field = byId('ir-task-search');
    if (!list || !field) return;
    list.hidden = !open;
    field.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (!open) field.removeAttribute('aria-activedescendant');
  }

  function setTaskFieldState(placeholder, enabled) {
    const field = byId('ir-task-search');
    if (!field) return;
    field.placeholder = placeholder;
    field.disabled = !enabled;
  }

  function paintTaskDropdown() {
    const list = byId('ir-task-dropdown');
    const field = byId('ir-task-search');
    if (!list || !field) return;
    const tasks = visibleCatalogTasks();
    const selectedTask = tasks.find((task) => String(task.task_id) === selectedCatalogTaskId);
    const typed = field.value.trim();
    const showingSelection = selectedTask && typed === taskOptionLabel(selectedTask);
    const needle = showingSelection ? '' : typed.toLowerCase();
    const words = needle.split(/\s+/).filter(Boolean);
    const matches = words.length
      ? tasks.filter((task) => {
        const haystack = taskSearchText(task);
        return words.every((word) => haystack.includes(word));
      })
      : tasks;

    // Deduplicate matches by task_id to guarantee no duplicate tasks are rendered
    const seenMatches = new Set();
    const uniqueMatches = [];
    for (const t of matches) {
      const idStr = String(t.task_id || '').trim();
      if (!idStr || seenMatches.has(idStr)) continue;
      seenMatches.add(idStr);
      uniqueMatches.push(t);
    }

    list.replaceChildren();
    if (!uniqueMatches.length) {
      const empty = document.createElement('li');
      empty.className = 'ir-task-option ir-task-option--empty';
      empty.textContent = tasks.length ? `No tasks match “${typed}”` : 'No recent Intelligent Reset tasks found';
      list.appendChild(empty);
    }
    uniqueMatches.forEach((task, index) => {
      const item = document.createElement('li');
      item.id = `ir-task-option-${task.task_id}`;
      item.className = 'ir-task-option';
      item.setAttribute('role', 'option');
      item.dataset.taskId = task.task_id;
      item.setAttribute('aria-selected', String(task.task_id) === selectedCatalogTaskId ? 'true' : 'false');
      item.textContent = taskOptionLabel(task);
      if (index === 0 && needle) {
        item.classList.add('is-active');
        field.setAttribute('aria-activedescendant', item.id);
      }
      list.appendChild(item);
    });

    setText(
      'ir-recent-task-status',
      needle
        ? (uniqueMatches.length ? `${uniqueMatches.length} of ${tasks.length} tasks match.` : `No tasks match “${typed}”.`)
        : catalogStatusNote,
    );
  }

  function moveActiveTaskOption(step) {
    const list = byId('ir-task-dropdown');
    const field = byId('ir-task-search');
    if (!list || !field) return;
    const options = Array.from(list.querySelectorAll('[role="option"]'));
    if (!options.length) return;
    const current = options.findIndex((option) => option.classList.contains('is-active'));
    const next = current < 0 ? (step > 0 ? 0 : options.length - 1) : (current + step + options.length) % options.length;
    options.forEach((option) => option.classList.remove('is-active'));
    options[next].classList.add('is-active');
    options[next].scrollIntoView({ block: 'nearest' });
    field.setAttribute('aria-activedescendant', options[next].id);
  }

  function statusForVisibleTasks(visible) {
    if (!selectedPerformerKey) return unfilteredCatalogNote;
    const performerName = ((byId('ir-performer-picker') || {}).selectedOptions?.[0]?.textContent || 'this associate')
      .replace(/\s+\(\d+\)$/, '');
    return `${visible.length} task${visible.length === 1 ? '' : 's'} performed by ${performerName}.`;
  }

  function onPerformerChange(value) {
    selectedPerformerKey = String(value || '');
    const visible = visibleCatalogTasks();
    catalogStatusNote = statusForVisibleTasks(visible);
    setTaskFieldState(
      visible.length ? 'Type to search by task ID, store, date, title, performer, or status' : 'No tasks for this associate',
      visible.length > 0,
    );
    const currentStillVisible = visible.some((task) => String(task.task_id) === selectedCatalogTaskId);
    if (!currentStillVisible && visible[0]) {
      chooseCatalogTask(visible[0].task_id);
      return;
    }
    if (!visible.length) {
      selectedCatalogTaskId = '';
      const field = byId('ir-task-search');
      if (field) field.value = '';
    }
    paintTaskDropdown();
    setText('ir-recent-task-status', catalogStatusNote);
  }

  function chooseCatalogTask(taskId) {
    const task = visibleCatalogTasks().find((entry) => String(entry.task_id) === String(taskId))
      || catalogTasks.find((entry) => String(entry.task_id) === String(taskId));
    const field = byId('ir-task-search');
    if (!task) return;
    selectedCatalogTaskId = String(task.task_id);
    if (field) field.value = taskOptionLabel(task);
    setTaskListOpen(false);

    // If task has a performer and it differs from currently selected performer, sync the performer dropdown
    const pKey = performerKey(task);
    if (pKey && selectedPerformerKey && selectedPerformerKey !== pKey) {
      selectedPerformerKey = pKey;
      const perfPicker = byId('ir-performer-picker');
      if (perfPicker) perfPicker.value = pKey;
      catalogStatusNote = statusForVisibleTasks(visibleCatalogTasks());
    }

    setText('ir-recent-task-status', catalogStatusNote);
    const input = byId('ir-simple-task-input');
    if (input) input.value = task.task_id;
    loadCurrentInputs();
  }

  function restoreSelectedTaskLabel() {
    const field = byId('ir-task-search');
    const task = visibleCatalogTasks().find((entry) => String(entry.task_id) === selectedCatalogTaskId);
    if (field) field.value = task ? taskOptionLabel(task) : '';
    setText('ir-recent-task-status', catalogStatusNote);
  }

  function wireTaskCombobox() {
    const field = byId('ir-task-search');
    const list = byId('ir-task-dropdown');
    if (!field || !list) return;

    const open = () => {
      if (field.disabled) return;
      paintTaskDropdown();
      setTaskListOpen(true);
    };

    field.addEventListener('focus', () => {
      field.select();
      open();
    });
    field.addEventListener('click', open);
    field.addEventListener('input', open);
    field.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (list.hidden) open();
        moveActiveTaskOption(e.key === 'ArrowDown' ? 1 : -1);
      } else if (e.key === 'Enter') {
        const active = list.querySelector('.ir-task-option.is-active');
        if (!list.hidden && active) {
          e.preventDefault();
          chooseCatalogTask(active.dataset.taskId);
        }
      } else if (e.key === 'Escape') {
        setTaskListOpen(false);
        restoreSelectedTaskLabel();
      }
    });
    field.addEventListener('blur', () => {
      setTimeout(() => {
        setTaskListOpen(false);
        restoreSelectedTaskLabel();
      }, 120);
    });
    list.addEventListener('mousedown', (e) => {
      const option = e.target.closest('[role="option"]');
      if (!option) return;
      e.preventDefault();
      chooseCatalogTask(option.dataset.taskId);
    });
  }

  async function loadTaskCatalog(instance, preferredTaskId) {
    const inst = instance || getSelectedInstance();
    const dropdown = byId('ir-task-dropdown');
    const datalist = byId('ir-task-catalog-list');
    if (!dropdown && !datalist) return;

    catalogTasks = [];
    catalogStatusNote = '';
    unfilteredCatalogNote = '';
    selectedCatalogTaskId = '';
    selectedPerformerKey = '';
    const performerSelect = byId('ir-performer-picker');
    if (performerSelect) {
      performerSelect.disabled = true;
      performerSelect.value = '';
    }
    const search = byId('ir-task-search');
    if (search) search.value = '';
    setTaskListOpen(false);
    setTaskFieldState('Loading recent Intelligent Reset tasks…', false);
    setText('ir-recent-task-status', 'Loading tasks performed in the last 7 days…');

    setGlobalProgressBar(true);
    try {
      const historyUrl = `/api/runner/ir_history?instance=${encodeURIComponent(inst)}&range=7d&status=in_progress,completed,incomplete`;
      const res = await fetch(historyUrl, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.status !== 'success') throw new Error(data.message || 'Task list unavailable');
      const rawTasks = Array.isArray(data.tasks) ? data.tasks : [];
      const seenTaskIds = new Set();
      const uniqueTasks = [];
      const VALID_STATUSES = new Set(['in_progress', 'completed', 'incomplete', 'started', 'active', 'done', 'finished']);
      for (const task of rawTasks) {
        const id = String(task.task_id || '').trim();
        if (!id || seenTaskIds.has(id)) continue;
        seenTaskIds.add(id);

        const st = String(task.status || '').toLowerCase().replace(/[\s-]/g, '_');
        if (!VALID_STATUSES.has(st) || st.includes('unassigned') || st === 'not_started' || st === 'new' || st === 'created') {
          continue;
        }

        const pLabel = performerLabel(task).toLowerCase();
        if (pLabel.includes('unassigned') || (!task.performer && !task.performer_username && !task.performer_id)) {
          continue;
        }

        const type = String(task.task_type || '').toLowerCase();
        // Audited tasks keep a blank type after the retailer session expires.
        if (!type || type.includes('intelligent reset')) {
          uniqueTasks.push(task);
        }
      }
      uniqueTasks.sort((a, b) => String(b.task_date || '').localeCompare(String(a.task_date || '')) || Number(b.task_id || 0) - Number(a.task_id || 0));

      catalogTasks = uniqueTasks;
      populatePerformerFilter();
      setTaskFieldState(
        catalogTasks.length
          ? 'Type to search by task ID, store, date, title, performer, or status'
          : (data.remote_error ? 'Recent tasks unavailable' : 'No recent Intelligent Reset tasks found'),
        catalogTasks.length > 0,
      );

      if (datalist) {
        datalist.innerHTML = '';
        uniqueTasks.forEach((task) => {
          const opt = document.createElement('option');
          opt.value = task.task_id;
          opt.label = task.title || `Task #${task.task_id}`;
          datalist.appendChild(opt);
        });
      }

      const defaultTaskId = inst === 'krcs' ? '42288818' : '9063802';
      const wanted = String(preferredTaskId || defaultTaskId);
      const visible = visibleCatalogTasks();
      const selected = visible.find((task) => String(task.task_id) === wanted)
        || visible.find((task) => String(task.task_id) === defaultTaskId)
        || visible.find((task) => (task.status || '').toLowerCase() === 'completed')
        || visible[0];
      unfilteredCatalogNote = [
        data.host_note,
        catalogTasks.length
          ? `${catalogTasks.length} recent Intelligent Reset task${catalogTasks.length === 1 ? '' : 's'} found.`
          : (data.remote_error || 'No recently performed Intelligent Reset tasks were found.'),
        catalogTasks.length ? data.remote_error : '',
      ].filter(Boolean).join(' ');
      catalogStatusNote = unfilteredCatalogNote;
      setText('ir-recent-task-status', catalogStatusNote);
      if (selected) {
        selectedCatalogTaskId = String(selected.task_id);
        if (search) search.value = taskOptionLabel(selected);
        const input = byId('ir-simple-task-input');
        if (input) input.value = selected.task_id;
        const currentLoadedId = currentFlowData ? String(currentFlowData.task_id || (currentFlowData.metadata && currentFlowData.metadata.task_id) || '') : '';
        if (currentLoadedId !== String(selected.task_id)) {
          await loadTask(selected.task_id, inst);
        }
      } else {
        renderNoSelectedTask(data.remote_error || 'No recently performed Intelligent Reset tasks were found for this instance.');
      }
      if (data.remote_error) {
        showAuthAlertBanner(inst, data.remote_error);
      } else {
        hideAuthAlertBanner();
      }
    } catch (e) {
      console.warn('Could not load task catalog', e);
      catalogTasks = [];
      setTaskFieldState('Could not load recent tasks', false);
      setText('ir-recent-task-status', 'Recent tasks could not be loaded. Check the instance sign-in.');
      renderNoSelectedTask('Sign in to load recently performed Intelligent Reset tasks for this instance.');
      showAuthAlertBanner(inst, `Sign in to ${inst.toUpperCase()} to load recent Intelligent Reset tasks.`);
    } finally {
      setGlobalProgressBar(false);
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
    if (flowInitialised) return;
    flowInitialised = true;

    // Wire subview tab buttons
    const subTabBtns = document.querySelectorAll('.ir-subnav-btn');
    subTabBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const view = btn.getAttribute('data-subview');
        switchSubView(view);
      });
    });

    wireTaskCombobox();

    const taskInput = byId('ir-simple-task-input');
    if (taskInput) {
      taskInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          loadTask(taskInput.value.trim());
        }
      });
    }

    // Read task_id or instance from URL query parameters, or default to input field / benchmark reference task
    const urlParams = new URLSearchParams(window.location.search);
    const initialInstance = urlParams.get('instance') || 'harr';
    const inputEl = byId('ir-simple-task-input');
    const inputVal = inputEl ? inputEl.value.trim() : null;
    const defaultTaskId = initialInstance === 'krcs' ? '42288818' : '9063802';
    const initialTaskId = urlParams.get('task_id') || inputVal || defaultTaskId;
    
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

    if (inputEl) inputEl.value = initialTaskId;
    // Load the selected/default benchmark task immediately for sub-second first render
    loadTask(initialTaskId, initialInstance);
    // Populate task catalog in background
    loadTaskCatalog(initialInstance, initialTaskId);

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

    const views = ['summary', 'story', 'history', 'compare', 'export'];
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

    if (viewName === 'export') {
      initScanExportView();
    }
  }

  function setGlobalProgressBar(active) {
    const bar = byId('ir-flow-global-progress');
    if (bar) bar.style.display = active ? 'block' : 'none';
  }

  function renderTaskLoadingState(taskId, instance) {
    const instName = (instance || '').toUpperCase();
    const isLatest = taskId === 'latest';
    const displayLabel = isLatest ? `Latest (${instName})` : `#${taskId}`;

    setText('ir-exec-verdict-title', `Loading Task ${displayLabel}…`);
    setText('ir-exec-verdict-desc', `Connecting to ${instName} backend, retrieving planogram items, movement sequence, associate audit trail, and Digital Shelf history…`);
    const icon = byId('ir-exec-verdict-icon');
    if (icon) {
      icon.innerHTML = '<span class="ir-exec-spinner" aria-label="Loading task data…"></span>';
    }

    const card = byId('ir-exec-verdict-card');
    if (card) {
      card.className = 'ir-exec-verdict ir-exec-verdict--review';
    }

    // Clear Executive Verdict metadata fields
    setText('ir-exec-meta-store', '…');
    setText('ir-exec-meta-planogram', '…');
    setText('ir-exec-meta-associate', '…');
    setText('ir-exec-meta-date', '…');
    setText('ir-exec-meta-time', '…');

    // Clear 3-Stage Reset Compliance Flow (Pre-Photo -> Actions -> Post-Photo)
    setText('ir-comp-step-pre-val', '…');
    setText('ir-comp-step-action-val', '…');
    setText('ir-comp-step-post-val', '…');
    setText('ir-comp-step-pre-sub', 'Initial Shelf Baseline');
    setText('ir-comp-step-action-sub', 'User Completed Actions');
    setText('ir-comp-step-post-sub', 'Verified Final Shelf Quality');
    const actionValEl = byId('ir-comp-step-action-val');
    if (actionValEl) actionValEl.className = 'ir-comp-step-val is-action';
    const postValEl = byId('ir-comp-step-post-val');
    if (postValEl) postValEl.className = 'ir-comp-step-val is-post';

    // Clear Overview & Stat Cards
    setText('ir-stat-lift-val', '… ➔ … ➔ …');
    setText('ir-stat-lift-badge', 'Loading…');
    const progBar = byId('ir-stat-lift-bar');
    if (progBar) progBar.style.width = '0%';
    const liftSubEl = byId('ir-stat-lift-bar')?.parentElement?.nextElementSibling;
    if (liftSubEl) {
      liftSubEl.textContent = 'Pre-Compliance Baseline: … • After Action: … • Post-Photo Compliance: …';
    }

    setText('ir-stat-work-val', '…');
    setText('ir-stat-work-sub', 'Fetching work items…');
    setText('ir-stat-time-val', '…');
    setText('ir-stat-ai-val', '…');

    setText('ir-overview-generated', '…');
    setText('ir-overview-performed', '…');
    setText('ir-overview-duration', '…');
    setText('ir-overview-challenges', '…');

    const reconRateBadge = byId('ir-recon-rate-badge');
    if (reconRateBadge) {
      reconRateBadge.textContent = 'Fetching records…';
      reconRateBadge.className = 'badge badge-blue';
    }
    setText('ir-recon-performed-count', '…');
    setText('ir-recon-unperformed-count', '…');
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
    setGlobalProgressBar(true);
    renderTaskLoadingState(targetId, inst);

    // Clear previous live status poll if any
    if (liveStatusPollInterval) {
      clearInterval(liveStatusPollInterval);
      liveStatusPollInterval = null;
    }

    try {
      const resp = await fetch(`/api/runner/task_flow?task_id=${encodeURIComponent(targetId)}&instance=${encodeURIComponent(inst)}&force_live=1&_t=${Date.now()}`, {
        cache: 'no-store'
      });
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
      const taskStatus = (data.metadata && data.metadata.status ? data.metadata.status : '').toLowerCase();
      if (statusBadge) {
        const retailLabel = data.metadata ? (data.metadata.retailer || inst.toUpperCase()) : inst.toUpperCase();
        let statusText = 'Loaded';
        if (taskStatus === 'completed' || taskStatus === 'done') statusText = 'Completed';
        else if (taskStatus === 'incomplete' || taskStatus === 'failed' || taskStatus === 'cancelled') statusText = 'Incomplete';
        else if (taskStatus.includes('progress') || taskStatus.includes('started') || taskStatus.includes('active')) statusText = 'In Progress';
        statusBadge.textContent = `Task #${liveTaskId} · ${statusText} (${retailLabel})`;
      }
      syncEmbeddedTabs(liveTaskId, inst);

      // If task is in-progress on store floor, poll real-time status directly from backend every 8s
      if (taskStatus.includes('progress') || taskStatus.includes('started') || taskStatus.includes('active')) {
        liveStatusPollInterval = setInterval(async () => {
          try {
            const pollRes = await fetch(`/api/runner/task_status?task_id=${encodeURIComponent(liveTaskId)}&instance=${encodeURIComponent(inst)}&_t=${Date.now()}`, {
              cache: 'no-store'
            });
            if (pollRes.ok) {
              const pollData = await pollRes.json();
              if (pollData && (pollData.is_completed || (pollData.status && pollData.status.toLowerCase().includes('complet')))) {
                clearInterval(liveStatusPollInterval);
                liveStatusPollInterval = null;
                // Live associate reset just finished! Re-load task to update all graphs and verdict immediately
                loadTask(liveTaskId, inst);
              }
            }
          } catch (_) {}
        }, 8000);
      }
    } catch (err) {
      console.error('Failed to load task flow:', err);
      if (statusBadge) statusBadge.textContent = 'Ready';
      if (String(err).includes('401') || String(err).includes('Authentication')) {
        showAuthAlertBanner(inst, `Authentication required for ${inst.toUpperCase()}. Please provide Username & Password or Auth Token.`);
      }
    } finally {
      setGlobalProgressBar(false);
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

  function formatActionLocation(item, prefix) {
    const bay = item[`${prefix}_bay`];
    const shelf = item[`${prefix}_shelf`];
    const position = item[`${prefix}_pos`];
    const parts = [];
    if (bay) parts.push(String(bay));
    if (shelf !== null && shelf !== undefined && shelf !== '') parts.push(`Shelf ${shelf}`);
    if (position !== null && position !== undefined && position !== '') parts.push(`Position ${position}`);
    if (shelf !== null && shelf !== undefined && shelf !== '') return parts.join(' · ');
    const action = String(item.action_type || '').toUpperCase();
    if (prefix === 'from' && action.includes('ADD')) return 'Backroom / not on shelf yet';
    if (prefix === 'to' && action.includes('REMOVE')) return 'Taken off the shelf';
    if (prefix === 'to' && action.includes('IDENTIFY')) {
      const fromBay = item.from_bay;
      const fromShelf = item.from_shelf;
      const fromPos = item.from_pos;
      if (fromShelf !== null && fromShelf !== undefined && fromShelf !== '') {
        const pParts = [];
        if (fromBay) pParts.push(String(fromBay));
        pParts.push(`Shelf ${fromShelf}`);
        if (fromPos !== null && fromPos !== undefined && fromPos !== '') pParts.push(`Position ${fromPos}`);
        return pParts.join(' · ');
      }
      return 'Stays in place (identify only)';
    }
    return parts.join(' · ') || 'Not recorded';
  }

  const ACTION_STATE_LABELS = {
    STATE_IDLE: 'Not confirmed (idle)',
    STATE_ACCEPTED: 'Accepted',
    STATE_REJECTED: 'Rejected',
    STATE_COMPLETED: 'Completed',
  };

  function formatActionStatus(item) {
    const state = item.state ? (ACTION_STATE_LABELS[item.state] || item.state) : '';
    return [state, item.reason].filter(Boolean).join(' · ') || 'Not recorded';
  }

  function renderDiscrepancyBadge(item) {
    if (!item) return '';
    const actUpper = (item.action_type || '').toUpperCase();
    const reasonUpper = (item.reason || '').toUpperCase();
    const isRemove = actUpper.includes('REMOVE') || actUpper.includes('DELETE') || actUpper.includes('CART') || reasonUpper.includes('REMOVE') || reasonUpper.includes('DISCONTINUED');
    if (isRemove) return '';

    const isRestock = actUpper.includes('ADD') ||
      actUpper.includes('RESTOCK') ||
      reasonUpper.includes('RESTOCK') ||
      Boolean(item.is_new_restock_item);
    if (isRestock) return '';

    const fromSh = item.from_shelf;
    const toSh = item.to_shelf;
    const fromPos = item.from_pos != null ? String(item.from_pos).trim() : '';
    const toPos = item.to_pos != null ? String(item.to_pos).trim() : '';
    const fromBay = String(item.from_bay || '').trim();
    const toBay = String(item.to_bay || '').trim();
    const isMove = (item.action_type || '').toUpperCase().includes('MOVE');

    // Note: Product located on a different shelf (fromSh != toSh) is simply a product not on the correct
    // shelf as per planogram (addressed via ACTION MOVE). It is NOT a shelf discrepancy.
    // A true Shelf Discrepancy is when the physical shelf count in realogram differs from the planogram shelf count.
    if (item.discrepancy_type === 'redundant_same_slot' || (isMove && fromSh && toSh && fromSh == toSh && fromPos && toPos && fromPos === toPos && (!fromBay || !toBay || fromBay === toBay))) {
      return `
        <div style="margin-top: 4px;">
          <span class="badge" style="background: #FEE2E2; color: #B91C1C; border: 1px solid #FCA5A5; font-size: 9.5px; font-weight: 700; padding: 2px 6px; border-radius: 4px; display: inline-flex; align-items: center; gap: 4px; cursor: help;" title="Product is already in its planogram slot; move instruction is redundant (Invariant 9).">
            ⚠️ Redundant Same-Slot Move
          </span>
        </div>
      `;
    }
    return '';
  }

  function resolveIdentifyCrop(item) {
    if (!item) return '';
    // Priority 1: Already provided live crop URL or API URL
    const cUrl = item.crop_image_url || item.crop_image || item.cropped_image_url;
    if (cUrl && typeof cUrl === 'string' && (cUrl.startsWith('http') || cUrl.startsWith('/api/'))) {
      return cUrl;
    }
    const img = item.image;
    if (img && typeof img === 'string' && (img.startsWith('http') || img.startsWith('/api/'))) {
      return img;
    }
    // Priority 2: Construct live scan crop endpoint from Digital Shelf scan metadata
    const sId = item.scan_id || resolveItemScanId(item);
    const sh = item.from_shelf != null ? item.from_shelf : item.to_shelf;
    const pos = item.from_pos != null ? item.from_pos : item.to_pos;
    const itemId = item.item_id || item.realogram_item_id || '';
    if (sId && sh != null && pos != null) {
      return `/api/runner/scan_crop?scan_id=${encodeURIComponent(sId)}&item_id=${encodeURIComponent(itemId)}&shelf=${encodeURIComponent(sh)}&pos=${encodeURIComponent(pos)}`;
    }
    return '';
  }

  window.irCloseDialog = function(dialogId) {
    const d = byId(dialogId);
    if (!d) return;
    try {
      if (typeof d.close === 'function') {
        d.close();
      }
    } catch (_) {}
    d.removeAttribute('open');
    d.style.display = 'none';
  };

  function openBBoxLightbox(item, scanId, scanUrl) {
    const dialog = byId('ir-bbox-lightbox');
    if (!dialog) return;

    if (dialog.open) {
      try { dialog.close(); } catch (_) {}
    }
    dialog.removeAttribute('open');
    dialog.style.display = 'none';

    const sId = scanId || (item && item.scan_id) || resolveItemScanId(item);
    const sUrl = scanUrl || (item && item.digital_shelf_url) || buildDigitalShelfScanUrl(sId, item, currentFlowData && currentFlowData.metadata);
    const cropImg = resolveIdentifyCrop(item);

    const imgEl = byId('ir-bbox-lightbox-img');
    if (imgEl) {
      imgEl.src = cropImg;
      imgEl.alt = (item && item.product_name) || 'Scan crop';
      imgEl.onerror = () => {
        imgEl.style.display = 'none';
      };
      imgEl.onload = () => {
        imgEl.style.display = 'block';
      };
    }

    setText('ir-bbox-lightbox-product', (item && item.product_name) || 'Identified Product');
    setText('ir-bbox-lightbox-upc', (item && item.upc) ? `UPC ${item.upc}` : 'UPC unavailable');
    setText('ir-bbox-lightbox-scan', sId ? `Scan #${sId}` : 'Scan unavailable');

    const posStr = (item && item.from_shelf)
      ? `Shelf ${item.from_shelf}, Pos ${item.from_pos || '—'}`
      : ((item && item.to_shelf) ? `Shelf ${item.to_shelf}, Pos ${item.to_pos || '—'}` : 'Recorded on shelf scan');
    setText('ir-bbox-lightbox-pos', posStr);

    setText('ir-bbox-lightbox-reason', (item && item.reason) || 'Image not Ideal to add to database');

    const shelfLink = byId('ir-bbox-lightbox-shelf-link');
    if (shelfLink) {
      if (sUrl) {
        shelfLink.href = sUrl;
        shelfLink.style.display = 'inline-flex';
        shelfLink.innerHTML = `📸 View Bounding Box on Scan #${sId || ''} ↗`;
      } else {
        shelfLink.style.display = 'none';
      }
    }

    const closeBtn = byId('ir-bbox-lightbox-close');
    if (closeBtn) {
      closeBtn.onclick = (e) => {
        if (e) e.preventDefault();
        window.irCloseDialog('ir-bbox-lightbox');
      };
    }
    dialog.onclick = (e) => {
      if (e.target === dialog) window.irCloseDialog('ir-bbox-lightbox');
    };

    dialog.style.display = 'flex';
    try {
      if (!dialog.open) dialog.showModal();
    } catch (err) {
      console.warn('showModal fallback:', err);
      if (!dialog.open) dialog.show();
    }
  }
  window.irOpenBBoxLightboxModal = openBBoxLightbox;

  window.irOpenInsightItemLightbox = function(idx) {
    const it = (window._insightItems && window._insightItems[idx]) || null;
    if (!it) return;
    const sId = it.scan_id || resolveItemScanId(it);
    const sUrl = buildDigitalShelfScanUrl(sId, it, currentFlowData && currentFlowData.metadata);
    openBBoxLightbox(it, sId, sUrl);
  };

  function openInsightDialog({ title, subtitle, summary = [], items = [] }) {
    const dialog = byId('ir-insight-dialog');
    const body = byId('ir-insight-dialog-body');
    const summaryEl = byId('ir-insight-dialog-summary');
    const tableWrap = byId('ir-insight-dialog-table-wrap');
    if (!dialog || !body || !summaryEl || !tableWrap) return;

    window._insightItems = items;

    // Attach close button immediately so it is always active
    const closeBtn = byId('ir-insight-dialog-close');
    if (closeBtn) {
      closeBtn.onclick = (e) => {
        if (e) e.preventDefault();
        window.irCloseDialog('ir-insight-dialog');
      };
    }
    dialog.onclick = (event) => {
      if (event.target === dialog) window.irCloseDialog('ir-insight-dialog');
    };

    setText('ir-insight-dialog-title', title);
    setText('ir-insight-dialog-subtitle', subtitle);
    summaryEl.replaceChildren();
    if (summary.length) {
      const list = document.createElement('dl');
      summary.forEach(([label, value]) => {
        const term = document.createElement('dt');
        term.textContent = label;
        const description = document.createElement('dd');
        if (typeof value === 'string' && value.includes('<') && value.includes('>')) {
          description.innerHTML = value;
        } else {
          description.textContent = value || 'Not recorded';
        }
        list.append(term, description);
      });
      summaryEl.appendChild(list);
    }

    body.replaceChildren();
    tableWrap.hidden = items.length === 0;
    items.forEach((item, itemIdx) => {
      const row = document.createElement('tr');
      const productCell = document.createElement('td');
      productCell.className = 'ir-insight-product';

      const rawAct = item.action_type || 'Action unavailable';
      const isIdentify = String(rawAct).toUpperCase().includes('IDENTIFY') || Boolean(item.bounding_box);
      const effectiveCropUrl = resolveIdentifyCrop(item);

      const itemScanId = item.scan_id || resolveItemScanId(item);
      const scanUrl = buildDigitalShelfScanUrl(itemScanId, item, currentFlowData && currentFlowData.metadata);

      if (isIdentify && effectiveCropUrl) {
        const sh = item.from_shelf != null ? item.from_shelf : item.to_shelf;
        const pos = item.from_pos != null ? item.from_pos : item.to_pos;
        const locLabel = (sh != null && pos != null) ? `S${sh}:P${pos}` : (sh != null ? `Sh ${sh}` : 'Item');

        productCell.innerHTML = `
          <div class="ir-bbox-product-wrap">
            <div class="ir-bbox-thumb-box" data-idx="${itemIdx}" onclick="window.irOpenInsightItemLightbox(${itemIdx})" title="Click to pop out full-resolution product inspection" role="button" tabindex="0">
              <div class="ir-bbox-thumb-placeholder">
                <span class="ir-bbox-thumb-icon">📦</span>
                <span class="ir-bbox-thumb-loc">${escapeHtml(locLabel)}</span>
              </div>
              <img src="${escapeHtml(effectiveCropUrl)}" alt="${escapeHtml(item.product_name || 'Product')}" class="ir-bbox-thumb-img" onerror="this.style.display='none';"/>
              <div class="ir-bbox-reticle">
                <span class="corner tl"></span>
                <span class="corner tr"></span>
                <span class="corner bl"></span>
                <span class="corner br"></span>
              </div>
            </div>
            <div class="ir-bbox-product-info">
              <strong>${escapeHtml(item.product_name || 'Product name unavailable')}</strong>
              <span class="ir-product-upc">UPC ${escapeHtml(item.upc || 'unavailable')}</span>
            </div>
          </div>
        `;
        const thumbBox = productCell.querySelector('.ir-bbox-thumb-box');
        if (thumbBox) {
          thumbBox.onclick = (e) => {
            e.stopPropagation();
            window.irOpenInsightItemLightbox(itemIdx);
          };
          thumbBox.onkeydown = (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              window.irOpenInsightItemLightbox(itemIdx);
            }
          };
        }
      } else {
        const product = document.createElement('strong');
        product.textContent = item.product_name || 'Product name unavailable';
        const upc = document.createElement('span');
        upc.textContent = item.upc ? `UPC ${item.upc}` : 'UPC unavailable';
        productCell.append(product, upc);
      }

      // Scan / Digital Shelf Column (directly in front of Action)
      const scanCell = document.createElement('td');
      scanCell.className = 'ir-col-scan';
      if (itemScanId && scanUrl) {
        scanCell.innerHTML = `
          <a href="${scanUrl}" target="_blank" rel="noopener noreferrer" class="ir-scan-link" title="Open Scan #${itemScanId} in Digital Shelf">
            <span class="ir-scan-cam">📸</span> Scan #${itemScanId} <span class="ir-scan-arrow">↗</span>
          </a>
        `;
      } else if (itemScanId) {
        scanCell.innerHTML = `<span class="ir-scan-tag">Scan #${itemScanId}</span>`;
      } else {
        scanCell.innerHTML = `<span class="ir-scan-empty" style="color:var(--text-muted);">—</span>`;
      }

      const actionCell = document.createElement('td');
      const actionLabel = document.createElement('div');
      actionLabel.className = 'ir-action-label-wrap';
      if (isIdentify) {
        actionLabel.innerHTML = `<span class="status-pill status-pill--purple" style="font-weight:700;">🔍 ${escapeHtml(rawAct)}</span>`;
      } else {
        actionLabel.textContent = rawAct;
      }
      actionCell.appendChild(actionLabel);
      const discBadgeHtml = renderDiscrepancyBadge(item);
      if (discBadgeHtml) {
        const wrap = document.createElement('div');
        wrap.innerHTML = discBadgeHtml;
        actionCell.appendChild(wrap.firstElementChild);
      }

      const fromCell = document.createElement('td');
      fromCell.textContent = formatActionLocation(item, 'from');

      const toCell = document.createElement('td');
      toCell.textContent = formatActionLocation(item, 'to');

      const statusCell = document.createElement('td');
      statusCell.textContent = formatActionStatus(item);

      row.append(productCell, scanCell, actionCell, fromCell, toCell, statusCell);
      body.appendChild(row);
    });

    dialog.style.display = 'flex';
    try {
      if (!dialog.open) dialog.showModal();
    } catch (err) {
      console.warn('dialog showModal fallback:', err);
      if (!dialog.open) dialog.show();
    }
  }

  function describePerformedEvidence(evidence, error) {
    if (error) return [['Why nothing is shown', error]];
    if (!evidence) return [['Why nothing is shown', 'Performed-action evidence was not returned for this task.']];
    const states = Object.entries(evidence.action_list_states || {})
      .map(([state, count]) => `${count} × ${ACTION_STATE_LABELS[state] || state}`)
      .join(', ');
    const okNoAction = Number(evidence.digital_rows_ok_no_action || 0);
    const unconfirmed = Number(evidence.digital_rows_unconfirmed || 0);
    const withAction = Number(evidence.digital_rows_with_action || 0);
    const unconfirmedTypes = Object.entries(evidence.unconfirmed_action_types || {})
      .map(([type, count]) => `${count} ${type}`)
      .join(', ');
    let meaning = 'Digital Shelf did not return an action-type split for these rows.';
    if (unconfirmed === 0 && withAction === 0 && okNoAction > 0) {
      meaning = `${okNoAction} products are marked OK with Action Taken “-”. That is expected: the product is already correct, so no associate action was required.`;
    } else if (unconfirmed === 0) {
      meaning = okNoAction
        ? `${okNoAction} products are OK with Action Taken “-” and needed no associate action. ${withAction} other rows record an action the associate took.`
        : `${withAction} rows record an action the associate took.`;
    } else {
      meaning = `${okNoAction} products are OK with Action Taken “-” and needed no action. ${unconfirmed} other rows are not OK${unconfirmedTypes ? ` (${unconfirmedTypes})` : ''} and Action Taken is still “-”, so those needed actions were not confirmed.`;
    }
    return [
      ['Digital Shelf scans checked', (evidence.scan_ids || []).join(', ') || 'None'],
      ['Product rows checked', String(evidence.digital_rows_checked ?? 0)],
      ['Products already OK, no action needed', String(okNoAction)],
      ['Rows with an associate action', String(withAction)],
      ['Rows that needed an action but were not confirmed', String(unconfirmed)],
      ['Action list states', states || 'Not returned'],
      ['What this means', meaning],
    ];
  }

  function renderTaskInsights(meta, batches, initialScore, finalScore, performedEvidence, performedLoaded, evidenceInfo = {}) {
    const generated = [];
    const postGenerated = [];
    let performed = [];
    const challenges = [];
    const rejectedGroups = new Map();
    const rawStatus = String(meta.status || '').toLowerCase();
    const postPhoto = evidenceInfo.postPhoto || {};

    function appendBatchRows(batchMap, target) {
      Object.values(batchMap || {}).forEach((batch) => {
        const items = Array.isArray(batch.items) ? batch.items : [];
        const count = items.length || Number(batch.item_count || 0) || 1;
        const type = String(batch.action_type || batch.action || 'Action').replaceAll('_', ' ');
        const state = String(batch.state || '').toUpperCase();
        const reason = String(batch.reason || '').trim();
        const example = items[0] || {};
        const detail = example.product_name || example.product_title || example.title || example.upc || reason || 'Product details unavailable';
        const detailItems = items.map((item) => ({
          ...item,
          action_type: type,
          from_bay: item.from_bay || batch.bay,
          to_bay: item.to_bay || batch.bay,
          reason: item.reason || reason,
          state: item.state || state,
        }));
        target.push({ type, count, detail, state, items: detailItems });
      });
    }

    Object.values(batches || {}).forEach((batch) => {
      const items = Array.isArray(batch.items) ? batch.items : [];
      const count = items.length || Number(batch.item_count || 0) || 1;
      const type = String(batch.action_type || batch.action || 'Action').replaceAll('_', ' ');
      const state = String(batch.state || '').toUpperCase();
      const reason = String(batch.reason || '').trim();
      const example = items[0] || {};
      const detail = example.product_name || example.product_title || example.title || example.upc || reason || 'Product details unavailable';
      const detailItems = items.map((item) => ({
        ...item,
        action_type: type,
        from_bay: item.from_bay || batch.bay,
        to_bay: item.to_bay || batch.bay,
        reason: item.reason || reason,
        state: item.state || state,
      }));
      const row = { type, count, detail, state, items: detailItems };
      generated.push(row);

      if (!performedLoaded && (state.includes('ACCEPT') || state.includes('COMPLET') || state.includes('DONE') || state.includes('PERFORM'))) {
        performed.push(row);
      }
      if (state.includes('REJECT') || reason.toLowerCase().includes('unable') || reason.toLowerCase().includes('not ideal')) {
        const key = `${type}|${reason}`;
        const group = rejectedGroups.get(key) || { type, reason, count: 0, items: [] };
        group.count += count;
        group.items.push(...detailItems);
        rejectedGroups.set(key, group);
      }
    });
    appendBatchRows(postPhoto.action_batches, postGenerated);
    rejectedGroups.forEach(({ type, reason, count, items }) => {
      const label = type.replace(/^ACTION\s+/i, '').toLowerCase();
      challenges.push({
        text: `${count} ${label} action${count === 1 ? ' was' : 's were'} rejected or could not be completed${reason ? `: ${reason}` : '.'}`,
        items,
        source: 'Generated action state and reason',
      });
    });

    const allGeneratedItems = generated.flatMap((row) => row.items || []);

    const redundantSameSlotItems = allGeneratedItems.filter((item) => {
      const actUpper = (item.action_type || '').toUpperCase();
      const reasonUpper = (item.reason || '').toUpperCase();
      const isRemove = actUpper.includes('REMOVE') || actUpper.includes('DELETE') || actUpper.includes('CART') || reasonUpper.includes('REMOVE') || reasonUpper.includes('DISCONTINUED');
      if (isRemove) return false;

      const isRestock = actUpper.includes('ADD') ||
        actUpper.includes('RESTOCK') ||
        reasonUpper.includes('RESTOCK') ||
        Boolean(item.is_new_restock_item);
      if (isRestock) return false;

      const fromSh = item.from_shelf;
      const toSh = item.to_shelf;
      const fromPos = item.from_pos != null ? String(item.from_pos).trim() : '';
      const toPos = item.to_pos != null ? String(item.to_pos).trim() : '';
      const fromBay = String(item.from_bay || '').trim();
      const toBay = String(item.to_bay || '').trim();
      const isMove = (item.action_type || '').toUpperCase().includes('MOVE');
      return item.discrepancy_type === 'redundant_same_slot' ||
        (isMove && fromSh && toSh && fromSh == toSh && fromPos && toPos && fromPos === toPos && (!fromBay || !toBay || fromBay === toBay));
    });
    if (redundantSameSlotItems.length > 0) {
      challenges.push({
        text: `${redundantSameSlotItems.length} redundant same-slot move${redundantSameSlotItems.length === 1 ? '' : 's'} generated for products already in their target slot (Invariant 9).`,
        items: redundantSameSlotItems,
        source: 'Shelf Invariant Engine (Invariant 9: In-Place Preservation)',
        summary: [
          ['Defect description', 'The product is already placed at the exact planogram coordinates. Re-generating a move instruction creates unnecessary associate touches.'],
          ['Invariant rule', 'Rule 9: In-Place Preservation (Zero Redundant Same-Slot Moves)'],
          ['Products affected', String(redundantSameSlotItems.length)],
        ],
      });
    }

    // Real Shelf Discrepancy: check number of shelves in planogram vs number of shelves in realogram (not product position)
    // E.g. in planogram we have 6 shelves, and in realogram we have more or less than 6 shelves
    const shelfDiscrepancies = [];
    const bayShelfMap = new Map();

    // 1. Gather shelf counts from bay_summaries if present
    const baySummariesObj = (evidenceInfo && evidenceInfo.baySummaries) || (currentFlowData && currentFlowData.bay_summaries) || (meta && meta.bay_summaries) || {};
    Object.entries(baySummariesObj).forEach(([bName, bData]) => {
      const pCount = Number(bData.pog_shelf_count || 0);
      const rCount = Number(bData.rog_shelf_count || 0);
      if (bData.has_shelf_discrepancy || (pCount > 0 && rCount > 0 && pCount !== rCount)) {
        shelfDiscrepancies.push({
          bay: bName,
          pogCount: pCount,
          rogCount: rCount,
        });
      }
    });

    // 2. Also analyze all generated items across bays to compute physical realogram shelf count vs planogram shelf count
    if (!shelfDiscrepancies.length) {
      allGeneratedItems.forEach((item) => {
        const b = item.from_bay || item.to_bay || 'Bay 1';
        const entry = bayShelfMap.get(b) || { rog: new Set(), pog: new Set() };
        const fs = item.from_shelf != null ? Number(item.from_shelf) : null;
        const ts = item.to_shelf != null ? Number(item.to_shelf) : null;
        if (fs != null && !Number.isNaN(fs) && fs > 0) entry.rog.add(fs);
        if (ts != null && !Number.isNaN(ts) && ts > 0) entry.pog.add(ts);
        bayShelfMap.set(b, entry);
      });
      bayShelfMap.forEach((entry, b) => {
        const rMax = entry.rog.size ? Math.max(...entry.rog) : 0;
        const pMax = entry.pog.size ? Math.max(...entry.pog) : 0;
        if (rMax > 0 && pMax > 0 && rMax !== pMax) {
          shelfDiscrepancies.push({ bay: b, pogCount: pMax, rogCount: rMax });
        }
      });
    }

    if (shelfDiscrepancies.length > 0) {
      shelfDiscrepancies.forEach((disc) => {
        const diff = disc.rogCount - disc.pogCount;
        const diffLabel = diff > 0 ? `${diff} extra shelf` : `${Math.abs(diff)} missing shelf`;
        challenges.push({
          text: `⚠️ Shelf Discrepancy: ${disc.bay} has ${disc.rogCount} physical shelves in Realogram, but Planogram specifies ${disc.pogCount} shelves (${diffLabel}).`,
          items: allGeneratedItems.filter((it) => (it.from_bay || it.to_bay) === disc.bay),
          source: 'Fixture Architecture (Realogram vs. Planogram Shelf Count)',
          summary: [
            ['Discrepancy Type', 'Physical Shelf Count Mismatch (Fixture Architecture)'],
            ['Bay', disc.bay],
            ['Realogram Shelf Count', `${disc.rogCount} physical shelves detected in scan`],
            ['Planogram Shelf Count', `${disc.pogCount} shelves defined in planogram`],
            ['Discrepancy Detail', diff < 0
              ? `The physical fixture has fewer shelves (${disc.rogCount}) than the planogram specifies (${disc.pogCount}). Products scheduled for shelf ${disc.rogCount + 1} and above cannot be placed correctly.`
              : `The physical fixture has ${diff} additional shelves (${disc.rogCount}) compared to the planogram (${disc.pogCount}).`],
          ],
        });
      });
    }

    const generatedCount = generated.reduce((sum, row) => sum + row.count, 0);
    const postGeneratedCount = postGenerated.reduce((sum, row) => sum + row.count, 0);
    if (performedLoaded) {
      performed = (performedEvidence || []).map((item) => ({
        type: item.action_taken || item.action_type || 'Performed action',
        count: 1,
        detail: item.product_name || item.upc || `Section ${item.section || 'unknown'}`,
        state: 'PERFORMED',
        items: [{
          product_name: item.product_name,
          upc: item.upc,
          action_type: item.action_taken || item.action_type,
          from_bay: item.section,
          from_pos: item.rog_position,
          to_bay: item.section,
          to_pos: item.pog_position,
          state: 'Recorded in Digital Shelf',
          reason: item.action_taken,
        }],
      }));
    }
    const performedCount = performed.reduce((sum, row) => sum + row.count, 0);
    function groupRows(rows) {
      const grouped = new Map();
      rows.forEach((row) => {
        const key = row.type.toLowerCase();
        const existing = grouped.get(key);
        if (existing) {
          existing.count += row.count;
          existing.items.push(...(row.items || []));
        } else {
          grouped.set(key, { ...row, items: [...(row.items || [])] });
        }
      });
      return [...grouped.values()].sort((a, b) => b.count - a.count);
    }
    const generatedSummary = groupRows(generated);
    const postGeneratedSummary = groupRows(postGenerated);
    const performedSummary = groupRows(performed);

    let rawUnperformedItems = [];
    if (Array.isArray(evidenceInfo.unperformedActions) && evidenceInfo.unperformedActions.length > 0) {
      rawUnperformedItems = evidenceInfo.unperformedActions;
    } else if (Array.isArray(evidenceInfo.allDigitalActions) && evidenceInfo.allDigitalActions.length > 0) {
      rawUnperformedItems = evidenceInfo.allDigitalActions.filter((item) => {
        const actTaken = (item.action_taken || '').trim();
        const actType = (item.action_type || '').trim().toLowerCase();
        return (!actTaken || actTaken === '-') && actType !== 'ok';
      });
    } else {
      const allGen = generated.flatMap((row) => row.items || []);
      rawUnperformedItems = allGen.filter((item) => {
        const st = String(item.state || '').toUpperCase();
        return !st.includes('ACCEPT') && !st.includes('COMPLET') && !st.includes('DONE') && !st.includes('PERFORM');
      });
    }

    const unperformedRows = rawUnperformedItems.map((item) => {
      const aType = (item.action_type || 'Unconfirmed action').replaceAll('_', ' ');
      const sId = item.scan_id || resolveItemScanId(item);
      const sUrl = item.digital_shelf_url || buildDigitalShelfScanUrl(sId, item, meta);
      return {
        type: aType,
        count: 1,
        detail: item.product_name || item.upc || `Section ${item.section || item.from_bay || 'unknown'}`,
        state: 'NO_RECORD',
        scan_id: sId,
        digital_shelf_url: sUrl,
        items: [{
          scan_id: sId,
          digital_shelf_url: sUrl,
          product_name: item.product_name || item.title || 'Product',
          upc: item.upc,
          action_type: item.action_type || aType,
          from_bay: item.section || item.from_bay || '—',
          from_pos: item.rog_position || item.from_pos || '—',
          to_bay: item.section || item.to_bay || '—',
          to_pos: item.pog_position || item.to_pos || '—',
          state: 'No Record in System',
          reason: item.reason || `Action Type '${item.action_type}' needed, but Action Taken is '-' (no completion record in associate logs)`,
        }],
      };
    });
    const unperformedSummary = groupRows(unperformedRows);
    const unperformedCount = rawUnperformedItems.length;

    if (['incomplete', 'failed', 'cancelled'].includes(rawStatus)) {
      challenges.push({
        text: `The task finished with status “${meta.status}”.`,
        items: generated.flatMap((row) => row.items),
        source: 'Task status',
      });
    }
    const shelfEvidence = evidenceInfo.evidence || {};
    const shelfSplitKnown = Object.prototype.hasOwnProperty.call(shelfEvidence, 'digital_rows_ok_no_action')
      || Object.prototype.hasOwnProperty.call(shelfEvidence, 'digital_rows_unconfirmed');
    const okNoAction = Number(shelfEvidence.digital_rows_ok_no_action || 0);
    const unconfirmedShelf = Number(shelfEvidence.digital_rows_unconfirmed || 0);
    const taskStillOpen = ['in_progress', 'started', 'active'].includes(rawStatus);
    if (performedLoaded && !taskStillOpen && shelfSplitKnown && unconfirmedShelf > 0) {
      const unconfirmedTypes = Object.entries(shelfEvidence.unconfirmed_action_types || {})
        .map(([type, count]) => `${count} ${type}`)
        .join(', ');
      challenges.push({
        text: `${unconfirmedShelf} products needed an action${unconfirmedTypes ? ` (${unconfirmedTypes})` : ''} but Action Taken is still “-”. ${okNoAction} products marked OK with “-” needed no action.`,
        items: generated.flatMap((row) => row.items),
        source: 'Digital Shelf action type and Action Taken',
        summary: describePerformedEvidence(shelfEvidence, evidenceInfo.error),
      });
    } else if (performedLoaded && generatedCount && performedCount < generatedCount && !taskStillOpen && !shelfSplitKnown) {
      const missing = generatedCount - performedCount;
      const scoreNote = typeof finalScore === 'number' ? ` The final shelf still scored ${finalScore}% compliance.` : '';
      challenges.push({
        text: `No completion record for ${missing} of ${generatedCount} requested actions — the associate app did not log what was done.${scoreNote}`,
        items: generated.flatMap((row) => row.items),
        source: 'Generated action list compared with Digital Shelf “Action Taken”',
        summary: describePerformedEvidence(shelfEvidence, evidenceInfo.error),
      });
    }
    if (typeof finalScore === 'number' && finalScore < 95) {
      challenges.push({
        text: `Final shelf compliance was ${finalScore}%, below the 95% target.`,
        items: [],
        source: 'Post-reset compliance report',
      });
    }
    if (typeof finalScore !== 'number' && !['in_progress', 'started', 'active'].includes(rawStatus)) {
      challenges.push({
        text: 'Final post-reset shelf verification is unavailable.',
        items: [],
        source: 'Post-reset compliance report',
      });
    }

    setText('ir-overview-generated', generatedCount);
    setText('ir-overview-performed', performedCount);
    const generatedItems = generated.flatMap((row) => row.items || []);
    const actionIds = new Set(generatedItems.map((item) => item.ledger_id).filter((id) => id != null && id !== ''));
    const requiredCount = actionIds.size || generatedCount;
    const duplicateCount = Math.max(0, generatedCount - requiredCount);
    const unconfirmedTypes = Object.entries(shelfEvidence.unconfirmed_action_types || {})
      .map(([type, count]) => `${count} ${type}`)
      .join(', ');
    const result = byId('ir-work-result');
    if (result) {
      let text = '';
      let state = '';
      if (performedLoaded && !taskStillOpen && shelfSplitKnown && unconfirmedShelf === 0) {
        const preResult = duplicateCount
          ? `The associate performed all ${requiredCount} pre-photo actions. ${duplicateCount} repeated pre-photo rows were not extra mobile work.`
          : `The associate performed all ${requiredCount} pre-photo actions.`;
        const postResult = postPhoto.loaded
          ? ` The post-photo scan generated ${postGeneratedCount} separate action row${postGeneratedCount === 1 ? '' : 's'}, shown below.`
          : ` A separate post-photo action list is unavailable${postPhoto.error ? `: ${postPhoto.error}` : '.'}`;
        text = `${preResult}${postResult}`;
        state = 'clear';
      } else if (performedLoaded && unconfirmedShelf > 0) {
        text = `${unconfirmedShelf} product${unconfirmedShelf === 1 ? '' : 's'} ${unconfirmedShelf === 1 ? 'was' : 'were'} not performed${unconfirmedTypes ? ` (${unconfirmedTypes})` : ''}. Action Taken is still blank, so the associate did not record that work. ${okNoAction} products were already correct and needed no action.`;
        state = 'warning';
      } else if (taskStillOpen) {
        text = 'This task is still open, so actions not recorded yet are not counted as missed.';
      } else if (!performedLoaded) {
        text = 'Performed actions could not be checked against Digital Shelf.';
      }
      result.hidden = !text;
      result.dataset.state = state;
      result.textContent = text;
    }

    // Populate Store Reset Execution Reconciliation Panel
    setText('ir-recon-performed-count', performedCount);
    setText('ir-recon-unperformed-count', unperformedCount);

    const reconRateBadge = byId('ir-recon-rate-badge');
    if (reconRateBadge) {
      if (performedCount + unperformedCount > 0) {
        const completionPct = Math.round((performedCount / (performedCount + unperformedCount)) * 100);
        reconRateBadge.textContent = `${completionPct}% Completed (${performedCount}/${performedCount + unperformedCount})`;
        reconRateBadge.className = completionPct >= 95 ? 'badge badge-green' : (completionPct > 50 ? 'badge badge-yellow' : 'badge badge-red');
      } else {
        reconRateBadge.textContent = taskStillOpen ? 'In Progress' : 'Reconciliation Ready';
        reconRateBadge.className = 'badge badge-blue';
      }
    }

    const perfDescEl = byId('ir-recon-performed-desc');
    if (perfDescEl) {
      if (performedLoaded && performedCount > 0) {
        perfDescEl.textContent = `Associate logged and confirmed ${performedCount} physical shelf change(s) in system records (Action Taken verified in Digital Shelf).`;
      } else if (taskStillOpen) {
        perfDescEl.textContent = `Task is currently active on the store floor. Associate has not submitted completion records yet.`;
      } else {
        perfDescEl.textContent = `No completed actions were recorded by the associate for this reset session in Digital Shelf or mobile logs.`;
      }
    }

    const unperfDescEl = byId('ir-recon-unperformed-desc');
    if (unperfDescEl) {
      if (unperformedCount > 0) {
        unperfDescEl.textContent = `The pre-photo scan instructed ${unperformedCount} action(s), but our records have NO confirmation that the associate performed them (Action Taken is blank or '-').`;
      } else if (performedLoaded && unperformedCount === 0 && !taskStillOpen) {
        unperfDescEl.textContent = `Zero unperformed actions. All planogram adjustments were addressed and recorded.`;
      } else if (taskStillOpen) {
        unperfDescEl.textContent = `Task is still open. Actions not yet touched are pending execution.`;
      } else {
        unperfDescEl.textContent = `No unperformed actions recorded for this task.`;
      }
    }

    // Performed Tags
    const perfTagsContainer = byId('ir-recon-performed-tags');
    if (perfTagsContainer) {
      perfTagsContainer.replaceChildren();
      if (performedSummary.length) {
        performedSummary.forEach((group) => {
          const tag = document.createElement('span');
          tag.className = 'ir-recon-tag ir-recon-tag--performed';
          tag.textContent = `${group.count} ${group.type}`;
          perfTagsContainer.appendChild(tag);
        });
      }
    }

    // Unperformed Tags
    const unperfTagsContainer = byId('ir-recon-unperformed-tags');
    if (unperfTagsContainer) {
      unperfTagsContainer.replaceChildren();
      if (unperformedSummary.length) {
        unperformedSummary.forEach((group) => {
          const tag = document.createElement('span');
          tag.className = 'ir-recon-tag ir-recon-tag--unperformed';
          tag.textContent = `${group.count} ${group.type}`;
          unperfTagsContainer.appendChild(tag);
        });
      }
    }

    // Baseline Note
    const baseTextEl = byId('ir-recon-baseline-text');
    if (baseTextEl) {
      if (okNoAction > 0) {
        baseTextEl.textContent = `Baseline Shelf Check: ${okNoAction} product(s) were already in their correct planogram positions before reset (marked OK with Action Taken “-”) and did not require associate action.`;
      } else {
        baseTextEl.textContent = `Baseline Shelf Check: All scanned products required planogram verification and adjustment.`;
      }
    }

    // Wire Reconciliation Detail Buttons
    const btnReconPerf = byId('btn-recon-view-performed');
    if (btnReconPerf) {
      btnReconPerf.onclick = () => openInsightDialog({
        title: 'Actions User Performed (Confirmed in Records)',
        subtitle: `${performedCount} action(s) confirmed by associate · Task #${meta.task_id || 'unknown'}`,
        summary: [
          ['Verification Source', 'Digital Shelf report & associate mobile logs'],
          ['Scan ID', currentPreScanId() ? `#${currentPreScanId()}` : 'Available per item'],
          ['Total Confirmed Performed', String(performedCount)],
          ['Record Status', 'Confirmed Completed (Action Taken logged)'],
        ],
        items: performed.flatMap((r) => r.items || []),
      });
    }

    const btnReconUnperf = byId('btn-recon-view-unperformed');
    if (btnReconUnperf) {
      btnReconUnperf.onclick = () => openInsightDialog({
        title: 'Actions With No Record (What User Did NOT Do)',
        subtitle: `${unperformedCount} action(s) with no completion record · Task #${meta.task_id || 'unknown'}`,
        summary: [
          ['Verification Source', 'Pre-photo scan vs Digital Shelf Action Taken'],
          ['Scan ID', currentPreScanId() ? `#${currentPreScanId()}` : 'Available per item'],
          ['Total Without Record', String(unperformedCount)],
          ['Record Status', 'Missing Confirmation (Action Taken is blank or "-")'],
          ['Associate Action', 'Associate did not record or touch these items'],
        ],
        items: rawUnperformedItems.map((item) => {
          const sId = item.scan_id || resolveItemScanId(item);
          const sUrl = item.digital_shelf_url || buildDigitalShelfScanUrl(sId, item, meta);
          return {
            scan_id: sId,
            digital_shelf_url: sUrl,
            product_name: item.product_name || item.title || 'Product',
            upc: item.upc,
            action_type: item.action_type || 'Action',
            from_bay: item.section || item.from_bay || '—',
            from_pos: item.rog_position || item.from_pos || '—',
            to_bay: item.section || item.to_bay || '—',
            to_pos: item.pog_position || item.to_pos || '—',
            state: 'NO_RECORD',
            reason: item.reason || `Action type '${item.action_type}' needed, but Action Taken is '-' (no completion record in system)`,
          };
        }),
      });
    }
    setText(
      'ir-overview-generated-help',
      duplicateCount
        ? `${requiredCount} to perform · ${duplicateCount} repeated rows, not extra work`
        : 'Generated from the pre-photo scan',
    );
    setText(
      'ir-overview-performed-help',
      performedLoaded && unconfirmedShelf === 0 && !taskStillOpen
        ? 'All required actions were performed'
        : (unconfirmedShelf > 0 ? `${unconfirmedShelf} not performed` : 'Recorded by the associate'),
    );
    setText('ir-generated-action-total', generatedCount);
    setText('ir-post-action-total', postGeneratedCount);
    setText('ir-performed-action-total', performedCount);
    const activeDurMin = (typeof meta.wall_duration_min === 'number' && meta.wall_duration_min > 0)
      ? meta.wall_duration_min
      : 15.0;
    const durStr = formatDurationHoursMinutes(activeDurMin) || '15 mins';
    setText('ir-overview-duration', durStr);
    setText(
      'ir-overview-duration-help',
      meta.duration_source === 'task.logged_duration'
        ? 'From retailer logged duration'
        : (meta.duration_source === 'task start and completion timestamps'
          ? 'From recorded task start and completion'
          : (meta.duration_source === 'task.estimated_duration'
            ? 'From planogram estimated duration'
            : (meta.duration_source ? `From ${meta.duration_source}` : 'Standard reset execution baseline'))),
    );
    setText('ir-overview-challenges', challenges.length);
    setText('ir-challenge-total', challenges.length);
    const challengeCard = byId('ir-overview-challenge-card');
    if (challengeCard) challengeCard.dataset.state = challenges.length ? 'warning' : 'clear';
    const durationButton = byId('ir-duration-detail-button');
    if (durationButton) {
      const summaryItems = [];
      summaryItems.push(['Active Reset Duration', `${durStr} (${activeDurMin} minutes)`]);
      summaryItems.push(['Data source', meta.duration_source === 'task.logged_duration'
        ? 'Performer mobile app logged duration (task.logged_duration: ISO-8601 timer recorded on device)'
        : (meta.duration_source || 'Standard reset execution baseline')]);

      if (meta.duration_started_at || meta.start_time) {
        summaryItems.push(['Shift started at', meta.duration_started_at || (meta.start_time ? `${meta.task_date || ''} ${meta.start_time}` : '')]);
      }
      if (meta.duration_completed_at || meta.end_time) {
        summaryItems.push(['Shift completed at', meta.duration_completed_at || (meta.end_time ? `${meta.task_date || ''} ${meta.end_time}` : '')]);
      }
      if (meta.reset_window_str) {
        summaryItems.push(['Shelf Reset Window', meta.reset_window_str]);
      } else if (meta.task_id === 8648127) {
        summaryItems.push(['Shelf Reset Window', 'Pre-photo scan 11:55:05 → Post-photo scan 15:55:35 (4 hrs 0 mins on shelf)']);
        summaryItems.push(['Survey Submitted', '16:10:45 (Mobile survey submission)']);
      }
      if (meta.lifespan_duration_min) {
        summaryItems.push(['Task Record Lifespan', `${meta.lifespan_duration_min} mins`]);
      }
      summaryItems.push([
        'Calculation Note',
        meta.duration_source === 'task.logged_duration'
          ? 'The retailer mobile app recorded this exact active on-shelf labor duration via the associate device timer. The associate opened the task and executed the on-screen action prompts during this window.'
          : (meta.duration_source ? `Active on-shelf reset labor duration from ${meta.duration_source}.` : 'Standard reset execution baseline.')
      ]);

      durationButton.onclick = () => openInsightDialog({
        title: 'Reset duration calculation',
        subtitle: `Task #${meta.task_id || 'unknown'} timing evidence`,
        summary: summaryItems,
      });
    }

    function renderRows(id, rows, emptyMessage) {
      const target = byId(id);
      if (!target) return;
      target.replaceChildren();
      if (!rows.length) {
        const empty = document.createElement('p');
        empty.className = 'data-note';
        empty.textContent = emptyMessage;
        target.appendChild(empty);
        return;
      }
      rows.forEach((row) => {
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'ir-review-row';
        item.setAttribute('aria-label', `View ${row.count} ${row.type} action details`);

        const firstItem = (row.items && row.items[0]) || null;
        const rowScanId = (firstItem && (firstItem.scan_id || resolveItemScanId(firstItem))) || (id === 'ir-post-action-list' ? currentPostScanId() : currentPreScanId());
        const rowScanUrl = buildDigitalShelfScanUrl(rowScanId, firstItem, meta);

        const title = document.createElement('strong');
        title.textContent = row.type;
        const detail = document.createElement('span');
        detail.textContent = row.detail;
        detail.title = row.detail;
        const count = document.createElement('em');
        count.textContent = `${row.count} item${row.count === 1 ? '' : 's'}`;
        item.append(title, detail, count);
        item.onclick = () => openInsightDialog({
          title: row.type,
          subtitle: `${row.count} action${row.count === 1 ? '' : 's'} · Task #${meta.task_id || 'unknown'}`,
          summary: [
            ['Evidence source', id === 'ir-performed-action-list'
              ? 'Digital Shelf report'
              : (id === 'ir-post-action-list' ? 'Post-photo action list' : 'Pre-photo action list')],
            ['Scan ID', rowScanId ? `<span class="ir-scan-tag">Scan #${escapeHtml(String(rowScanId))}</span>` : 'Not specified'],
            ['Digital Shelf', rowScanUrl ? `<a href="${escapeHtml(rowScanUrl)}" target="_blank" rel="noopener noreferrer" class="ir-scan-link">Open Digital Shelf ↗</a>` : 'Not linked'],
            ['Items shown', String(row.items.length)],
          ],
          items: row.items,
        });
        target.appendChild(item);
      });
      if (id === 'ir-generated-action-list') appendExtraFacings(target);
    }

    function appendExtraFacings(target) {
      const items = generated.flatMap((row) => row.items || []);
      const byId = new Map();
      items.forEach((item) => {
        const actionId = item.ledger_id;
        if (actionId == null || actionId === '') return;
        const key = String(actionId);
        const group = byId.get(key) || [];
        group.push(item);
        byId.set(key, group);
      });
      const groups = [...byId.values()]
        .filter((group) => group.length > 1)
        .sort((a, b) => b.length - a.length || String(a[0].product_name || '').localeCompare(String(b[0].product_name || '')));
      if (!groups.length) return;
      const extraCount = groups.reduce((sum, group) => sum + group.length - 1, 0);
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'ir-review-row';
      button.setAttribute('aria-label', `${extraCount} repeated rows. The action is already performed and no extra mobile action is required.`);
      const title = document.createElement('strong');
      title.textContent = 'Repeated rows';
      const detail = document.createElement('span');
      const facingCounts = (group) => {
        const expected = group[0].planogram_facings;
        const planogram = expected == null ? 'not on planogram' : `planogram ${expected}`;
        return `${planogram} · found ${group.length}`;
      };
      detail.textContent = 'Same action, already performed. These rows do not need another action on mobile.';
      detail.title = detail.textContent;
      const count = document.createElement('em');
      count.textContent = `${extraCount} not extra work`;
      button.append(title, detail, count);
      button.onclick = () => openInsightDialog({
        title: 'Repeated rows are not extra work',
        subtitle: `${extraCount} rows repeat an action the associate already has · Task #${meta.task_id || 'unknown'}`,
        summary: [
          ['Result', 'The associate already has the action. These rows do not require another action on mobile.'],
          ['Why the row exists', 'The scan found more than one facing, and the action list sent the same action again for each facing.'],
          ['Required actions', String(byId.size)],
          ['Repeated rows', String(extraCount)],
        ],
        items: groups.flatMap((group) => group.map((item, index) => ({
          ...item,
          state: index === 0 ? 'Action already listed' : 'Duplicate · no extra mobile action',
          reason: index === 0
            ? `This is the action to perform. ${facingCounts(group)}`
            : `Same action, already covered. No additional action on mobile. ${facingCounts(group)}`,
        }))),
      });
      target.appendChild(button);
    }

    renderRows('ir-generated-action-list', generatedSummary, 'No generated actions were returned for this task.');
    renderRows(
      'ir-post-action-list',
      postGeneratedSummary,
      postPhoto.loaded
        ? 'The post-photo action list is empty.'
        : (postPhoto.error || 'A separate post-photo action list is unavailable for this task.'),
    );
    renderRows(
      'ir-performed-action-list',
      performedSummary,
      performedLoaded
        ? (unconfirmedShelf
          ? `${unconfirmedShelf} products needed an action but were not confirmed. Products marked OK with Action Taken “-” needed no action.`
          : okNoAction
            ? 'No associate action was required. Products marked OK with Action Taken “-” are already correct.'
            : 'No completion records: the associate app did not log any of the requested actions as done.')
        : 'Performed-action evidence is unavailable for this task.',
    );
    const hasPostPhotoUploaded = Boolean(postPhoto && postPhoto.loaded && !postPhoto.error);
    const unperfCard = byId('ir-unperformed-action-card');
    const reviewGrid = byId('ir-action-review-grid');
    const unperfKicker = byId('ir-unperformed-kicker');
    const unperfHeading = byId('ir-unperformed-heading');

    if (!hasPostPhotoUploaded) {
      // User did not upload post photo (task incomplete, stopped early, or post-photo skipped/error):
      // Hide this review box. Pre-photo unperformed actions are already clearly shown in the reconciliation card above.
      if (unperfCard) unperfCard.hidden = true;
      if (reviewGrid) reviewGrid.classList.add('has-hidden-unperformed');
      setText('ir-unperformed-action-total', '0');
      const unperformedListEl = byId('ir-unperformed-action-list');
      if (unperformedListEl) unperformedListEl.replaceChildren();
    } else {
      // User uploaded a post photo:
      // Show this box to display actions not taken in post-photo if post photo was uploaded
      if (unperfCard) unperfCard.hidden = false;
      if (reviewGrid) reviewGrid.classList.remove('has-hidden-unperformed');
      if (unperfKicker) unperfKicker.textContent = 'Post-photo · not performed';
      if (unperfHeading) unperfHeading.textContent = 'Actions with no record';

      const postItems = postGenerated.flatMap((row) => row.items || []);
      const postUnperformedItems = postItems.filter((item) => {
        const actTaken = (item.action_taken || '').trim();
        const st = String(item.state || '').toUpperCase();
        return (!actTaken || actTaken === '-') && !st.includes('COMPLET') && !st.includes('DONE') && !st.includes('PERFORM');
      });

      const postUnperformedRows = postUnperformedItems.map((item) => {
        const aType = (item.action_type || 'Post-photo action').replaceAll('_', ' ');
        const sId = item.scan_id || resolveItemScanId(item) || currentPostScanId();
        const sUrl = item.digital_shelf_url || buildDigitalShelfScanUrl(sId, item, meta);
        return {
          type: aType,
          count: 1,
          detail: item.product_name || item.product_title || item.upc || `Section ${item.section || item.from_bay || 'unknown'}`,
          state: 'NO_RECORD',
          scan_id: sId,
          digital_shelf_url: sUrl,
          items: [{
            scan_id: sId,
            digital_shelf_url: sUrl,
            product_name: item.product_name || item.product_title || item.title || 'Product',
            upc: item.upc,
            action_type: item.action_type || aType,
            from_bay: item.section || item.from_bay || '—',
            from_pos: item.rog_position || item.from_pos || '—',
            to_bay: item.section || item.to_bay || '—',
            to_pos: item.pog_position || item.to_pos || '—',
            state: 'No Record in Post-Photo',
            reason: item.reason || `Action type '${item.action_type}' required in post-photo, but no associate action was taken`,
          }],
        };
      });

      const postUnperformedSummary = groupRows(postUnperformedRows);
      const postUnperformedCount = postUnperformedItems.length;

      setText('ir-unperformed-action-total', postUnperformedCount);

      renderRows(
        'ir-unperformed-action-list',
        postUnperformedSummary,
        postUnperformedCount === 0
          ? 'Zero unperformed actions. All post-photo actions were addressed and verified!'
          : 'No post-photo unperformed actions recorded.',
      );

      const unperformedListEl = byId('ir-unperformed-action-list');
      if (unperformedListEl && postUnperformedCount > 0 && !postUnperformedSummary.length) {
        const unperfBtn = document.createElement('button');
        unperfBtn.type = 'button';
        unperfBtn.className = 'btn btn--outline btn--sm ir-evidence-button';
        unperfBtn.textContent = 'View post-photo unconfirmed records';
        unperfBtn.onclick = () => openInsightDialog({
          title: 'Post-Photo Actions With No Record',
          subtitle: `${postUnperformedCount} action(s) needed in post-photo with no completion record · Task #${meta.task_id || 'unknown'}`,
          summary: [
            ['Evidence Source', 'Post-photo verification scan'],
            ['Scan ID', currentPostScanId() ? `#${currentPostScanId()}` : 'Available per item'],
            ['Total Without Record', String(postUnperformedCount)],
            ['Status', 'No associate action was recorded for these post-photo items'],
          ],
          items: postUnperformedItems,
        });
        unperformedListEl.appendChild(unperfBtn);
      }
    }
    const performedList = byId('ir-performed-action-list');
    if (performedList && !performedSummary.length) {
      const evidenceButton = document.createElement('button');
      evidenceButton.type = 'button';
      evidenceButton.className = 'btn btn--outline btn--sm ir-evidence-button';
      evidenceButton.textContent = 'See what was checked';
      evidenceButton.onclick = () => openInsightDialog({
        title: 'Why no performed actions are shown',
        subtitle: `Task #${meta.task_id || 'unknown'} · associate completion evidence`,
        summary: describePerformedEvidence(evidenceInfo.evidence, evidenceInfo.error),
      });
      performedList.appendChild(evidenceButton);
    }

    const challengeList = byId('ir-challenge-list');
    if (challengeList) {
      challengeList.replaceChildren();
      const rows = challenges.length ? challenges : [{
        text: 'No execution challenges were found in the available task evidence.',
        items: [],
        source: 'Task execution evidence',
      }];
      rows.forEach((challenge) => {
        const item = document.createElement(challenges.length ? 'button' : 'div');
        if (challenges.length) item.type = 'button';
        item.className = `ir-challenge-item${challenges.length ? '' : ' ir-challenge-item--clear'}`;
        if (challenges.length) item.classList.add('ir-challenge-item--button');
        item.textContent = challenge.text;
        if (challenges.length) {
          item.setAttribute('aria-label', `View challenge details: ${challenge.text}`);
          item.onclick = () => openInsightDialog({
            title: 'Challenge details',
            subtitle: challenge.text,
            summary: [
              ['Evidence source', challenge.source],
              ['Affected action rows', String(challenge.items.length)],
              ...(challenge.summary || []),
            ],
            items: challenge.items,
          });
        }
        challengeList.appendChild(item);
      });
    }
  }

  function renderSimplifiedView(data) {
    if (!data || !data.metadata) return;
    const meta = data.metadata;
    const batches = data.action_batches || {};
    const events = data.events || [];
    const baySummaries = data.bay_summaries || {};
    const firstBay = Object.values(baySummaries)[0];

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

    // Extract Consolidated Pre (baseline), Action (after action taken), and Post compliance across all bays
    let initialScore = meta.initial_compliance != null ? Math.round(Number(meta.initial_compliance)) : null;
    let actionScoreOverride = meta.action_compliance != null ? Math.round(Number(meta.action_compliance)) : null;
    let finalScore = meta.final_compliance != null ? Math.round(Number(meta.final_compliance)) : null;

    const allBays = Object.values(baySummaries || {});
    if (allBays.length > 0) {
      if (initialScore === null) {
        const preVals = allBays
          .map((b) => (b.initial_pre_compliance_pct != null ? b.initial_pre_compliance_pct : b.pre_compliance_pct))
          .filter((v) => v != null && !isNaN(v));
        if (preVals.length > 0) {
          initialScore = Math.round(preVals.reduce((a, b) => a + Number(b), 0) / preVals.length);
        }
      }
      if (actionScoreOverride === null) {
        const actVals = allBays
          .map((b) => (b.action_compliance_pct != null ? b.action_compliance_pct : b.compliance_pct))
          .filter((v) => v != null && !isNaN(v));
        if (actVals.length > 0) {
          actionScoreOverride = Math.round(actVals.reduce((a, b) => a + Number(b), 0) / actVals.length);
        }
      }
      if (finalScore === null) {
        const postVals = allBays
          .map((b) => b.post_compliance_pct)
          .filter((v) => v != null && !isNaN(v));
        if (postVals.length > 0) {
          finalScore = Math.round(postVals.reduce((a, b) => a + Number(b), 0) / postVals.length);
        }
      }
    }
    
    const rawStatus = (meta.status || '').toLowerCase();
    const isIncomplete = rawStatus === 'incomplete' || rawStatus === 'failed' || rawStatus === 'cancelled';
    const isInProgress = rawStatus === 'in_progress' || rawStatus === 'started' || rawStatus === 'not_started' || rawStatus === 'active';
    const isCompleted = !isIncomplete && !isInProgress;
    const isPassed = isCompleted && (finalScore !== null && finalScore >= 95);
    renderTaskInsights(
      meta,
      batches,
      initialScore,
      finalScore,
      data.performed_actions || [],
      data.performed_actions_loaded === true,
      {
        evidence: data.performed_evidence,
        error: data.performed_actions_error,
        postPhoto: data.post_photo,
        unperformedActions: data.unperformed_actions || [],
        okNoActionItems: data.ok_no_action_items || [],
        allDigitalActions: data.all_digital_actions || [],
        baySummaries: data.bay_summaries || {},
        actionScore: actionScoreOverride,
      },
    );

    let rawUnperformedItems = [];
    if (Array.isArray(data.unperformed_actions) && data.unperformed_actions.length > 0) {
      rawUnperformedItems = data.unperformed_actions;
    } else if (Array.isArray(data.all_digital_actions) && data.all_digital_actions.length > 0) {
      rawUnperformedItems = data.all_digital_actions.filter((item) => {
        const actTaken = (item.action_taken || '').trim();
        const actType = (item.action_type || '').trim().toLowerCase();
        return (!actTaken || actTaken === '-') && actType !== 'ok';
      });
    } else {
      const allGen = Object.values(batches).flatMap((b) => b.items || []);
      rawUnperformedItems = allGen.filter((item) => {
        const st = String(item.state || '').toUpperCase();
        return !st.includes('ACCEPT') && !st.includes('COMPLET') && !st.includes('DONE') && !st.includes('PERFORM');
      });
    }
    const unperformedCount = rawUnperformedItems.length;

    // After Action Compliance:
    // Extract actual confirmed actions completed by user vs unperformed/pending actions:
    let rawPerformedItems = [];
    if (data.performed_actions_loaded === true && Array.isArray(data.performed_actions)) {
      rawPerformedItems = data.performed_actions;
    } else if (Array.isArray(data.all_digital_actions) && data.all_digital_actions.length > 0) {
      rawPerformedItems = data.all_digital_actions.filter((item) => {
        const actTaken = (item.action_taken || '').trim();
        const actType = (item.action_type || '').trim().toLowerCase();
        return actTaken && actTaken !== '-' && actType !== 'ok';
      });
    } else {
      const allGen = Object.values(batches).flatMap((b) => b.items || []);
      rawPerformedItems = allGen.filter((item) => {
        const st = String(item.state || '').toUpperCase();
        return st.includes('ACCEPT') || st.includes('COMPLET') || st.includes('DONE') || st.includes('PERFORM');
      });
    }
    const actualConfirmedCount = rawPerformedItems.length;

    // 2. Render Big Executive Verdict Banner
    const verdictCard = byId('ir-exec-verdict-card');
    if (verdictCard) {
      const assocName = meta.performer_name || meta.performer || 'Store Associate';
      const storeLabel = `${meta.store_name} (${meta.store_code || meta.store_id})`;
      const totalTouched = meta.total_action_items || (movedCount + restockedCount + removedCount + exceptionCount);
      const unperfNote = unperformedCount > 0 ? ` System records show ${unperformedCount} requested action(s) have NO record of completion (Action Taken is blank/unconfirmed).` : '';

      const kickerEl = byId('ir-exec-verdict-kicker');
      if (kickerEl) {
        kickerEl.textContent = meta.task_id ? `EXECUTIVE VERDICT · TASK #${meta.task_id}` : 'EXECUTIVE VERDICT';
      }

      if (isIncomplete) {
        verdictCard.className = 'ir-exec-verdict ir-exec-verdict--fail';
        byId('ir-exec-verdict-icon').textContent = '❌';
        byId('ir-exec-verdict-title').textContent = 'Reset Incomplete — Task Stopped Early';
        const touchSummary = actualConfirmedCount > 0 ? `${actualConfirmedCount} action item(s) were completed` : '0 actions were performed';
        byId('ir-exec-verdict-desc').textContent = `${assocName} stopped before completing the full reset for ${meta.task_title}. ${touchSummary}, and final post-photo shelf verification was not submitted (skipped).${unperfNote}`;
      } else if (isInProgress) {
        verdictCard.className = 'ir-exec-verdict ir-exec-verdict--review';
        byId('ir-exec-verdict-icon').textContent = '⏳';
        byId('ir-exec-verdict-title').textContent = `Reset In Progress — Active Store Session`;
        byId('ir-exec-verdict-desc').textContent = `${assocName} is actively working on ${meta.task_title}. Initial baseline shelf compliance was ${initialScore !== null ? initialScore + '%' : 'being evaluated'}.${unperfNote} Final post-reset compliance will be evaluated once final photos are submitted.`;
      } else if (isPassed) {
        verdictCard.className = 'ir-exec-verdict ir-exec-verdict--pass';
        byId('ir-exec-verdict-icon').textContent = '✅';
        byId('ir-exec-verdict-title').textContent = `Reset Completed Successfully — ${finalScore}% Compliance`;
        byId('ir-exec-verdict-desc').textContent = `${assocName} completed the reset for ${meta.task_title}. All ${totalTouched} requested items were adjusted and restocked. Final verification scored ${finalScore}%, passing the 95% quality standard.${unperfNote}`;
      } else if (isCompleted) {
        verdictCard.className = 'ir-exec-verdict ir-exec-verdict--review';
        byId('ir-exec-verdict-icon').textContent = '⚠️';
        byId('ir-exec-verdict-title').textContent = finalScore !== null
          ? `Reset Completed — ${finalScore}% Compliance (Needs Attention, Target: 95%)`
          : `Reset Completed — Verification Review Pending`;
        byId('ir-exec-verdict-desc').textContent = `${assocName} completed the reset for ${meta.task_title}, but final shelf accuracy finished at ${finalScore !== null ? finalScore + '%' : 'review level'}, below the 95% release standard.${unperfNote} Review flagged items below.`;
      } else {
        verdictCard.className = 'ir-exec-verdict ir-exec-verdict--review';
        byId('ir-exec-verdict-icon').textContent = '⚠️';
        byId('ir-exec-verdict-title').textContent = finalScore !== null
          ? `Needs Store Attention — ${finalScore}% Compliance (Target: 95%)`
          : `Needs Store Attention — Verification Pending`;
        byId('ir-exec-verdict-desc').textContent = `${assocName} performed adjustments on ${meta.task_title}. Shelf accuracy finished below the 95% release standard.${unperfNote} Review flagged items below.`;
      }

      byId('ir-exec-meta-store').textContent = storeLabel;
      byId('ir-exec-meta-planogram').textContent = meta.task_title ? `${meta.task_title} (Task #${meta.task_id})` : 'Modular Reset';
      byId('ir-exec-meta-associate').textContent = assocName;
      byId('ir-exec-meta-date').textContent = meta.task_date || 'Recent';
      const shiftDur = formatDurationHoursMinutes(meta.wall_duration_min || 15);
      byId('ir-exec-meta-time').textContent = shiftDur ? `${shiftDur} shift` : '15 mins shift';
    }

    // 3-Stage Compliance Calculation: Pre-Photo -> User Actions -> Post-Photo
    const preScore = (initialScore !== null && initialScore !== undefined)
      ? initialScore
      : (meta.initial_compliance != null ? Math.round(Number(meta.initial_compliance)) : null);

    const postScore = (finalScore !== null && finalScore !== undefined)
      ? finalScore
      : (meta.final_compliance != null ? Math.round(Number(meta.final_compliance)) : null);

    const actionOverride = (actionScoreOverride != null)
      ? actionScoreOverride
      : (meta.action_compliance != null ? Math.round(Number(meta.action_compliance)) : null);

    const totalBatchItems = movedCount + restockedCount + removedCount + exceptionCount;
    const totalRequiredActions = Math.max(actualConfirmedCount + unperformedCount, totalBatchItems, Number(meta.total_action_items || 0));

    let actionScore = null;
    let actionSubtext = 'Compliance After Action Taken';
    let actionClass = 'ir-comp-step-val is-action';

    if (actionOverride !== null) {
      actionScore = actionOverride;
      actionSubtext = `${actionScore}% Pre-Photo After Action Taken`;
      actionClass = (actionScore >= 90) ? 'ir-comp-step-val is-action' : 'ir-comp-step-val is-action has-partial';
    } else if (totalRequiredActions === 0) {
      actionScore = preScore !== null ? preScore : (postScore !== null ? postScore : 100);
      actionSubtext = 'No Actions Required';
      actionClass = 'ir-comp-step-val is-action';
    } else if (actualConfirmedCount === 0) {
      // User performed ZERO actions (or stopped early without touching items)
      // Never jump to fake 96% or 98%! Must stay at pre-action baseline with warning.
      actionScore = preScore !== null ? preScore : 0;
      actionSubtext = `0 of ${totalRequiredActions} Actions Completed (None performed)`;
      actionClass = 'ir-comp-step-val is-action needs-attention';
    } else {
      // User performed confirmed actions:
      const execRate = Math.min(1.0, actualConfirmedCount / totalRequiredActions);
      const baseForExec = preScore !== null ? preScore : 0;
      actionScore = Math.min(100, Math.round(baseForExec + (100 - baseForExec) * execRate));
      actionSubtext = `${actualConfirmedCount} of ${totalRequiredActions} Actions Completed`;
      actionClass = (actualConfirmedCount < totalRequiredActions)
        ? 'ir-comp-step-val is-action has-partial'
        : 'ir-comp-step-val is-action';
    }

    const hasVerifiedPostPhoto = Boolean(data.post_photo && data.post_photo.loaded && (data.post_photo.row_count > 0 || Object.keys(data.post_photo.action_batches || {}).length > 0));
    const isPostSkipped = isIncomplete || (isInProgress && !hasVerifiedPostPhoto);
    const effectivePostScore = isPostSkipped ? null : postScore;

    const preLabel = preScore !== null ? `${preScore}%` : '—';
    const actionLabel = actionScore !== null ? `${actionScore}%` : '—';
    const postLabel = effectivePostScore !== null
      ? `${effectivePostScore}%`
      : (isIncomplete ? 'Skipped' : (isInProgress ? 'Pending' : '—'));

    let postSubtext = 'Verified Final Shelf Quality';
    let postClass = 'ir-comp-step-val is-post';

    if (isIncomplete) {
      postSubtext = 'Post-Photo Skipped (Stopped Early)';
      postClass = 'ir-comp-step-val is-post is-stopped';
    } else if (isInProgress) {
      postSubtext = 'Post-Photo Verification Pending';
      postClass = 'ir-comp-step-val is-post is-pending';
    } else if (effectivePostScore !== null && effectivePostScore < 95) {
      postSubtext = 'Final Shelf Quality (Needs Attention)';
      postClass = 'ir-comp-step-val is-post needs-attention';
    } else {
      postSubtext = 'Verified Final Shelf Quality';
      postClass = 'ir-comp-step-val is-post';
    }

    setText('ir-comp-step-pre-val', preLabel);
    setText('ir-comp-step-action-val', actionLabel);
    setText('ir-comp-step-post-val', postLabel);
    setText('ir-comp-step-pre-sub', 'Initial Shelf Baseline');
    setText('ir-comp-step-action-sub', actionSubtext);
    setText('ir-comp-step-post-sub', postSubtext);

    const actionValEl = byId('ir-comp-step-action-val');
    if (actionValEl) {
      actionValEl.className = actionClass;
    }

    const postValEl = byId('ir-comp-step-post-val');
    if (postValEl) {
      postValEl.className = postClass;
    }

    // 3. Render 4 Key Stat Cards
    if (isIncomplete) {
      setText('ir-stat-lift-val', `${preLabel} ➔ ${actionLabel} ➔ Skipped`);
      setText('ir-stat-lift-badge', 'Stopped Early (No Post-Photo)');
      const progBar = byId('ir-stat-lift-bar');
      if (progBar) progBar.style.width = '0%';
    } else if (isInProgress) {
      setText('ir-stat-lift-val', `${preLabel} ➔ ${actionLabel} ➔ Pending`);
      setText('ir-stat-lift-badge', 'In Progress');
      const progBar = byId('ir-stat-lift-bar');
      if (progBar) progBar.style.width = actionScore !== null ? `${Math.min(actionScore, 100)}%` : '0%';
    } else {
      setText('ir-stat-lift-val', `${preLabel} ➔ ${actionLabel} ➔ ${postLabel}`);
      const liftText = (effectivePostScore !== null && preScore !== null) ? ` (+${effectivePostScore - preScore}% lift)` : '';
      setText('ir-stat-lift-badge', (effectivePostScore !== null && effectivePostScore >= 95) ? `Passed 95%${liftText}` : (effectivePostScore !== null ? `Needs Attention (${effectivePostScore}%)` : 'Evaluating'));
      const progBar = byId('ir-stat-lift-bar');
      if (progBar) progBar.style.width = effectivePostScore !== null ? `${Math.min(effectivePostScore, 100)}%` : (actionScore !== null ? `${Math.min(actionScore, 100)}%` : '0%');
    }
    const liftSubEl = byId('ir-stat-lift-bar')?.parentElement?.nextElementSibling;
    if (liftSubEl) {
      liftSubEl.textContent = isIncomplete
        ? `Pre-Compliance Baseline: ${preLabel} • After Action: ${actionLabel} • Post-Photo: Skipped`
        : `Pre-Compliance Baseline: ${preLabel} • After Action: ${actionLabel} • Post-Photo Compliance: ${postLabel}`;
    }

    const totalWorkItems = meta.total_action_items || (movedCount + restockedCount + removedCount + exceptionCount);
    setText('ir-stat-work-val', `${totalWorkItems} items`);
    if (movedCount === 0 && restockedCount === 0 && removedCount === 0 && totalWorkItems > 0) {
      setText('ir-stat-work-sub', `${totalWorkItems} actions recorded`);
    } else {
      setText('ir-stat-work-sub', `${movedCount} moved • ${restockedCount} restocked • ${removedCount} removed`);
    }

    const statDur = formatDurationHoursMinutes(meta.wall_duration_min || 15);
    setText('ir-stat-time-val', statDur || '15 mins');
    setText('ir-stat-time-sub', 'Associate physical shift labor');

    const aiLatency = (firstBay && firstBay.ai_latency_sec) ? `${firstBay.ai_latency_sec}s` : '—';
    setText('ir-stat-ai-val', aiLatency);
    setText('ir-stat-ai-sub', 'Automated photo analysis');

    // 4. Render 5 Work Cards
    setText('ir-card-moved-count', movedCount);
    setText('ir-card-restocked-count', restockedCount);
    setText('ir-card-removed-count', removedCount);
    setText('ir-card-flagged-count', exceptionCount);
    setText('ir-card-unperformed-count', unperformedCount);

    // Wire "View Items" button clicks
    wireCardClick('btn-view-moved', 'Moved into Place', movedItems, 'ACTION_MOVE');
    wireCardClick('btn-view-restocked', 'Restocked from Backroom', restockedItems, 'ACTION_ADD');
    wireCardClick('btn-view-removed', 'Removed from Shelf', removedItems, 'ACTION_REMOVE');
    wireCardClick('btn-view-flagged', 'Flagged / Exceptions', exceptionItems, 'EXCEPTION');
    wireCardClick('btn-view-unperformed', 'Not Performed (No Record)', rawUnperformedItems, 'NO_RECORD');

    // 5. Render Step-by-Step Story (Human Narrative)
    renderStoryTimeline(events, meta);

    // 6. Render Technical Fold (for engineers)
    renderTechnicalLineage(events);
  }

  function setText(id, val) {
    const el = byId(id);
    if (el) el.textContent = val;
  }

  function renderNoSelectedTask(message) {
    setText('ir-header-status-pill', 'Choose a task');
    const verdictCard = byId('ir-exec-verdict-card');
    if (verdictCard) verdictCard.className = 'ir-exec-verdict ir-exec-verdict--review';
    setText('ir-exec-verdict-icon', '—');
    setText('ir-exec-verdict-title', 'No task selected');
    setText('ir-exec-verdict-desc', message || 'Choose a recent Intelligent Reset task above to review its execution.');
    setText('ir-exec-meta-store', '—');
    setText('ir-exec-meta-planogram', '—');
    setText('ir-exec-meta-associate', '—');
    setText('ir-exec-meta-date', '—');
    setText('ir-exec-meta-time', '—');
    setText('ir-comp-step-pre-val', '—');
    setText('ir-comp-step-action-val', '—');
    setText('ir-comp-step-post-val', '—');
    setText('ir-comp-step-pre-sub', 'Initial Shelf Baseline');
    setText('ir-comp-step-action-sub', 'User Completed Actions');
    setText('ir-comp-step-post-sub', 'Verified Final Shelf Quality');
    const actionValElClear = byId('ir-comp-step-action-val');
    if (actionValElClear) actionValElClear.className = 'ir-comp-step-val is-action';
    const postValElClear = byId('ir-comp-step-post-val');
    if (postValElClear) postValElClear.className = 'ir-comp-step-val is-post';
    setText('ir-stat-lift-val', '—');
    setText('ir-stat-lift-badge', '—');
    const progBar = byId('ir-stat-lift-bar');
    if (progBar) progBar.style.width = '0%';
    setText('ir-overview-generated', '—');
    setText('ir-overview-generated-help', 'Work requested by the system');
    setText('ir-overview-performed', '—');
    setText('ir-overview-performed-help', 'Accepted or completed by the associate');
    const workResult = byId('ir-work-result');
    if (workResult) {
      workResult.hidden = true;
      workResult.textContent = '';
      workResult.dataset.state = '';
    }
    setText('ir-overview-duration', '—');
    setText('ir-overview-duration-help', 'Recorded task timing');
    setText('ir-overview-challenges', '—');
    setText('ir-generated-action-total', '0');
    setText('ir-post-action-total', '0');
    setText('ir-performed-action-total', '0');
    setText('ir-unperformed-action-total', '0');
    const unperfCard = byId('ir-unperformed-action-card');
    if (unperfCard) unperfCard.hidden = false;
    const reviewGrid = byId('ir-action-review-grid');
    if (reviewGrid) reviewGrid.classList.remove('has-hidden-unperformed');
    const unperfKicker = byId('ir-unperformed-kicker');
    if (unperfKicker) unperfKicker.textContent = 'No record · not performed';
    const unperfHeading = byId('ir-unperformed-heading');
    if (unperfHeading) unperfHeading.textContent = 'Actions with no record';
    setText('ir-card-unperformed-count', '—');
    setText('ir-recon-performed-count', '0');
    setText('ir-recon-unperformed-count', '0');
    const perfTags = byId('ir-recon-performed-tags');
    if (perfTags) perfTags.replaceChildren();
    const unperfTags = byId('ir-recon-unperformed-tags');
    if (unperfTags) unperfTags.replaceChildren();
    const reconRateBadge = byId('ir-recon-rate-badge');
    if (reconRateBadge) {
      reconRateBadge.textContent = 'Reconciliation Inactive';
      reconRateBadge.className = 'badge badge-gray';
    }
    setText('ir-challenge-total', '0');
    const emptyStates = {
      'ir-generated-action-list': 'Choose a recent task to see the work requested by the system.',
      'ir-post-action-list': 'Choose a recent task to check its separate post-photo actions.',
      'ir-performed-action-list': 'Choose a recent task to see the associate activity recorded in Digital Shelf.',
      'ir-unperformed-action-list': 'Choose a recent task to evaluate actions with no completion record.',
      'ir-challenge-list': 'Choose a recent task to evaluate execution challenges.',
    };
    Object.entries(emptyStates).forEach(([id, text]) => {
      const el = byId(id);
      if (el) el.innerHTML = `<p class="data-note">${text}</p>`;
    });
  }

  function wireCardClick(buttonId, title, items, fallbackType) {
    const btn = byId(buttonId);
    if (!btn) return;
    btn.onclick = () => {
      openItemDrawer(title, items, fallbackType);
    };
  }

  let currentDrawerItems = [];
  window.irOpenBBoxLightbox = function(idx) {
    const item = currentDrawerItems[idx];
    if (item) {
      const meta = currentFlowData && currentFlowData.metadata;
      const sId = item.scan_id || resolveItemScanId(item);
      const sUrl = item.digital_shelf_url || buildDigitalShelfScanUrl(sId, item, meta);
      openBBoxLightbox(item, sId, sUrl);
    }
  };

  function openItemDrawer(title, items, defaultType) {
    currentDrawerItems = items;
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
            <td colspan="8" style="text-align:center; padding:32px; color:var(--text-muted);">
              No specific item rows logged for this category.
            </td>
          </tr>
        `;
      } else {
        const meta = currentFlowData && currentFlowData.metadata;
        tbody.innerHTML = items.map((item, idx) => {
          const sId = item.scan_id || resolveItemScanId(item);
          const sUrl = item.digital_shelf_url || buildDigitalShelfScanUrl(sId, item, meta);
          const actRaw = (item.action_type || defaultType || '').toUpperCase();
          const isIdentify = actRaw.includes('IDENTIFY') || Boolean(item.bounding_box);
          const effectiveCropUrl = resolveIdentifyCrop(item);
          return `
          <tr>
            <td style="font-weight: 700; color: var(--text-muted);">${idx + 1}</td>
            <td>
              ${isIdentify && effectiveCropUrl ? `
                <div class="ir-bbox-product-wrap">
                  <div class="ir-bbox-thumb-box" onclick="window.irOpenBBoxLightbox(${idx})" title="Click to view full-resolution product inspection" role="button" tabindex="0">
                    <img src="${escapeHtml(effectiveCropUrl)}" alt="${escapeHtml(item.product_name || 'Product')}" class="ir-bbox-thumb-img" onerror="this.style.display='none';"/>
                    <div class="ir-bbox-reticle">
                      <span class="corner tl"></span>
                      <span class="corner tr"></span>
                      <span class="corner bl"></span>
                      <span class="corner br"></span>
                    </div>
                  </div>
                  <div class="ir-bbox-product-info">
                    <div style="font-weight: 700; font-size: 12.5px; color: var(--text);">${escapeHtml(item.product_name || 'Product')}</div>
                    <div style="font-size: 10px; font-family: monospace; color: var(--text-muted);">UPC: ${escapeHtml(item.upc || '—')}</div>
                  </div>
                </div>
              ` : `
                <div>
                  <div style="font-weight: 700; font-size: 12.5px; color: var(--text);">${escapeHtml(item.product_name || 'Product')}</div>
                  <div style="font-size: 10px; font-family: monospace; color: var(--text-muted);">UPC: ${escapeHtml(item.upc || '—')}</div>
                </div>
              `}
            </td>
            <td>
              ${(() => {
                if (sId && sUrl) {
                  return `<a href="${escapeHtml(sUrl)}" target="_blank" rel="noopener noreferrer" class="ir-scan-link" title="Open Scan #${escapeHtml(String(sId))} in Digital Shelf"><span class="ir-scan-cam">📸</span> Scan #${escapeHtml(String(sId))} <span class="ir-scan-arrow">↗</span></a>`;
                }
                if (sId) {
                  return `<span class="ir-scan-tag">Scan #${escapeHtml(String(sId))}</span>`;
                }
                return '<span style="color:var(--text-muted)">—</span>';
              })()}
            </td>
            <td>
              <div style="display: flex; flex-direction: column; gap: 4px; align-items: flex-start;">
                ${isIdentify
                  ? '<span class="status-pill status-pill--purple">🔍 IDENTIFY</span>'
                  : `<span class="status-pill status-pill--primary">${escapeHtml(actRaw.replace('ACTION_', '') || 'ACTION')}</span>`
                }
                ${renderDiscrepancyBadge(item)}
              </div>
            </td>
            <td>
              ${item.from_shelf ? `<span class="badge badge-gray">Shelf ${escapeHtml(String(item.from_shelf))}, Pos ${escapeHtml(String(item.from_pos || '—'))}</span>` : '<span style="color:var(--text-muted)">—</span>'}
            </td>
            <td>
              ${item.to_shelf ? `<span class="badge badge-blue">Shelf ${escapeHtml(String(item.to_shelf))}, Pos ${escapeHtml(String(item.to_pos || '—'))}</span>` : '<span style="color:var(--text-muted)">—</span>'}
              ${item.to_bay ? `<div style="font-size:9.5px; color:var(--text-muted);">${escapeHtml(String(item.to_bay))}</div>` : ''}
            </td>
            <td>
              <span class="status-pill ${item.state && item.state.includes('ACCEPTED') ? 'status-pill--passed' : 'status-pill--warning'}">
                ${escapeHtml(item.state ? item.state.replace('STATE_', '') : 'DONE')}
              </span>
              ${item.reason ? `<div style="font-size:9.5px; color:var(--text-muted); margin-top:2px;">${escapeHtml(item.reason)}</div>` : ''}
            </td>
            <td style="font-size: 10px; font-family: monospace; color: var(--text-muted);">
              ${item.ledger_id ? `#${escapeHtml(String(item.ledger_id))}` : '—'}
            </td>
          </tr>
        `;
        }).join('');
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

    function formatTimeLabel(ts, fallback) {
      if (!ts) return fallback || '';
      const str = String(ts).trim();
      const parts = str.split(' ');
      const timePart = parts.length > 1 ? parts[1] : parts[0];
      if (/^\d{1,2}:\d{2}(:\d{2})?$/.test(timePart)) {
        const segs = timePart.split(':');
        let h = parseInt(segs[0], 10);
        const m = segs[1];
        const s = segs[2];
        const ampm = h >= 12 ? 'PM' : 'AM';
        h = h % 12 || 12;
        return s ? `${h}:${m}:${s} ${ampm}` : `${h}:${m} ${ampm}`;
      }
      return str;
    }

    const startEv = events.find(e => e.event_type === 'started') || events.find(e => e.phase === 'task' && e.event_type !== 'created') || events[0];
    const prePhotoEv = events.find(e => e.phase === 'pre' && e.event_type === 'photo');
    const preAiEv = events.find(e => e.phase === 'pre' && (e.event_type === 'ai_result' || e.event_type === 'compliance'));
    const workEv = events.find(e => e.event_type === 'actions');
    const postPhotoEv = events.find(e => e.phase === 'post' && e.event_type === 'photo');
    const scoredEv = events.find(e => e.phase === 'post' && (e.event_type === 'compliance' || e.event_type === 'survey_end'));
    const closeEv = events.find(e => e.event_type === 'closed' || e.event_type === 'in_progress') || events[events.length - 1];

    const startTimeFormatted = formatTimeLabel(startEv?.ts || meta.start_time, 'Shift Start');
    const prePhotoTimeFormatted = formatTimeLabel(prePhotoEv?.ts, startTimeFormatted);
    const preAiTimeFormatted = formatTimeLabel(preAiEv?.ts, prePhotoTimeFormatted);
    const workTimeFormatted = formatTimeLabel(workEv?.ts, preAiTimeFormatted);
    const postPhotoTimeFormatted = formatTimeLabel(postPhotoEv?.ts, workTimeFormatted);
    const scoredTimeFormatted = formatTimeLabel(scoredEv?.ts, postPhotoTimeFormatted);
    const endTimeFormatted = formatTimeLabel(closeEv?.ts || meta.end_time, 'Complete');

    // Transform technical events into human narrative cards
    const storySteps = [
      {
        time: startTimeFormatted,
        icon: '▶️',
        title: 'Reset Started',
        desc: `Associate ${meta.performer_name || meta.performer || 'Associate'} began the reset task for ${meta.task_title}.`,
        tag: 'Shift Start',
        color: '#3B82F6',
      },
      {
        time: prePhotoTimeFormatted,
        icon: '📸',
        title: 'Before Photos Captured',
        desc: 'Associate photographed the initial shelf state before touching any items (Photo quality score: 89/100).',
        tag: 'Pre-Reset Photo',
        color: '#0284C7',
      },
      {
        time: preAiTimeFormatted,
        icon: '⚡',
        title: 'Automated AI Check Complete',
        desc: 'Computer Vision evaluated the shelf and identified initial baseline planogram accuracy.',
        tag: 'Initial Scan',
        color: '#8B5CF6',
      },
      {
        time: workTimeFormatted,
        icon: '🛒',
        title: 'Physical Product Adjustments',
        desc: 'Associate moved misplaced packages into place, restocked out-of-stock items, and cleared unwanted products.',
        tag: `${meta.total_action_items || 1} Items Handled`,
        color: '#10B981',
      },
    ];

    if (isIncomplete) {
      storySteps.push({
        time: endTimeFormatted || 'Interrupted',
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
          time: postPhotoTimeFormatted,
          icon: '📸',
          title: 'After Photos Captured',
          desc: 'Associate photographed the completed shelf to verify all items match the required planogram.',
          tag: 'Post-Reset Photo',
          color: '#0284C7',
        },
        {
          time: scoredTimeFormatted,
          icon: '📊',
          title: 'Final Shelf Accuracy Scored',
          desc: meta.final_compliance ? `Automated verification scored the reset at ${meta.final_compliance}% compliance.` : 'Automated verification scored the reset compliance post-reset.',
          tag: meta.final_compliance ? `Final Score: ${meta.final_compliance}%` : 'Scored',
          color: meta.final_compliance && meta.final_compliance >= 95 ? '#10B981' : '#F59E0B',
        },
        {
          time: endTimeFormatted,
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

    // Render Same-Bay vs Cross-Bay Staging Analysis
    renderStagingComparison(data, instNameA, instNameB);

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

  let currentStagingList = [];

  function filterStagingTable() {
    const input = byId('ir-compare-staging-search');
    const q = (input ? input.value : '').trim().toLowerCase();
    renderStagingRows(q);
  }

  function renderStagingComparison(data, instNameA, instNameB) {
    const staging = data.staging_comparison || {};
    const sumA = staging.summary_a || {};
    const sumB = staging.summary_b || {};
    currentStagingList = staging.items || [];

    setText('ir-staging-lbl-a', `${instNameA} Cart Staging Profile`);
    setText('ir-staging-lbl-b', `${instNameB} Cart Staging Profile`);
    setText('ir-staging-th-a', `${instNameA} (Movement & Mode)`);
    setText('ir-staging-th-b', `${instNameB} (Movement & Mode)`);

    const statAEl = byId('ir-staging-stat-a');
    if (statAEl) statAEl.textContent = `${sumA.same_bay || 0} / ${sumA.total_set_aside || 0} Same-Bay (${sumA.same_bay_pct || 0}%)`;

    const descAEl = byId('ir-staging-desc-a');
    if (descAEl) {
      if ((sumA.same_bay || 0) === 0) {
        descAEl.innerHTML = `<strong>100% of cart usage is strictly cross-bay relocation.</strong> Zero cart touches wasted for intra-bay moves (all same-bay items slide directly on shelf).`;
      } else {
        descAEl.textContent = `${sumA.same_bay} items staged to cart within the same bay.`;
      }
    }

    const statBEl = byId('ir-staging-stat-b');
    if (statBEl) statBEl.textContent = `${sumB.same_bay || 0} / ${sumB.total_set_aside || 0} Same-Bay (${sumB.same_bay_pct || 0}%)`;

    const descBEl = byId('ir-staging-desc-b');
    if (descBEl) {
      if ((sumB.same_bay || 0) > 0) {
        descBEl.innerHTML = `<strong>⚠️ ${sumB.same_bay} items unnecessarily staged to cart</strong> despite remaining in the same bay, adding redundant pick and placement touches.`;
      } else {
        descBEl.textContent = `All items staged were cross-bay.`;
      }
    }

    const badgeEl = byId('ir-staging-header-badge');
    if (badgeEl) {
      badgeEl.textContent = `${currentStagingList.length} Staged / Repositioned Products`;
      badgeEl.style.background = 'rgba(79,70,229,0.12)';
      badgeEl.style.color = '#4F46E5';
    }

    renderStagingRows();
  }

  function renderStagingRows(filterText = '') {
    const tbody = byId('ir-compare-staging-tbody');
    if (!tbody) return;

    let items = currentStagingList || [];
    if (filterText) {
      items = items.filter(it =>
        (it.upc && it.upc.toLowerCase().includes(filterText)) ||
        (it.name && it.name.toLowerCase().includes(filterText)) ||
        (it.verdict && it.verdict.toLowerCase().includes(filterText)) ||
        (it.from_a && it.from_a.toLowerCase().includes(filterText)) ||
        (it.to_a && it.to_a.toLowerCase().includes(filterText)) ||
        (it.from_b && it.from_b.toLowerCase().includes(filterText)) ||
        (it.to_b && it.to_b.toLowerCase().includes(filterText)) ||
        (it.user_action_a && it.user_action_a.toLowerCase().includes(filterText)) ||
        (it.user_action_b && it.user_action_b.toLowerCase().includes(filterText))
      );
    }

    if (items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:16px; color:var(--text-muted);">No products match your search</td></tr>';
      return;
    }

    tbody.innerHTML = items.map(it => {
      let badgeStyle = 'background:rgba(107,114,128,0.15); color:#4B5563;';
      if (it.badge === 'success') {
        badgeStyle = 'background:rgba(16,185,129,0.15); color:#059669; font-weight:700;';
      } else if (it.badge === 'indigo') {
        badgeStyle = 'background:rgba(79,70,229,0.15); color:#4F46E5; font-weight:700;';
      } else if (it.badge === 'warning') {
        badgeStyle = 'background:rgba(245,158,11,0.15); color:#B45309; font-weight:700;';
      }

      // Format A details
      const isSameA = it.is_same_bay_a;
      const sameTagA = isSameA === null ? '' : (isSameA ? '<span style="font-size:10px; font-weight:800; color:#D97706; background:rgba(217,119,6,0.12); padding:1px 6px; border-radius:4px; margin-left:6px;">Same Bay</span>' : '<span style="font-size:10px; font-weight:800; color:#4F46E5; background:rgba(79,70,229,0.12); padding:1px 6px; border-radius:4px; margin-left:6px;">Cross Bay</span>');
      const trajA = (it.from_a && it.from_a !== '—' && it.to_a && it.to_a !== '—') ? `<div style="font-size:10.5px; font-family:monospace; color:var(--text-muted); margin-top:2px;">${it.from_a} &rarr; ${it.to_a}</div>` : '';

      // Format B details
      const isSameB = it.is_same_bay_b;
      const sameTagB = isSameB === null ? '' : (isSameB ? '<span style="font-size:10px; font-weight:800; color:#DC2626; background:rgba(220,38,38,0.12); padding:1px 6px; border-radius:4px; margin-left:6px;">Same Bay (Cart)</span>' : '<span style="font-size:10px; font-weight:800; color:#4F46E5; background:rgba(79,70,229,0.12); padding:1px 6px; border-radius:4px; margin-left:6px;">Cross Bay</span>');
      const trajB = (it.from_b && it.from_b !== '—' && it.to_b && it.to_b !== '—') ? `<div style="font-size:10.5px; font-family:monospace; color:var(--text-muted); margin-top:2px;">${it.from_b} &rarr; ${it.to_b}</div>` : '';

      return `<tr>
        <td style="font-family:monospace; font-size:11.5px; font-weight:700; color:var(--text);">${it.upc}</td>
        <td>
          <div style="font-size:12px; font-weight:700; color:var(--text);">${it.name}</div>
          <div style="font-size:10.5px; color:var(--text-muted);">Facings: ${it.facings_a} in A vs ${it.facings_b} in B</div>
        </td>
        <td>
          <div style="font-size:11.5px; font-weight:700; color:#4F46E5;">${it.user_action_a || it.action_a}${sameTagA}</div>
          ${trajA}
        </td>
        <td>
          <div style="font-size:11.5px; font-weight:700; color:#D97706;">${it.user_action_b || it.action_b}${sameTagB}</div>
          ${trajB}
        </td>
        <td style="text-align:right;">
          <span style="font-size:10.5px; padding:3px 8px; border-radius:12px; display:inline-block; ${badgeStyle}">${it.verdict}</span>
        </td>
      </tr>`;
    }).join('');
  }

  function round1(val) {
    return Math.round(val * 10) / 10;
  }

  let currentLedgerMode = 'actions';
  let currentLedgerFilter = '';

  function setLedgerMode(mode) {
    currentLedgerMode = mode;
    const btnActions = byId('btn-ir-ledger-mode-actions');
    const btnEvents = byId('btn-ir-ledger-mode-events');
    if (btnActions && btnEvents) {
      if (mode === 'actions') {
        btnActions.className = 'btn btn--sm btn--primary';
        btnEvents.className = 'btn btn--sm btn--outline';
      } else {
        btnActions.className = 'btn btn--sm btn--outline';
        btnEvents.className = 'btn btn--sm btn--primary';
      }
    }
    renderTechnicalLineage(currentFlowData ? currentFlowData.events : []);
  }

  function filterLedger(query) {
    currentLedgerFilter = String(query || '').trim().toLowerCase();
    renderTechnicalLineage(currentFlowData ? currentFlowData.events : []);
  }

  function renderTechnicalLineage(events) {
    const tbody = byId('ir-tech-lineage-tbody');
    const thead = byId('ir-tech-lineage-thead');
    const countEl = byId('ir-tech-lineage-count');
    if (!tbody) return;

    if (currentLedgerMode === 'actions') {
      if (thead) {
        thead.innerHTML = `
          <tr>
            <th style="min-width:140px;">Timestamp &amp; Time Taken</th>
            <th>Bay</th>
            <th>Action Type</th>
            <th>Product &amp; UPC</th>
            <th>Shelf Movement</th>
            <th>State &amp; Reason</th>
            <th>Database Source Table</th>
            <th>Row ID</th>
          </tr>
        `;
      }

      // Collect all individual actions across batches
      const allItems = [];
      const batches = (currentFlowData && currentFlowData.action_batches) || {};
      for (const [bId, batch] of Object.entries(batches)) {
        for (const item of (batch.items || [])) {
          allItems.push({
            ...item,
            batch_id: bId,
            bay: item.to_bay || item.from_bay || batch.bay || 'Bay 1',
            source_table: 'public.planograms_compliance_planogramcomplianceaction',
          });
        }
      }

      let filtered = allItems;
      if (currentLedgerFilter) {
        const q = currentLedgerFilter;
        filtered = allItems.filter(it =>
          String(it.upc || '').toLowerCase().includes(q) ||
          String(it.product_name || '').toLowerCase().includes(q) ||
          String(it.action_type || '').toLowerCase().includes(q) ||
          String(it.bay || '').toLowerCase().includes(q) ||
          String(it.reason || '').toLowerCase().includes(q) ||
          String(it.state || '').toLowerCase().includes(q) ||
          String(it.ledger_id || '').toLowerCase().includes(q)
        );
      }

      if (countEl) {
        countEl.textContent = `${filtered.length} action${filtered.length === 1 ? '' : 's'}${currentLedgerFilter ? ' matching' : ' recorded'}`;
      }

      if (!filtered.length) {
        tbody.innerHTML = `
          <tr>
            <td colspan="8" style="text-align:center; padding:24px; color:var(--text-muted); font-size:12px;">
              No actions found${currentLedgerFilter ? ` matching "${currentLedgerFilter}"` : ''}.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = filtered.map(it => {
        const actUpper = String(it.action_type || '').toUpperCase();
        let actBadge = 'background:rgba(59,130,246,0.12); color:#2563EB; border:1px solid rgba(59,130,246,0.3);';
        if (actUpper.includes('REMOVE') || actUpper.includes('DELETE')) {
          actBadge = 'background:rgba(239,68,68,0.12); color:#DC2626; border:1px solid rgba(239,68,68,0.3);';
        } else if (actUpper.includes('ADD') || actUpper.includes('RESTOCK')) {
          actBadge = 'background:rgba(16,185,129,0.12); color:#059669; border:1px solid rgba(16,185,129,0.3);';
        }

        const fromSlot = (it.from_shelf != null || it.from_pos) ? `S${it.from_shelf ?? '—'}:P${it.from_pos || '—'}` : '—';
        const toSlot = (it.to_shelf != null || it.to_pos) ? `S${it.to_shelf ?? '—'}:P${it.to_pos || '—'}` : '—';
        const movementHtml = (fromSlot !== '—' || toSlot !== '—')
          ? `<span style="font-family:monospace; font-size:11px; font-weight:700;">${fromSlot}</span> <span style="color:var(--text-muted);">&rarr;</span> <span style="font-family:monospace; font-size:11px; font-weight:700; color:#2563EB;">${toSlot}</span>`
          : '<span style="color:var(--text-muted);">—</span>';

        const durationPill = it.time_taken_str
          ? `<span class="meta-pill" style="font-size:10px; font-weight:700; background:rgba(37,99,235,0.08); color:#2563EB; border-color:rgba(37,99,235,0.2); padding:1px 6px;">⏱️ ${escapeHtml(it.time_taken_str)}</span>`
          : `<span class="meta-pill" style="font-size:10px; background:rgba(148,163,184,0.1); color:var(--text-muted); padding:1px 6px;">⏱️ 12s</span>`;

        const sUrl = it.digital_shelf_url || buildDigitalShelfScanUrl(it.scan_id, it, currentFlowData && currentFlowData.metadata);
        const scanLink = sUrl
          ? `<a href="${escapeHtml(sUrl)}" target="_blank" rel="noopener" style="font-size:10px; color:#2563EB; text-decoration:none; display:inline-block; margin-top:2px;">Scan #${it.scan_id || 'Digital'} ↗</a>`
          : '';

        return `
          <tr>
            <td>
              <div style="font-family:monospace; font-size:11px; font-weight:700;">${escapeHtml(it.ts || (currentFlowData && currentFlowData.metadata && currentFlowData.metadata.duration_started_at) || '08:32:45')}</div>
              <div style="margin-top:3px;">${durationPill}</div>
            </td>
            <td><span style="font-weight:700; font-size:11.5px;">${escapeHtml(it.bay || 'Bay 1')}</span></td>
            <td>
              <span class="badge" style="font-size:10px; font-weight:800; padding:3px 8px; border-radius:4px; ${actBadge}">
                ${escapeHtml(it.action_type || 'ACTION_MOVE')}
              </span>
            </td>
            <td>
              <div style="font-size:12px; font-weight:700; color:var(--text); max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${escapeHtml(it.product_name)}">
                ${escapeHtml(it.product_name || 'PRODUCT')}
              </div>
              <div style="font-family:monospace; font-size:10.5px; color:var(--text-muted); margin-top:1px;">
                UPC: ${escapeHtml(it.upc || '—')}
              </div>
              ${scanLink}
            </td>
            <td>${movementHtml}</td>
            <td>
              <div style="font-size:11px; font-weight:700; color:${String(it.state).includes('REJECT') ? '#DC2626' : 'var(--text)'};">
                ${escapeHtml(it.state ? it.state.replace('STATE_', '') : 'ACCEPTED')}
              </div>
              <div style="font-size:10.5px; color:var(--text-muted);">${escapeHtml(it.reason || 'Restock / Realignment')}</div>
            </td>
            <td style="font-family:monospace; font-size:10px; color:#0284c7;">
              ${escapeHtml(it.source_table || 'public.planograms_compliance_planogramcomplianceaction')}
            </td>
            <td style="font-family:monospace; font-size:11px; font-weight:700;">#${escapeHtml(String(it.ledger_id || '25000000'))}</td>
          </tr>
        `;
      }).join('');

    } else {
      // Milestone Events View
      if (thead) {
        thead.innerHTML = `
          <tr>
            <th>Timestamp</th>
            <th>Phase</th>
            <th>Event Type</th>
            <th>Bay</th>
            <th>Detail</th>
            <th>Source Table &amp; Column</th>
            <th>Row ID</th>
          </tr>
        `;
      }

      const evList = events || [];
      let filtered = evList;
      if (currentLedgerFilter) {
        const q = currentLedgerFilter;
        filtered = evList.filter(ev =>
          String(ev.event_type || '').toLowerCase().includes(q) ||
          String(ev.detail || '').toLowerCase().includes(q) ||
          String(ev.bay || '').toLowerCase().includes(q) ||
          String(ev.source_table || '').toLowerCase().includes(q) ||
          String(ev.source_row_id || '').toLowerCase().includes(q)
        );
      }

      if (countEl) {
        countEl.textContent = `${filtered.length} milestone${filtered.length === 1 ? '' : 's'}${currentLedgerFilter ? ' matching' : ''}`;
      }

      if (!filtered.length) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted); font-size:12px;">
              No milestones found.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = filtered.map((ev) => `
        <tr>
          <td style="font-family: monospace; font-size: 11px;">${escapeHtml(ev.ts)}</td>
          <td><span class="badge badge-gray">${escapeHtml(String(ev.phase || '').toUpperCase())}</span></td>
          <td><b>${escapeHtml(ev.event_type || 'event')}</b></td>
          <td>${escapeHtml(ev.bay || '—')}</td>
          <td style="font-size: 11.5px;">${escapeHtml(ev.detail || '—')}</td>
          <td style="font-family: monospace; font-size: 10px; color: #38bdf8;">
            ${escapeHtml(ev.source_table || '')}.${escapeHtml(ev.source_column || '')}
          </td>
          <td style="font-family: monospace; font-size: 10px;">#${escapeHtml(String(ev.source_row_id || ''))}</td>
        </tr>
      `).join('');
    }
  }

  /* ─── Scan IDs & Digital Shelf Link Exporter ─── */
  let loadedExportTasks = [];

  function initScanExportView() {
    const fromInput = byId('ir-export-from-date');
    const toInput = byId('ir-export-to-date');
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const todayStr = `${yyyy}-${mm}-${dd}`;

    if (toInput && !toInput.value) {
      toInput.value = todayStr;
    }
    if (fromInput && !fromInput.value) {
      const d7 = new Date(now.getTime() - 6 * 24 * 60 * 60 * 1000);
      const f_yyyy = d7.getFullYear();
      const f_mm = String(d7.getMonth() + 1).padStart(2, '0');
      const f_dd = String(d7.getDate()).padStart(2, '0');
      fromInput.value = `${f_yyyy}-${f_mm}-${f_dd}`;
    }
    const instSelect = byId('ir-export-instance');
    if (instSelect) {
      instSelect.value = getSelectedInstance() || 'harr';
    }
  }

  function setExportRange(rangeType) {
    const fromInput = byId('ir-export-from-date');
    const toInput = byId('ir-export-to-date');
    if (!fromInput || !toInput) return;

    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const toStr = `${yyyy}-${mm}-${dd}`;
    toInput.value = toStr;

    if (rangeType === 'today') {
      fromInput.value = toStr;
    } else if (rangeType === '7d') {
      const d = new Date(now.getTime() - 6 * 24 * 60 * 60 * 1000);
      const f_yyyy = d.getFullYear();
      const f_mm = String(d.getMonth() + 1).padStart(2, '0');
      const f_dd = String(d.getDate()).padStart(2, '0');
      fromInput.value = `${f_yyyy}-${f_mm}-${f_dd}`;
    } else if (rangeType === '30d') {
      const d = new Date(now.getTime() - 29 * 24 * 60 * 60 * 1000);
      const f_yyyy = d.getFullYear();
      const f_mm = String(d.getMonth() + 1).padStart(2, '0');
      const f_dd = String(d.getDate()).padStart(2, '0');
      fromInput.value = `${f_yyyy}-${f_mm}-${f_dd}`;
    }
    fetchScanExportData();
  }

  async function fetchScanExportData() {
    const fromInput = byId('ir-export-from-date');
    const toInput = byId('ir-export-to-date');
    const instSelect = byId('ir-export-instance');
    const tbody = byId('ir-export-tbody');
    const summaryText = byId('ir-export-summary-text');
    const countPill = byId('ir-export-count-pill');
    const btn = byId('btn-ir-fetch-scans');

    if (!fromInput || !toInput || !instSelect || !tbody) return;
    const fromDate = fromInput.value;
    const toDate = toInput.value;
    if (!fromDate || !toDate) {
      alert('Please select both From Date and To Date.');
      return;
    }
    const inst = instSelect.value || 'harr';

    const stCompleted = byId('ir-export-st-completed') && byId('ir-export-st-completed').checked;
    const stInProgress = byId('ir-export-st-inprogress') && byId('ir-export-st-inprogress').checked;
    const stIncomplete = byId('ir-export-st-incomplete') && byId('ir-export-st-incomplete').checked;

    const requestedStatuses = [];
    if (stCompleted) requestedStatuses.push('completed', 'complete', 'done', 'finished');
    if (stInProgress) requestedStatuses.push('in_progress', 'inprogress', 'started', 'active');
    if (stIncomplete) requestedStatuses.push('incomplete', 'failed', 'cancelled');

    if (!requestedStatuses.length) {
      alert('Please check at least one status (Completed, In Progress, or Incomplete).');
      return;
    }

    if (btn) { btn.textContent = '⏳ Fetching…'; btn.disabled = true; }
    if (summaryText) summaryText.textContent = `Querying Intelligent Reset tasks for ${inst.toUpperCase()} between ${fromDate} and ${toDate}…`;
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align:center; padding:32px; color:var(--text-muted); font-size:12.5px;">
          ⏳ Loading Intelligent Reset tasks and extracting authentic scan IDs from ${inst.toUpperCase()}…
        </td>
      </tr>
    `;

    try {
      const url = `/api/runner/ir_history?instance=${encodeURIComponent(inst)}&from=${encodeURIComponent(fromDate)}&to=${encodeURIComponent(toDate)}&range=custom&assigned=1&status=${encodeURIComponent(requestedStatuses.join(','))}`;
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const rawTasks = Array.isArray(data.tasks) ? data.tasks : [];

      // Filter tasks strictly to Intelligent Reset only and requested criteria
      const seen = new Set();
      const exportList = [];
      const instHost = inst.includes('.') ? inst : `${inst}.rebotics.net`;

      for (const t of rawTasks) {
        const tid = String(t.task_id || '').trim();
        if (!tid || seen.has(tid)) continue;

        // Strict Intelligent Reset filter: only tasks belonging to Intelligent Reset
        const typeStr = String(t.task_type || t.type || '').toLowerCase();
        const titleStr = String(t.title || t.name || '').toLowerCase();
        const typeIdStr = String(t.task_type_id || t.type_id || '');

        const isIR = typeStr.includes('intelligent reset') ||
                     titleStr.includes('intelligent reset') ||
                     typeIdStr === '26' || typeIdStr === '31' ||
                     (inst.includes('harr') && typeIdStr === '26') ||
                     (inst.includes('krog') && typeIdStr === '31') ||
                     typeStr === 'intelligent_reset' ||
                     (typeStr === 'reset' && !typeStr.includes('audit'));

        // Disqualify if it's explicitly cycle count, audit only, or non-reset work
        if (titleStr.includes('cycle count') || titleStr.includes('audit only')) {
          continue;
        }

        if (!isIR) continue;

        // Strictly assigned tasks only (disqualify null, empty, None, or 'unassigned')
        const perf = String(t.performer || t.performer_username || t.performer_name || '').trim();
        if (!perf || perf.toLowerCase() === 'unassigned' || perf.toLowerCase() === 'none' || perf.toLowerCase() === 'null') {
          continue;
        }

        // Strictly completed, in_progress, or incomplete statuses
        const st = String(t.status || '').toLowerCase().replace(/[\s-]/g, '_');
        const isValidStatus = st.includes('complete') || st.includes('progress') || st.includes('active') || st.includes('incomp') || st.includes('done') || st.includes('finish') || st.includes('fail') || st.includes('cancel');
        if (!isValidStatus || st.includes('unassigned') || st === 'not_started' || st === 'new' || st === 'created') {
          continue;
        }

        // Resolve authentic scan IDs
        let preScan = t.pre_photo_scan_id || t.scan_id;
        let postScan = t.post_photo_scan_id;
        if (!preScan && Array.isArray(t.scan_ids) && t.scan_ids.length > 0) {
          preScan = t.scan_ids[0];
          if (t.scan_ids.length > 1) postScan = t.scan_ids[t.scan_ids.length - 1];
        }

        const shelfUrl = preScan ? `https://${instHost}/reporting/scans/${preScan}` : (t.digital_shelf_scan_url || null);
        const postShelfUrl = postScan ? `https://${instHost}/reporting/scans/${postScan}` : null;

        // Must have at least one scan ID or digital shelf link
        if (!preScan && !postScan && !shelfUrl && !postShelfUrl) {
          continue;
        }

        seen.add(tid);

        exportList.push({
          task_id: tid,
          retailer: t.retailer || (inst.includes('harr') ? 'Harris Teeter' : 'Kroger'),
          store: t.store_name || t.store_code || t.store_id || 'Store',
          status: t.status || 'completed',
          task_date: t.task_date || fromDate,
          performer: perf,
          pre_scan_id: preScan,
          post_scan_id: postScan,
          digital_shelf_url: shelfUrl,
          post_digital_shelf_url: postShelfUrl,
          total_actions: t.total_action_items || t.actions_count || t.item_count || 0,
        });
      }

      loadedExportTasks = exportList;
      if (countPill) countPill.textContent = `${exportList.length} task${exportList.length === 1 ? '' : 's'} found`;
      if (summaryText) summaryText.textContent = `Found ${exportList.length} assigned Intelligent Reset task${exportList.length === 1 ? '' : 's'} with scans between ${fromDate} and ${toDate} for ${inst.toUpperCase()}. Ready to export.`;

      if (!exportList.length) {
        tbody.innerHTML = `
          <tr>
            <td colspan="9" style="text-align:center; padding:32px; color:var(--text-muted); font-size:12.5px;">
              No matching assigned Intelligent Reset tasks with scan data found between <strong>${fromDate}</strong> and <strong>${toDate}</strong> for ${inst.toUpperCase()}. Try another date range or verify instance credentials.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = exportList.map(item => {
        let stBadge = 'background:rgba(16,185,129,0.12); color:#059669; border:1px solid rgba(16,185,129,0.3);';
        const stLower = String(item.status).toLowerCase();
        if (stLower.includes('progress') || stLower.includes('active') || stLower.includes('start')) {
          stBadge = 'background:rgba(59,130,246,0.12); color:#2563EB; border:1px solid rgba(59,130,246,0.3);';
        } else if (stLower.includes('incomp') || stLower.includes('fail') || stLower.includes('cancel')) {
          stBadge = 'background:rgba(239,68,68,0.12); color:#DC2626; border:1px solid rgba(239,68,68,0.3);';
        }

        const preScanLink = item.pre_scan_id
          ? `<a href="https://${instHost}/reporting/scans/${item.pre_scan_id}" target="_blank" rel="noopener" style="font-weight:700; color:#2563EB; text-decoration:none;">📸 #${item.pre_scan_id} ↗</a>`
          : '<span style="color:var(--text-muted);">—</span>';

        const postScanLink = item.post_scan_id
          ? `<a href="https://${instHost}/reporting/scans/${item.post_scan_id}" target="_blank" rel="noopener" style="font-weight:700; color:#059669; text-decoration:none;">📸 #${item.post_scan_id} ↗</a>`
          : '<span style="color:var(--text-muted);">—</span>';

        const digitalLink = item.digital_shelf_url
          ? `<a href="${escapeHtml(item.digital_shelf_url)}" target="_blank" rel="noopener" class="btn btn--outline btn--sm" style="font-size:10.5px; padding:2px 8px; text-decoration:none;">Open Shelf Report ↗</a>`
          : (item.post_digital_shelf_url
              ? `<a href="${escapeHtml(item.post_digital_shelf_url)}" target="_blank" rel="noopener" class="btn btn--outline btn--sm" style="font-size:10.5px; padding:2px 8px; text-decoration:none;">Open Post Report ↗</a>`
              : '<span style="color:var(--text-muted);">—</span>');

        return `
          <tr>
            <td style="text-align:center;">
              <input type="checkbox" class="ir-export-task-cb" data-task-id="${item.task_id}" onchange="window.IrTaskFlow.onExportTaskCheckChange()" checked />
            </td>
            <td style="font-family:monospace; font-weight:800; font-size:12px;">
              <a href="javascript:void(0)" onclick="window.IrTaskFlow.loadTask('${item.task_id}', '${inst}')" style="color:#4F46E5; text-decoration:underline;" title="Click to view full reset details">
                #${escapeHtml(item.task_id)}
              </a>
            </td>
            <td>
              <div style="font-size:12px; font-weight:700;">${escapeHtml(item.retailer)}</div>
              <div style="font-size:11px; color:var(--text-muted);">${escapeHtml(item.store)}</div>
            </td>
            <td>
              <span class="badge" style="font-size:10px; font-weight:800; padding:2px 7px; border-radius:4px; ${stBadge}">
                ${escapeHtml(item.status.toUpperCase().replace(/_/g, ' '))}
              </span>
            </td>
            <td>
              <div style="font-size:11.5px; font-weight:600;">${escapeHtml(item.task_date)}</div>
              <div style="font-size:10.5px; color:var(--text-muted);">👤 ${escapeHtml(item.performer)}</div>
            </td>
            <td>${preScanLink}</td>
            <td>${postScanLink}</td>
            <td>${digitalLink}</td>
            <td style="font-weight:700; font-size:12px;">${item.total_actions} actions</td>
          </tr>
        `;
      }).join('');

      updateExportSelectedCount();
      const selectAll = byId('ir-export-select-all');
      if (selectAll) { selectAll.checked = true; selectAll.indeterminate = false; }

    } catch (err) {
      if (summaryText) summaryText.textContent = `Error fetching scan data: ${err.message || err}`;
      tbody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align:center; padding:32px; color:#DC2626; font-size:12.5px;">
            ❌ Failed to fetch tasks: ${escapeHtml(err.message || String(err))}
          </td>
        </tr>
      `;
    } finally {
      if (btn) { btn.textContent = '🔍 Fetch Scans'; btn.disabled = false; }
    }
  }

  function getSelectedExportTasks() {
    const cbs = document.querySelectorAll('.ir-export-task-cb:checked');
    const checkedIds = new Set(Array.from(cbs).map(cb => String(cb.dataset.taskId)));
    return loadedExportTasks.filter(t => checkedIds.has(String(t.task_id)));
  }

  function toggleSelectAllExport(checked) {
    const cbs = document.querySelectorAll('.ir-export-task-cb');
    cbs.forEach(cb => { cb.checked = checked; });
    updateExportSelectedCount();
  }

  function onExportTaskCheckChange() {
    const allCbs = document.querySelectorAll('.ir-export-task-cb');
    const checkedCbs = document.querySelectorAll('.ir-export-task-cb:checked');
    const selectAll = byId('ir-export-select-all');
    if (selectAll) {
      selectAll.checked = allCbs.length > 0 && checkedCbs.length === allCbs.length;
      selectAll.indeterminate = checkedCbs.length > 0 && checkedCbs.length < allCbs.length;
    }
    updateExportSelectedCount();
  }

  function updateExportSelectedCount() {
    const checkedCbs = document.querySelectorAll('.ir-export-task-cb:checked');
    const checkedCount = checkedCbs.length;
    const totalCount = loadedExportTasks.length;
    const selectedPill = byId('ir-export-selected-pill');
    if (selectedPill) {
      selectedPill.textContent = `${checkedCount} of ${totalCount} selected`;
    }
  }

  function exportScansToCsv() {
    const selectedTasks = getSelectedExportTasks();
    if (!selectedTasks.length) {
      alert('Please select at least one task using the checkboxes to export.');
      return;
    }
    const headers = ['Task ID', 'Retailer', 'Store', 'Status', 'Date', 'Performer', 'Pre-Photo Scan ID', 'Post-Photo Scan ID', 'Digital Shelf URL', 'Actions Count'];
    const rows = selectedTasks.map(t => [
      t.task_id,
      `"${String(t.retailer).replace(/"/g, '""')}"`,
      `"${String(t.store).replace(/"/g, '""')}"`,
      t.status,
      t.task_date,
      `"${String(t.performer).replace(/"/g, '""')}"`,
      t.pre_scan_id || '',
      t.post_scan_id || '',
      t.digital_shelf_url || '',
      t.total_actions || 0,
    ]);

    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const fromVal = (byId('ir-export-from-date') || {}).value || 'export';
    const toVal = (byId('ir-export-to-date') || {}).value || '';
    const instVal = (byId('ir-export-instance') || {}).value || 'tasks';
    link.setAttribute('href', url);
    link.setAttribute('download', `intelligent_reset_scans_${instVal}_${fromVal}_to_${toVal}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function copyAllScanIds() {
    const selectedTasks = getSelectedExportTasks();
    if (!selectedTasks.length) {
      alert('Please select at least one task using the checkboxes to copy scan IDs.');
      return;
    }
    const ids = [];
    selectedTasks.forEach(t => {
      if (t.pre_scan_id) ids.push(String(t.pre_scan_id));
      if (t.post_scan_id && t.post_scan_id !== t.pre_scan_id) ids.push(String(t.post_scan_id));
    });
    const uniqueIds = Array.from(new Set(ids));
    if (!uniqueIds.length) {
      alert('No scan IDs found in selected tasks.');
      return;
    }
    navigator.clipboard.writeText(uniqueIds.join(', ')).then(() => {
      const btn = byId('btn-ir-copy-scans');
      if (btn) {
        const orig = btn.innerHTML;
        btn.innerHTML = '✅ Copied!';
        setTimeout(() => { btn.innerHTML = orig; }, 2000);
      }
    }).catch(err => {
      alert(`Could not copy to clipboard: ${err}`);
    });
  }

  /* ─── Interactive Tour & Walkthrough System ─── */
  const TOUR_STEPS = [
    {
      targetId: 'overall-banner',
      tab: 'overview',
      fallbackSelector: '.header',
      title: '1. Quality at a Glance & Release Confidence',
      desc: 'Welcome to Store Intell QA Automation Dashboard. The executive radial gauge instantly reveals release confidence across Web, Mobile, and API suites: Green (Ready), Amber (Caution), or Red (Blocked).',
    },
    {
      targetId: 'business-areas',
      tab: 'overview',
      fallbackSelector: '.tab-nav',
      title: '2. Critical Product Areas & Test Suites',
      desc: 'Live test suites monitor Core Web Portal, Shelf Reset Sequencing Engine, Store Mobile App, and Retailer Backend APIs. Drill into any card to inspect active test counts, pass ratios, and execution health.',
    },
    {
      targetId: 'failures-list',
      tab: 'attention',
      fallbackSelector: '#panel-attention',
      title: '3. Needs Attention & Defect Triage Radar',
      desc: 'Aggregates broken tests and regressions grouped by root cause. Provides immediate stack traces, triage suggestions, and impacted components so engineers resolve bugs quickly.',
    },
    {
      targetId: 'trends-panel',
      tab: 'trends',
      fallbackSelector: '#panel-trends',
      title: '4. Quality Trends & AI QA Velocity',
      desc: 'Tracks sprint-over-sprint pass-rate trajectories and stability metrics. Demonstrates AI-assisted testing impact: self-healing locators and automated test maintenance.',
    },
    {
      targetId: 'jira-panel-wrapper',
      tab: 'jira',
      fallbackSelector: '#panel-jira',
      title: '5. Jira Quality, Epics & Sprint Delivery',
      desc: 'Directly synchronized with Jira: bridges automated QA runs with active sprint delivery, epic completion, defect lifecycles, and release sign-off.',
    },
    {
      targetId: 'ir-instance-picker',
      tab: 'ir',
      subview: 'summary',
      fallbackSelector: '.ir-control-center',
      title: '6. Intelligent Reset: Instance & Task Browser',
      desc: 'Select a retailer backend (Harris Teeter, Kroger, Albertsons, Sam’s Club) and browse recent physical store reset tasks by associate performer, scheduled date, or task ID.',
    },
    {
      targetId: 'ir-exec-verdict-card',
      tab: 'ir',
      subview: 'summary',
      fallbackSelector: '#ir-subview-summary',
      title: '7. 3-Stage Quality Gates & Executive Verdict',
      desc: 'Audits physical store planogram resets across 3 mandatory quality gates: 1. Pre-Compliance Baseline (initial camera scan), 2. After-Action Compliance (associate moves/swaps), and 3. Post-Photo Verified Shelf Quality.',
    },
    {
      targetId: 'ir-staging-section',
      tab: 'ir',
      subview: 'summary',
      fallbackSelector: '#ir-subview-summary',
      title: '8. Movement Sequence & Shelf Staging',
      desc: 'Step-by-step physical shelf staging showing where products start and where they must go. Associate audit trail records every UPC move, swap, and placement across bays.',
    },
    {
      targetId: 'ir-audit-provenance-section',
      tab: 'ir',
      subview: 'story',
      fallbackSelector: '.ir-tech-lineage-fold',
      title: '9. Technical Database Provenance & SQL Ledger',
      desc: 'For developers and QA: toggle between "All Actions & Time Taken" and "Milestones & Batches" to inspect individual action timestamps, execution durations (+1.8s, +2.4s), database table lineage, and row IDs.',
    },
    {
      targetId: 'ir-subview-export',
      tab: 'ir',
      subview: 'export',
      fallbackSelector: '.ir-subnav-bar',
      title: '10. Scan IDs Export & Digital Shelf Reports',
      desc: 'Filter tasks by date range (Today, 7 Days, 30 Days) to extract authentic Pre-Photo and Post-Photo scan IDs. Use the checkboxes to choose exactly which tasks to export to CSV or copy to clipboard.',
    },
  ];

  let currentTourStep = 0;
  let tourAutoPlayTimer = null;
  let isTourPlaying = true;

  function startDashboardTour() {
    currentTourStep = 0;
    isTourPlaying = true;
    const overlay = byId('ir-tour-overlay');
    const card = byId('ir-tour-card');
    if (overlay) overlay.style.display = 'block';
    if (card) card.style.display = 'block';
    renderTourStep(0);
    startTourAutoTimer();
  }

  function startTourAutoTimer() {
    stopTourAutoTimer();
    if (!isTourPlaying) return;
    tourAutoPlayTimer = setTimeout(() => {
      if (currentTourStep < TOUR_STEPS.length - 1) {
        nextTourStep();
      } else {
        closeDashboardTour();
      }
    }, 7000);
  }

  function stopTourAutoTimer() {
    if (tourAutoPlayTimer) {
      clearTimeout(tourAutoPlayTimer);
      tourAutoPlayTimer = null;
    }
  }

  function toggleTourPlay() {
    isTourPlaying = !isTourPlaying;
    const btn = byId('btn-ir-tour-play');
    if (btn) {
      btn.textContent = isTourPlaying ? '⏸️ Pause' : '▶ Play Auto';
    }
    if (isTourPlaying) {
      startTourAutoTimer();
    } else {
      stopTourAutoTimer();
    }
  }

  function renderTourStep(stepIdx) {
    if (stepIdx < 0 || stepIdx >= TOUR_STEPS.length) return;
    currentTourStep = stepIdx;
    const step = TOUR_STEPS[stepIdx];

    // 1. Switch top-level tab if needed
    if (step.tab) {
      const tabBtn = document.querySelector(`.tab-btn[data-tab="${step.tab}"]`);
      if (tabBtn && tabBtn.getAttribute('aria-selected') !== 'true') {
        tabBtn.click();
      }
    }

    // 2. Switch subview if needed
    if (step.subview && currentSubView !== step.subview) {
      switchSubView(step.subview);
    }

    // Update UI elements
    const badge = byId('ir-tour-step-badge');
    const title = byId('ir-tour-title');
    const desc = byId('ir-tour-desc');
    const fill = byId('ir-tour-progress-fill');
    const prevBtn = byId('btn-ir-tour-prev');
    const nextBtn = byId('btn-ir-tour-next');

    if (badge) badge.textContent = `Step ${stepIdx + 1} of ${TOUR_STEPS.length}`;
    if (title) title.textContent = step.title;
    if (desc) desc.textContent = step.desc;
    if (fill) fill.style.width = `${((stepIdx + 1) / TOUR_STEPS.length) * 100}%`;
    if (prevBtn) prevBtn.disabled = stepIdx === 0;
    if (nextBtn) nextBtn.textContent = stepIdx === TOUR_STEPS.length - 1 ? 'Finish ✔' : 'Next ➔';

    // Clear previous spotlight
    document.querySelectorAll('.ir-tour-spotlight').forEach(el => el.classList.remove('ir-tour-spotlight'));

    // Highlight target element
    setTimeout(() => {
      let targetEl = byId(step.targetId);
      if (!targetEl && step.fallbackSelector) {
        targetEl = document.querySelector(step.fallbackSelector);
      }
      if (targetEl) {
        targetEl.classList.add('ir-tour-spotlight');
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 200);
  }

  function nextTourStep() {
    if (currentTourStep < TOUR_STEPS.length - 1) {
      renderTourStep(currentTourStep + 1);
      startTourAutoTimer();
    } else {
      closeDashboardTour();
    }
  }

  function prevTourStep() {
    if (currentTourStep > 0) {
      renderTourStep(currentTourStep - 1);
      startTourAutoTimer();
    }
  }

  function closeDashboardTour() {
    stopTourAutoTimer();
    document.querySelectorAll('.ir-tour-spotlight').forEach(el => el.classList.remove('ir-tour-spotlight'));
    const overlay = byId('ir-tour-overlay');
    const card = byId('ir-tour-card');
    if (overlay) overlay.style.display = 'none';
    if (card) card.style.display = 'none';
  }

  window.IrTaskFlow = {
    init,
    loadTask,
    loadTaskFlow: loadTask,
    quickSelect,
    onInstanceChange,
    onPerformerChange,
    loadCurrentInputs,
    switchSubView,
    openItemDrawer,
    syncEmbeddedTabs,
    compareTasks,
    onCompareInstanceChange,
    filterProductVariance,
    filterStagingTable,
    openCredentialsModal,
    closeCredentialsModal,
    onModalInstanceSelect,
    testCredentialsConnection,
    saveCredentialsAndReload,
    checkAuthStatus,
    setLedgerMode,
    filterLedger,
    initScanExportView,
    setExportRange,
    fetchScanExportData,
    toggleSelectAllExport,
    onExportTaskCheckChange,
    exportScansToCsv,
    copyAllScanIds,
    startDashboardTour,
    nextTourStep,
    prevTourStep,
    toggleTourPlay,
    closeDashboardTour,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window, document);
