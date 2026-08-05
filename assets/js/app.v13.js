/**
 * Public automation dashboard — release confidence for technical + non-technical audiences.
 */

const BUILD_TAG = '20260805c';
const DASHBOARD_VERSION = window.DASHBOARD_VERSION || '13';

const REPO_DISPLAY = {
  web: { icon: '🌐', label: 'Web' },
  'mobile-ios': { icon: '🍎', label: 'iOS' },
  'mobile-android': { icon: '🤖', label: 'Android' },
  api: { icon: '🔌', label: 'API' },
};

const VIEW_MODES = ['full', 'executive', 'demo'];
let CURRENT_RESULTS = [];
let VIEW_MODE = 'full';
let DEMO_STEP = 0;

const DEMO_STEPS = [
  { id: 'overall-banner', title: 'Release confidence', tip: 'Start with the overall score, then Web / iOS / Android / API.' },
  { id: 'business-areas', title: 'Product areas', tip: 'Which product journeys need attention?' },
  { id: 'issue-triage', title: 'Issue types', tip: 'Separate environment problems, flaky tests, and real defects.' },
  { id: 'failures-panel', title: 'What needs attention', tip: 'Concrete items with plain-language next steps.' },
  { id: 'trends-panel', title: 'Recent trends', tip: 'Is quality improving or slipping across recent runs?' },
  { id: 'ai-impact', title: 'AI impact', tip: 'How AI-assisted automation reduces noise and protects releases.' },
  { id: 'repo-cards', title: 'Suite details', tip: 'Technical depth for QA — CI, Allure, and run metadata.' },
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

function renderOverallBanner(summaries) {
  const health = computeHealthScore(summaries);
  if (health.level === 'unknown') {
    return `<div class="health-banner health-banner--unknown">
      <div class="health-banner__score"><span class="health-banner__value">—</span><span class="health-banner__label">Loading</span></div>
      <div class="health-banner__copy"><p class="health-banner__eyebrow">Overall release confidence</p><p class="health-banner__sentence">${escapeHtml(health.sentence)}</p></div>
    </div>`;
  }

  const suiteCards = (health.suiteScores || []).map((s) => `
    <article class="suite-health suite-health--${s.level}" data-suite="${escapeHtml(s.id)}">
      <div class="suite-health__top">
        <span class="suite-health__name">${s.icon} ${escapeHtml(REPO_DISPLAY[s.id]?.label || s.title)}</span>
        <span class="suite-health__badge">${escapeHtml(s.label)}</span>
      </div>
      <div class="suite-health__score">${s.score == null ? '—' : s.score}</div>
      <p class="suite-health__meta">${s.counts.total ? `${s.passPct}% pass · ${s.counts.review} need review` : 'No data'}</p>
      <p class="suite-health__sentence">${escapeHtml(s.sentence)}</p>
    </article>`).join('');

  return `
    <div class="health-stack">
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

function renderAiImpact(summaries, aiImpact) {
  const data = aiImpact || AI_IMPACT_CACHE || {};
  const signals = deriveAiSignals(summaries);
  const caps = (data.capabilities || []).map((c) => `
    <article class="ai-cap">
      <h3>${escapeHtml(c.title)}</h3>
      <p>${escapeHtml(c.blurb)}</p>
    </article>`).join('');

  const metrics = (data.metrics || []).map((m) => `
    <div class="ai-metric">
      <span class="ai-metric__value">${escapeHtml(m.value)}</span>
      <span class="ai-metric__label">${escapeHtml(m.label)}</span>
      ${m.note ? `<span class="ai-metric__note">${escapeHtml(m.note)}</span>` : ''}
    </div>`).join('');

  const liveStats = `
    <div class="ai-live">
      <div class="ai-metric">
        <span class="ai-metric__value">${signals.healCandidates}</span>
        <span class="ai-metric__label">UI-noise signals</span>
        <span class="ai-metric__note">Good candidates for healing</span>
      </div>
      <div class="ai-metric">
        <span class="ai-metric__value">${signals.humanDecisions}</span>
        <span class="ai-metric__label">Human decisions</span>
        <span class="ai-metric__note">Expected vs actual mismatches</span>
      </div>
    </div>`;

  const story = (data.story || []).map((line) => `<li>${escapeHtml(line)}</li>`).join('');
  const liveBullets = signals.bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join('');

  return `
    <div class="panel__header ai-panel__header">
      <div>
        <p class="ai-kicker">Built with AI · AI-in-QA</p>
        <h2>AI impact</h2>
        <p>${escapeHtml(data.headline || 'Automation that recovers, explains, and protects release decisions.')}</p>
      </div>
    </div>
    <div class="ai-panel__body">
      <div class="ai-metrics-row">${metrics}${liveStats}</div>
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
    const limit = VIEW_MODE === 'executive' ? 3 : 8;
    for (const failure of summary.topFailures.slice(0, limit)) {
      items.push({ repo: summary.repo, ...failure });
    }
  }
  if (!items.length) return null;
  const categoryBar = VIEW_MODE === 'executive' ? '' : renderCategorySummaryBar(summaries);
  const list = items.slice(0, VIEW_MODE === 'executive' ? 6 : 50).map((f) => renderFailureItem(f)).join('');
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

function renderTrendsPanel(summaries) {
  const rows = REPO_CONFIG.map((cfg, i) => {
    const summary = summaries[i];
    const trend = summary?.historyTrend || [];
    if (!trend.length && !(summary?.counts?.total > 0)) return '';
    const counts = summary?.counts || computeCounts(summary);
    const rates = computeRates(counts);
    const dir = trendDirection(trend);
    const spark = trend.length
      ? renderTrendBars(trend)
      : `<p class="trend-empty">Only the latest run is available</p>`;
    return `
      <article class="trend-card trend-card--${cfg.id}">
        <div class="trend-card__head">
          <h3>${cfg.icon} ${escapeHtml(REPO_DISPLAY[cfg.id]?.label || cfg.title)}</h3>
          <span class="trend-dir trend-dir--${dir.cls}">${escapeHtml(dir.label)}</span>
        </div>
        <p class="trend-card__now">${counts.total ? `${rates.passPct}% pass on latest run` : 'No data yet'}</p>
        ${spark}
      </article>`;
  }).filter(Boolean).join('');

  if (!rows) {
    return `
      <div class="panel__header"><h2>Recent trends</h2><p>Not enough history published yet</p></div>
      <p class="loading-cards">Trends appear after a few CI publishes.</p>`;
  }

  return `
    <div class="panel__header">
      <h2>Recent trends</h2>
      <p>Are we getting healthier across the last few runs?</p>
    </div>
    <div class="trend-grid">${rows}</div>`;
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

async function copyShareSnapshot() {
  const text = buildShareSnapshot(CURRENT_RESULTS);
  const btn = document.getElementById('share-btn');
  try {
    await navigator.clipboard.writeText(text);
    if (btn) {
      const prev = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = prev; }, 1600);
    }
  } catch {
    window.prompt('Copy this quality snapshot:', text);
  }
}

