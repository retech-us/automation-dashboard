/**
 * Public automation dashboard — latest Allure report stats + report metadata.
 */

const REPO_CONFIG = [
  {
    id: 'web',
    title: 'Web Automation',
    description: 'Selenium + Cucumber',
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
    description: 'Appium iOS',
    icon: '🍎',
    platform: 'iOS',
    reportUrl: 'https://retech-us.github.io/retech-mobile-automation/ios/',
    ciRunUrl: 'https://github.com/retech-us/retech-mobile-automation/actions',
    summaryUrl: 'https://retech-us.github.io/retech-mobile-automation/run-summary.json',
    widgetUrl: 'https://retech-us.github.io/retech-mobile-automation/ios/widgets/summary.json',
    environmentUrl: 'https://retech-us.github.io/retech-mobile-automation/ios/widgets/environment.json',
    executorsUrl: 'https://retech-us.github.io/retech-mobile-automation/ios/widgets/executors.json',
    localPath: 'data/mobile-ios.json',
    aggregateBatches: true,
  },
  {
    id: 'mobile-android',
    title: 'Mobile — Android',
    description: 'Appium Android',
    icon: '🤖',
    platform: 'Android',
    reportUrl: 'https://retech-us.github.io/retech-mobile-automation/android/',
    ciRunUrl: 'https://github.com/retech-us/retech-mobile-automation/actions',
    summaryUrl: 'https://retech-us.github.io/retech-mobile-automation/run-summary.json',
    widgetUrl: 'https://retech-us.github.io/retech-mobile-automation/android/widgets/summary.json',
    environmentUrl: 'https://retech-us.github.io/retech-mobile-automation/android/widgets/environment.json',
    executorsUrl: 'https://retech-us.github.io/retech-mobile-automation/android/widgets/executors.json',
    localPath: 'data/mobile-android.json',
    aggregateBatches: true,
  },
  {
    id: 'api',
    title: 'API Automation',
    description: 'REST Assured',
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

function parseEnvironment(widget) {
  if (!Array.isArray(widget)) return {};
  const lookup = {};
  for (const item of widget) {
    if (item.values?.[0]) lookup[item.name] = item.values[0];
  }
  const ci = lookup.CI === 'true' || String(lookup.Environment || '').toLowerCase() === 'ci';
  let instance = lookup.Instance || null;
  const baseUrl = lookup['Base URL'] || '';
  if (!instance && baseUrl) {
    const match = baseUrl.match(/https?:\/\/([^.]+)\./i);
    if (match) instance = match[1];
  }
  return {
    branch: lookup.Branch || lookup['Git Branch'],
    commit: lookup['Commit.SHA'] || lookup.Commit,
    environment: ci ? 'CI' : (lookup.Environment || null),
    instance,
    baseUrl: baseUrl || null,
    browser: lookup.Browser,
    workflow: lookup.Workflow,
    app: lookup.App,
  };
}

function mergeWidgets(widgets) {
  const totals = { total: 0, passed: 0, failed: 0, broken: 0, skipped: 0 };
  let stop = 0;
  let start = Infinity;
  for (const widget of widgets) {
    if (!widget?.statistic) continue;
    const s = widget.statistic;
    totals.total += s.total || 0;
    totals.passed += s.passed || 0;
    totals.failed += s.failed || 0;
    totals.broken += s.broken || 0;
    totals.skipped += s.skipped || 0;
    if (widget.time?.stop) stop = Math.max(stop, widget.time.stop);
    if (widget.time?.start) start = Math.min(start, widget.time.start);
  }
  if (!totals.total) return null;
  return {
    reportName: 'Aggregated Allure Report',
    statistic: totals,
    time: {
      start: start === Infinity ? undefined : start,
      stop: stop || undefined,
      duration: stop && start !== Infinity ? stop - start : 0,
    },
  };
}

async function fetchMobileWidget(config) {
  const primary = await fetchJson(config.widgetUrl);
  if (primary?.statistic?.total > 0) return primary;

  const widgets = [];
  if (primary?.statistic) widgets.push(primary);
  for (let batch = 1; batch <= 5; batch++) {
    const w = await fetchJson(`${config.reportUrl}batch-${batch}/widgets/summary.json`);
    if (w?.statistic?.total > 0) widgets.push(w);
  }
  return mergeWidgets(widgets) || primary;
}

function computeCounts(summary) {
  const s = summary?.summary || {};
  const total = s.total || 0;
  const passed = s.passed || 0;
  const review = (s.failed || 0) + (s.broken || 0);
  const skipped = s.skipped || 0;
  return { total, passed, review, skipped };
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
    status: total === 0 ? 'unknown' : reviewCount(failed, broken) > 0 ? 'active' : 'stable',
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
  payload.counts = computeCounts(payload);
  return payload;
}

function reviewCount(failed, broken) {
  return (failed || 0) + (broken || 0);
}

function enrich(payload, config, envMeta, executors, runSummary) {
  if (envMeta.branch) payload.branch = envMeta.branch;
  if (envMeta.commit) payload.commit = envMeta.commit;
  if (envMeta.environment) payload.environment = envMeta.environment;
  if (envMeta.instance) payload.instance = envMeta.instance;
  if (envMeta.baseUrl) payload.baseUrl = envMeta.baseUrl;
  if (envMeta.browser) payload.browser = envMeta.browser;
  if (envMeta.workflow) payload.workflow = envMeta.workflow;
  if (envMeta.app) payload.app = envMeta.app;

  if (Array.isArray(executors) && executors[0]?.buildUrl) {
    payload.ciRunUrl = executors[0].buildUrl;
    if (!payload.environment && executors[0].buildUrl.includes('github.com')) {
      payload.environment = 'CI';
    }
  }
  if (Array.isArray(executors) && executors[0]?.buildName && !payload.workflow) {
    payload.workflow = executors[0].buildName;
  }

  if (runSummary) {
    if (!payload.branch && runSummary.branch) payload.branch = runSummary.branch;
    if (!payload.commit && runSummary.commit) payload.commit = runSummary.commit;
    if (!payload.environment && runSummary.environment) {
      const env = String(runSummary.environment);
      if (env.toLowerCase() === 'ci') payload.environment = 'CI';
    }
    if (!payload.instance && runSummary.instance) payload.instance = runSummary.instance;
    if (runSummary.topFailures?.length) payload.topFailures = runSummary.topFailures;
    if (runSummary.failureCategories) payload.failureCategories = runSummary.failureCategories;
    if (runSummary.runId) payload.runId = runSummary.runId;
    if (runSummary.ciRunUrl && !executors?.length) payload.ciRunUrl = runSummary.ciRunUrl;
  }

  payload.counts = computeCounts(payload);
  return payload;
}

function placeholder(config) {
  return {
    repo: config.id,
    status: 'unknown',
    summary: { total: 0, passed: 0, failed: 0, broken: 0, skipped: 0 },
    counts: { total: 0, passed: 0, review: 0, skipped: 0 },
    reportUrl: config.reportUrl,
    ciRunUrl: config.ciRunUrl,
    topFailures: [],
    failureCategories: {},
    dataSource: 'unavailable',
  };
}

async function fetchSummary(config) {
  const [executors, runSummary, envWidget] = await Promise.all([
    fetchJson(config.executorsUrl),
    fetchJson(config.summaryUrl),
    fetchJson(config.environmentUrl),
  ]);
  const widget = config.aggregateBatches
    ? await fetchMobileWidget(config)
    : await fetchJson(config.widgetUrl);
  const envMeta = parseEnvironment(envWidget);

  let payload;
  if (widget?.statistic) {
    payload = fromWidget(config, widget);
  } else if (runSummary?.repo) {
    payload = { ...runSummary, dataSource: 'run-summary.json', counts: computeCounts(runSummary) };
  } else {
    const cached = await fetchJson(config.localPath);
    if (cached?.repo) return cached;
    return placeholder(config);
  }

  return enrich(payload, config, envMeta, executors, runSummary?.repo ? runSummary : null);
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

function renderCategoryChips(categories) {
  if (!categories || !Object.keys(categories).length) return '';
  const chips = Object.entries(categories)
    .map(([cat, count]) => `<span class="category-chip">${cat}: ${count}</span>`)
    .join('');
  return `<div class="category-chips"><strong>Topics:</strong> ${chips}</div>`;
}

function renderCard(config, summary) {
  const counts = summary?.counts || computeCounts(summary);
  const noData = counts.total === 0;

  return `
    <article class="card" data-repo="${config.id}">
      <div class="card__header">
        <div>
          <h2 class="card__title">${config.icon} ${config.title}</h2>
          <p class="card__desc">${config.description}</p>
        </div>
        <div class="metric-badge" title="Tests executed in latest Allure report">
          <span class="metric-badge__value">${noData ? '—' : counts.total}</span>
          <span class="metric-badge__label">tests run</span>
        </div>
      </div>
      <div class="card__body">
        ${noData ? `<p class="no-data-msg">${config.id === 'mobile-android' ? 'No Android results published yet. Data will appear after the next CI run completes.' : 'No test results published yet for this suite.'}</p>` : `
        <div class="stats">
          <div class="stat"><span class="stat__value">${counts.total}</span><span class="stat__label">Executed</span></div>
          <div class="stat"><span class="stat__value stat__value--ok">${counts.passed}</span><span class="stat__label">Completed</span></div>
          <div class="stat"><span class="stat__value stat__value--review">${counts.review}</span><span class="stat__label">For review</span></div>
          <div class="stat"><span class="stat__value">${counts.skipped}</span><span class="stat__label">Skipped</span></div>
        </div>`}
        <ul class="meta-list">
          ${config.platform ? `<li><strong>Platform:</strong> ${config.platform}</li>` : ''}
          <li><strong>Environment:</strong> ${summary?.environment || '—'}</li>
          <li><strong>Instance:</strong> ${summary?.instance ? escapeHtml(summary.instance) : '—'}</li>
          <li><strong>Branch:</strong> ${summary?.branch || '—'} ${summary?.commit ? '@ ' + summary.commit : ''}</li>
          <li><strong>Last run:</strong> ${formatDate(summary?.finishedAt)}</li>
          <li><strong>Duration:</strong> ${formatDuration(summary?.durationMs)}</li>
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

function renderOverallBanner(summaries) {
  const valid = summaries.filter((s) => (s?.counts?.total || 0) > 0);
  const totalTests = valid.reduce((a, s) => a + (s.counts?.total || 0), 0);
  if (!valid.length) return '<strong>Loading latest Allure report data…</strong>';
  return `<div class="overall-banner neutral"><strong>${valid.length} suites monitored</strong> · ${totalTests} tests executed in latest CI runs · Data sourced from Allure reports</div>`;
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
    return '<p style="color:var(--muted);padding:8px 0;">Detailed failure notes appear here when available from run summaries.</p>';
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
  document.getElementById('overall-banner').innerHTML = renderOverallBanner(results);
  document.getElementById('failures-list').innerHTML = renderFailures(results);
  document.getElementById('last-updated').textContent = `Latest Allure data · ${new Date().toLocaleString()}`;
}

document.getElementById('refresh-btn').addEventListener('click', loadDashboard);
loadDashboard();
