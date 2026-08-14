/**
 * Public automation dashboard — release confidence for technical + non-technical audiences.
 */

const BUILD_TAG = '20260807d';
const DASHBOARD_VERSION = window.DASHBOARD_VERSION || '16';

const REPO_DISPLAY = {
  web: { icon: '🌐', label: 'Web', color: '#3b82f6' },
  'mobile-ios': { icon: '🍎', label: 'iOS', color: '#a855f7' },
  'mobile-android': { icon: '🤖', label: 'Android', color: '#10b981' },
  api: { icon: '🔌', label: 'API', color: '#f59e0b' },
};

const DASHBOARD_TABS = ['overview', 'attention', 'trends', 'ai', 'suites'];
let CURRENT_RESULTS = [];
let ACTIVE_TAB = 'overview';
let TREND_RANGE = 'weekly';
let TREND_HISTORY = null;
let INCLUDE_ESTIMATED = false;
try {
  INCLUDE_ESTIMATED = localStorage.getItem('dashboard.includeEstimated') === '1';
} catch { /* ignore */ }

const TREND_RANGES = [
  { id: 'daily', label: 'Daily', days: 30, bucket: 'day' },
  { id: 'weekly', label: 'Weekly', days: 84, bucket: 'week' },
  { id: 'monthly', label: 'Monthly', days: 365, bucket: 'month' },
  { id: 'quarterly', label: 'Quarterly', days: 730, bucket: 'quarter' },
  { id: 'yearly', label: 'Yearly', days: 1825, bucket: 'year' },
];

/** Product journeys — mapped from failure / feature names for non-technical viewers. */
const BUSINESS_AREAS = [
  {
    id: 'login',
    label: 'Login & Access',
    blurb: 'Can people sign in and reach the product?',
    keywords: ['login', 'sign in', 'auth', 'credentials', 'session'],
  },
  {
    id: 'scans',
    label: 'Scans & Capture',
    blurb: 'Upload, list, and review store scans',
    keywords: ['scan', 'capture', 'realogram', 'spatial', 'upload scan'],
  },
  {
    id: 'tasks',
    label: 'Tasks',
    blurb: 'Create, schedule, and complete store tasks',
    keywords: ['task'],
  },
  {
    id: 'approvals',
    label: 'Approvals & AI Review',
    blurb: 'Product / OCR / automated approvals',
    keywords: ['approval', 'approvals', 'ocr', 'products approval'],
  },
  {
    id: 'price',
    label: 'Price Tags',
    blurb: 'Price tag corrections and validation',
    keywords: ['price tag', 'price tags', 'pricing'],
  },
  {
    id: 'imports',
    label: 'Imports & Data',
    blurb: 'Import / export and data pipelines',
    keywords: ['import', 'export', 'csv', 'fixture', 'test data'],
  },
  {
    id: 'mobile',
    label: 'Mobile Associate',
    blurb: 'iOS & Android associate app journeys',
    keywords: ['out of shelf', 'oos', 'tracked capture', 'navigation through', 'mobile'],
    repos: ['mobile-ios', 'mobile-android'],
  },
  {
    id: 'api',
    label: 'API Contracts',
    blurb: 'Backend services stay compatible',
    keywords: [],
    repos: ['api'],
  },
];

const CATEGORY_PLAIN = {
  login: 'Sign-in or access problem',
  locator: 'Screen layout changed — element hard to find',
  timeout: 'Page or API took too long to respond',
  api: 'Backend / API returned an error',
  data: 'Test or product data did not match expectations',
  environment: 'Environment or deploy issue',
  assertion: 'Result did not match what we expected',
  unknown: 'Needs a closer look',
};

const CATEGORY_NEXT_STEP = {
  login: 'Confirm staging auth is up and credentials are valid.',
  locator: 'Compare the latest screenshot with the current UI — likely a layout rename.',
  timeout: 'Check whether the server/API is slow or overloaded — treat as environment first.',
  api: 'Inspect the failing endpoint status and recent backend changes.',
  data: 'Verify fixtures / seed data for this flow still match the environment.',
  environment: 'Check environment health, server latency, and recent deploys before retesting.',
  assertion: 'Confirm whether the product behavior changed on purpose.',
  unknown: 'Open the report once, skim the screenshot, then assign an owner.',
};

/** Simple triage buckets for non-technical reviews */
const ISSUE_BUCKETS = {
  flaky: {
    id: 'flaky',
    label: 'Flaky test',
    short: 'Flaky',
    blurb: 'Unstable automation — may pass on retry; do not treat as a confirmed defect.',
    nextStep: 'Quarantine or stabilize the test; avoid blocking release on this alone.',
  },
  environment: {
    id: 'environment',
    label: 'Environment',
    short: 'Env',
    blurb: 'Servers, deploy, credentials, or late/slow responses — not a product bug yet.',
    nextStep: 'Check environment health, server latency, credentials, and recent deploys.',
  },
  defect: {
    id: 'defect',
    label: 'Likely defect',
    short: 'Defect',
    blurb: 'Looks like real product / API behavior that needs a fix or intentional change.',
    nextStep: 'Assign a product or engineering owner and confirm expected behavior.',
  },
};

let AI_IMPACT_CACHE = null;
let AI_USAGE_CACHE = null;

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
    .map((cat) => `<span class="category-chip">${escapeHtml(humanizeCategory(cat))}: ${totals[cat]}</span>`)
    .join('');
  return `<div class="failure-categories-bar"><strong>By theme</strong>${chips}</div>`;
}

function repoLabel(repoId) {
  const d = REPO_DISPLAY[repoId] || { icon: '', label: repoId };
  return `${d.icon} ${d.label}`.trim();
}

function renderFailureItem(f) {
  const status = f.status === 'broken' ? 'broken' : 'failed';
  const explanation = explainFailure(f);
  const links = [];
  if (hasValue(f.reportUrl)) {
    links.push(`<a class="failure-link tech-only" href="${escapeHtml(f.reportUrl)}" target="_blank" rel="noopener">Allure</a>`);
  }
  if (hasValue(f.ciRunUrl)) {
    links.push(`<a class="failure-link tech-only" href="${escapeHtml(f.ciRunUrl)}" target="_blank" rel="noopener">CI run</a>`);
  }
  const linksHtml = links.length ? `<div class="failure-links">${links.join('')}</div>` : '';
  return `
    <div class="failure-item failure-item--${explanation.bucketId}">
      <div class="failure-item__tags">
        <span class="bucket-pill bucket-pill--${explanation.bucketId}">${escapeHtml(explanation.bucketLabel)}</span>
        <span class="status-pill status-pill--${status}">${status === 'broken' ? 'unstable' : 'failed'}</span>
        <span class="suite-tag">${escapeHtml(repoLabel(f.repo))}</span>
      </div>
      <div class="failure-item__body">
        <h4>${escapeHtml(friendlyFailureTitle(f))}</h4>
        <p class="failure-meaning"><strong>What happened:</strong> ${escapeHtml(explanation.meaning)}</p>
        <p class="failure-type">${escapeHtml(explanation.typeLine)}</p>
        <p class="failure-next"><strong>Suggested next step:</strong> ${escapeHtml(explanation.nextStep)}</p>
        ${explanation.detail ? `<p class="failure-meta tech-only">${escapeHtml(explanation.detail)}</p>` : ''}
        ${linksHtml}
      </div>
    </div>`;
}

function renderCategoryChips(categories) {
  if (!categories || !Object.keys(categories).length) return '';
  const chips = Object.entries(categories)
    .map(([cat, count]) => `<span class="category-chip">${escapeHtml(humanizeCategory(cat))}: ${count}</span>`)
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
  const plainStatus =
    status === 'pass' ? 'Healthy'
      : status === 'warn' ? 'Mostly healthy'
        : status === 'fail' ? 'Needs attention'
          : 'No data';

  return `
    <article class="card card--${config.id} card--${status}" data-repo="${config.id}">
      <div class="card__header">
        <div>
          <h2 class="card__title">${config.icon} ${config.title}</h2>
          <p class="card__desc exec-hide">${config.description}</p>
          <p class="card__desc exec-only">${plainStatus}${noData ? '' : ` · ${rates.passPct}% of checks passed`}</p>
          ${branchLabel ? `<span class="branch-pill tech-only">${branchLabel}</span>` : ''}
        </div>
        <div class="rate-badge ${status}" title="Pass rate from latest available run">
          <span class="rate-badge__value">${noData ? '—' : rates.passPct + '%'}</span>
          <span class="rate-badge__label">${badgeLabel(counts, rates)}</span>
        </div>
      </div>
      <div class="card__body">
        ${noData ? `<p class="no-data-msg">No published test results found for this suite yet.</p>` : `
        <div class="progress-bar" aria-hidden="true">
          <div class="progress-bar__pass" style="width:${rates.passPct}%"></div>
          <div class="progress-bar__fail" style="width:${rates.failPct}%"></div>
        </div>
        <div class="stats">
          <div class="stat"><span class="stat__value">${counts.total}</span><span class="stat__label">Total</span></div>
          <div class="stat stat--pass"><span class="stat__value stat__value--pass">${counts.passed}</span><span class="stat__label">Passed</span></div>
          ${counts.review > 0 ? `<div class="stat stat--fail"><span class="stat__value stat__value--fail">${counts.review}</span><span class="stat__label">Needs review</span></div>` : ''}
          ${counts.skipped > 0 ? `<div class="stat tech-only"><span class="stat__value">${counts.skipped}</span><span class="stat__label">Skipped</span></div>` : ''}
        </div>
        <div class="result-row">
          <span class="status-badge ${status}">${status === 'pass' ? '● All passed' : status === 'warn' ? '● Mostly passed' : '● Has failures'}</span>
          <span class="result-row__meta">${rates.passPct}% pass${counts.review > 0 ? ` · ${rates.failPct}% need review` : ''}</span>
        </div>
        <div class="tech-only">${renderTrendBars(summary?.historyTrend)}</div>
        ${summary?.lastAvailable ? '<p class="data-note tech-only">Latest publish was empty — showing last available Allure run from report history.</p>' : ''}`}
        <div class="tech-only">
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
        </div>
        <div class="card__actions tech-only">
          <a class="link-btn primary" href="${summary?.reportUrl || config.reportUrl}" target="_blank" rel="noopener">View Allure Report</a>
          <a class="link-btn" href="${summary?.ciRunUrl || config.ciRunUrl}" target="_blank" rel="noopener">View CI Run</a>
        </div>
        <p class="exec-only card-exec-note">Last checked ${escapeHtml(formatDate(summary?.finishedAt) || 'recently')}</p>
      </div>
    </article>
  `;
}

function collectFailures(summaries) {
  const items = [];
  for (const summary of summaries) {
    if (!summary?.topFailures?.length) continue;
    for (const failure of summary.topFailures) {
      items.push({ repo: summary.repo, ...failure });
    }
  }
  return items;
}

function textBlob(failure) {
  return `${failure.name || ''} ${failure.feature || ''} ${failure.reason || ''} ${failure.category || ''}`.toLowerCase();
}

function matchArea(area, failure, summary) {
  if (area.repos?.length && area.repos.includes(failure.repo || summary?.repo)) {
    if (!area.keywords?.length) return true;
  }
  const blob = textBlob(failure);
  return (area.keywords || []).some((kw) => blob.includes(kw.toLowerCase()));
}

function areaStatusFromHits(hits, suitePassPct) {
  if (!hits.length) {
    if (suitePassPct != null && suitePassPct < 70) return 'watch';
    return 'healthy';
  }
  const hardFails = hits.filter((h) => h.status === 'failed').length;
  if (hardFails >= 2 || hits.length >= 4) return 'risk';
  if (hardFails >= 1 || hits.length >= 2) return 'watch';
  return 'watch';
}

function suitePassPct(summary) {
  const counts = summary?.counts || computeCounts(summary);
  if (!counts.total) return null;
  return computeRates(counts).passPct;
}

function buildBusinessAreas(summaries) {
  const failures = collectFailures(summaries);
  const byRepo = Object.fromEntries(summaries.map((s) => [s.repo, s]));

  return BUSINESS_AREAS.map((area) => {
    let hits = failures.filter((f) => matchArea(area, f, byRepo[f.repo]));

    // Whole-suite signal for mobile / API when no named failures mapped
    if (!hits.length && area.repos?.length) {
      for (const repoId of area.repos) {
        const summary = byRepo[repoId];
        const counts = summary?.counts;
        if (!counts?.total) continue;
        if (counts.review > 0) {
          hits = hits.concat(
            (summary.topFailures || []).slice(0, 3).map((f) => ({ repo: repoId, ...f })),
          );
          if (!hits.length) {
            hits.push({
              repo: repoId,
              name: `${REPO_DISPLAY[repoId]?.label || repoId} suite needs attention`,
              status: counts.review > 5 ? 'failed' : 'broken',
              category: 'unknown',
              reason: `${counts.review} tests need review`,
            });
          }
        }
      }
    }

    const relatedRepos = area.repos?.length
      ? area.repos
      : [...new Set(hits.map((h) => h.repo).filter(Boolean))];
    const relatedPcts = relatedRepos
      .map((id) => suitePassPct(byRepo[id]))
      .filter((p) => p != null);
    const avgPct = relatedPcts.length
      ? relatedPcts.reduce((a, b) => a + b, 0) / relatedPcts.length
      : null;

    const status = areaStatusFromHits(hits, avgPct);
    return {
      ...area,
      status,
      hitCount: hits.length,
      sample: hits.slice(0, 2),
    };
  });
}