function resolveInitialMode() {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = (params.get('mode') || '').toLowerCase();
  if (VIEW_MODES.includes(fromUrl)) return fromUrl;
  try {
    const saved = localStorage.getItem('dashboard.viewMode');
    if (VIEW_MODES.includes(saved) && saved !== 'demo') return saved;
  } catch { /* ignore */ }
  return 'full';
}

function setViewMode(mode, { persist = true, updateUrl = true } = {}) {
  if (!VIEW_MODES.includes(mode)) mode = 'full';
  VIEW_MODE = mode;
  document.body.classList.toggle('mode-executive', mode === 'executive');
  document.body.classList.toggle('mode-demo', mode === 'demo');
  document.body.classList.toggle('mode-full', mode === 'full');

  const execBtn = document.getElementById('exec-mode-btn');
  const demoBtn = document.getElementById('demo-mode-btn');
  if (execBtn) {
    execBtn.setAttribute('aria-pressed', mode === 'executive' ? 'true' : 'false');
    execBtn.textContent = mode === 'executive' ? 'Exit executive' : 'Executive mode';
  }
  if (demoBtn) {
    demoBtn.setAttribute('aria-pressed', mode === 'demo' ? 'true' : 'false');
    demoBtn.textContent = mode === 'demo' ? 'Exit demo' : 'Demo mode';
  }

  const demoBar = document.getElementById('demo-bar');
  if (demoBar) demoBar.hidden = mode !== 'demo';

  if (persist && mode !== 'demo') {
    try { localStorage.setItem('dashboard.viewMode', mode); } catch { /* ignore */ }
  }
  if (updateUrl) {
    const url = new URL(window.location.href);
    if (mode === 'full') url.searchParams.delete('mode');
    else url.searchParams.set('mode', mode);
    window.history.replaceState({}, '', url);
  }

  if (mode === 'demo') {
    DEMO_STEP = 0;
    applyDemoStep();
  } else {
    clearDemoHighlight();
  }

  if (CURRENT_RESULTS.length) renderDashboard(CURRENT_RESULTS, AI_IMPACT_CACHE);
}

function clearDemoHighlight() {
  document.querySelectorAll('.demo-highlight').forEach((el) => el.classList.remove('demo-highlight'));
}

