/**
 * Public automation dashboard — latest Allure report stats + enriched metadata.
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
    environmentUrl: 'https://retech-us.github.io/retech-web-automation/widgets/environment.json',
    executorsUrl: 'https://retech-us.github.io/retech-web-automation/widgets/executors.json',
    localPath: 'data/web.json',
  },
  {
    id: 'mobile-ios',
    title: 'Mobile — iOS',
    description: 'Appium iOS tests (all batches)',
    icon: '🍎',
    platform: 'iOS',
    defaultEnvironment: 'Alpha app',
    reportUrl: 'https://retech-us.github.io/retech-mobile-automation/ios/',
    ciRunUrl: 'https://github.com/retech-us/retech-mobile-automation/actions',
    summaryUrl: 'https://retech-us.github.io/retech-mobile-automation/run-summary.json',
    widgetUrl: 'https://retech-us.github.io/retech-mobile-automation/ios/widgets/summary.json',
    environmentUrl: 'https://retech-us.github.io/retech-mobile-automation/ios/widgets/environment.json',
    executorsUrl: 'https://retech-us.github.io/retech-mobile-automation/ios/widgets/executors.json',
    localPath: 'data/mobile-ios.json',
  },
  {
    id: 'mobile-android',
    title: 'Mobile — Android',
    description: 'Appium Android tests (all batches)',
    icon: '🤖',
    platform: 'Android',
    defaultEnvironment: 'Alpha app',
    reportUrl: 'https://retech-us.github.io/retech-mobile-automation/android/',
    ciRunUrl: 'https://github.com/retech-us/retech-mobile-automation/actions',
    summaryUrl: 'https://retech-us.github.io/retech-mobile-automation/run-summary.json',
    widgetUrl: 'https://retech-us.github.io/retech-mobile-automation/android/widgets/summary.json',
    environmentUrl: 'https://retech-us.github.io/retech-mobile-automation/android/widgets/environment.json',
    executorsUrl: 'https://retech-us.github.io/retech-mobile-automation/android/widgets/executors.json',
    localPath: 'data/mobile-android.json',
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
    environmentUrl: 'https://retech-us.github.io/retech-api-automation/widgets/environment.json',
    executorsUrl: 'https://retech-us.github.io/retech-api-automation/widgets/executors.json',
    localPath: 'data/api.json',
  },
];

async function fetchJson(url) {
  try {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

function formatAppEnvironment(value) {
  if (!value) return null;
  const normalized = String(value).trim().toLowerCase();
  if (!normalized) return null;
  if (normalized.endsWith(' app')) {
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1) + ' app';
}

function resolveEnvironment(envMeta, config) {
  const raw = envMeta.environment || envMeta.instance;
  if (raw) return formatAppEnvironment(raw);
  if (config.defaultEnvironment) return config.defaultEnvironment;
  return null;
}

function parseEnvironment(widget) {
  if (!Array.isArray(widget)) return {};
  const lookup = {};
  for (const item of widget) {
    if (item.values?.[0]) lookup[item.name] = item.values[0];
  }
  return {
    branch: lookup.Branch || lookup['Git Branch'],
    commit: lookup['Commit.SHA'] || lookup.Commit,
    environment: lookup.Environment || lookup['Test Environment'] || lookup.Instance,
    instance: lookup.Instance,
    baseUrl: lookup['Base URL'],
    browser: lookup.Browser,
    workflow: lookup.Workflow,
  };
}

function computeRates(summary) {
  const s = summary?.summary || {};
  const total = s.total || 0;
  const passed = s.passed || 0;
  const failed = (s.failed || 0) + (s.broken || 0);
  const skipped = s.skipped || 0;
  if (!total) return { passPct: 0, failPct: 0, skipPct: 0 };
  return {
    passPct: Math.round((passed / total) * 1000) / 10,
    failPct: Math.round((failed / total) * 1000) / 10,
    skipPct: Math.round((skipped / total) * 1000) / 10,
  };
}

function fromWidget(config, widget) {
  const stats = widget.statistic || {};
  const failed = stats.failed || 0;
  const broken = stats.broken || 0;
  const passed = stats.passed || 0;
  const skipped = stats.skipped || 0;
  const total = stats.total || 0;
  const stop = widget.time?.stop;
  const payload = {
    schemaVersion: '1.0',
    repo: config.id,
    repoName: config.id.startsWith('mobile')
      ? 'retech-us/retech-mobile-automation'
      : `retech-us/retech-${config.id === 'api' ? 'api' : config.id}-automation`,
    status: failed + broken > 0 ? 'failed' : total > 0 ? 'passed' : 'unknown',
    finishedAt: stop ? new Date(stop).toISOString() : new Date().toISOString(),
    durationMs: widget.time?.duration || 0,
    summary: { total, passed, failed, broken, skipped },
    reportUrl: config.reportUrl,
    ciRunUrl: config.ciRunUrl,
    topFailures: [],
    failureCategories: {},
    dataSource: 'allure-report',
    reportName: widget.reportName,
  };
  payload.rates = computeRates(payload);
  return payload;
}

function enrich(payload, config, envMeta, executors, runSummary) {
  if (envMeta.branch) payload.branch = envMeta.branch;
  if (envMeta.commit) payload.commit = envMeta.commit;
  const resolvedEnv = resolveEnvironment(envMeta, config);
  if (resolvedEnv) payload.environment = resolvedEnv;
  if (envMeta.instance) payload.instance = envMeta.instance;
  if (envMeta.baseUrl) payload.baseUrl = envMeta.baseUrl;
  if (envMeta.browser) payload.browser = envMeta.browser;
  if (envMeta.workflow) payload.workflow = envMeta.workflow;

  if (Array.isArray(executors) && executors[0]?.buildUrl) {
    payload.ciRunUrl = executors[0].buildUrl;
  }
  if (Array.isArray(executors) && executors[0]?.buildName && !payload.workflow) {
    payload.workflow = executors[0].buildName;
  }

  if (runSummary) {
    if (!payload.branch && runSummary.branch) payload.branch = runSummary.branch;
    if (!payload.commit && runSummary.commit) payload.commit = runSummary.commit;
    if (runSummary.topFailures?.length) payload.topFailures = runSummary.topFailures;
    if (runSummary.failureCategories) payload.failureCategories = runSummary.failureCategories;
    if (runSummary.runId) payload.runId = runSummary.runId;
    if (runSummary.ciRunUrl && !executors?.length) payload.ciRunUrl = runSummary.ciRunUrl;
  }

  payload.rates = computeRates(payload);
  return payload;
}

function placeholder(config) {
  return {
    repo: config.id,
    status: 'unknown',
    summary: { total: 0, passed: 0, failed: 0, broken: 0, skipped: 0 },
    rates: { passPct: 0, failPct: 0, skipPct: 0 },
    reportUrl: config.reportUrl,
    ciRunUrl: config.ciRunUrl,
    topFailures: [],
    failureCategories: {},
    dataSource: 'unavailable',
  };
}

async function fetchSummary(config) {
  const [widget, executors, runSummary, envWidget] = await Promise.all([
    fetchJson(config.widgetUrl),
    fetchJson(config.executorsUrl),
    fetchJson(config.summaryUrl),
    fetchJson(config.environmentUrl),
  ]);
  const envMeta = parseEnvironment(envWidget);

  let payload;
  if (widget?.statistic) {
    payload = fromWidget(config, widget);
  } else if (runSummary?.repo) {
    payload = { ...runSummary, dataSource: 'run-summary.json', rates: computeRates(runSummary) };
  } else {
    const cached = await fetchJson(config.localPath);
    if (cached?.repo) return cached;
    return placeholder(config);
  }

  return enrich(payload, config, envMeta, executors, runSummary?.repo ? runSummary : null);
}

function combineMobileSummaries(summaries, configs) {
  const iosIdx = configs.findIndex((c) => c.id === 'mobile-ios');
  const androidIdx = configs.findIndex((c) => c.id === 'mobile-android');
  if (iosIdx < 0 || androidIdx < 0) return null;
  const ios = summaries[iosIdx]?.summary || {};
  const android = summaries[androidIdx]?.summary || {};
  const total = (ios.total || 0) + (android.total || 0);
  const passed = (ios.passed || 0) + (android.passed || 0);
  const failed = (ios.failed || 0) + (android.failed || 0) + (ios.broken || 0) + (android.broken || 0);
  if (!total) return null;
  const passPct = Math.round((passed / total) * 1000) / 10;
  return { total, passed, failed, passPct };
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

function rateClass(passPct) {
  if (passPct >= 90) return 'pass';
  if (passPct >= 70) return 'warn';
  return 'fail';
}

function renderCategoryChips(categories) {
  if (!categories || !Object.keys(categories).length) return '';
  const chips = Object.entries(categories)
    .map(([cat, count]) => `<span class="category-chip">${cat}: ${count}</span>`)
    .join('');
  return `<div class="category-chips"><strong>Failure types:</strong> ${chips}</div>`;
}

function renderCard(config, summary) {
  const s = summary?.summary || { total: 0, passed: 0, failed: 0, skipped: 0 };
  const rates = summary?.rates || computeRates(summary);
  const noData = s.total === 0;
  const passPct = rates.passPct ?? 0;
  const failPct = rates.failPct ?? 0;

  return `
    <article class="card" data-repo="${config.id}">
      <div class="card__header">
        <div>
          <h2 class="card__title">${config.icon} ${config.title}</h2>
          <p class="card__desc">${config.description}</p>
        </div>
        <div class="rate-badge ${rateClass(passPct)}" title="Pass rate from latest Allure report">
          <span class="rate-badge__value">${noData ? '—' : passPct + '%'}</span>
          <span class="rate-badge__label">pass rate</span>
        </div>
      </div>
      <div class="card__body">
        ${noData ? '<p class="no-data-msg">No test data available yet.</p>' : `
        <div class="stats">
          <div class="stat"><span class="stat__value">${s.total}</span><span class="stat__label">Total</span></div>
          <div class="stat"><span class="stat__value" style="color:var(--pass)">${passPct}%</span><span class="stat__label">Passed (${s.passed})</span></div>
          <div class="stat"><span class="stat__value" style="color:var(--fail)">${failPct}%</span><span class="stat__label">Failed (${(s.failed || 0) + (s.broken || 0)})</span></div>
          <div class="stat"><span class="stat__value">${rates.skipPct}%</span><span class="stat__label">Skipped (${s.skipped})</span></div>
        </div>
        <div class="progress-bar" aria-hidden="true">
          <span class="progress-bar__pass" style="width:${passPct}%"></span>
          <span class="progress-bar__fail" style="width:${failPct}%"></span>
        </div>`}
        <ul class="meta-list">
          <li><strong>Platform:</strong> ${config.platform || '—'}</li>
          <li><strong>Environment:</strong> ${summary?.environment || '—'}</li>
          ${summary?.instance ? `<li><strong>Instance:</strong> ${escapeHtml(summary.instance)}</li>` : ''}
          ${summary?.baseUrl ? `<li><strong>Base URL:</strong> ${escapeHtml(summary.baseUrl)}</li>` : ''}
          <li><strong>Branch:</strong> ${summary?.branch || '—'} ${summary?.commit ? '@ ' + summary.commit : ''}</li>
          <li><strong>Last run:</strong> ${formatDate(summary?.finishedAt)}</li>
          <li><strong>Duration:</strong> ${formatDuration(summary?.durationMs)}</li>
          <li><strong>Source:</strong> Latest Allure report</li>
        </ul>
        ${renderCategoryChips(summary?.failureCategories)}
        <div class="card__actions">
          <a class="link-btn primary" href="${summary?.reportUrl || config.reportUrl}" target="_blank" rel="noopener">View Allure Report</a>
          <a class="link-btn" href="${summary?.ciRunUrl || config.ciRunUrl}" target="_blank" rel="noopener">View CI Run</a>
        </div>
      </div>
    </article>
  `;
}

function renderOverallBanner(summaries, configs) {
  const valid = summaries.filter((s) => s?.summary?.total > 0);
  if (!valid.length) return '<strong>Loading latest Allure report data…</strong>';
  const avgPass = Math.round(valid.reduce((a, s) => a + (s.rates?.passPct || 0), 0) / valid.length * 10) / 10;
  const failedSuites = valid.filter((s) => (s.rates?.failPct || 0) > 0).length;
  const cls = failedSuites > 0 ? 'fail' : 'pass';
  const mobileCombined = combineMobileSummaries(summaries, configs);
  const mobileNote = mobileCombined
    ? ` · Mobile combined: ${mobileCombined.total} tests, ${mobileCombined.passPct}% pass (iOS + Android)`
    : '';
  return `<div class="overall-banner ${cls}"><strong>Overall pass rate: ${avgPass}%</strong> · ${failedSuites} of ${valid.length} suites have failures${mobileNote}</div>`;
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
    return '<p style="color:var(--muted);padding:8px 0;">No detailed failure breakdown available yet for this repo.</p>';
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
  document.getElementById('repo-cards').innerHTML = '<p style="color:var(--muted)">Loading latest Allure reports…</p>';
  const results = await Promise.all(REPO_CONFIG.map((cfg) => fetchSummary(cfg)));
  document.getElementById('repo-cards').innerHTML = REPO_CONFIG.map((cfg, i) => renderCard(cfg, results[i])).join('');
  document.getElementById('overall-banner').innerHTML = renderOverallBanner(results, REPO_CONFIG);
  document.getElementById('failures-list').innerHTML = renderFailures(results);
  document.getElementById('last-updated').textContent = `Latest Allure data · ${new Date().toLocaleString()}`;
}

document.getElementById('refresh-btn').addEventListener('click', loadDashboard);
loadDashboard();