function computeSuiteHealth(summary, config) {
  const counts = summary?.counts || computeCounts(summary);
  const rates = computeRates(counts);
  const status = cardStatus(summary, counts, rates);
  if (!counts.total) {
    return {
      id: config.id,
      title: config.title,
      icon: config.icon,
      level: 'unknown',
      label: 'No data',
      score: null,
      passPct: 0,
      counts,
      sentence: 'No published results yet.',
    };
  }

  let level = 'high';
  let label = 'High';
  if (rates.passPct < 70 || status === 'fail') {
    level = 'risk';
    label = 'At risk';
  } else if (rates.passPct < 90 || status === 'warn') {
    level = 'watch';
    label = 'Watch';
  }

  let score = Math.round(rates.passPct - (counts.review > 0 ? Math.min(counts.review, 15) : 0));
  score = Math.max(0, Math.min(100, score));

  const display = REPO_DISPLAY[config.id]?.label || config.title;
  let sentence;
  if (level === 'high') {
    sentence = `${display} looks ready (${rates.passPct}% passed).`;
  } else if (level === 'watch') {
    sentence = `${display} is mostly OK — ${counts.review} check${counts.review === 1 ? '' : 's'} still need a look.`;
  } else {
    sentence = `${display} is not release-ready yet — ${counts.review} of ${counts.total} checks need review.`;
  }

  return {
    id: config.id,
    title: config.title,
    icon: config.icon,
    level,
    label,
    score,
    passPct: rates.passPct,
    counts,
    sentence,
  };
}

function computeHealthScore(summaries) {
  const valid = summaries.filter((s) => (s?.counts?.total || 0) > 0);
  const suiteScores = REPO_CONFIG.map((cfg, i) => computeSuiteHealth(summaries[i], cfg));

  if (!valid.length) {
    return {
      level: 'unknown',
      label: 'Waiting for data',
      score: null,
      passPct: 0,
      totalTests: 0,
      totalPassed: 0,
      totalFailed: 0,
      suiteCount: 0,
      sentence: 'Loading the latest quality signal…',
      areas: [],
      suiteScores,
    };
  }

  const totalTests = valid.reduce((a, s) => a + (s.counts?.total || 0), 0);
  const totalPassed = valid.reduce((a, s) => a + (s.counts?.passed || 0), 0);
  const totalFailed = valid.reduce((a, s) => a + (s.counts?.review || 0), 0);
  const passPct = totalTests ? Math.round((totalPassed / totalTests) * 1000) / 10 : 0;

  const suiteLevels = valid.map((s) => {
    const counts = s.counts || computeCounts(s);
    return cardStatus(s, counts, computeRates(counts));
  });
  const failSuites = suiteLevels.filter((l) => l === 'fail').length;
  const warnSuites = suiteLevels.filter((l) => l === 'warn').length;
  const areas = buildBusinessAreas(summaries);
  const riskAreas = areas.filter((a) => a.status === 'risk');
  const watchAreas = areas.filter((a) => a.status === 'watch');

  let level = 'high';
  let label = 'High';
  if (passPct < 70 || failSuites >= 2 || riskAreas.length >= 2) {
    level = 'risk';
    label = 'At risk';
  } else if (passPct < 90 || failSuites >= 1 || warnSuites >= 2 || watchAreas.length >= 2) {
    level = 'watch';
    label = 'Watch';
  }

  let score = Math.round(passPct - failSuites * 8 - riskAreas.length * 4);
  score = Math.max(0, Math.min(100, score));

  const sentence = buildHealthSentence({
    level,
    label,
    passPct,
    valid,
    areas,
    riskAreas,
    watchAreas,
    totalFailed,
    suiteScores,
  });

  return {
    level,
    label,
    score,
    passPct,
    totalTests,
    totalPassed,
    totalFailed,
    suiteCount: valid.length,
    sentence,
    areas,
    suiteScores,
  };
}

function buildHealthSentence({ level, label, passPct, valid, areas, riskAreas, watchAreas, totalFailed, suiteScores }) {
  const strong = (suiteScores || [])
    .filter((s) => s.level === 'high')
    .map((s) => REPO_DISPLAY[s.id]?.label || s.title);
  const weak = (suiteScores || [])
    .filter((s) => s.level === 'risk' || s.level === 'watch')
    .map((s) => `${REPO_DISPLAY[s.id]?.label || s.title} (${s.label})`);

  const attention = [...riskAreas, ...watchAreas]
    .slice(0, 3)
    .map((a) => a.label);

  if (level === 'high') {
    const strongBit = strong.length ? ` ${strong.join(', ')} look solid.` : '';
    return `Overall release confidence is ${label} (${passPct}% passed).${strongBit}`;
  }

  if (level === 'watch') {
    const suitesBit = weak.length ? ` Suites to watch: ${weak.join(', ')}.` : '';
    const focus = attention.length ? ` Product focus: ${attention.join(', ')}.` : '';
    const good = strong.length ? ` ${strong.join(' & ')} are in good shape.` : '';
    return `Overall release confidence is ${label} (${passPct}% passed).${good}${suitesBit}${focus}`;
  }

  const suitesBit = weak.length ? ` Weakest suites: ${weak.join(', ')}.` : '';
  const focus = attention.length ? ` Biggest product gaps: ${attention.join(', ')}.` : '';
  return `Overall release confidence is ${label} (${passPct}% passed).${suitesBit}${focus} Separate environment and flaky noise from real defects before calling the build ready.`;
}


function computeReleaseGate(summaries) {
  const health = computeHealthScore(summaries);
  const triage = summarizeIssueBuckets(summaries);
  const failures = collectFailures(summaries);
  const blockers = [];

  for (const s of health.suiteScores || []) {
    if (s.level === 'risk') {
      blockers.push({
        title: `${REPO_DISPLAY[s.id]?.label || s.title} at risk`,
        detail: s.sentence || `${s.passPct}% pass · ${s.counts?.review || 0} need review`,
        tab: 'suites',
      });
    }
  }
  for (const f of failures.slice(0, 8)) {
    const exp = explainFailure(f);
    if (exp.bucket === 'defect' || exp.bucket === 'environment') {
      blockers.push({
        title: friendlyFailureTitle(f),
        detail: `${exp.bucketLabel} · ${REPO_DISPLAY[f.repo]?.label || f.repo}`,
        tab: 'attention',
      });
    }
  }
  // unique by title
  const seen = new Set();
  const top = [];
  for (const b of blockers) {
    const key = b.title.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    top.push(b);
    if (top.length >= 3) break;
  }

  let verdict = 'ship';
  let label = 'Ship';
  let blurb = 'No critical blockers in the mapped signal — ready for release discussion.';
  if (health.level === 'risk' || triage.counts.defect >= 3 || (health.suiteScores || []).filter((s) => s.level === 'risk').length >= 2) {
    verdict = 'hold';
    label = 'Hold';
    blurb = 'Do not ship yet — clear the blockers below first.';
  } else if (health.level === 'watch' || triage.counts.defect >= 1 || triage.counts.environment >= 1) {
    verdict = 'investigate';
    label = 'Investigate';
    blurb = 'Not a hard stop — verify the items below before calling it green.';
  } else if (!top.length && health.level === 'high') {
    blurb = 'Suites look healthy — confirm with owners, then ship.';
  }

  while (top.length < 3 && failures[top.length]) {
    const f = failures[top.length];
    const exp = explainFailure(f);
    top.push({
      title: friendlyFailureTitle(f),
      detail: `${exp.bucketLabel} · ${REPO_DISPLAY[f.repo]?.label || f.repo}`,
      tab: 'attention',
    });
  }

  return { verdict, label, blurb, blockers: top.slice(0, 3), health, triage };
}

function computeWeekOverWeek(summaries) {
  const points = collectTrendPoints(TREND_HISTORY, summaries, { includeEstimated: false });
  const weekly = TREND_RANGES.find((r) => r.id === 'weekly');
  const agg = aggregateTrendSeries(points, weekly);
  const overall = agg.series.overall || [];
  const nums = overall.map((v, i) => ({ v, i })).filter((x) => x.v != null);
  if (nums.length < 2) {
    return { available: false, delta: null, thisWeek: null, lastWeek: null, suites: [] };
  }
  const thisWeek = nums[nums.length - 1].v;
  const lastWeek = nums[nums.length - 2].v;
  const delta = Math.round((thisWeek - lastWeek) * 10) / 10;
  const suites = REPO_CONFIG.map((cfg) => {
    const series = agg.series[cfg.id] || [];
    const vals = series.map((v, i) => ({ v, i })).filter((x) => x.v != null);
    if (vals.length < 2) return { id: cfg.id, label: REPO_DISPLAY[cfg.id].label, delta: null, thisWeek: vals.at(-1)?.v ?? null };
    const tw = vals[vals.length - 1].v;
    const lw = vals[vals.length - 2].v;
    return {
      id: cfg.id,
      label: REPO_DISPLAY[cfg.id].label,
      icon: cfg.icon,
      thisWeek: tw,
      lastWeek: lw,
      delta: Math.round((tw - lw) * 10) / 10,
    };
  });
  return {
    available: true,
    thisWeek,
    lastWeek,
    delta,
    label: delta >= 1 ? `Up ${delta} pts` : delta <= -1 ? `Down ${Math.abs(delta)} pts` : 'Flat',
    cls: delta >= 1 ? 'up' : delta <= -1 ? 'down' : 'flat',
    suites,
  };
}

function suiteSparklineValues(suiteId, summaries) {
  const points = collectTrendPoints(TREND_HISTORY, summaries, { includeEstimated: false })
    .filter((p) => p.suite === suiteId && p.passPct != null)
    .sort((a, b) => a.date.localeCompare(b.date));
  // Prefer last 7 unique dates
  const byDay = new Map();
  for (const p of points) byDay.set(p.date, p.passPct);
  const days = [...byDay.keys()].sort();
  const last = days.slice(-7);
  return last.map((d) => byDay.get(d));
}

