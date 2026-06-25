/**
 * Public automation dashboard — latest Allure report stats + report metadata.
 */

const BUILD_TAG = '20260625f';
const DASHBOARD_VERSION = window.DASHBOARD_VERSION || '10';

const REPO_DISPLAY = {
  web: { icon: '🌐', label: 'Web' },
  'mobile-ios': { icon: '🍎', label: 'iOS' },
  'mobile-android': { icon: '🤖', label: 'Android' },
  api: { icon: '🔌', label: 'API' },
};

function getBootstrapSnapshot(config) {
  const snapshots = window.DASHBOARD_SNAPSHOTS?.snapshots;
  if (!snapshots) return null;
  return snapshots[config.id] || null;
}

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
    behaviorsUrl: 'https://retech-us.github.io/retech-web-automation/widgets/behaviors.json',
    environmentUrl: 'https://retech-us.github.io/retech-web-automation/widgets/environment.json',
    executorsUrl: 'https://retech-us.github.io/retech-web-automation/widgets/executors.json',
    localPath: 'data/web.json',
    githubWorkflowHint: 'Java CI',
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
    behaviorsUrl: 'https://retech-us.github.io/retech-mobile-automation/ios/widgets/behaviors.json',
    environmentUrl: 'https://retech-us.github.io/retech-mobile-automation/ios/widgets/environment.json',
    executorsUrl: 'https://retech-us.github.io/retech-mobile-automation/ios/widgets/executors.json',
    localPath: 'data/mobile-ios.json',
    aggregateBatches: true,
    githubWorkflowHint: 'Mobile Tests',
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
    behaviorsUrl: 'https://retech-us.github.io/retech-mobile-automation/android/widgets/behaviors.json',
    environmentUrl: 'https://retech-us.github.io/retech-mobile-automation/android/widgets/environment.json',
    executorsUrl: 'https://retech-us.github.io/retech-mobile-automation/android/widgets/executors.json',
    localPath: 'data/mobile-android.json',
    aggregateBatches: true,
    githubWorkflowHint: 'Mobile Tests',
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
    behaviorsUrl: 'https://retech-us.github.io/retech-api-automation/widgets/behaviors.json',
    environmentUrl: 'https://retech-us.github.io/retech-api-automation/widgets/environment.json',
    executorsUrl: 'https://retech-us.github.io/retech-api-automation/widgets/executors.json',
    localPath: 'data/api.json',
    githubWorkflowHint: 'API',
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
    appName: lookup['APP Name'] || lookup['App Name'],
    appVersion: lookup['App Version'],
    targetEnvironment: lookup['Test Environment'],
    osName: lookup['OS Name'] || lookup.OS,
  };
}

async function fetchGithubRun(repoName, workflowHint) {
  const url = `https://api.github.com/repos/${repoName}/actions/runs?per_page=20&status=completed`;
  try {
    const response = await fetch(url, {
      cache: 'no-store',
      headers: { Accept: 'application/vnd.github+json' },
    });
    if (!response.ok) return null;
    const data = await response.json();
    for (const run of data.workflow_runs || []) {
      const name = run.name || '';
      if (!name.toLowerCase().includes(workflowHint.toLowerCase())) continue;
      if (name.toLowerCase().includes('pages build')) continue;
      return {
        branch: run.head_branch,
        commit: (run.head_sha || '').slice(0, 7),
        ciRunUrl: run.html_url,
        workflow: name,
        runNumber: run.run_number,
        runId: String(run.id || ''),
        finishedAt: run.updated_at,
      };
    }
  } catch { /* optional enrichment */ }
  return null;
}

