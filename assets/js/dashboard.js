/**
 * Static automation dashboard — fetches run-summary.json from each repo.
 * Data sources: bundled data/*.json (updated by CI) with live fallback to GitHub Pages.
 */

const REPO_CONFIG = [
  {
    id: 'web',
    title: 'Web Automation',
    description: 'Selenium + Cucumber + Allure',
    localPath: 'data/web.json',
    remoteUrl: 'https://retech-us.github.io/retech-web-automation/run-summary.json',
    icon: '🌐',
  },
  {
    id: 'mobile',
    title: 'Mobile Automation',
    description: 'Appium + Allure (iOS & Android)',
    localPath: 'data/mobile.json',
    remoteUrl: 'https://retech-us.github.io/retech-mobile-automation/run-summary.json',
    icon: '📱',
  },
  {
    id: 'api',
    title: 'API Automation',
    description: 'REST Assured + Allure',
    localPath: 'data/api.json',
    remoteUrl: 'https://retech-us.github.io/retech-api-automation/run-summary.json',
    icon: '🔌',
  },
];

async function fetchSummary(config) {
  const sources = [config.localPath, config.remoteUrl];
  for (const url of sources) {
    try {
      const response = await fetch(url, { cache: 'no-store' });
      if (!response.ok) continue;
      const data = await response.json();
      if (data && data.repo) return data;
    } catch (_) {
      // try next source
    }
  }
  return null;
}

function formatDuration(ms) {
  if (!ms) return '—';
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function statusClass(status) {
  if (status === 'passed') return 'pass';
  if (status === 'failed') return 'fail';
  return 'unknown';
}

function renderCard(config, summary) {
  const status = summary?.status || 'unknown';
  const s = summary?.summary || { total: 0, passed: 0, failed: 0, skipped: 0 };

  return `
    <article class="card" data-repo="${config.id}">
      <div class="card__header">
        <div>
          <h2 class="card__title">${config.icon} ${config.title}</h2>
          <p class="card__desc">${config.description}</p>
        </div>
        <span class="status-badge ${statusClass(status)}">${status}</span>
      </div>
      <div class="card__body">
        <div class="stats">
          <div class="stat"><span class="stat__value">${s.total}</span><span class="stat__label">Total</span></div>
          <div class="stat"><span class="stat__value" style="color:var(--pass)">${s.passed}</span><span class="stat__label">Passed</span></div>
          <div class="stat"><span class="stat__value" style="color:var(--fail)">${s.failed + (s.broken || 0)}</span><span class="stat__label">Failed</span></div>
          <div class="stat"><span class="stat__value">${s.skipped}</span><span class="stat__label">Skipped</span></div>
        </div>
        <ul class="meta-list">
          <li><strong>Environment:</strong> ${summary?.environment || '—'}</li>
          <li><strong>Branch:</strong> ${summary?.branch || '—'} @ ${summary?.commit || '—'}</li>
          <li><strong>Finished:</strong> ${formatDate(summary?.finishedAt)}</li>
          <li><strong>Duration:</strong> ${formatDuration(summary?.durationMs)}</li>
        </ul>
        <div class="card__actions">
          <a class="link-btn primary" href="${summary?.reportUrl || '#'}" target="_blank" rel="noopener">View Allure Report</a>
          <a class="link-btn" href="${summary?.ciRunUrl || '#'}" target="_blank" rel="noopener">View CI Run</a>
        </div>
      </div>
    </article>
  `;
}

function renderOverallBanner(summaries) {
  const valid = summaries.filter(Boolean);
  if (!valid.length) {
    return '<strong>No run data available.</strong> Ensure each repo publishes <code>run-summary.json</code> to GitHub Pages.';
  }
  const failed = valid.filter((s) => s.status === 'failed').length;
  const passed = valid.filter((s) => s.status === 'passed').length;
  const cls = failed > 0 ? 'fail' : 'pass';
  const msg = failed > 0
    ? `${failed} of ${valid.length} automation suites failed on the latest run.`
    : `All ${passed} automation suites passed on the latest run.`;
  return `<div class="overall-banner ${cls}"><strong>${msg}</strong></div>`;
}

function renderFailures(summaries) {
  const items = [];
  for (const summary of summaries) {
    if (!summary?.topFailures?.length) continue;
    for (const failure of summary.topFailures.slice(0, 5)) {
      items.push({ repo: summary.repo, ...failure });
    }
  }
  if (!items.length) {
    return '<p style="color:var(--muted);padding:8px 0;">No recent failures 🎉</p>';
  }
  return items
    .map(
      (f) => `
      <div class="failure-item">
        <span class="category-tag">${f.category || 'unknown'} · ${f.repo}</span>
        <div>
          <h4>${escapeHtml(f.name)}</h4>
          <p>${escapeHtml(f.reason || 'No reason provided')}</p>
        </div>
      </div>`
    )
    .join('');
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function loadDashboard() {
  const cardsEl = document.getElementById('repo-cards');
  const bannerEl = document.getElementById('overall-banner');
  const failuresEl = document.getElementById('failures-list');
  const updatedEl = document.getElementById('last-updated');

  cardsEl.innerHTML = '<p style="color:var(--muted)">Loading run summaries…</p>';

  const results = await Promise.all(REPO_CONFIG.map((cfg) => fetchSummary(cfg)));
  const cardsHtml = REPO_CONFIG.map((cfg, i) => renderCard(cfg, results[i])).join('');

  cardsEl.innerHTML = cardsHtml;
  bannerEl.innerHTML = renderOverallBanner(results);
  failuresEl.innerHTML = renderFailures(results);
  updatedEl.textContent = `Updated ${new Date().toLocaleString()}`;
}

document.getElementById('refresh-btn').addEventListener('click', loadDashboard);
loadDashboard();