function renderSparkline(values, color) {
  const nums = (values || []).filter((v) => v != null);
  if (nums.length < 2) return '<span class="sparkline sparkline--empty" title="Not enough history"></span>';
  const w = 72;
  const h = 22;
  const min = Math.min(...nums, 0);
  const max = Math.max(...nums, 100);
  const span = Math.max(1, max - min);
  const pts = nums.map((v, i) => {
    const x = (i / (nums.length - 1)) * (w - 2) + 1;
    const y = h - 2 - ((v - min) / span) * (h - 4);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return `<svg class="sparkline" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><polyline fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" points="${pts}" /></svg>`;
}

function formatDelta(delta) {
  if (delta == null) return { text: '—', cls: 'flat' };
  if (delta >= 1) return { text: `+${delta} pts`, cls: 'up' };
  if (delta <= -1) return { text: `${delta} pts`, cls: 'down' };
  return { text: '0 pts', cls: 'flat' };
}

function renderOverallBanner(summaries) {
  const health = computeHealthScore(summaries);
  const gate = computeReleaseGate(summaries);
  const wow = computeWeekOverWeek(summaries);

  if (health.level === 'unknown') {
    return `<div class="health-banner health-banner--unknown">
      <div class="health-banner__score"><span class="health-banner__value">—</span><span class="health-banner__label">Loading</span></div>
      <div class="health-banner__copy"><p class="health-banner__eyebrow">Overall release confidence</p><p class="health-banner__sentence">${escapeHtml(health.sentence)}</p></div>
    </div>`;
  }

  const blockers = gate.blockers.length
    ? `<ol class="gate-blockers">${gate.blockers.map((b, i) => `
        <li>
          <button type="button" class="gate-blocker" data-goto-tab="${escapeHtml(b.tab || 'attention')}">
            <span class="gate-blocker__n">${i + 1}</span>
            <span>
              <strong>${escapeHtml(b.title)}</strong>
              <em>${escapeHtml(b.detail)}</em>
            </span>
          </button>
        </li>`).join('')}</ol>`
    : `<p class="gate-blockers gate-blockers--none">No mapped blockers in the top list.</p>`;

  const wowSuites = (wow.suites || []).map((s) => {
    const d = formatDelta(s.delta);
    return `<span class="wow-chip"><span>${s.icon || ''} ${escapeHtml(s.label)}</span><strong class="trend-dir trend-dir--${d.cls}">${escapeHtml(d.text)}</strong></span>`;
  }).join('');

  const wowBlock = wow.available ? `
    <div class="wow-strip" aria-label="This week versus last week">
      <div class="wow-strip__main">
        <span class="wow-strip__label">This week vs last week</span>
        <strong class="trend-dir trend-dir--${wow.cls}">${escapeHtml(wow.label)}</strong>
        <span class="wow-strip__meta">${formatPct(wow.thisWeek)} now · was ${formatPct(wow.lastWeek)}</span>
      </div>
      <div class="wow-strip__suites">${wowSuites}</div>
    </div>` : `
    <div class="wow-strip wow-strip--empty">
      <span class="wow-strip__label">This week vs last week</span>
      <span class="wow-strip__meta">Need at least two weekly points to compare.</span>
    </div>`;

  const suiteCards = (health.suiteScores || []).map((s) => {
    const spark = renderSparkline(suiteSparklineValues(s.id, summaries), REPO_DISPLAY[s.id]?.color || '#93c5fd');
    const wowSuite = (wow.suites || []).find((x) => x.id === s.id);
    const d = formatDelta(wowSuite?.delta);
    return `
    <article class="suite-health suite-health--${s.level}" data-suite="${escapeHtml(s.id)}">
      <div class="suite-health__top">
        <span class="suite-health__name">${s.icon} ${escapeHtml(REPO_DISPLAY[s.id]?.label || s.title)}</span>
        <span class="suite-health__badge">${escapeHtml(s.label)}</span>
      </div>
      <div class="suite-health__score-row">
        <div class="suite-health__score">${s.score == null ? '—' : s.score}</div>
        ${spark}
      </div>
      <p class="suite-health__meta">${s.counts.total ? `${s.passPct}% pass · ${s.counts.review} need review` : 'No data'}
        ${wowSuite?.delta != null ? ` · <span class="trend-dir trend-dir--${d.cls}">${escapeHtml(d.text)} vs last week</span>` : ''}
      </p>
      <p class="suite-health__sentence">${escapeHtml(s.sentence)}</p>
    </article>`;
  }).join('');

  return `
    <div class="health-stack">
      <div class="gate-banner gate-banner--${gate.verdict}" aria-label="Release gate verdict">
        <div class="gate-banner__verdict">
          <span class="gate-banner__kicker">Release gate</span>
          <strong class="gate-banner__label">${escapeHtml(gate.label)}</strong>
          <p>${escapeHtml(gate.blurb)}</p>
        </div>
        <div class="gate-banner__blockers">
          <p class="gate-banner__kicker">Top blockers</p>
          ${blockers}
        </div>
      </div>
      <div class="health-banner health-banner--${health.level}">
        <div class="health-banner__score" title="Composite release confidence across all suites">
          <span class="health-banner__value">${health.score}</span>
          <span class="health-banner__label">${escapeHtml(health.label)}</span>
        </div>
        <div class="health-banner__copy">
          <p class="health-banner__eyebrow">Overall release confidence</p>
          <p class="health-banner__sentence">${escapeHtml(health.sentence)}</p>
          <p class="health-banner__meta">
            <span class="text-pass">${health.totalPassed} passed</span>
            · <span class="${health.totalFailed ? 'text-fail' : 'text-pass'}">${health.totalFailed} need review</span>
            · ${health.totalTests} checks across ${health.suiteCount} suites
            · ${health.passPct}% pass
          </p>
        </div>
      </div>
      ${wowBlock}
      <div class="suite-health-grid" aria-label="Release confidence by project">
        ${suiteCards}
      </div>
    </div>`;
}

function renderBusinessAreas(summaries) {
  const areas = buildBusinessAreas(summaries);
  const tiles = areas.map((area) => {
    const statusLabel =
      area.status === 'healthy' ? 'Looking good'
        : area.status === 'watch' ? 'Needs attention'
          : 'At risk';
    const sample = area.sample?.[0]
      ? `<p class="area-tile__sample">${escapeHtml(friendlyFailureTitle(area.sample[0]))} — ${escapeHtml(explainFailure(area.sample[0]).meaning)}</p>`
      : `<p class="area-tile__sample area-tile__sample--ok">No open issues mapped here</p>`;
    return `
      <article class="area-tile area-tile--${area.status}">
        <div class="area-tile__top">
          <span class="area-dot" aria-hidden="true"></span>
          <span class="area-tile__status">${statusLabel}</span>
        </div>
        <h3 class="area-tile__title">${escapeHtml(area.label)}</h3>
        <p class="area-tile__blurb">${escapeHtml(area.blurb)}</p>
        ${sample}
      </article>`;
  }).join('');

  return `
    <div class="panel__header">
      <h2>Product areas</h2>
      <p>Traffic lights for journeys that matter to the business — not suite names</p>
    </div>
    <div class="area-grid">${tiles}</div>`;
}

function friendlyFailureTitle(failure) {
  const raw = (failure.feature || failure.name || 'Quality check').trim();
  return raw
    .replace(/^verify\s+/i, '')
    .replace(/^validate\s+/i, '')
    .replace(/^to\s+validate\s+/i, '')
    .replace(/^should/i, '')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^./, (c) => c.toUpperCase());
}

function parseCountReason(reason) {
  if (!reason) return null;
  const match = String(reason).match(/(\d+)\s*failed\s*·\s*(\d+)\s*broken/i);
  if (!match) return null;
  const failed = Number(match[1]);
  const broken = Number(match[2]);
  const parts = [];
  if (failed) parts.push(`${failed} clear failure${failed === 1 ? '' : 's'}`);
  if (broken) parts.push(`${broken} unstable check${broken === 1 ? '' : 's'}`);
  return { failed, broken, text: parts.length ? parts.join(' and ') + ' in this journey' : null };
}

function classifyIssueBucket(failure) {
  const cat = failure.category || 'unknown';
  const status = failure.status || '';
  const blob = `${failure.name || ''} ${failure.feature || ''} ${failure.reason || ''} ${cat}`.toLowerCase();
  const counts = parseCountReason(failure.reason);

  const looksLikeSlowServer =
    /timeout|timed?\s*out|waiting|wait for|slow|latency|response (time|late|delay)|server (slow|late|delay)|api (slow|late|delay)|gateway|504|502|503/i.test(blob)
    || cat === 'timeout';

  const looksLikeIntermittent =
    /flaky|intermittent|unstable|race|sometimes|occasionally|heisen/i.test(blob);

  // 1) Environment — infra / access / deploy / slow server responses
  if (
    cat === 'environment'
    || /503|502|504|deploy|outage|environment down|credential|auth (api|down|server)|base url|grid|device (offline|busy)/i.test(blob)
  ) {
    return 'environment';
  }
  // Login category alone is env-ish only when it looks like access/setup
  if (cat === 'login' && /credential|auth|session|403|401|sign.?in/i.test(blob)) {
    return 'environment';
  }
  // Waiting on a late server/API response → environment (not a product defect yet)
  // Only keep as flaky if the text clearly says intermittent flake.
  if (looksLikeSlowServer && !looksLikeIntermittent) {
    return 'environment';
  }

  // 2) Likely defect — clear product / API / data / UI contract mismatch
  if (
    cat === 'assertion'
    || cat === 'api'
    || cat === 'data'
    || cat === 'locator'
    || status === 'failed'
    || (counts && counts.failed > 0)
  ) {
    return 'defect';
  }

  // 3) Flaky — unstable / broken-heavy without hard product assert
  if (
    status === 'broken'
    || looksLikeIntermittent
    || (counts && counts.broken > 0 && counts.failed === 0)
  ) {
    return 'flaky';
  }

  return 'defect';
}

function humanizeFailure(failure) {
  return explainFailure(failure).meaning;
}

function humanizeCategory(category) {
  return CATEGORY_PLAIN[category] || CATEGORY_PLAIN.unknown;
}

function explainFailure(failure) {
  const category = failure.category || 'unknown';
  const categoryLabel = humanizeCategory(category);
  const bucketId = classifyIssueBucket(failure);
  const bucket = ISSUE_BUCKETS[bucketId];
  const countInfo = parseCountReason(failure.reason);
  const countPhrase = countInfo?.text || null;
  const rawReason = failure.reason && !/failed\s*·|broken in feature/i.test(failure.reason)
    ? failure.reason
    : null;
  const title = friendlyFailureTitle(failure);
  const suite = REPO_DISPLAY[failure.repo]?.label || failure.repo || 'suite';

  let meaning;
  if (rawReason) {
    meaning = `${title} on ${suite}: ${rawReason}`;
  } else if (countPhrase) {
    meaning = `${title} on ${suite} has ${countPhrase}.`;
  } else if (failure.status === 'broken') {
    meaning = `${title} on ${suite} is unstable right now.`;
  } else {
    meaning = `${title} on ${suite} did not meet expectations.`;
  }

  const typeLine =
    bucketId === 'environment'
      ? `Type: Environment issue — ${bucket.blurb}`
      : bucketId === 'flaky'
        ? `Type: Flaky test — ${bucket.blurb}`
        : `Type: Likely defect — ${bucket.blurb}`;

  return {
    categoryLabel,
    bucketId,
    bucketLabel: bucket.label,
    meaning,
    typeLine,
    nextStep: bucket.nextStep || CATEGORY_NEXT_STEP[category] || CATEGORY_NEXT_STEP.unknown,
    detail: failure.feature && failure.feature !== failure.name
      ? `Technical name: ${failure.name}`
      : (failure.name && failure.name !== title ? `Technical name: ${failure.name}` : ''),
  };
}

function summarizeIssueBuckets(summaries) {
  const failures = collectFailures(summaries);
  const counts = { environment: 0, flaky: 0, defect: 0 };
  const samples = { environment: [], flaky: [], defect: [] };
  for (const f of failures) {
    const bucket = classifyIssueBucket(f);
    counts[bucket] += 1;
    if (samples[bucket].length < 3) samples[bucket].push(f);
  }
  return { counts, samples, total: failures.length };
}

function renderIssueTriage(summaries) {
  const { counts, samples, total } = summarizeIssueBuckets(summaries);
  const cards = ['environment', 'flaky', 'defect'].map((id) => {
    const meta = ISSUE_BUCKETS[id];
    const n = counts[id] || 0;
    const sampleHtml = (samples[id] || []).map((f) => `
      <li>
        <strong>${escapeHtml(friendlyFailureTitle(f))}</strong>
        <span>${escapeHtml(REPO_DISPLAY[f.repo]?.label || f.repo)}</span>
      </li>`).join('') || '<li class="triage-empty">None in the latest mapped failures</li>';
    return `
      <article class="triage-card triage-card--${id}">
        <div class="triage-card__top">
          <h3>${escapeHtml(meta.label)}</h3>
          <span class="triage-count">${n}</span>
        </div>
        <p class="triage-card__blurb">${escapeHtml(meta.blurb)}</p>
        <p class="triage-card__next"><strong>Do this:</strong> ${escapeHtml(meta.nextStep)}</p>
        <ul class="triage-samples">${sampleHtml}</ul>
      </article>`;
  }).join('');

  const guidance = total
    ? `Of ${total} mapped issues: <strong>${counts.defect}</strong> likely defects, <strong>${counts.flaky}</strong> flaky, <strong>${counts.environment}</strong> environment. Fix defects for release; quarantine flakes; verify env before retesting.`
    : 'No mapped failures right now — keep monitoring suite confidence.';

  return `
    <div class="panel__header">
      <h2>Environment · Flaky · Defects</h2>
      <p>Simple split so meetings do not mix setup noise with real bugs</p>
    </div>
    <p class="triage-guidance">${guidance}</p>
    <div class="triage-grid">${cards}</div>`;
}

function deriveAiSignals(summaries) {
  const failures = collectFailures(summaries);
  const byCategory = {};
  for (const f of failures) {
    const cat = f.category || 'unknown';
    byCategory[cat] = (byCategory[cat] || 0) + 1;
  }
  const locatorish = (byCategory.locator || 0) + (byCategory.timeout || 0);
  const dataEnv = (byCategory.data || 0) + (byCategory.environment || 0);
  const assertion = byCategory.assertion || 0;

  const bullets = [];
  if (locatorish > 0) {
    bullets.push(`${locatorish} issue(s) look UI-timing related — self-healing is designed to absorb this class of noise.`);
  }
  if (assertion > 0) {
    bullets.push(`${assertion} result mismatch(es) likely need a human product decision, not an automatic heal.`);
  }
  if (dataEnv > 0) {
    bullets.push(`${dataEnv} data / environment signal(s) — AI quarantine helps keep these from blocking every PR.`);
  }
  if (!bullets.length) {
    bullets.push('Latest mapped failures are light — AI guardrails stay on standby while suites stay quiet.');
  }

  const healCandidates = locatorish;
  const humanDecisions = assertion;
  return { bullets, healCandidates, humanDecisions, byCategory };
}

function formatAiCount(n) {
  const v = Number(n) || 0;
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 10_000) return `${Math.round(v / 1000)}k`;
  return String(Math.round(v));
}

function formatAiMoney(usd) {
  const v = Number(usd) || 0;
  if (v === 0) return '$0';
  if (v < 0.01) return '<$0.01';
  return `$${v.toFixed(2)}`;
}

function formatAiDuration(mins) {
  const v = Number(mins) || 0;
  if (v <= 0) return '0m';
  if (v < 1) {
    const sec = Math.round(v * 60);
    return sec > 0 ? `${sec}s` : '<1s';
  }
  if (v < 60) {
    const whole = Math.floor(v);
    const sec = Math.round((v - whole) * 60);
    if (sec > 0) return `${whole}m ${sec}s`;
    return `${whole}m`;
  }
  const hrs = Math.floor(v / 60);
  const remainingMins = Math.round(v % 60);
  if (remainingMins > 0) return `${hrs}h ${remainingMins}m`;
  return `${hrs}h`;
}

function formatAiPct(pct) {
  const v = Number(pct) || 0;
  return `${v.toFixed(v >= 10 ? 0 : 1)}%`;
}