function summarizeHistoryTrend(trend) {
  if (!Array.isArray(trend)) return [];
  const rows = [];
  for (const entry of trend) {
    const data = entry?.data;
    if (!data?.total) continue;
    const total = data.total;
    const passed = data.passed || 0;
    const failed = (data.failed || 0) + (data.broken || 0);
    rows.push({
      passPct: Math.round((passed / total) * 1000) / 10,
      total,
      failed,
    });
    if (rows.length >= 6) break;
  }
  return rows;
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
  if (envMeta.appName) payload.appName = envMeta.appName;
  if (envMeta.appVersion) payload.appVersion = envMeta.appVersion;
  if (envMeta.targetEnvironment) payload.targetEnvironment = envMeta.targetEnvironment;
  if (envMeta.osName) payload.osName = envMeta.osName;

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
      else payload.environment = runSummary.environment;
    }
    if (!payload.instance && runSummary.instance) payload.instance = runSummary.instance;
    if (runSummary.topFailures?.length) payload.topFailures = runSummary.topFailures;
    if (runSummary.failureCategories && Object.keys(runSummary.failureCategories).length) {
      payload.failureCategories = runSummary.failureCategories;
    }
    if (runSummary.jobs?.length) payload.jobs = runSummary.jobs;
    if (runSummary.runId) payload.runId = runSummary.runId;
    if (runSummary.runNumber) payload.runNumber = runSummary.runNumber;
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
  const base = liveTotal >= bundledTotal
    ? { ...live }
    : { ...bundled, ...live, summary: bundled.summary, counts: bundled.counts || computeCounts(bundled) };
  const bundledFailures = bundled.topFailures?.length || 0;
  const liveFailures = live.topFailures?.length || 0;
  if (liveFailures < bundledFailures) {
    base.topFailures = bundled.topFailures;
    base.failureCategories = bundled.failureCategories || base.failureCategories;
  }
  if (!base.jobs?.length && bundled.jobs?.length) base.jobs = bundled.jobs;
  return base;
}
async function fetchSummary(config) {
  const bundled = getBootstrapSnapshot(config) || await fetchJson(config.localPath);
  const historyTrendUrl = `${config.reportUrl}widgets/history-trend.json`;
  const [executors, runSummary, envWidget, historyTrend, behaviors] = await Promise.all([
    fetchJson(config.executorsUrl),
    fetchJson(config.summaryUrl),
    fetchJson(config.environmentUrl),
    fetchJson(historyTrendUrl),
    fetchJson(config.behaviorsUrl),
  ]);
  const widget = config.aggregateBatches
    ? await fetchMobileWidget(config)
    : await fetchJson(config.widgetUrl);
  const envMeta = parseEnvironment(envWidget);
  const payload = resolveBestPayload(config, widget, historyTrend, runSummary, bundled);
  const summaryForEnrich = runSummary?.repo || runSummary?.summary ? runSummary : null;
  const enriched = enrich(payload, config, envMeta, executors, summaryForEnrich);
  enriched.historyTrend = summarizeHistoryTrend(historyTrend);
  const gh = config.githubWorkflowHint
    ? await fetchGithubRun(
        config.id.startsWith('mobile') ? 'retech-us/retech-mobile-automation' : `retech-us/retech-${config.id === 'api' ? 'api' : config.id}-automation`,
        config.githubWorkflowHint,
      )
    : null;
  if (gh) {
    if (!enriched.branch && gh.branch) enriched.branch = gh.branch;
    if (!enriched.commit && gh.commit) enriched.commit = gh.commit;
    if (gh.ciRunUrl) enriched.ciRunUrl = gh.ciRunUrl;
    if (!enriched.workflow && gh.workflow) enriched.workflow = gh.workflow;
    if (!enriched.runId && gh.runId) enriched.runId = gh.runId;
    if (gh.runNumber) enriched.runNumber = gh.runNumber;
    if ((!enriched.finishedAt || !enriched.durationMs) && gh.finishedAt) enriched.finishedAt = gh.finishedAt;
  }
  if (!enriched.topFailures?.length) {
    enriched.topFailures = failuresFromBehaviors(behaviors, config.reportUrl);
  }
  enriched.topFailures = attachFailureContext(enriched.topFailures, enriched, config);
  return mergeSummaries(bundled, enriched);
}

