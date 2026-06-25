/**
 * Public automation dashboard — always fetches live data from GitHub Pages.
 * Falls back to bundled data/*.json when live fetch fails (e.g. offline).
 */

const REPO_CONFIG = [
  {
    id: 'web',
    title: 'Web Automation',
    description: 'Selenium + Cucumber + Allure',
    icon: '🌐',
    reportUrl: 'https://retech-us.github.io/retech-web-automation/',
    ciRunUrl: 'https://github.com/retech-us/retech-web-automation/actions',
    summaryUrl: 'https://retech-us.github.io/retech-web-automation/run-summary.json',
    widgetUrl: 'https://retech-us.github.io/retech-web-automation/widgets/summary.json',
    localPath: 'data/web.json',
  },
  {
    id: 'mobile',
    title: 'Mobile Automation',
    description: 'Appium + Allure (iOS & Android)',
    icon: '📱',
    reportUrl: 'https://retech-us.github.io/retech-mobile-automation/',
    ciRunUrl: 'https://github.com/retech-us/retech-mobile-automation/actions',
    summaryUrl: 'https://retech-us.github.io/retech-mobile-automation/run-summary.json',
    widgetUrl: 'https://retech-us.github.io/retech-mobile-automation/widgets/summary.json',
    localPath: 'data/mobile.json',
  },
  {
    id: 'api',
    title: 'API Automation',
    description: 'REST Assured + Allure',
    icon: '🔌',
    reportUrl: 'https://retech-us.github.io/retech-api-automation/',
    ciRunUrl: 'https://github.com/retech-us/retech-api-automation/actions',
    summaryUrl: 'https://retech-us.github.io/retech-api-automation/run-summary.json',
    widgetUrl: 'https://retech-us.github.io/retech-api-automation/widgets/summary.json',
    localPath: 'data/api.json',
  },
];

async function fetchJson(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) return null;
  return response.json();
}

function fromWidget(config, widget) {
  const stats = widget.statistic || {};
  const failed = stats.failed || 0;
  const broken = stats.broken || 0;
  const passed = stats.passed || 0;
  const skipped = stats.skipped || 0;
  const total = stats.total || 0;
  const status = failed + broken > 0 ? 'failed' : total > 0 ? 'passed' : 'unknown';
  return {
    schemaVersion: '1.0',
    repo: config.id,
    repoName: `retech-us/retech-${config.id === 'api' ? 'api' : config.id}-automation`,
    status,
    environment: 'staging',
    suite: 'regression',
    finishedAt: new Date().toISOString(),
    durationMs: widget.time?.duration || 0,
    summary: { total, passed, failed, broken, skipped },
    reportUrl: config.reportUrl,
    ciRunUrl: config.ciRunUrl,
    topFailures: [],
    failureCategories: {},
    dataSource: 'allure-widget-fallback',
    reportName: widget.reportName,
  };
}

function placeholder(config) {
  return {
    schemaVersion: '1.0',
    repo: config.id,
    status: 'unknown',
    summary: { total: 0, passed: 0, failed: 0, broken: 0, skipped: 0 },
    reportUrl: config.reportUrl,
    ciRunUrl: config.ciRunUrl,
    topFailures: [],
    dataSource: 'unavailable',
  };
}

async function fetchSummary(config) {
  // 1. Live run-summary.json (richest data)
  try {
    const summary = await fetchJson(config.summaryUrl);
    if (summary?.repo) {
      summary.dataSource = 'run-summary.json';
      return summary;
    }
  } catch (_) { /* continue */ }

  // 2. Allure widget fallback (pass/fail counts from published report)
  try {
    const widget = await fetchJson(config.widgetUrl);
    if (widget?.statistic) return fromWidget(config, widget);
  } catch (_) { /* continue */ }

  // 3. Bundled cache (updated by dashboard CI every 30 min)
  try {
    const cached = await fetchJson(config.localPath);
    if (cached?.repo) return cached;
  } catch (_) { /* continue */ }

  return placeholder(config);
}