function formatRelativeTime(iso) {
  if (!iso) return 'recently';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return String(iso);
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 2) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs}h ago`;
  return new Date(iso).toLocaleDateString();
}

function topMapEntries(map, limit = 5) {
  if (!map || typeof map !== 'object') return [];
  return Object.entries(map)
    .map(([key, val]) => ({ key, val: Number(val) || 0 }))
    .sort((a, b) => b.val - a.val)
    .slice(0, limit);
}

function buildAiUsageHelpBullets(totals, signals) {
  const bullets = [];
  if (totals.reposReporting > 0) {
    if (totals.healsSucceeded > 0) {
      bullets.push(`${formatAiCount(totals.healsSucceeded)} locator recoveries kept tests running instead of failing on UI drift.`);
    }
    if (totals.estimatedMinutesSaved > 0) {
      bullets.push(`~${formatAiDuration(totals.estimatedMinutesSaved)} of manual triage avoided this run (framework estimate).`);
    }
    if (totals.learnedLocatorsCount > 0) {
      bullets.push(`${formatAiCount(totals.learnedLocatorsCount)} learned locators in memory — repeat breaks heal faster.`);
    }
    if (totals.flakyQuarantineCount > 0) {
      bullets.push(`${formatAiCount(totals.flakyQuarantineCount)} flaky scenarios flagged for quarantine so PR gates stay honest.`);
    }
  }
  if (signals.healCandidates > 0) {
    bullets.push(`${signals.healCandidates} current failure(s) look UI-timing related — exactly what self-healing targets.`);
  }
  if (signals.humanDecisions > 0) {
    bullets.push(`${signals.humanDecisions} assertion mismatch(es) need a product decision — AI will not auto-green those.`);
  }
  if (!bullets.length) {
    bullets.push('AI metrics are read from each suite’s published Allure report (environment + attachments).');
  }
  return bullets;
}

function formatAiSource(source) {
  const map = {
    'allure-environment': 'Allure environment',
    'allure-attachment': 'Allure attachment',
    'allure-pages-json': 'Allure report JSON',
    'ci-json': 'CI ai-usage.json',
  };
  return map[source] || source || '—';
}

function renderAiFrameworkCards(aiUsage) {
  const repos = aiUsage?.repos || {};
  const cards = Object.keys(REPO_DISPLAY).map((id) => {
    const entry = repos[id] || {};
    const label = REPO_DISPLAY[id]?.label || id;
    const framework = entry.framework || '—';
    const status = entry.status || 'pending';
    const s = entry.summary || {};
    const statusCls = status === 'live' ? 'ai-framework-card--live'
      : status === 'enabled' ? 'ai-framework-card--enabled' : 'ai-framework-card--pending';
    const statusLabel = status === 'live' ? 'Reporting'
      : status === 'enabled' ? 'AI enabled' : 'Pending';
    const metric = status === 'live'
      ? `${formatAiCount(s.llmInvocations)} LLM · ${formatAiPct(s.healSuccessRatePct)} heal`
      : (entry.note || 'Waiting for Allure AI metrics');
    const report = entry.reportUrl
      ? `<a href="${escapeHtml(entry.reportUrl)}" target="_blank" rel="noopener">Allure report</a>`
      : '';
    return `
      <article class="ai-framework-card ${statusCls}">
        <p class="ai-framework-card__suite">${escapeHtml(label)}</p>
        <h3 class="ai-framework-card__framework">${escapeHtml(framework)}</h3>
        <p class="ai-framework-card__status">${escapeHtml(statusLabel)}</p>
        <p class="ai-framework-card__metric">${escapeHtml(metric)}</p>
        <p class="ai-framework-card__source">${status === 'live' ? escapeHtml(formatAiSource(entry.source)) : report}</p>
      </article>`;
  }).join('');
  return `<div class="ai-framework-grid">${cards}</div>`;
}

function renderAiUsageMetricCard(value, label, note, live = false) {
  return `
    <div class="ai-metric${live ? ' ai-metric--live' : ''}">
      <span class="ai-metric__value">${escapeHtml(value)}</span>
      <span class="ai-metric__label">${escapeHtml(label)}</span>
      ${note ? `<span class="ai-metric__note">${escapeHtml(note)}</span>` : ''}
    </div>`;
}

function renderAiRepoUsageRows(aiUsage) {
  const repos = aiUsage?.repos || {};
  const rows = Object.keys(REPO_DISPLAY).map((id) => {
    const entry = repos[id] || {};
    const s = entry.summary || {};
    const label = REPO_DISPLAY[id]?.label || id;
    const status = entry.status || 'pending';
    const inv = Number(s.llmInvocations) || 0;
    const healPct = Number(s.healSuccessRatePct) || 0;
    const statusBadge = status === 'live'
      ? '<span class="ai-repo-status ai-repo-status--live">Live</span>'
      : status === 'enabled'
        ? '<span class="ai-repo-status ai-repo-status--enabled">AI on</span>'
        : '<span class="ai-repo-status ai-repo-status--pending">Pending</span>';
    const report = entry.reportUrl
      ? `<a href="${escapeHtml(entry.reportUrl)}" target="_blank" rel="noopener">Allure</a>`
      : '—';
    const ci = entry.ciRunUrl
      ? `<a href="${escapeHtml(entry.ciRunUrl)}" target="_blank" rel="noopener">CI</a>`
      : '—';
    return `
      <tr>
        <td>${escapeHtml(label)} ${statusBadge}</td>
        <td>${escapeHtml(entry.framework || '—')}</td>
        <td>${status === 'live' ? formatAiCount(inv) : '—'}</td>
        <td>${status === 'live' && (s.healsSucceeded || s.healsFailed) ? formatAiPct(healPct) : '—'}</td>
        <td>${status === 'live' ? formatAiMoney(s.estimatedCostUsd) : '—'}</td>
        <td>${status === 'live' ? formatAiDuration(s.estimatedMinutesSaved) : '—'}</td>
        <td>${status === 'live' ? escapeHtml(formatAiSource(entry.source)) : '—'}</td>
        <td>${report} · ${ci}</td>
      </tr>`;
  }).join('');

  const jobRows = [];
  for (const [repoId, entry] of Object.entries(repos)) {
    for (const job of entry.jobs || []) {
      const m = job.metrics || {};
      jobRows.push(`
        <tr class="ai-job-row">
          <td>${escapeHtml(REPO_DISPLAY[repoId]?.label || repoId)} · ${escapeHtml(job.name || 'job')}</td>
          <td>CI job</td>
          <td>${formatAiCount(m.llmInvocations || m.llmDecisionCount)}</td>
          <td>${m.healSuccessRatePct != null ? formatAiPct(m.healSuccessRatePct) : '—'}</td>
          <td>${formatAiMoney(m.estimatedCostUsd || m.aiEstimatedCostDollars)}</td>
          <td>${formatAiDuration(m.estimatedMinutesSaved || m.aiEstimatedTimeSavedMinutes)}</td>
          <td>Allure attachment</td>
          <td>${escapeHtml(job.status || '—')}</td>
        </tr>`);
    }
  }

  return `
    <div class="ai-repo-table-wrap">
      <table class="ai-repo-table">
        <thead>
          <tr>
            <th>Suite</th>
            <th>Framework</th>
            <th>LLM calls</th>
            <th>Heal rate</th>
            <th>Est. cost</th>
            <th>Time saved</th>
            <th>Source</th>
            <th>Links</th>
          </tr>
        </thead>
        <tbody>${rows}${jobRows.join('')}</tbody>
      </table>
    </div>`;
}

function renderAiTopLists(aiUsage) {
  const repos = aiUsage?.repos || {};
  const locators = {};
  const modules = {};
  for (const entry of Object.values(repos)) {
    for (const [k, v] of Object.entries(entry.topFailingLocators || {})) {
      locators[k] = (locators[k] || 0) + (Number(v) || 0);
    }
    for (const [k, v] of Object.entries(entry.topHealedModules || {})) {
      modules[k] = (modules[k] || 0) + (Number(v) || 0);
    }
  }
  const locList = topMapEntries(locators, 5);
  const modList = topMapEntries(modules, 5);
  if (!locList.length && !modList.length) return '';

  const locHtml = locList.map((r) => `<li><span>${escapeHtml(r.key)}</span><strong>${r.val}</strong></li>`).join('')
    || '<li class="triage-empty">No locator hotspots yet</li>';
  const modHtml = modList.map((r) => `<li><span>${escapeHtml(r.key)}</span><strong>${r.val}</strong></li>`).join('')
    || '<li class="triage-empty">No healed modules yet</li>';

  return `
    <div class="ai-top-grid">
      <div>
        <h3>Top failing locators (AI)</h3>
        <ul class="ai-top-list">${locHtml}</ul>
      </div>
      <div>
        <h3>Most healed modules</h3>
        <ul class="ai-top-list">${modHtml}</ul>
      </div>
    </div>`;
}

function renderAiImpact(summaries, aiImpact, aiUsage) {
  const data = aiImpact || AI_IMPACT_CACHE || {};
  const usage = aiUsage || AI_USAGE_CACHE || {};
  const signals = deriveAiSignals(summaries);
  const totals = usage.totals || {};
  const hasLive = (totals.reposReporting || 0) > 0;
  const hasEnabled = (totals.frameworksWithAiEnabled || 0) > 0;

  const caps = (data.capabilities || []).map((c) => `
    <article class="ai-cap">
      <h3>${escapeHtml(c.title)}</h3>
      <p>${escapeHtml(c.blurb)}</p>
    </article>`).join('');

  const usageMetrics = hasLive ? `
    ${renderAiUsageMetricCard(formatAiCount(totals.llmInvocations), 'LLM invocations', 'Symphony gateway calls this run', true)}
    ${renderAiUsageMetricCard(formatAiPct(totals.healSuccessRatePct), 'Heal success', `${formatAiCount(totals.healsSucceeded)} ok · ${formatAiCount(totals.healsFailed)} failed`, true)}
    ${renderAiUsageMetricCard(formatAiMoney(totals.estimatedCostUsd), 'Est. AI cost', 'Per-run framework estimate', true)}
    ${renderAiUsageMetricCard(formatAiDuration(totals.estimatedMinutesSaved), 'Time saved', 'Less manual locator triage', true)}
    ${renderAiUsageMetricCard(formatAiCount(totals.learnedLocatorsCount), 'Learned locators', 'Memory across runs', true)}
    ${renderAiUsageMetricCard(formatAiCount(totals.elementInteractions), 'UI interactions', 'Elements touched in framework', true)}
  ` : (data.metrics || []).map((m) => renderAiUsageMetricCard(m.value, m.label, m.note)).join('');

  const liveStats = `
    <div class="ai-live">
      ${renderAiUsageMetricCard(String(signals.healCandidates), 'UI-noise signals', 'Good healing candidates')}
      ${renderAiUsageMetricCard(String(signals.humanDecisions), 'Human decisions', 'Assertion / product mismatches')}
    </div>`;

  const helpBullets = buildAiUsageHelpBullets(totals, signals).map((b) => `<li>${escapeHtml(b)}</li>`).join('');
  const story = (data.story || []).map((line) => `<li>${escapeHtml(line)}</li>`).join('');
  const liveBullets = signals.bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join('');
  const updated = usage.updatedAt ? `<p class="ai-updated">AI metrics updated ${escapeHtml(formatRelativeTime(usage.updatedAt))}</p>` : '';
  const pendingNote = hasLive ? '' : (
    hasEnabled
      ? '<p class="ai-pending">AI is enabled in Allure for some suites — full metrics appear after the next CI run publishes <code>AI.*</code> environment keys or an <code>ai-usage.json</code> attachment.</p>'
      : '<p class="ai-pending">Waiting for Allure reports to publish AI metrics (<code>AI.*</code> environment keys or <code>ai-usage.json</code> attachment per framework).</p>'
  );

  return `
    <div class="panel__header ai-panel__header">
      <div>
        <p class="ai-kicker">Built with AI · framework usage</p>
        <h2>AI usage metrics</h2>
        <p>${escapeHtml(data.headline || 'How AI-assisted healing and guardrails reduce noise in automation runs.')}</p>
        ${updated}
      </div>
    </div>
    <div class="ai-panel__body">
      ${pendingNote}
      <section class="ai-section" aria-label="AI by framework">
        <h3 class="ai-section__title">By framework</h3>
        <p class="ai-section__sub">Which automation stack is using AI — pulled from each suite’s published Allure report.</p>
        ${renderAiFrameworkCards(usage)}
      </section>
      <section class="ai-section" aria-label="Live AI usage counters">
        <h3 class="ai-section__title">This run</h3>
        <div class="ai-metrics-row">${usageMetrics}${liveStats}</div>
      </section>
      <section class="ai-section" aria-label="Per suite AI usage">
        <h3 class="ai-section__title">By suite &amp; CI job</h3>
        <p class="ai-section__sub">Aggregated from Allure environment, attachments, and <code>ai-usage.json</code> when published.</p>
        ${renderAiRepoUsageRows(usage)}
      </section>
      ${renderAiTopLists(usage)}
      <section class="ai-section" aria-label="How AI helps automation">
        <h3 class="ai-section__title">How it helps automation</h3>
        <ul class="ai-help-list">${helpBullets}</ul>
      </section>
      <div class="ai-caps">${caps}</div>
      <div class="ai-story">
        <div>
          <h3>Why this matters</h3>
          <ul>${story}</ul>
        </div>
        <div>
          <h3>What today’s failures suggest</h3>
          <ul>${liveBullets}</ul>
        </div>
      </div>
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
  const list = items.slice(0, 50).map((f) => renderFailureItem(f)).join('');
  return `${categoryBar}<div class="failures-list-inner">${list}</div>`;
}

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function trendDirection(trend) {
  if (!trend || trend.length < 2) return { label: 'Steady', cls: 'flat' };
  const newest = trend[0].passPct;
  const older = trend[Math.min(trend.length - 1, 3)].passPct;
  const delta = Math.round((newest - older) * 10) / 10;
  if (delta >= 5) return { label: `Up ${delta} pts`, cls: 'up' };
  if (delta <= -5) return { label: `Down ${Math.abs(delta)} pts`, cls: 'down' };
  return { label: 'Steady', cls: 'flat' };
}

