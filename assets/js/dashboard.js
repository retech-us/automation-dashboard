/**
 * Public automation dashboard — latest Allure report stats + report metadata.
 */

const BUILD_TAG = '20260625b';

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
    const sep = url.includes('?') ? '&' : '?';
    const response = await fetch(`${url}${sep}_=${BUILD_TAG}`, { cache: 'no-store' });
    if (!response.ok) return null;
    const data = await response.json();
    return data;
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

function latestFromHistoryTrend(trend) {
  if (!Array.isArray(trend)) return null;
  for (const entry of trend) {
    const data = entry?.data;
    if (data?.total > 0) return data;
  }
  return null;
}

function fromRunSummary(config, runSummary) {
  const payload = {
    ...runSummary,
    repo: config.id,
    reportUrl: runSummary.reportUrl || config.reportUrl,
    ciRunUrl: runSummary.ciRunUrl || config.ciRunUrl,
    dataSource: 'run-summary.json',
  };
  payload.counts = computeCounts(payload);
  return payload;
}

function resolveBestPayload(config, widget, historyTrend, runSummary, cached) {
  const candidates = [];

  const rank = (payload, score) => candidates.push({ payload, score });

  if (widget?.statistic?.total > 0) {
    rank(fromWidget(config, widget), 1000 + widget.statistic.total);
  }
  if (runSummary?.summary?.total > 0) {
    rank(fromRunSummary(config, runSummary), 900 + runSummary.summary.total);
  }
  const trendStats = latestFromHistoryTrend(historyTrend);
  if (trendStats?.total > 0) {
    const payload = fromWidget(config, {
      statistic: trendStats,
      time: {},
      reportName: 'Allure Report',
    });
    payload.dataSource = 'allure-history-trend';
    payload.lastAvailable = true;
    rank(payload, 800 + trendStats.total);
  }
  if (cached?.summary?.total > 0) {
    const bundledScore = cached.dataSource && cached.dataSource !== 'unavailable' ? 950 : 750;
    rank({ ...cached }, bundledScore + cached.summary.total);
  }
  if (widget?.statistic) {
    rank(fromWidget(config, widget), 50);
  }

  if (!candidates.length) return placeholder(config);
  candidates.sort((a, b) => b.score - a.score);
  return candidates[0].payload;
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
    if (runSummary.ciRunUrl) payload.ciRunUrl = runSummary.ciRunUrl;
  }

  if (!payload.environment && payload.ciRunUrl?.includes('github.com')) {
    payload.environment = 'CI';
  }

  payload.counts = computeCounts(payload);
  return payload;
}