function formatDuration(ms) {
  if (!ms) return '—';
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

function formatDate(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

function statusClass(status) {
  if (status === 'passed') return 'pass';
  if (status === 'failed') return 'fail';
  return 'unknown';
}

function dataSourceNote(summary) {
  if (!summary?.dataSource || summary.dataSource === 'run-summary.json') return '';
  if (summary.dataSource === 'allure-widget-fallback') {
    return '<li><strong>Data:</strong> Live from Allure report (full failure details after next CI run)</li>';
  }
  return '<li><strong>Data:</strong> Awaiting first CI run</li>';
}

function renderCard(config, summary) {
  const status = summary?.status || 'unknown';
  const s = summary?.summary || { total: 0, passed: 0, failed: 0, skipped: 0 };
  const noData = status === 'unknown' && s.total === 0;

  return `
    <article class="card" data-repo="${config.id}">
      <div class="card__header">
        <div>
          <h2 class="card__title">${config.icon} ${config.title}</h2>
          <p class="card__desc">${config.description}</p>
        </div>
        <span class="status-badge ${statusClass(status)}">${noData ? 'no data' : status}</span>
      </div>
      <div class="card__body">
        ${noData ? '<p class="no-data-msg">No test data available yet. Data appears after the next CI run.</p>' : `
        <div class="stats">
          <div class="stat"><span class="stat__value">${s.total}</span><span class="stat__label">Total</span></div>
          <div class="stat"><span class="stat__value" style="color:var(--pass)">${s.passed}</span><span class="stat__label">Passed</span></div>
          <div class="stat"><span class="stat__value" style="color:var(--fail)">${s.failed + (s.broken || 0)}</span><span class="stat__label">Failed</span></div>
          <div class="stat"><span class="stat__value">${s.skipped}</span><span class="stat__label">Skipped</span></div>
        </div>`}
        <ul class="meta-list">
          <li><strong>Environment:</strong> ${summary?.environment || '—'}</li>
          <li><strong>Branch:</strong> ${summary?.branch || '—'} ${summary?.commit ? '@ ' + summary.commit : ''}</li>
          <li><strong>Finished:</strong> ${formatDate(summary?.finishedAt)}</li>
          <li><strong>Duration:</strong> ${formatDuration(summary?.durationMs)}</li>
          ${dataSourceNote(summary)}
        </ul>
        <div class="card__actions">
          <a class="link-btn primary" href="${summary?.reportUrl || config.reportUrl}" target="_blank" rel="noopener">View Allure Report</a>
          <a class="link-btn" href="${summary?.ciRunUrl || config.ciRunUrl}" target="_blank" rel="noopener">View CI Run</a>
        </div>
      </div>
    </article>
  `;
}

function renderOverallBanner(summaries) {
  const valid = summaries.filter((s) => s && s.summary?.total > 0);
  if (!valid.length) {
    return '<strong>Loading data from automation repos…</strong> If this persists, check that GitHub Pages is enabled on each repo.';
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
    return '<p style="color:var(--muted);padding:8px 0;">No detailed failure reasons yet. API repo shows these after CI publishes run-summary.json.</p>';
  }
  return items.map((f) => `
    <div class="failure-item">
      <span class="category-tag">${f.category || 'unknown'} · ${f.repo}</span>
      <div>
        <h4>${escapeHtml(f.name)}</h4>
        <p>${escapeHtml(f.reason || 'No reason provided')}</p>
      </div>
    </div>`).join('');
}

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function loadDashboard() {
  const cardsEl = document.getElementById('repo-cards');
  const bannerEl = document.getElementById('overall-banner');
  const failuresEl = document.getElementById('failures-list');
  const updatedEl = document.getElementById('last-updated');

  cardsEl.innerHTML = '<p style="color:var(--muted)">Loading live data from GitHub Pages…</p>';

  const results = await Promise.all(REPO_CONFIG.map((cfg) => fetchSummary(cfg)));
  cardsEl.innerHTML = REPO_CONFIG.map((cfg, i) => renderCard(cfg, results[i])).join('');
  bannerEl.innerHTML = renderOverallBanner(results);
  failuresEl.innerHTML = renderFailures(results);
  updatedEl.textContent = `Live data · Updated ${new Date().toLocaleString()}`;
}

document.getElementById('refresh-btn').addEventListener('click', loadDashboard);
loadDashboard();