function parseDay(iso) {
  const [y, m, d] = String(iso).slice(0, 10).split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

function formatDay(date) {
  return date.toISOString().slice(0, 10);
}

function bucketKey(date, bucket) {
  const y = date.getUTCFullYear();
  const m = date.getUTCMonth();
  const d = date.getUTCDate();
  if (bucket === 'day') return formatDay(date);
  if (bucket === 'week') {
    // ISO week
    const tmp = new Date(Date.UTC(y, m, d));
    const dayNum = tmp.getUTCDay() || 7;
    tmp.setUTCDate(tmp.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
    const week = Math.ceil((((tmp - yearStart) / 86400000) + 1) / 7);
    return `${tmp.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
  }
  if (bucket === 'month') return `${y}-${String(m + 1).padStart(2, '0')}`;
  if (bucket === 'quarter') return `${y}-Q${Math.floor(m / 3) + 1}`;
  return `${y}`;
}

function weekStartFromKey(key) {
  const [ys, ws] = String(key).split('-W');
  const y = Number(ys);
  const w = Number(ws);
  if (!y || !w) return null;
  const jan4 = new Date(Date.UTC(y, 0, 4));
  const dayNum = jan4.getUTCDay() || 7;
  const monday = new Date(jan4);
  monday.setUTCDate(jan4.getUTCDate() - dayNum + 1 + (w - 1) * 7);
  return monday;
}

function bucketLabel(key, bucket) {
  if (bucket === 'day') {
    const dt = parseDay(key);
    return dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' });
  }
  if (bucket === 'week') {
    const monday = weekStartFromKey(key);
    if (!monday) return key;
    return monday.toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' });
  }
  if (bucket === 'month') {
    const [y, m] = key.split('-');
    return new Date(Date.UTC(+y, +m - 1, 1)).toLocaleDateString(undefined, { month: 'short', year: 'numeric', timeZone: 'UTC' });
  }
  if (bucket === 'quarter') {
    const [y, q] = key.split('-Q');
    return `Q${q} ${y}`;
  }
  return key;
}

function bucketLabelLong(key, bucket) {
  if (bucket === 'week') {
    const monday = weekStartFromKey(key);
    if (!monday) return key;
    const sunday = new Date(monday);
    sunday.setUTCDate(monday.getUTCDate() + 6);
    const a = monday.toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' });
    const b = sunday.toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' });
    return `Week of ${a} – ${b}`;
  }
  if (bucket === 'day') {
    return parseDay(key).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  }
  return bucketLabel(key, bucket);
}

function resolveTrendRange() {
  return TREND_RANGES.find((r) => r.id === TREND_RANGE) || TREND_RANGES.find((r) => r.id === 'weekly');
}

function collectTrendPoints(history, liveResults, opts = {}) {
  const includeEstimated = opts.includeEstimated ?? INCLUDE_ESTIMATED;
  let points = [...(history?.points || [])];
  if (!includeEstimated) {
    points = points.filter((p) => p.source !== 'estimated-backfill');
  }
  for (let i = 0; i < REPO_CONFIG.length; i++) {
    const cfg = REPO_CONFIG[i];
    const summary = liveResults?.[i];
    const counts = summary?.counts || computeCounts(summary);
    if (!counts.total) continue;
    const rates = computeRates(counts);
    const day = (summary?.finishedAt || new Date().toISOString()).slice(0, 10);
    points.push({
      date: day,
      suite: cfg.id,
      passPct: rates.passPct,
      total: counts.total,
      passed: counts.passed,
      failed: counts.review,
      source: 'live',
    });
  }
  return points;
}

function aggregateTrendSeries(points, range) {
  const now = new Date();
  const cutoff = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  cutoff.setUTCDate(cutoff.getUTCDate() - range.days);

  const filtered = points.filter((p) => {
    if (!p?.date || p.passPct == null) return false;
    const day = parseDay(p.date);
    return day >= cutoff;
  });

  const suites = REPO_CONFIG.map((c) => c.id);
  const buckets = new Map();

  for (const p of filtered) {
    const day = parseDay(p.date);
    const key = bucketKey(day, range.bucket);
    if (!buckets.has(key)) buckets.set(key, { key, order: day.getTime(), suites: {}, estimatedOnly: true, hasEstimated: false, hasReal: false });
    const slot = buckets.get(key);
    const isEst = p.source === 'estimated-backfill';
    if (isEst) slot.hasEstimated = true;
    else slot.hasReal = true;
    if (slot.hasReal) slot.estimatedOnly = false;
    const weight = Math.max(1, p.total || 1);
    const cur = slot.suites[p.suite] || { sum: 0, weight: 0, passed: 0, total: 0, estimated: 0 };
    cur.sum += p.passPct * weight;
    cur.weight += weight;
    cur.passed += p.passed || 0;
    cur.total += p.total || 0;
    if (isEst) cur.estimated += weight;
    slot.suites[p.suite] = cur;
  }

  const keys = [...buckets.values()].sort((a, b) => a.order - b.order);
  const labels = keys.map((b) => bucketLabel(b.key, range.bucket));
  const labelsLong = keys.map((b) => bucketLabelLong(b.key, range.bucket));
  const keysList = keys.map((b) => b.key);
  const series = {};
  const totals = {};
  for (const suite of suites) {
    series[suite] = keys.map((b) => {
      const cur = b.suites[suite];
      if (!cur?.weight) return null;
      return Math.round((cur.sum / cur.weight) * 10) / 10;
    });
    totals[suite] = keys.map((b) => {
      const cur = b.suites[suite];
      return cur ? { passed: cur.passed, total: cur.total } : null;
    });
  }

  series.overall = keys.map((b) => {
    let sum = 0;
    let weight = 0;
    for (const suite of suites) {
      const cur = b.suites[suite];
      if (!cur?.weight) continue;
      sum += cur.sum;
      weight += cur.weight;
    }
    return weight ? Math.round((sum / weight) * 10) / 10 : null;
  });

  totals.overall = keys.map((b) => {
    let passed = 0;
    let total = 0;
    for (const suite of suites) {
      const cur = b.suites[suite];
      if (!cur) continue;
      passed += cur.passed || 0;
      total += cur.total || 0;
    }
    return total ? { passed, total } : null;
  });

  const estimated = filtered.some((p) => p.source === 'estimated-backfill');
  const estimatedFlags = keys.map((b) => !!b.estimatedOnly);
  const mixedFlags = keys.map((b) => !!(b.hasEstimated && b.hasReal));
  return {
    labels,
    labelsLong,
    keys: keysList,
    series,
    totals,
    estimated,
    estimatedFlags,
    mixedFlags,
    pointCount: filtered.length,
    estimatedPointCount: filtered.filter((p) => p.source === 'estimated-backfill').length,
    bucketCount: keys.length,
    range,
    includeEstimated: INCLUDE_ESTIMATED,
  };
}

function seriesStats(values) {
  const nums = values.filter((v) => v != null);
  if (!nums.length) return null;
  const latest = [...values].reverse().find((v) => v != null);
  const first = values.find((v) => v != null);
  const avg = Math.round((nums.reduce((a, b) => a + b, 0) / nums.length) * 10) / 10;
  const best = Math.max(...nums);
  const worst = Math.min(...nums);
  const delta = first == null || latest == null ? 0 : Math.round((latest - first) * 10) / 10;
  let dir = { label: 'Steady', cls: 'flat' };
  if (delta >= 3) dir = { label: `Up ${delta} pts`, cls: 'up' };
  else if (delta <= -3) dir = { label: `Down ${Math.abs(delta)} pts`, cls: 'down' };
  return { latest, first, avg, best, worst, delta, dir, samples: nums.length };
}

function buildTrendPath(values, width, height, padX, padY, yMin = 0, yMax = 100) {
  const usableW = width - padX * 2;
  const usableH = height - padY * 2;
  const span = Math.max(1, yMax - yMin);
  const pts = [];
  for (let i = 0; i < values.length; i++) {
    if (values[i] == null) continue;
    const x = padX + (values.length === 1 ? usableW / 2 : (i / (values.length - 1)) * usableW);
    const y = padY + (1 - (values[i] - yMin) / span) * usableH;
    pts.push({ x, y, v: values[i], i });
  }
  if (!pts.length) return { d: '', area: '', pts: [] };

  let d = `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] || p2;
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
  }

  const baseY = padY + usableH;
  const area = `${d} L${pts[pts.length - 1].x.toFixed(1)},${baseY.toFixed(1)} L${pts[0].x.toFixed(1)},${baseY.toFixed(1)} Z`;
  return { d, area, pts };
}

function trendLineDefs() {
  return [
    { id: 'overall', label: 'Overall', color: '#f8fafc', width: 3.2, area: true },
    ...REPO_CONFIG.map((c) => ({
      id: c.id,
      label: REPO_DISPLAY[c.id].label,
      color: REPO_DISPLAY[c.id].color,
      width: 2.2,
      area: false,
    })),
  ];
}

function renderTrendChartSvg(agg) {
  const width = 1120;
  const height = 230;
  const padX = 44;
  const padY = 26;
  const yMin = 0;
  const yMax = 100;
  const lines = trendLineDefs();
  const usableH = height - padY * 2;

  const yTicks = [0, 25, 50, 70, 85, 100];
  const grid = yTicks.map((pct) => {
    const y = padY + (1 - (pct - yMin) / (yMax - yMin)) * usableH;
    const guide = pct === 70 || pct === 85;
    return `
      <line x1="${padX}" y1="${y}" x2="${width - padX}" y2="${y}" class="chart-grid ${guide ? 'chart-grid--guide' : ''}" />
      <text x="${padX - 8}" y="${y + 3}" class="chart-axis">${pct}%</text>`;
  }).join('');

  const guideNotes = `
    <text x="${width - padX}" y="${padY + (1 - (85 - yMin) / (yMax - yMin)) * usableH - 5}" class="chart-guide-label" text-anchor="end">High ≥ 85%</text>
    <text x="${width - padX}" y="${padY + (1 - (70 - yMin) / (yMax - yMin)) * usableH - 5}" class="chart-guide-label chart-guide-label--watch" text-anchor="end">Watch ≥ 70%</text>`;

  const labelStep = Math.max(1, Math.ceil(agg.labels.length / 6));
  const xLabels = agg.labels.map((label, i) => {
    if (i % labelStep !== 0 && i !== agg.labels.length - 1) return '';
    const x = padX + (agg.labels.length === 1 ? (width - padX * 2) / 2 : (i / (agg.labels.length - 1)) * (width - padX * 2));
    return `<text x="${x}" y="${height - 8}" class="chart-xlabel">${escapeHtml(label)}</text>`;
  }).join('');

  const endMeta = lines.map((line) => {
    const { pts } = buildTrendPath(agg.series[line.id] || [], width, height, padX, padY, yMin, yMax);
    const last = pts[pts.length - 1];
    return last ? { id: line.id, color: line.color, x: last.x, y: last.y, v: last.v } : null;
  }).filter(Boolean).sort((a, b) => a.y - b.y);

  for (let i = 1; i < endMeta.length; i++) {
    const gap = endMeta[i].y - endMeta[i - 1].y;
    if (gap < 12) endMeta[i].y = endMeta[i - 1].y + 12;
  }
  const endY = Object.fromEntries(endMeta.map((e) => [e.id, e.y]));

  const paths = lines.map((line, seriesIndex) => {
    const { d, area, pts } = buildTrendPath(agg.series[line.id] || [], width, height, padX, padY, yMin, yMax);
    if (!d) return '';
    const areaEl = line.area
      ? `<path d="${area}" class="chart-area" fill="url(#overallGlow)" opacity="0.35" />`
      : '';
    const dots = pts.map((p, di) => {
      const isLatest = di === pts.length - 1;
      const isEst = !!agg.estimatedFlags?.[p.i];
      const isMixed = !!agg.mixedFlags?.[p.i];
      const cls = [
        'chart-dot',
        isLatest ? 'chart-dot--live' : '',
        isEst ? 'chart-dot--estimated' : '',
        isMixed ? 'chart-dot--mixed' : '',
      ].filter(Boolean).join(' ');
      return `
      <circle class="${cls}" data-line="${line.id}" data-idx="${p.i}" style="--dot-delay:${(0.45 + di * 0.04).toFixed(2)}s" cx="${p.x}" cy="${p.y}" r="${isLatest ? 4.5 : 3.2}" fill="${isEst ? 'transparent' : line.color}" stroke="${line.color}" stroke-width="${isEst ? 1.8 : 1.4}" stroke-dasharray="${isEst ? '2 2' : 'none'}">
        <title>${escapeHtml(line.label)}: ${formatPct(p.v)} · ${escapeHtml(agg.labelsLong?.[p.i] || agg.labels[p.i] || '')}${isEst ? ' · estimated' : ''}</title>
      </circle>`;
    }).join('');
    const last = pts[pts.length - 1];
    const labelY = last ? (endY[line.id] ?? last.y) : null;
    const endLabel = last
      ? `<text class="chart-end-label" x="${Math.min(width - 6, last.x + 8)}" y="${labelY + 3}" fill="${line.color}">${escapeHtml(line.label)} ${formatPct(last.v)}</text>`
      : '';
    const liveRing = last
      ? `<circle class="chart-live-ring" cx="${last.x}" cy="${last.y}" r="7" fill="none" stroke="${line.color}" />`
      : '';
    return `
      <g class="chart-series" data-series="${line.id}" style="--series-delay:${(seriesIndex * 0.12).toFixed(2)}s">
        ${areaEl}
        <path class="chart-line ${line.id === 'overall' ? 'chart-line--overall' : ''} ${agg.estimated ? 'chart-line--has-estimated' : ''}" d="${d}" fill="none" stroke="${line.color}" stroke-width="${line.width}" stroke-linecap="round" stroke-linejoin="round" />
        ${dots}
        ${liveRing}
        ${endLabel}
      </g>`;
  }).join('');

  const hitZones = (agg.labels || []).map((_, i) => {
    const x = padX + (agg.labels.length === 1 ? (width - padX * 2) / 2 : (i / (agg.labels.length - 1)) * (width - padX * 2));
    const half = agg.labels.length <= 1 ? (width - padX * 2) / 2 : ((width - padX * 2) / (agg.labels.length - 1)) / 2;
    return `<rect class="chart-hit" data-idx="${i}" x="${x - half}" y="${padY}" width="${Math.max(12, half * 2)}" height="${usableH}" fill="transparent" />`;
  }).join('');

  const payloadRaw = JSON.stringify({
    labels: agg.labels,
    labelsLong: agg.labelsLong,
    series: agg.series,
    totals: agg.totals,
    lines: lines.map((l) => ({ id: l.id, label: l.label, color: l.color })),
    chartBox: { padX, padY, width, height, usableW: width - padX * 2, usableH },
  });
  const payloadAttr = escapeHtml(payloadRaw);

  const legend = lines.map((line) => `
    <button type="button" class="chart-legend__item is-active" data-series-toggle="${line.id}" aria-pressed="true">
      <i style="background:${line.color}"></i>${escapeHtml(line.label)}
    </button>
  `).join('');

  return `
    <div class="chart-toolbar">
      <div class="chart-legend">${legend}</div>
      <span class="chart-live-badge" aria-live="polite"><span class="chart-live-badge__dot"></span> Live</span>
    </div>
    <div class="chart-wrap" data-trend-chart data-trend-json="${payloadAttr}">
      <div class="chart-tooltip" id="trend-tooltip" hidden></div>
      <div class="chart-scan" aria-hidden="true"></div>
      <svg class="trend-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Automation pass-rate trend">
        <defs>
          <linearGradient id="overallGlow" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#94a3b8" stop-opacity="0.45" />
            <stop offset="100%" stop-color="#94a3b8" stop-opacity="0" />
          </linearGradient>
        </defs>
        ${grid}
        ${guideNotes}
        ${paths}
        <line class="chart-crosshair" id="trend-crosshair" x1="0" y1="${padY}" x2="0" y2="${padY + usableH}" hidden />
        ${xLabels}
        ${hitZones}
      </svg>
    </div>`;
}

function formatPct(v) {
  if (v == null || Number.isNaN(v)) return '—';
  return `${Number(v).toFixed(Number(v) % 1 ? 1 : 0)}%`;
}

function renderTrendValueTable(agg) {
  const lines = trendLineDefs();
  const rows = agg.labels.map((label, i) => {
    const cells = lines.map((line) => {
      const v = agg.series[line.id]?.[i];
      const t = agg.totals?.[line.id]?.[i];
      const detail = t?.total ? `${t.passed}/${t.total}` : '';
      return `<td>
        <strong style="color:${line.color}">${formatPct(v)}</strong>
        ${detail ? `<span class="trend-table__sub">${escapeHtml(detail)}</span>` : ''}
      </td>`;
    }).join('');
    return `<tr>
      <th scope="row">${escapeHtml(agg.labelsLong?.[i] || label)}</th>
      ${cells}
    </tr>`;
  }).join('');

  const head = lines.map((line) => `<th scope="col">${escapeHtml(line.label)}</th>`).join('');
  return `
    <div class="trend-table-wrap">
      <table class="trend-table">
        <thead>
          <tr>
            <th scope="col">Period</th>
            ${head}
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function renderTrendSummaryStrip(agg) {
  const overall = seriesStats(agg.series.overall || []);
  if (!overall) return '';
  return `
    <div class="trend-summary">
      <div class="trend-summary__item">
        <span class="trend-summary__label">Latest overall</span>
        <strong>${formatPct(overall.latest)}</strong>
      </div>
      <div class="trend-summary__item">
        <span class="trend-summary__label">Period average</span>
        <strong>${formatPct(overall.avg)}</strong>
      </div>
      <div class="trend-summary__item">
        <span class="trend-summary__label">Best / worst</span>
        <strong>${formatPct(overall.best)} · ${formatPct(overall.worst)}</strong>
      </div>
      <div class="trend-summary__item">
        <span class="trend-summary__label">Change in range</span>
        <strong class="trend-dir trend-dir--${overall.dir.cls}">${escapeHtml(overall.dir.label)}</strong>
      </div>
    </div>`;
}

function renderTrendsPanel(summaries) {
  const range = resolveTrendRange();
  const points = collectTrendPoints(TREND_HISTORY, summaries);
  const agg = aggregateTrendSeries(points, range);
  const hasData = agg.labels.length > 0;

  const rangeBtns = TREND_RANGES.map((r) => `
    <button type="button" class="range-btn ${r.id === TREND_RANGE ? 'is-active' : ''}" data-trend-range="${r.id}" aria-pressed="${r.id === TREND_RANGE}">
      ${escapeHtml(r.label)}
    </button>`).join('');

  const mini = trendLineDefs().filter((l) => l.id !== 'overall').map((line) => {
    const stats = seriesStats(agg.series[line.id] || []);
    const cfg = REPO_CONFIG.find((c) => c.id === line.id);
    if (!stats) {
      return `
        <article class="trend-card trend-card--${line.id}">
          <div class="trend-card__head">
            <h3>${cfg?.icon || ''} ${escapeHtml(line.label)}</h3>
            <span class="trend-dir trend-dir--flat">No data</span>
          </div>
          <p class="trend-card__now">No points in this range</p>
        </article>`;
    }
    return `
      <article class="trend-card trend-card--${line.id}">
        <div class="trend-card__head">
          <h3>${cfg?.icon || ''} ${escapeHtml(line.label)}</h3>
          <span class="trend-dir trend-dir--${stats.dir.cls}">${escapeHtml(stats.dir.label)}</span>
        </div>
        <p class="trend-card__now"><strong>${formatPct(stats.latest)}</strong> latest · avg ${formatPct(stats.avg)}</p>
        <p class="trend-card__meta">Best ${formatPct(stats.best)} · Worst ${formatPct(stats.worst)} · ${stats.samples} ${range.bucket}${stats.samples === 1 ? '' : 's'}</p>
      </article>`;
  }).join('');

  const estToggle = `
    <label class="est-toggle">
      <input type="checkbox" id="include-estimated" ${INCLUDE_ESTIMATED ? 'checked' : ''} />
      Show estimated backfill
    </label>`;

  return `
    <div class="panel__header trend-panel__header">
      <div>
        <h2>Automation trends</h2>
        <p>Pass rate over time — real CI points by default. Hover for exact values.</p>
      </div>
      <div class="trend-panel__controls">
        <div class="range-toggle" role="group" aria-label="Trend range">${rangeBtns}</div>
        ${estToggle}
      </div>
    </div>
    ${hasData ? renderTrendSummaryStrip(agg) : ''}
    ${hasData ? renderTrendChartSvg(agg) : '<p class="loading-cards">No trend history yet — it grows as CI publishes runs.</p>'}
    <p class="chart-footnote">
      Showing ${escapeHtml(range.label.toLowerCase())} buckets
      · ${agg.bucketCount} periods · ${agg.pointCount} raw points
      ${INCLUDE_ESTIMATED
        ? ` · estimated backfill visible (${agg.estimatedPointCount || 0} points) — dashed markers`
        : ' · estimated backfill hidden'}
    </p>
    ${hasData ? renderTrendValueTable(agg) : ''}
    <div class="trend-grid trend-grid--mini">${mini}</div>`;
}

function setTrendRange(rangeId) {
  if (!TREND_RANGES.some((r) => r.id === rangeId)) return;
  TREND_RANGE = rangeId;
  try { localStorage.setItem('dashboard.trendRange', rangeId); } catch { /* ignore */ }
  if (CURRENT_RESULTS.length) {
    const trendsEl = document.getElementById('trends-panel');
    if (trendsEl) {
      trendsEl.innerHTML = renderTrendsPanel(CURRENT_RESULTS);
      wireTrendChart();
    }
  }
  const url = new URL(window.location.href);
  if (rangeId === 'weekly') url.searchParams.delete('range');
  else url.searchParams.set('range', rangeId);
  window.history.replaceState({}, '', url);
}

function animateTrendChart(wrap) {
  const svg = wrap?.querySelector('.trend-chart');
  if (!svg) return;

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  svg.classList.remove('is-drawn', 'is-animating', 'is-live');
  wrap.classList.remove('is-live');
  void svg.getBoundingClientRect();
  svg.classList.add('is-animating');

  const paths = [...svg.querySelectorAll('.chart-line')];
  paths.forEach((path) => {
    path.style.transition = 'none';
    path.style.strokeDasharray = '';
    path.style.strokeDashoffset = '';
  });

  if (reduce) {
    svg.classList.add('is-drawn', 'is-live');
    wrap.classList.add('is-live');
    return;
  }

  requestAnimationFrame(() => {
    paths.forEach((path, i) => {
      let len = 0;
      try { len = path.getTotalLength(); } catch { len = 0; }
      if (!len) {
        path.style.opacity = '1';
        return;
      }
      const delay = i * 0.1;
      path.style.strokeDasharray = `${len}`;
      path.style.strokeDashoffset = `${len}`;
      path.style.opacity = '1';
      void path.getBoundingClientRect();
      path.style.transition = `stroke-dashoffset 0.95s cubic-bezier(0.22, 1, 0.36, 1) ${delay}s`;
      path.style.strokeDashoffset = '0';
    });
    svg.classList.add('is-drawn');
    window.setTimeout(() => {
      // Keep dash pattern for a subtle flowing “live stream” on overall
      const overall = svg.querySelector('.chart-line--overall');
      if (overall) {
        let len = 0;
        try { len = overall.getTotalLength(); } catch { len = 0; }
        if (len) {
          overall.style.transition = 'none';
          overall.style.strokeDasharray = `${Math.max(18, len * 0.08)} ${Math.max(10, len * 0.04)}`;
          overall.style.strokeDashoffset = '0';
          overall.classList.add('is-streaming');
        }
      }
      svg.classList.add('is-live');
      wrap.classList.add('is-live');
      startTrendLiveSweep(wrap);
    }, 1200);
  });
}

let TREND_LIVE_TIMER = null;

function startTrendLiveSweep(wrap) {
  if (TREND_LIVE_TIMER) {
    clearInterval(TREND_LIVE_TIMER);
    TREND_LIVE_TIMER = null;
  }
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const scan = wrap.querySelector('.chart-scan');
  const badge = document.querySelector('.chart-live-badge');
  if (!scan) return;

  let tick = 0;
  TREND_LIVE_TIMER = window.setInterval(() => {
    if (!document.body.contains(wrap)) {
      clearInterval(TREND_LIVE_TIMER);
      TREND_LIVE_TIMER = null;
      return;
    }
    tick += 1;
    // Restart CSS sweep by toggling class
    scan.classList.remove('is-sweeping');
    void scan.getBoundingClientRect();
    scan.classList.add('is-sweeping');

    // Pulse latest values in summary so it feels “updating”
    document.querySelectorAll('.trend-summary__item strong').forEach((el, i) => {
      el.classList.remove('is-tick');
      void el.getBoundingClientRect();
      window.setTimeout(() => el.classList.add('is-tick'), i * 40);
    });

    if (badge) {
      badge.classList.remove('is-blink');
      void badge.getBoundingClientRect();
      badge.classList.add('is-blink');
    }

    // Softly re-pulse live rings
    wrap.querySelectorAll('.chart-live-ring').forEach((ring, i) => {
      ring.classList.remove('is-ping');
      void ring.getBoundingClientRect();
      window.setTimeout(() => ring.classList.add('is-ping'), i * 60);
    });
  }, 4200);

  // kick first sweep shortly after live mode starts
  window.setTimeout(() => scan.classList.add('is-sweeping'), 200);
}

function wireTrendChart() {
  const wrap = document.querySelector('[data-trend-chart]');
  if (!wrap) return;
  const tooltip = wrap.querySelector('#trend-tooltip');
  const crosshair = wrap.querySelector('#trend-crosshair');
  if (!tooltip) return;

  let data;
  try { data = JSON.parse(wrap.getAttribute('data-trend-json') || '{}'); } catch { return; }

  animateTrendChart(wrap);

  const panel = wrap.closest('.panel') || document.getElementById('trends-panel');
  panel?.querySelectorAll('.chart-legend [data-series-toggle]').forEach((btn) => {
    if (btn.dataset.wired) return;
    btn.dataset.wired = '1';
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-series-toggle');
      const series = document.querySelector(`.chart-series[data-series="${id}"]`);
      const on = !btn.classList.contains('is-active');
      btn.classList.toggle('is-active', on);
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      if (series) {
        series.style.display = on ? '' : 'none';
        if (on) {
          series.classList.remove('is-revealed');
          void series.getBoundingClientRect();
          series.classList.add('is-revealed');
          const path = series.querySelector('.chart-line');
          if (path && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            let len = 0;
            try { len = path.getTotalLength(); } catch { /* ignore */ }
            if (len) {
              path.style.transition = 'none';
              path.style.strokeDasharray = `${len}`;
              path.style.strokeDashoffset = `${len}`;
              void path.getBoundingClientRect();
              path.style.transition = 'stroke-dashoffset 0.85s cubic-bezier(0.22, 1, 0.36, 1)';
              path.style.strokeDashoffset = '0';
            }
          }
        }
      }
    });
  });

  const showIdx = (idx, clientX, clientY) => {
    if (idx == null || idx < 0) return;
    const lines = (data.lines || []).filter((l) => {
      const el = document.querySelector(`.chart-series[data-series="${l.id}"]`);
      return !el || el.style.display !== 'none';
    });
    const rows = lines.map((l) => {
      const v = data.series?.[l.id]?.[idx];
      const t = data.totals?.[l.id]?.[idx];
      const detail = t?.total ? ` (${t.passed}/${t.total})` : '';
      return `<div class="chart-tooltip__row"><span><i style="background:${l.color}"></i>${escapeHtml(l.label)}</span><strong>${formatPct(v)}${escapeHtml(detail)}</strong></div>`;
    }).join('');
    tooltip.innerHTML = `
      <div class="chart-tooltip__title">${escapeHtml(data.labelsLong?.[idx] || data.labels?.[idx] || '')}</div>
      ${rows}`;
    tooltip.hidden = false;
    const rect = wrap.getBoundingClientRect();
    const left = Math.min(rect.width - 220, Math.max(8, clientX - rect.left + 12));
    const top = Math.min(rect.height - 20, Math.max(8, clientY - rect.top - 12));
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;

    const hit = wrap.querySelector(`.chart-hit[data-idx="${idx}"]`);
    if (crosshair && hit) {
      const x = Number(hit.getAttribute('x')) + Number(hit.getAttribute('width')) / 2;
      crosshair.setAttribute('x1', x);
      crosshair.setAttribute('x2', x);
      crosshair.removeAttribute('hidden');
    }
  };

  const hideTip = () => {
    tooltip.hidden = true;
    if (crosshair) crosshair.setAttribute('hidden', '');
  };

  wrap.querySelectorAll('.chart-hit').forEach((hit) => {
    hit.addEventListener('mousemove', (e) => {
      showIdx(Number(hit.getAttribute('data-idx')), e.clientX, e.clientY);
    });
    hit.addEventListener('mouseleave', hideTip);
  });
}

async function loadTrendHistory() {
  const bundled = window.DASHBOARD_SNAPSHOTS?.snapshots?.['automation-trend'];
  const live = await fetchJson('data/history/automation-trend.json');
  TREND_HISTORY = live || bundled || { points: [] };
  return TREND_HISTORY;
}

function buildShareSnapshot(summaries) {
  const health = computeHealthScore(summaries);
  const areas = health.areas || buildBusinessAreas(summaries);
  const lines = [];
  lines.push('Store Intell QA — Quality snapshot');
  lines.push(`Release confidence: ${health.label}${health.score != null ? ` (${health.score}/100)` : ''}`);
  lines.push(health.sentence);
  lines.push('');
  lines.push(`Checks: ${health.totalPassed} passed · ${health.totalFailed} need review · ${health.totalTests} total (${health.passPct}% pass)`);
  lines.push('');
  lines.push('Release confidence by project:');
  for (const s of health.suiteScores || []) {
    lines.push(`- ${REPO_DISPLAY[s.id]?.label || s.title}: ${s.label}${s.score != null ? ` (${s.score}/100, ${s.passPct}% pass)` : ' (no data)'}`);
  }
  const triage = summarizeIssueBuckets(summaries);
  lines.push('');
  lines.push(`Issue split: ${triage.counts.defect} likely defects · ${triage.counts.flaky} flaky · ${triage.counts.environment} environment`);
  lines.push('');
  lines.push('Product areas:');
  for (const area of areas) {
    const mark = area.status === 'healthy' ? 'OK' : area.status === 'watch' ? 'WATCH' : 'RISK';
    lines.push(`- [${mark}] ${area.label}`);
  }
  lines.push('');
  lines.push('Suites:');
  for (let i = 0; i < REPO_CONFIG.length; i++) {
    const cfg = REPO_CONFIG[i];
    const s = summaries[i];
    const counts = s?.counts || computeCounts(s);
    const rates = computeRates(counts);
    if (!counts.total) {
      lines.push(`- ${cfg.title}: no data`);
      continue;
    }
    lines.push(`- ${cfg.title}: ${rates.passPct}% pass (${counts.passed}/${counts.total}, ${counts.review} need review)`);
  }
  const top = collectFailures(summaries).slice(0, 5);
  if (top.length) {
    lines.push('');
    lines.push('Top attention items:');
    for (const f of top) {
      const exp = explainFailure(f);
      lines.push(`- ${friendlyFailureTitle(f)} (${REPO_DISPLAY[f.repo]?.label || f.repo}): ${exp.meaning}`);
    }
  }
  lines.push('');
  lines.push(`Generated ${new Date().toLocaleString()} · Dashboard v${DASHBOARD_VERSION}`);
  return lines.join('\n');
}

function resolveInitialTrendRange() {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = (params.get('range') || '').toLowerCase();
  if (TREND_RANGES.some((r) => r.id === fromUrl)) return fromUrl;
  try {
    const saved = localStorage.getItem('dashboard.trendRange');
    if (TREND_RANGES.some((r) => r.id === saved)) return saved;
  } catch { /* ignore */ }
  return 'weekly';
}

function resolveInitialTab() {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = (params.get('tab') || '').toLowerCase();
  if (DASHBOARD_TABS.includes(fromUrl)) return fromUrl;
  try {
    const saved = localStorage.getItem('dashboard.activeTab');
    if (DASHBOARD_TABS.includes(saved)) return saved;
  } catch { /* ignore */ }
  return 'overview';
}

function setActiveTab(tab, { persist = true, updateUrl = true } = {}) {
  if (!DASHBOARD_TABS.includes(tab)) tab = 'overview';
  ACTIVE_TAB = tab;

  document.querySelectorAll('.tab-btn').forEach((btn) => {
    const selected = btn.getAttribute('data-tab') === tab;
    btn.setAttribute('aria-selected', selected ? 'true' : 'false');
    btn.classList.toggle('tab-btn--active', selected);
  });

  document.querySelectorAll('.tab-panel').forEach((panel) => {
    panel.hidden = panel.id !== `panel-${tab}`;
  });

  if (persist) {
    try { localStorage.setItem('dashboard.activeTab', tab); } catch { /* ignore */ }
  }
  if (updateUrl) {
    const url = new URL(window.location.href);
    if (tab === 'overview') url.searchParams.delete('tab');
    else url.searchParams.set('tab', tab);
    window.history.replaceState({}, '', url);
  }
}

function wireTabs() {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => setActiveTab(btn.getAttribute('data-tab')));
  });
}

function renderDashboard(results, aiImpact, aiUsage) {
  if (aiImpact) AI_IMPACT_CACHE = aiImpact;
  if (aiUsage) AI_USAGE_CACHE = aiUsage;
  CURRENT_RESULTS = results || [];

  const banner = document.getElementById('overall-banner');
  if (banner) banner.innerHTML = renderOverallBanner(results);

  const triageEl = document.getElementById('issue-triage');
  if (triageEl) triageEl.innerHTML = renderIssueTriage(results);

  const areasEl = document.getElementById('business-areas');
  if (areasEl) areasEl.innerHTML = renderBusinessAreas(results);

  const trendsEl = document.getElementById('trends-panel');
  if (trendsEl) {
    trendsEl.innerHTML = renderTrendsPanel(results);
    wireTrendChart();
  }

  const aiEl = document.getElementById('ai-impact');
  if (aiEl) aiEl.innerHTML = renderAiImpact(results, AI_IMPACT_CACHE, AI_USAGE_CACHE);

  const cards = document.getElementById('repo-cards');
  if (cards) cards.innerHTML = REPO_CONFIG.map((cfg, i) => renderCard(cfg, results[i])).join('');

  const failuresHtml = renderFailures(results);
  const failuresList = document.getElementById('failures-list');
  const failuresEmpty = document.getElementById('failures-empty');
  if (failuresList) failuresList.innerHTML = failuresHtml || '';
  if (failuresEmpty) failuresEmpty.hidden = !!failuresHtml;
}

async function loadAiImpact() {
  const bundled = window.DASHBOARD_SNAPSHOTS?.snapshots?.['ai-impact'];
  const live = await fetchJson('data/ai-impact.json');
  return live || bundled || null;
}

async function loadAiUsage() {
  const bundled = window.DASHBOARD_SNAPSHOTS?.snapshots?.['ai-usage'];
  const live = await fetchJson('data/ai-usage.json');
  return live || bundled || null;
}

/* ─── Dashboard-only AI chatbot (grounded in live snapshot) ─── */

const CHAT_OFFTOPIC = [
  'weather', 'joke', 'recipe', 'stock', 'bitcoin', 'politics', 'movie', 'sport',
  'write code', 'python script', 'javascript function', 'homework', 'poem',
];

function matchSuiteId(text) {
  const q = text.toLowerCase();
  if (/\bios\b|iphone|apple/.test(q)) return 'mobile-ios';
  if (/android/.test(q)) return 'mobile-android';
  if (/\bapi\b|rest|backend|contract/.test(q)) return 'api';
  if (/\bweb\b|selenium|ui dashboard|frontend/.test(q)) return 'web';
  return null;
}

function isDashboardRelated(question) {
  const q = question.toLowerCase().trim();
  if (!q) return false;
  if (CHAT_OFFTOPIC.some((w) => q.includes(w)) && !/dashboard|test|fail|pass|flaky|defect|release|suite|allure|trend|automation|qa/.test(q)) {
    return false;
  }
  const topical = [
    'release', 'confidence', 'pass', 'fail', 'flaky', 'defect', 'environment', 'timeout',
    'suite', 'web', 'ios', 'android', 'api', 'trend', 'weekly', 'monthly', 'daily',
    'approval', 'login', 'scan', 'task', 'allure', 'ci', 'quarantine', 'heal',
    'dashboard', 'automation', 'quality', 'risk', 'watch', 'attention', 'product area',
    'what', 'why', 'how many', 'status', 'health', 'summary', 'snapshot', 'ready',
  ];
  if (topical.some((t) => q.includes(t))) return true;
  // Allow short follow-ups / suite names
  if (matchSuiteId(q)) return true;
  // Search failure titles
  const failures = collectFailures(CURRENT_RESULTS);
  return failures.some((f) => {
    const blob = `${f.name || ''} ${f.feature || ''}`.toLowerCase();
    return q.split(/\s+/).filter((w) => w.length > 3).some((w) => blob.includes(w));
  });
}

function buildChatKnowledge() {
  const health = computeHealthScore(CURRENT_RESULTS);
  const triage = summarizeIssueBuckets(CURRENT_RESULTS);
  const areas = buildBusinessAreas(CURRENT_RESULTS);
  const range = resolveTrendRange();
  const points = collectTrendPoints(TREND_HISTORY, CURRENT_RESULTS);
  const agg = aggregateTrendSeries(points, range);
  const suites = (health.suiteScores || []).map((s) => ({
    id: s.id,
    label: REPO_DISPLAY[s.id]?.label || s.title,
    score: s.score,
    level: s.label,
    passPct: s.passPct,
    total: s.counts?.total || 0,
    review: s.counts?.review || 0,
    sentence: s.sentence,
  }));
  const failures = collectFailures(CURRENT_RESULTS).slice(0, 12).map((f) => {
    const exp = explainFailure(f);
    return {
      title: friendlyFailureTitle(f),
      suite: REPO_DISPLAY[f.repo]?.label || f.repo,
      bucket: exp.bucketLabel,
      meaning: exp.meaning,
      nextStep: exp.nextStep,
    };
  });
  return {
    overall: {
      score: health.score,
      label: health.label,
      passPct: health.passPct,
      sentence: health.sentence,
      totalTests: health.totalTests,
      totalPassed: health.totalPassed,
      totalFailed: health.totalFailed,
    },
    suites,
    triage: triage.counts,
    triageSamples: triage.samples,
    areas: areas.map((a) => ({
      label: a.label,
      status: a.status,
      sample: a.sample?.[0] ? friendlyFailureTitle(a.sample[0]) : null,
    })),
    trend: {
      range: range.label,
      labels: agg.labels.slice(-6),
      overall: (agg.series.overall || []).slice(-6),
      estimated: agg.estimated,
    },
    failures,
    releaseGate: (() => {
      try {
        const g = computeReleaseGate(CURRENT_RESULTS);
        return { verdict: g.verdict, label: g.label, blurb: g.blurb, blockers: g.blockers };
      } catch { return null; }
    })(),
    weekOverWeek: (() => {
      try {
        const w = computeWeekOverWeek(CURRENT_RESULTS);
        return w.available ? { label: w.label, thisWeek: w.thisWeek, lastWeek: w.lastWeek, delta: w.delta, suites: w.suites } : null;
      } catch { return null; }
    })(),
    ai: {
      headline: AI_IMPACT_CACHE?.headline || null,
    },
  };
}

function answerFromKnowledge(question) {
  const q = question.toLowerCase().trim();
  const k = buildChatKnowledge();
  const suiteId = matchSuiteId(q);
  const suite = suiteId ? k.suites.find((s) => s.id === suiteId) : null;

  if (/^(hi|hello|hey|help)\b/.test(q) || q === 'help') {
    return [
      'I only answer questions about this automation dashboard.',
      'Try asking:',
      '• What is overall release confidence?',
      '• How is Web / iOS / Android / API doing?',
      '• How many defects vs flaky vs environment issues?',
      '• What needs attention on Approvals?',
      '• What does the weekly trend show?',
    ].join('\n');
  }

  if (!isDashboardRelated(question)) {
    return 'I can only answer questions about this dashboard’s automation data (release confidence, suites, product areas, environment/flaky/defects, trends, and failures). Please ask something related to QA quality on this page.';
  }

  if (/overall|release confidence|are we ready|release ready|health score|summary|ship|hold|gate/.test(q) && !suiteId) {
    const gate = computeReleaseGate(CURRENT_RESULTS);
    const wow = computeWeekOverWeek(CURRENT_RESULTS);
    return [
      `Release gate: **${gate.label}** — ${gate.blurb}`,
      gate.blockers.length
        ? 'Top blockers: ' + gate.blockers.map((b, i) => `${i + 1}) ${b.title}`).join('; ')
        : 'No top blockers mapped.',
      `Overall release confidence is **${k.overall.label}** (${k.overall.score}/100, ${k.overall.passPct}% pass).`,
      wow.available ? `This week vs last week: **${wow.label}** (${formatPct(wow.thisWeek)} vs ${formatPct(wow.lastWeek)}).` : '',
      k.overall.sentence,
      'Suites: ' + k.suites.map((s) => `${s.label} ${s.level} (${s.passPct}%)`).join(' · '),
    ].filter(Boolean).join('\n');
  }

  if (suite) {
    return [
      `${suite.label} release confidence: **${suite.level}** (${suite.score}/100).`,
      suite.sentence,
      `Latest run: ${suite.passPct}% pass · ${suite.review} of ${suite.total} checks need review.`,
    ].join('\n');
  }

  if (/flaky|defect|environment|triage|noise|bucket|timeout/.test(q)) {
    const t = k.triage;
    const lines = [
      `Issue split from mapped failures: **${t.defect} likely defects**, **${t.flaky} flaky**, **${t.environment} environment**.`,
      'Rules in short:',
      '• Environment — servers, deploy, credentials, or late/slow responses (including wait timeouts).',
      '• Flaky — unstable/broken-only automation; don’t block release alone.',
      '• Likely defect — assertion/API/data/UI mismatches that need a product owner.',
    ];
    if (/defect/.test(q) && k.triageSamples.defect?.length) {
      lines.push('Example defects: ' + k.triageSamples.defect.map((f) => friendlyFailureTitle(f)).join('; '));
    }
    if (/flaky/.test(q) && k.triageSamples.flaky?.length) {
      lines.push('Example flaky: ' + k.triageSamples.flaky.map((f) => friendlyFailureTitle(f)).join('; '));
    }
    if (/environment|timeout/.test(q) && k.triageSamples.environment?.length) {
      lines.push('Example environment: ' + k.triageSamples.environment.map((f) => friendlyFailureTitle(f)).join('; '));
    }
    if (/environment|timeout/.test(q) && !k.triageSamples.environment?.length) {
      lines.push('No environment issues in the current mapped failure list.');
    }
    return lines.join('\n');
  }

  if (/trend|weekly|monthly|daily|quarter|yearly|improving|slipping|graph/.test(q)) {
    const recent = k.trend.labels.map((label, i) => {
      const v = k.trend.overall[i];
      return v == null ? null : `${label}: ${v}%`;
    }).filter(Boolean);
    return [
      `Trend range is currently **${k.trend.range}** (change with the Daily/Weekly/Monthly/… buttons).`,
      recent.length ? `Recent overall pass-rate points: ${recent.join(' · ')}` : 'Not enough trend points in this range yet.',
      k.trend.estimated ? 'Note: some older points are estimated backfill until CI history grows.' : 'Trend points come from published run history.',
    ].join('\n');
  }

  if (/product area|journey|login|approval|scan|task|price|mobile associate|api contract/.test(q)) {
    const focus = k.areas.filter((a) => a.status !== 'healthy');
    const lines = ['Product area traffic lights:'];
    for (const a of k.areas) {
      const mark = a.status === 'healthy' ? 'OK' : a.status === 'watch' ? 'WATCH' : 'RISK';
      lines.push(`• [${mark}] ${a.label}${a.sample ? ` — ${a.sample}` : ''}`);
    }
    if (focus.length) {
      lines.push(`Focus first on: ${focus.map((a) => a.label).join(', ')}.`);
    }
    return lines.join('\n');
  }

  if (/attention|top failure|what failed|failing|broken|issue/.test(q)) {
    if (!k.failures.length) return 'No mapped failures in the current dashboard snapshot.';
    return ['Top items needing attention:', ...k.failures.slice(0, 6).map((f, i) =>
      `${i + 1}. [${f.bucket}] ${f.title} (${f.suite}) — ${f.meaning} Next: ${f.nextStep}`,
    )].join('\n');
  }

  if (/ai impact|self-?heal|quarantine|quality gate/.test(q)) {
    return [
      k.ai.headline || 'This dashboard highlights AI-assisted QA capabilities.',
      'Capabilities covered here: self-healing locators, flaky quarantine, AI quality gate, and learned locator memory.',
      `Current triage signal: ${k.triage.defect} defects · ${k.triage.flaky} flaky · ${k.triage.environment} environment.`,
    ].join('\n');
  }

  // Keyword search against failures / areas / suites
  const tokens = q.split(/\s+/).filter((w) => w.length > 3);
  const hits = k.failures.filter((f) => tokens.some((t) => `${f.title} ${f.meaning}`.toLowerCase().includes(t)));
  if (hits.length) {
    return ['Here’s what the dashboard shows for that:', ...hits.slice(0, 4).map((f) =>
      `• [${f.bucket}] ${f.title} (${f.suite}) — ${f.meaning}`,
    )].join('\n');
  }

  return [
    'I can answer from the current dashboard snapshot only.',
    `Overall is ${k.overall.label} (${k.overall.passPct}% pass).`,
    'Ask about a suite (Web/iOS/Android/API), defects vs flaky vs environment, product areas, trends, or what needs attention.',
  ].join('\n');
}

function formatChatHtml(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/_(.+?)_/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

function appendChatMessage(role, text) {
  const log = document.getElementById('chat-log');
  if (!log) return;
  const div = document.createElement('div');
  div.className = `chat-msg chat-msg--${role}`;
  div.innerHTML = role === 'assistant'
    ? formatChatHtml(text)
    : escapeHtml(text);
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function setChatOpen(open) {
  const panel = document.getElementById('chat-panel');
  const toggle = document.getElementById('chat-toggle');
  if (!panel || !toggle) return;
  panel.hidden = !open;
  toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  if (open) document.getElementById('chat-input')?.focus();
}

function routeChatIntent(question) {
  const q = question.toLowerCase();
  if (/trend|weekly|monthly|daily|graph|improving|slipping/.test(q)) {
    if (/monthly/.test(q)) setTrendRange('monthly');
    else if (/daily/.test(q)) setTrendRange('daily');
    else if (/quarter|yearly|year/.test(q)) setTrendRange(/year/.test(q) ? 'yearly' : 'quarterly');
    else setTrendRange('weekly');
    setActiveTab('trends');
    return 'trends';
  }
  if (/attention|blocker|failing|what failed|defect|flaky|environment/.test(q)) {
    setActiveTab('attention');
    return 'attention';
  }
  if (/ai impact|self-?heal|quarantine/.test(q)) {
    setActiveTab('ai');
    return 'ai';
  }
  if (/suite detail|allure|ci run|repo card/.test(q)) {
    setActiveTab('suites');
    return 'suites';
  }
  if (/release gate|ship|hold|investigate|overall|confidence|product area/.test(q)) {
    setActiveTab('overview');
    return 'overview';
  }
  return null;
}


async function handleChatSubmit(event) {
  event?.preventDefault?.();
  const input = document.getElementById('chat-input');
  const askBtn = document.querySelector('#chat-form button[type="submit"]');
  if (!input) return;
  const question = input.value.trim();
  if (!question) return;
  if (!CURRENT_RESULTS.length) {
    appendChatMessage('assistant', 'Dashboard data is still loading — try again in a moment.');
    return;
  }
  appendChatMessage('user', question);
  input.value = '';
  const tab = routeChatIntent(question);
  const suffix = tab ? `\n\n_Opened the **${tab}** tab for you._` : '';

  if (askBtn) askBtn.disabled = true;
  try {
    const answer = answerFromKnowledge(question);
    appendChatMessage('assistant', answer + suffix);
  } finally {
    if (askBtn) askBtn.disabled = false;
    input.focus();
  }
}

function buildExportPackHtml() {
  const health = computeHealthScore(CURRENT_RESULTS);
  const gate = computeReleaseGate(CURRENT_RESULTS);
  const wow = computeWeekOverWeek(CURRENT_RESULTS);
  const triage = summarizeIssueBuckets(CURRENT_RESULTS);
  const failures = collectFailures(CURRENT_RESULTS).slice(0, 8);
  const when = new Date().toLocaleString();

  const blockerLis = gate.blockers.map((b, i) => `<li><strong>${i + 1}. ${escapeHtml(b.title)}</strong> — ${escapeHtml(b.detail)}</li>`).join('')
    || '<li>None mapped</li>';
  const suiteRows = (health.suiteScores || []).map((s) => {
    const wowS = (wow.suites || []).find((x) => x.id === s.id);
    const d = formatDelta(wowS?.delta);
    return `<tr><td>${escapeHtml(REPO_DISPLAY[s.id]?.label || s.title)}</td><td>${s.label}</td><td>${s.passPct}%</td><td>${escapeHtml(d.text)}</td></tr>`;
  }).join('');
  const failRows = failures.map((f) => {
    const exp = explainFailure(f);
    return `<tr><td>${escapeHtml(friendlyFailureTitle(f))}</td><td>${escapeHtml(REPO_DISPLAY[f.repo]?.label || f.repo)}</td><td>${escapeHtml(exp.bucketLabel)}</td></tr>`;
  }).join('');

  return `<!DOCTYPE html><html><head><meta charset="utf-8" />
<title>Store Intell QA — Steering pack</title>
<style>
  body{font-family:Georgia,serif;margin:0;color:#0f172a;background:#fff}
  .slide{page-break-after:always;padding:36px 48px;min-height:90vh;box-sizing:border-box}
  h1{font-size:28px;margin:0 0 8px} h2{font-size:20px;margin:0 0 12px}
  .muted{color:#64748b;font-size:13px} .verdict{font-size:42px;margin:12px 0}
  .ship{color:#15803d}.hold{color:#b91c1c}.investigate{color:#b45309}
  table{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px}
  th,td{border-bottom:1px solid #e2e8f0;text-align:left;padding:8px 6px}
  th{color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
  ul,ol{line-height:1.5} .meta{margin-top:18px;font-size:13px;color:#475569}
  @media print{.slide{padding:24px}}
</style></head><body>
<section class="slide">
  <p class="muted">Store Intell QA · Steering pack · ${escapeHtml(when)}</p>
  <h1>Release gate</h1>
  <p class="verdict ${escapeHtml(gate.verdict)}">${escapeHtml(gate.label)}</p>
  <p>${escapeHtml(gate.blurb)}</p>
  <h2>Top blockers</h2>
  <ol>${blockerLis}</ol>
  <p class="meta">Overall confidence: ${escapeHtml(health.label)} (${health.score}/100, ${health.passPct}% pass)</p>
</section>
<section class="slide">
  <h1>Week-over-week</h1>
  <p>${wow.available ? `Overall ${escapeHtml(wow.label)} · now ${formatPct(wow.thisWeek)} vs ${formatPct(wow.lastWeek)}` : 'Not enough weekly history yet.'}</p>
  <table><thead><tr><th>Suite</th><th>Status</th><th>Pass</th><th>vs last week</th></tr></thead>
  <tbody>${suiteRows}</tbody></table>
  <p class="meta">Issue split: ${triage.counts.defect} defects · ${triage.counts.flaky} flaky · ${triage.counts.environment} environment</p>
</section>
<section class="slide">
  <h1>What needs attention</h1>
  <table><thead><tr><th>Item</th><th>Suite</th><th>Type</th></tr></thead>
  <tbody>${failRows || '<tr><td colspan="3">No mapped failures</td></tr>'}</tbody></table>
  <p class="meta">${escapeHtml(health.sentence)}</p>
</section>
</body></html>`;
}

function exportSteeringPack() {
  if (!CURRENT_RESULTS.length) {
    window.alert('Dashboard data is still loading.');
    return;
  }
  const html = buildExportPackHtml();
  const win = window.open('', '_blank', 'noopener,noreferrer,width=960,height=720');
  if (!win) {
    window.alert('Pop-up blocked — allow pop-ups to export the steering pack.');
    return;
  }
  win.document.open();
  win.document.write(html);
  win.document.close();
  win.focus();
  window.setTimeout(() => {
    try { win.print(); } catch { /* ignore */ }
  }, 350);
}

function wireChatbot() {
  const toggle = document.getElementById('chat-toggle');
  const closeBtn = document.getElementById('chat-close');
  const form = document.getElementById('chat-form');
  const chips = document.querySelectorAll('[data-chat-q]');
  toggle?.addEventListener('click', () => {
    const panel = document.getElementById('chat-panel');
    setChatOpen(!!panel?.hidden);
  });
  closeBtn?.addEventListener('click', () => setChatOpen(false));
  form?.addEventListener('submit', handleChatSubmit);
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const input = document.getElementById('chat-input');
      if (!input) return;
      input.value = chip.getAttribute('data-chat-q') || '';
      handleChatSubmit();
    });
  });
}

async function loadDashboard() {
  document.getElementById('repo-cards').innerHTML = '<p class="loading-cards">Loading latest test results…</p>';
  document.getElementById('last-updated').textContent = `Dashboard v${DASHBOARD_VERSION} · refreshing…`;

  const aiImpactPromise = loadAiImpact();
  const aiUsagePromise = loadAiUsage();
  const historyPromise = loadTrendHistory();
  const bundled = REPO_CONFIG.map((cfg) => getBootstrapSnapshot(cfg));
  const bundledAi = window.DASHBOARD_SNAPSHOTS?.snapshots?.['ai-impact'];
  const bundledUsage = window.DASHBOARD_SNAPSHOTS?.snapshots?.['ai-usage'];
  await historyPromise;
  if (bundled.some((b) => (b?.summary?.total || 0) > 0)) {
    renderDashboard(
      bundled.map((b, i) => (b?.summary ? b : placeholder(REPO_CONFIG[i]))),
      bundledAi,
      bundledUsage,
    );
    document.getElementById('last-updated').textContent = `Dashboard v${DASHBOARD_VERSION} · ${new Date().toLocaleString()}`;
  }

  const [results, aiImpact, aiUsage] = await Promise.all([
    Promise.all(REPO_CONFIG.map((cfg) => fetchSummary(cfg))),
    aiImpactPromise,
    aiUsagePromise,
  ]);
  renderDashboard(results, aiImpact, aiUsage);
  document.getElementById('last-updated').textContent = `Dashboard v${DASHBOARD_VERSION} · live · ${new Date().toLocaleString()}`;
}

function setIncludeEstimated(on) {
  INCLUDE_ESTIMATED = !!on;
  try { localStorage.setItem('dashboard.includeEstimated', on ? '1' : '0'); } catch { /* ignore */ }
  if (CURRENT_RESULTS.length) {
    const trendsEl = document.getElementById('trends-panel');
    if (trendsEl) {
      trendsEl.innerHTML = renderTrendsPanel(CURRENT_RESULTS);
      wireTrendChart();
    }
    const banner = document.getElementById('overall-banner');
    if (banner) banner.innerHTML = renderOverallBanner(CURRENT_RESULTS);
  }
}

function wireControls() {
  document.getElementById('refresh-btn')?.addEventListener('click', loadDashboard);
  document.getElementById('export-btn')?.addEventListener('click', exportSteeringPack);
  document.getElementById('trends-panel')?.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-trend-range]');
    if (btn) {
      setTrendRange(btn.getAttribute('data-trend-range'));
      return;
    }
  });
  document.getElementById('trends-panel')?.addEventListener('change', (event) => {
    const input = event.target.closest('#include-estimated');
    if (!input) return;
    setIncludeEstimated(input.checked);
  });
  document.getElementById('overall-banner')?.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-goto-tab]');
    if (!btn) return;
    setActiveTab(btn.getAttribute('data-goto-tab'));
  });

  // Live tracker demo & settings controls
  document.getElementById('live-sim-btn')?.addEventListener('click', () => {
    if (window.LiveTracker) {
      window.LiveTracker.simulateRun('web');
    }
  });

  const settingsModal = document.getElementById('token-modal');
  const tokenInput = document.getElementById('github-token-input');

  document.getElementById('settings-btn')?.addEventListener('click', () => {
    if (settingsModal && tokenInput && window.LiveTracker) {
      tokenInput.value = window.LiveTracker.getToken();
      settingsModal.hidden = false;
      tokenInput.focus();
    }
  });

  document.getElementById('token-modal-cancel')?.addEventListener('click', () => {
    if (settingsModal) settingsModal.hidden = true;
  });

  document.getElementById('token-modal-save')?.addEventListener('click', () => {
    if (settingsModal && tokenInput && window.LiveTracker) {
      window.LiveTracker.setToken(tokenInput.value);
      settingsModal.hidden = true;
    }
  });

  wireTabs();
  wireChatbot();
}

ACTIVE_TAB = resolveInitialTab();
TREND_RANGE = resolveInitialTrendRange();
wireControls();
setActiveTab(ACTIVE_TAB, { persist: false, updateUrl: false });
loadDashboard();