function reviewCount(failed, broken) {
  return (failed || 0) + (broken || 0);
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

function mergeSummaries(bundled, live) {
  if (!bundled?.summary?.total) return live;
  if (!live?.summary?.total) return bundled;
  const bundledTotal = bundled.summary.total || 0;
  const liveTotal = live.summary.total || 0;
  if (liveTotal >= bundledTotal) return live;
  return { ...bundled, ...live, summary: bundled.summary, counts: bundled.counts || computeCounts(bundled) };
}
async function fetchSummary(config) {
  const bundled = await fetchJson(config.localPath);
  const historyTrendUrl = `${config.reportUrl}widgets/history-trend.json`;
  const [executors, runSummary, envWidget, historyTrend] = await Promise.all([
    fetchJson(config.executorsUrl),
    fetchJson(config.summaryUrl),
    fetchJson(config.environmentUrl),
    fetchJson(historyTrendUrl),
  ]);
  const widget = config.aggregateBatches
    ? await fetchMobileWidget(config)
    : await fetchJson(config.widgetUrl);
  const envMeta = parseEnvironment(envWidget);
  const payload = resolveBestPayload(config, widget, historyTrend, runSummary, bundled);
  const summaryForEnrich = runSummary?.repo || runSummary?.summary ? runSummary : null;
  const enriched = enrich(payload, config, envMeta, executors, summaryForEnrich);
  return mergeSummaries(bundled, enriched);
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

function computeRates(counts) {
  const total = counts.total || 0;
  if (!total) return { passPct: 0, failPct: 0 };
  const passPct = Math.round((counts.passed / total) * 1000) / 10;
  const failPct = Math.round((counts.review / total) * 1000) / 10;
  return { passPct, failPct };
}

function cardStatus(summary, counts) {
  if (!counts.total) return 'unknown';
  return counts.review > 0 ? 'fail' : 'pass';
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
  const rates = computeRates(counts);
  const status = cardStatus(summary, counts);
  const noData = counts.total === 0;
  const branchLabel = summary?.branch
    ? `${escapeHtml(summary.branch)}${summary?.commit ? ` @ ${escapeHtml(summary.commit)}` : ''}`
    : '—';

  return `
    <article class="card card--${config.id} card--${status}" data-repo="${config.id}">
      <div class="card__header">
        <div>
          <h2 class="card__title">${config.icon} ${config.title}</h2>
          <p class="card__desc">${config.description}</p>
          ${summary?.branch ? `<span class="branch-pill" title="Branch from latest published Allure report">${branchLabel}</span>` : ''}
        </div>
        <div class="rate-badge ${status}" title="Pass rate from latest available run">
          <span class="rate-badge__value">${noData ? '—' : rates.passPct + '%'}</span>
          <span class="rate-badge__label">${noData ? 'no data' : counts.review > 0 ? 'has failures' : 'all passed'}</span>
        </div>
      </div>
      <div class="card__body">
        ${noData ? `<p class="no-data-msg">No published test results found for this suite in Allure reports.</p>` : `
        <div class="progress-bar" aria-hidden="true">
          <div class="progress-bar__pass" style="width:${rates.passPct}%"></div>
          <div class="progress-bar__fail" style="width:${rates.failPct}%"></div>
        </div>
        <div class="stats">
          <div class="stat"><span class="stat__value">${counts.total}</span><span class="stat__label">Total</span></div>
          <div class="stat stat--pass"><span class="stat__value stat__value--pass">${counts.passed}</span><span class="stat__label">Passed</span></div>
          <div class="stat stat--fail"><span class="stat__value stat__value--fail">${counts.review}</span><span class="stat__label">Failed</span></div>
          <div class="stat"><span class="stat__value">${counts.skipped}</span><span class="stat__label">Skipped</span></div>
        </div>
        <div class="result-row">
          <span class="status-badge ${status}">${status === 'pass' ? '● Passed' : status === 'fail' ? '● Failed' : '● Unknown'}</span>
          <span class="result-row__meta">${rates.passPct}% pass · ${rates.failPct}% fail</span>
        </div>
        ${summary?.lastAvailable ? '<p class="data-note">Latest publish was empty — showing last available Allure run from report history.</p>' : ''}`}
        <ul class="meta-list">
          ${config.platform ? `<li><strong>Platform:</strong> ${config.platform}</li>` : ''}
          <li><strong>Environment:</strong> ${summary?.environment || '—'}</li>
          <li><strong>Instance:</strong> ${summary?.instance ? escapeHtml(summary.instance) : '—'}</li>
          <li><strong>Branch:</strong> ${branchLabel}</li>
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
  if (!valid.length) return '<strong>Loading latest Allure report data…</strong>';

  const totalTests = valid.reduce((a, s) => a + (s.counts?.total || 0), 0);
  const totalPassed = valid.reduce((a, s) => a + (s.counts?.passed || 0), 0);
  const totalFailed = valid.reduce((a, s) => a + (s.counts?.review || 0), 0);
  const overallPass = totalTests ? Math.round((totalPassed / totalTests) * 1000) / 10 : 0;
  const bannerClass = totalFailed > 0 ? 'fail' : 'pass';

  return `<div class="overall-banner ${bannerClass}">
    <strong>${valid.length} suites</strong> · ${totalTests} tests ·
    <span class="text-pass">${totalPassed} passed</span> ·
    <span class="text-fail">${totalFailed} failed</span> ·
    ${overallPass}% overall pass · Latest published Allure results (any branch)
  </div>`;
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

function renderDashboard(results) {
  document.getElementById('repo-cards').innerHTML = REPO_CONFIG.map((cfg, i) => renderCard(cfg, results[i])).join('');
  document.getElementById('overall-banner').innerHTML = renderOverallBanner(results);
  document.getElementById('failures-list').innerHTML = renderFailures(results);
}

async function loadDashboard() {
  document.getElementById('repo-cards').innerHTML = '<p class="loading-cards">Loading latest test results…</p>';
  document.getElementById('last-updated').textContent = 'Refreshing…';

  const bundled = await Promise.all(REPO_CONFIG.map((cfg) => fetchJson(cfg.localPath)));
  if (bundled.some((b) => (b?.summary?.total || 0) > 0)) {
    renderDashboard(bundled.map((b, i) => b?.summary ? b : placeholder(REPO_CONFIG[i])));
    document.getElementById('last-updated').textContent = `Cached data · ${new Date().toLocaleString()}`;
  }

  const results = await Promise.all(REPO_CONFIG.map((cfg) => fetchSummary(cfg)));
  renderDashboard(results);
  document.getElementById('last-updated').textContent = `Live Allure data · ${new Date().toLocaleString()}`;
}

document.getElementById('refresh-btn').addEventListener('click', loadDashboard);
loadDashboard();