function applyDemoStep() {
  clearDemoHighlight();
  const step = DEMO_STEPS[DEMO_STEP];
  if (!step) return;
  const el = document.getElementById(step.id);
  if (el) {
    el.classList.add('demo-highlight');
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  const title = document.getElementById('demo-step-title');
  const tip = document.getElementById('demo-step-tip');
  const counter = document.getElementById('demo-step-counter');
  if (title) title.textContent = step.title;
  if (tip) tip.textContent = step.tip;
  if (counter) counter.textContent = `${DEMO_STEP + 1} / ${DEMO_STEPS.length}`;
}

function demoNext() {
  DEMO_STEP = Math.min(DEMO_STEPS.length - 1, DEMO_STEP + 1);
  applyDemoStep();
}

function demoPrev() {
  DEMO_STEP = Math.max(0, DEMO_STEP - 1);
  applyDemoStep();
}

function renderDashboard(results, aiImpact) {
  if (aiImpact) AI_IMPACT_CACHE = aiImpact;
  CURRENT_RESULTS = results || [];

  document.getElementById('overall-banner').innerHTML = renderOverallBanner(results);

  const triageEl = document.getElementById('issue-triage');
  if (triageEl) triageEl.innerHTML = renderIssueTriage(results);

  const areasEl = document.getElementById('business-areas');
  if (areasEl) areasEl.innerHTML = renderBusinessAreas(results);

  const trendsEl = document.getElementById('trends-panel');
  if (trendsEl) trendsEl.innerHTML = renderTrendsPanel(results);

  const aiEl = document.getElementById('ai-impact');
  if (aiEl) {
    aiEl.innerHTML = renderAiImpact(results, AI_IMPACT_CACHE);
    aiEl.hidden = VIEW_MODE === 'executive';
  }

  document.getElementById('repo-cards').innerHTML = REPO_CONFIG.map((cfg, i) => renderCard(cfg, results[i])).join('');

  const failuresHtml = renderFailures(results);
  const failuresPanel = document.getElementById('failures-panel');
  if (failuresPanel) {
    failuresPanel.hidden = !failuresHtml;
  }
  const failuresList = document.getElementById('failures-list');
  if (failuresList) failuresList.innerHTML = failuresHtml || '';

  if (VIEW_MODE === 'demo') applyDemoStep();
}

async function loadAiImpact() {
  const bundled = window.DASHBOARD_SNAPSHOTS?.snapshots?.['ai-impact'];
  const live = await fetchJson('data/ai-impact.json');
  return live || bundled || null;
}

async function loadDashboard() {
  document.getElementById('repo-cards').innerHTML = '<p class="loading-cards">Loading latest test results…</p>';
  document.getElementById('last-updated').textContent = `Dashboard v${DASHBOARD_VERSION} · refreshing…`;

  const aiImpactPromise = loadAiImpact();
  const bundled = REPO_CONFIG.map((cfg) => getBootstrapSnapshot(cfg));
  const bundledAi = window.DASHBOARD_SNAPSHOTS?.snapshots?.['ai-impact'];
  if (bundled.some((b) => (b?.summary?.total || 0) > 0)) {
    renderDashboard(
      bundled.map((b, i) => (b?.summary ? b : placeholder(REPO_CONFIG[i]))),
      bundledAi,
    );
    document.getElementById('last-updated').textContent = `Dashboard v${DASHBOARD_VERSION} · ${new Date().toLocaleString()}`;
  }

  const [results, aiImpact] = await Promise.all([
    Promise.all(REPO_CONFIG.map((cfg) => fetchSummary(cfg))),
    aiImpactPromise,
  ]);
  renderDashboard(results, aiImpact);
  document.getElementById('last-updated').textContent = `Dashboard v${DASHBOARD_VERSION} · live · ${new Date().toLocaleString()}`;
}

function wireControls() {
  document.getElementById('refresh-btn')?.addEventListener('click', loadDashboard);
  document.getElementById('exec-mode-btn')?.addEventListener('click', () => {
    setViewMode(VIEW_MODE === 'executive' ? 'full' : 'executive');
  });
  document.getElementById('demo-mode-btn')?.addEventListener('click', () => {
    setViewMode(VIEW_MODE === 'demo' ? 'full' : 'demo');
  });
  document.getElementById('share-btn')?.addEventListener('click', copyShareSnapshot);
  document.getElementById('demo-next')?.addEventListener('click', demoNext);
  document.getElementById('demo-prev')?.addEventListener('click', demoPrev);
  document.getElementById('demo-exit')?.addEventListener('click', () => setViewMode('full'));
}

VIEW_MODE = resolveInitialMode();
wireControls();
setViewMode(VIEW_MODE, { persist: false, updateUrl: false });
loadDashboard();