function failuresFromBehaviors(behaviors, reportUrl, limit = 8) {
  if (!behaviors?.items?.length) return [];
  const rows = [];
  for (const item of behaviors.items) {
    const failed = item.statistic?.failed || 0;
    const broken = item.statistic?.broken || 0;
    if (failed + broken === 0) continue;
    const status = failed > 0 ? 'failed' : 'broken';
    const category = status === 'broken' ? 'unknown' : 'assertion';
    rows.push({
      name: item.name,
      status,
      category,
      feature: item.name,
      reason: `${failed} failed · ${broken} broken in feature`,
      reportUrl: item.uid ? `${reportUrl}#behaviors/${item.uid}/` : reportUrl,
      severity: failed * 10 + broken,
    });
  }
  rows.sort((a, b) => b.severity - a.severity);
  return rows.slice(0, limit);
}

function attachFailureContext(failures, summary, config) {
  return (failures || []).map((f) => ({
    ...f,
    repo: summary?.repo || config.id,
    branch: f.branch || summary?.branch,
    reportUrl: f.reportUrl || summary?.reportUrl || config.reportUrl,
    ciRunUrl: summary?.ciRunUrl || config.ciRunUrl,
  }));
}

function formatDuration(ms) {
  if (!ms) return null;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

function formatDate(iso) {
  if (!iso) return null;
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

function hasValue(value) {
  if (value === undefined || value === null || value === '') return false;
  const text = String(value).trim();
  return text !== '' && text !== '—' && text !== '---' && text !== '–' && text !== 'null';
}

function computeRates(counts) {
  const total = counts.total || 0;
  if (!total) return { passPct: 0, failPct: 0 };
  const passPct = Math.round((counts.passed / total) * 1000) / 10;
  const failPct = Math.round((counts.review / total) * 1000) / 10;
  return { passPct, failPct };
}

function cardStatus(summary, counts, rates) {
  if (!counts.total) return 'unknown';
  if (counts.review === 0) return 'pass';
  if (rates.passPct >= 90) return 'warn';
  return 'fail';
}

function badgeLabel(counts, rates) {
  if (!counts.total) return 'no data';
  if (counts.review === 0) return 'all passed';
  return `${counts.review} failed`;
}

function metaItem(label, value) {
  if (!hasValue(value)) return '';
  return `<li><strong>${label}:</strong> ${value}</li>`;
}

function renderMetaList(items) {
  const html = items.filter(Boolean).join('');
  if (!html) return '';
  return `<ul class="meta-list meta-list--grid">${html}</ul>`;
}

function renderTrendBars(trend) {
  if (!trend?.length) return '';
  const bars = trend.map((t) => `
    <div class="trend-bar" title="${t.passPct}% pass · ${t.total} tests · ${t.failed} failed">
      <div class="trend-bar__fill ${t.failed > 0 ? 'trend-bar__fill--warn' : ''}" style="height:${Math.max(t.passPct, 4)}%"></div>
    </div>`).join('');
  return `<div class="trend-wrap"><span class="trend-label">Recent runs (newest → oldest)</span><div class="trend-bars">${bars}</div></div>`;
}

function renderCardFailures(summary) {
  if (!summary?.topFailures?.length) return '';
  const items = summary.topFailures.slice(0, 3).map((f) => `
    <div class="card-failure">
      <span class="status-pill status-pill--${f.status === 'broken' ? 'broken' : 'failed'}">${f.status === 'broken' ? 'broken' : 'failed'}</span>
      <span class="category-tag">${escapeHtml(f.category || 'unknown')}</span>
      <span class="card-failure__name">${escapeHtml(f.name)}</span>
    </div>`).join('');
  return `<div class="card-failures"><strong>Top failures</strong>${items}</div>`;
}

function renderJobBreakdown(jobs) {
  if (!jobs?.length) return '';
  const items = jobs.map((j) => {
    const status = (j.status || 'unknown').toLowerCase();
    const cls = status === 'success' ? 'pass' : status === 'failure' || status === 'failed' ? 'fail' : 'warn';
    return `<li class="job-row job-row--${cls}"><span>${escapeHtml(j.name)}</span><span>${escapeHtml(j.status)}</span></li>`;
  }).join('');
  return `<div class="job-breakdown"><strong>CI jobs</strong><ul>${items}</ul></div>`;
}

function aggregateFailureCategories(summaries) {
  const totals = {};
  for (const summary of summaries) {
    for (const [cat, count] of Object.entries(summary?.failureCategories || {})) {
      if (count > 0) totals[cat] = (totals[cat] || 0) + count;
    }
  }
  return totals;
}

function renderCategorySummaryBar(summaries) {
  const totals = aggregateFailureCategories(summaries);
  const keys = Object.keys(totals);
  if (!keys.length) return '';
  const chips = keys
    .sort((a, b) => totals[b] - totals[a])
    .map((cat) => `<span class="category-chip">${escapeHtml(cat)}: ${totals[cat]}</span>`)
    .join('');
  return `<div class="failure-categories-bar"><strong>By category</strong>${chips}</div>`;
}

function repoLabel(repoId) {
  const d = REPO_DISPLAY[repoId] || { icon: '', label: repoId };
  return `${d.icon} ${d.label}`.trim();
}

function renderFailureItem(f) {
  const status = f.status === 'broken' ? 'broken' : 'failed';
  const branchLine = hasValue(f.branch) ? `<p class="failure-meta">Branch: ${escapeHtml(f.branch)}</p>` : '';
  const featureLine = hasValue(f.feature) && f.feature !== f.name
    ? `<p class="failure-meta">Feature: ${escapeHtml(f.feature)}</p>` : '';
  const links = [];
  if (hasValue(f.reportUrl)) {
    links.push(`<a class="failure-link" href="${escapeHtml(f.reportUrl)}" target="_blank" rel="noopener">Allure</a>`);
  }
  if (hasValue(f.ciRunUrl)) {
    links.push(`<a class="failure-link" href="${escapeHtml(f.ciRunUrl)}" target="_blank" rel="noopener">CI run</a>`);
  }
  const linksHtml = links.length ? `<div class="failure-links">${links.join('')}</div>` : '';
  return `
    <div class="failure-item">
      <div class="failure-item__tags">
        <span class="status-pill status-pill--${status}">${status}</span>
        <span class="category-tag">${escapeHtml(f.category || 'unknown')}</span>
        <span class="suite-tag">${escapeHtml(repoLabel(f.repo))}</span>
      </div>
      <div class="failure-item__body">
        <h4>${escapeHtml(f.name)}</h4>
        ${featureLine}
        ${branchLine}
        ${hasValue(f.reason) ? `<p>${escapeHtml(f.reason)}</p>` : ''}
        ${linksHtml}
      </div>
    </div>`;
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
  const status = cardStatus(summary, counts, rates);
  const noData = counts.total === 0;
  const s = summary?.summary || {};
  const branchLabel = summary?.branch
    ? `${escapeHtml(summary.branch)}${summary?.commit ? ` @ ${escapeHtml(summary.commit)}` : ''}`
    : null;
  const failBreakdown = (s.failed || s.broken)
    ? `${s.failed || 0} failed · ${s.broken || 0} broken`
    : null;

  return `
    <article class="card card--${config.id} card--${status}" data-repo="${config.id}">
      <div class="card__header">
        <div>
          <h2 class="card__title">${config.icon} ${config.title}</h2>
          <p class="card__desc">${config.description}</p>
          ${branchLabel ? `<span class="branch-pill">${branchLabel}</span>` : ''}
        </div>
        <div class="rate-badge ${status}" title="Pass rate from latest available run">
          <span class="rate-badge__value">${noData ? '—' : rates.passPct + '%'}</span>
          <span class="rate-badge__label">${badgeLabel(counts, rates)}</span>
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
          ${counts.review > 0 ? `<div class="stat stat--fail"><span class="stat__value stat__value--fail">${counts.review}</span><span class="stat__label">Failed</span></div>` : ''}
          ${counts.skipped > 0 ? `<div class="stat"><span class="stat__value">${counts.skipped}</span><span class="stat__label">Skipped</span></div>` : ''}
        </div>
        <div class="result-row">
          <span class="status-badge ${status}">${status === 'pass' ? '● All passed' : status === 'warn' ? '● Mostly passed' : '● Has failures'}</span>
          <span class="result-row__meta">${rates.passPct}% pass${counts.review > 0 ? ` · ${rates.failPct}% fail` : ''}</span>
        </div>
        ${renderTrendBars(summary?.historyTrend)}
        ${summary?.lastAvailable ? '<p class="data-note">Latest publish was empty — showing last available Allure run from report history.</p>' : ''}`}
        ${renderMetaList([
          metaItem('Platform', config.platform),
          metaItem('Environment', summary?.environment),
          metaItem('Target env', summary?.targetEnvironment),
          metaItem('Instance', summary?.instance ? escapeHtml(summary.instance) : null),
          metaItem('Workflow', summary?.workflow ? escapeHtml(summary.workflow) : null),
          metaItem('CI run', summary?.runNumber ? `#${summary.runNumber}` : null),
          metaItem('Browser', summary?.browser),
          metaItem('App', summary?.appName),
          metaItem('App version', summary?.appVersion),
          metaItem('Base URL', summary?.baseUrl ? escapeHtml(summary.baseUrl) : null),
          metaItem('Breakdown', failBreakdown),
          metaItem('Last run', formatDate(summary?.finishedAt)),
          metaItem('Duration', formatDuration(summary?.durationMs)),
        ])}
        ${renderCategoryChips(summary?.failureCategories)}
        ${renderCardFailures(summary)}
        ${renderJobBreakdown(summary?.jobs)}
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
    for (const failure of summary.topFailures.slice(0, 8)) {
      items.push({ repo: summary.repo, ...failure });
    }
  }
  if (!items.length) return null;
  const categoryBar = renderCategorySummaryBar(summaries);
  const list = items.map((f) => renderFailureItem(f)).join('');
  return `${categoryBar}<div class="failures-list-inner">${list}</div>`;
}

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function renderDashboard(results) {
  document.getElementById('repo-cards').innerHTML = REPO_CONFIG.map((cfg, i) => renderCard(cfg, results[i])).join('');
  document.getElementById('overall-banner').innerHTML = renderOverallBanner(results);
  const failuresHtml = renderFailures(results);
  const failuresPanel = document.getElementById('failures-panel');
  if (failuresPanel) {
    failuresPanel.hidden = !failuresHtml;
  }
  document.getElementById('failures-list').innerHTML = failuresHtml || '';
}

async function loadDashboard() {
  document.getElementById('repo-cards').innerHTML = '<p class="loading-cards">Loading latest test results…</p>';
  document.getElementById('last-updated').textContent = `Dashboard v${DASHBOARD_VERSION} · refreshing…`;

  const bundled = REPO_CONFIG.map((cfg) => getBootstrapSnapshot(cfg));
  if (bundled.some((b) => (b?.summary?.total || 0) > 0)) {
    renderDashboard(bundled.map((b, i) => (b?.summary ? b : placeholder(REPO_CONFIG[i]))));
    document.getElementById('last-updated').textContent = `Dashboard v${DASHBOARD_VERSION} · ${new Date().toLocaleString()}`;
  }

  const results = await Promise.all(REPO_CONFIG.map((cfg) => fetchSummary(cfg)));
  renderDashboard(results);
  document.getElementById('last-updated').textContent = `Dashboard v${DASHBOARD_VERSION} · live · ${new Date().toLocaleString()}`;
}

document.getElementById('refresh-btn').addEventListener('click', loadDashboard);
loadDashboard();
