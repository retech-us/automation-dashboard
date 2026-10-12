/* Sentry tab: live span usage vs plan cap, per-service attribution, and month/week trends.
 * Live data: data/sentry-live.json, written by scripts/fetch-sentry.py from the Sentry API
 * (refreshed by the Update Dashboard workflow). Plan caps and the action log: data/sentry-config.json.
 * Per-day rates are used so partial months and weeks compare fairly. */
(function () {
  const LIVE_URL = 'data/sentry-live.json';
  const CONFIG_URL = 'data/sentry-config.json';
  let LIVE = null;
  let CONFIG = null;
  let LOADED = false;
  let FROM_ID = null;
  let TO_ID = null;

  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
  const isNum = (n) => n != null && Number.isFinite(n);
  const fmt = (n) => (isNum(n) ? Math.round(n).toLocaleString('en-US') : '—');
  const fmtM = (n) => (isNum(n) ? `${(n / 1e6).toFixed(1)}M` : '—');
  const fmtUsd = (n) => `$${(Number(n) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const fmtPct = (n) => (isNum(n) ? `${n > 0 ? '+' : ''}${n.toFixed(1)}%` : '—');
  const pct = (part, whole) => (whole ? (part / whole) * 100 : null);
  const pctChange = (from, to) => (from ? (to / from - 1) * 100 : null);

  function fmtFeature(value, unit) {
    if (!isNum(value)) return '—';
    if (unit === 'bytes') {
      if (value >= 1e9) return `${(value / 1e9).toFixed(2)} GB`;
      if (value >= 1e6) return `${(value / 1e6).toFixed(2)} MB`;
      return `${fmt(value)} B`;
    }
    if (unit === 'hours') return `${value} hours`;
    if (value >= 1e6) return fmtM(value);
    if (value >= 1e3) return `${(value / 1e3).toFixed(0)}K`;
    return fmt(value);
  }

  async function getJson(url, snapshotKey) {
    try {
      const res = await fetch(`${url}?_=${Date.now()}`, { cache: 'no-store' });
      if (res.ok) return await res.json();
    } catch { /* fall back to the bundled snapshot */ }
    return window.DASHBOARD_SNAPSHOTS?.snapshots?.[snapshotKey] || null;
  }

  async function loadData() {
    if (LOADED) return;
    [LIVE, CONFIG] = await Promise.all([
      getJson(LIVE_URL, 'sentry-live'),
      getJson(CONFIG_URL, 'sentry-config'),
    ]);
    LOADED = true;
  }

  const daysBetween = (start, end) => Math.round((new Date(`${end}T00:00:00Z`) - new Date(`${start}T00:00:00Z`)) / 86400000) + 1;

  function monthLabel(ym) {
    const [y, m] = ym.split('-').map(Number);
    return new Date(y, m - 1, 1).toLocaleString('en-US', { month: 'short', year: 'numeric' });
  }

  function timeAgo(iso) {
    const mins = Math.round((Date.now() - new Date(iso)) / 60000);
    if (!isNum(mins)) return '';
    if (mins < 60) return `${mins} min ago`;
    if (mins < 1440) return `${Math.round(mins / 60)} h ago`;
    return `${Math.round(mins / 1440)} d ago`;
  }

  /* Attempted = accepted + all dropped (what the apps tried to send). */
  function periodStats(row) {
    const attempted = row.accepted_total + row.all_dropped;
    const days = row.days_covered;
    return {
      id: row.month,
      label: `${monthLabel(row.month)}${days < 28 ? ' (partial)' : ''}`,
      days,
      accepted: row.accepted_total,
      quotaDropped: row.quota_dropped,
      attempted,
      acceptedPerDay: row.accepted_total / days,
      attemptedPerDay: attempted / days,
      quotaShare: pct(row.quota_dropped, attempted),
    };
  }

  function windowStats(rows) {
    const s = rows.reduce((a, r) => ({
      accepted: a.accepted + r.accepted, quota: a.quota + r.quota_dropped, dropped: a.dropped + r.dropped,
    }), { accepted: 0, quota: 0, dropped: 0 });
    const days = rows.length || 1;
    const attempted = s.accepted + s.dropped;
    return {
      days: rows.length,
      acceptedPerDay: s.accepted / days,
      attemptedPerDay: attempted / days,
      quotaShare: pct(s.quota, attempted),
    };
  }

  function planModel() {
    const plan = CONFIG?.plan || { features: [] };
    const period = LIVE?.billing_period || { ...plan.billing_period, source: 'config' };
    const usage = LIVE?.period_usage || {};
    const reserved = LIVE?.reserved || {};
    const features = plan.features.map((f) => ({
      ...f,
      used: usage[f.category],
      included: reserved[f.category] ?? f.included,
    }));
    const spans = features.find((f) => f.category === 'span') || {};
    const totalDays = period.start ? daysBetween(period.start, period.end) : 30;
    const today = new Date().toISOString().slice(0, 10);
    const elapsed = period.start ? Math.max(1, Math.min(totalDays, daysBetween(period.start, today < period.end ? today : period.end))) : null;
    return { plan, period, features, spans, totalDays, elapsed };
  }

  function kpi(value, label, note, tone = '') {
    return `<article class="sentry-kpi ${tone ? `sentry-kpi--${tone}` : ''}">
      <p class="sentry-kpi__value">${value}</p>
      <p class="sentry-kpi__label">${esc(label)}</p>
      <p class="sentry-kpi__note">${esc(note)}</p>
    </article>`;
  }

  function table(head, rows) {
    return `<div class="sentry-table-wrap"><table class="sentry-table">
      <thead><tr>${head.map((h) => `<th${h.num ? ' class="num"' : ''}>${esc(h.label)}</th>`).join('')}</tr></thead>
      <tbody>${rows.join('')}</tbody></table></div>`;
  }

  function renderLiveStatus() {
    if (!LIVE || LIVE.source !== 'sentry-api') {
      const why = LIVE?.errors?.join('; ') || 'data/sentry-live.json not found';
      return `<p class="sentry-verdict sentry-verdict--bad"><b>Live Sentry data unavailable:</b> ${esc(why)}. Add the <code>SENTRY_AUTH_TOKEN</code> secret to the Update Dashboard workflow.</p>`;
    }
    const partial = LIVE.errors?.length
      ? ` <span class="sentry-flag">Partial: ${esc(LIVE.errors.join('; '))}</span>`
      : '';
    return `<p class="sentry-note"><span class="sentry-status sentry-status--done">Live</span> From the Sentry API (${esc(LIVE.org)}), updated ${esc(timeAgo(LIVE.generated_at))} (${esc(new Date(LIVE.generated_at).toLocaleString())}). Refreshes every 15 minutes.${partial}</p>`;
  }

  function renderPlan() {
    const { plan, period, features, spans, totalDays, elapsed } = planModel();
    const used = spans.used;
    const cap = spans.included;
    const budgetPerDay = cap / totalDays;
    const runRate = isNum(used) && elapsed ? used / elapsed : null;
    const projected = isNum(runRate) ? runRate * totalDays : null;
    const extraTotal = features.reduce((a, f) => a + (f.extra_spend_usd || 0), 0);

    const kpis = [
      kpi(isNum(used) ? `${pct(used, cap).toFixed(0)}%` : '—', 'Span cap used', `${fmtM(used)} of ${fmtM(cap)} this period`, isNum(used) ? (used > cap ? 'bad' : 'good') : ''),
      kpi(fmtM(projected), 'Projected spans this period', `At ${fmtM(runRate)}/day over ${totalDays} days`, isNum(projected) ? (projected > cap ? 'bad' : 'good') : ''),
      kpi(isNum(used) ? (used > cap ? `${(100 - pct(cap, used)).toFixed(1)}%` : '0%') : '—', 'Cut needed to get under cap', `Daily budget ${fmt(budgetPerDay)} spans`),
      kpi(fmtUsd(extraTotal), 'Extra spend (all features)', `From Subscription page, as of ${plan.extra_spend_as_of || '—'}`),
    ].join('');

    const rows = features.map((f) => {
      const hasCap = f.included != null;
      const p = hasCap && isNum(f.used) ? pct(f.used, f.included) : null;
      const over = hasCap ? isNum(f.used) && f.used > f.included : (f.extra_spend_usd || 0) > 0;
      const near = !over && isNum(p) && p >= 80;
      const status = over ? (hasCap ? 'Over plan' : 'Over (cap not shown)') : near ? 'Near cap' : 'Within plan';
      const cls = over ? 'open' : near ? 'observed' : 'done';
      const flag = !over && (f.extra_spend_usd || 0) > 0
        ? '<span class="sentry-flag">Spend on a feature under its cap: check Sentry billing</span>'
        : '';
      return `<tr>
        <td>${esc(f.feature)}</td>
        <td class="num">${esc(fmtFeature(f.used, f.unit))}</td>
        <td class="num">${hasCap ? esc(fmtFeature(f.included, f.unit)) : '—'}</td>
        <td class="num">${isNum(p) ? `${p.toFixed(1)}%` : '—'}</td>
        <td class="num">${fmtUsd(f.extra_spend_usd)}</td>
        <td><span class="sentry-status sentry-status--${cls}">${esc(status)}</span>${flag}</td>
      </tr>`;
    });

    const periodNote = period.source === 'sentry-subscription'
      ? 'from your Sentry subscription'
      : 'assumed (set plan.billing_period in data/sentry-config.json)';
    return `
      <div class="sentry-kpis">${kpis}</div>
      <p class="sentry-note">Billing period ${esc(period.start)} to ${esc(period.end)}, ${esc(periodNote)}. Used values are live accepted volume for the period.</p>
      ${table([
        { label: 'Feature' }, { label: 'Used (live)', num: true }, { label: 'Included', num: true },
        { label: '% of plan', num: true }, { label: 'Extra spend', num: true }, { label: 'Status' },
      ], rows)}`;
  }

  function renderSources() {
    const projects = LIVE?.projects_period || [];
    const envs = (LIVE?.environments_30d || []).slice(0, 12);
    if (!projects.length && !envs.length) return '<p class="sentry-empty">No live attribution data yet.</p>';
    const total = projects.reduce((a, r) => a + r.accepted, 0);
    const projectRows = projects.map((r) => `<tr>
      <td>${esc(r.project)}</td><td class="num">${fmtM(r.accepted)}</td><td class="num">${isNum(pct(r.accepted, total)) ? `${pct(r.accepted, total).toFixed(1)}%` : '—'}</td></tr>`);
    const envRows = envs.map((r) => `<tr>
      <td>${esc(r.project)}</td><td>${esc(r.environment)}</td>
      <td class="num">${fmtM(r.stored)}</td><td class="num">${fmtM(r.extrapolated)}</td>
      <td class="num">${isNum(pct(r.stored, r.extrapolated)) ? `${pct(r.stored, r.extrapolated).toFixed(0)}%` : '—'}</td></tr>`);
    return `
      ${projects.length ? table([{ label: 'Project' }, { label: 'Billed spans this period', num: true }, { label: 'Share', num: true }], projectRows) : ''}
      ${envs.length ? `
      <p class="sentry-note">Last 30 days by environment. Stored spans are billed; "estimated" is Sentry's extrapolation by sample rate. A high "kept" share means traces are sampled far above the code's rate.</p>
      ${table([{ label: 'Project' }, { label: 'Environment' }, { label: 'Stored (billed)', num: true }, { label: 'Estimated', num: true }, { label: 'Kept', num: true }], envRows)}` : ''}`;
  }

  function verdict(a, b, labelA, labelB) {
    const att = pctChange(a.attemptedPerDay, b.attemptedPerDay);
    if (!isNum(att)) return '';
    const dropped = att < 0;
    const accLine = b.acceptedPerDay === 0
      ? ' Nothing was accepted, so ingestion is blocked by quota.'
      : ` Accepted spans per day changed ${fmtPct(pctChange(a.acceptedPerDay, b.acceptedPerDay))}.`;
    return `<p class="sentry-verdict sentry-verdict--${dropped ? 'good' : 'bad'}">
      <b>${dropped ? 'DROPPED' : 'NO DROP'}:</b> attempted spans per day ${dropped ? 'fell' : 'rose'} ${Math.abs(att).toFixed(1)}% from ${esc(labelA)} to ${esc(labelB)}.${accLine}
    </p>`;
  }

  function renderWeek() {
    // Drop today's incomplete bucket.
    const complete = (LIVE?.daily || []).slice(0, -1);
    if (complete.length < 14) return '';
    const last = windowStats(complete.slice(-7));
    const prev = windowStats(complete.slice(-14, -7));
    return `${verdict(prev, last, 'the previous 7 days', 'the last 7 days')}
      <p class="sentry-note">Last 7 days: ${fmtM(last.attemptedPerDay)} attempted and ${fmtM(last.acceptedPerDay)} accepted spans per day; ${isNum(last.quotaShare) ? last.quotaShare.toFixed(1) : '—'}% rejected for quota.</p>`;
  }

  function renderCompare(ms) {
    if (ms.length < 2) return '<p class="sentry-empty">Not enough months of live data to compare yet.</p>';
    const from = ms.find((m) => m.id === FROM_ID);
    const to = ms.find((m) => m.id === TO_ID);
    const sel = (name, val) => `<select data-sentry-select="${name}" class="sentry-select" aria-label="${name === 'from' ? 'Compare from' : 'Compare to'}">
      ${ms.map((m) => `<option value="${esc(m.id)}" ${m.id === val ? 'selected' : ''}>${esc(m.label)}</option>`).join('')}
    </select>`;
    const rows = [
      ['Attempted spans / day', from.attemptedPerDay, to.attemptedPerDay],
      ['Accepted spans / day', from.acceptedPerDay, to.acceptedPerDay],
      ['Quota-dropped spans / day', from.quotaDropped / from.days, to.quotaDropped / to.days],
    ].map(([label, a, b]) => {
      const ch = pctChange(a, b);
      const cls = !isNum(ch) ? '' : ch < 0 ? 'sentry-good' : 'sentry-bad';
      return `<tr><td>${esc(label)}</td><td class="num">${fmt(a)}</td><td class="num">${fmt(b)}</td><td class="num ${cls}">${fmtPct(ch)}</td></tr>`;
    });
    return `
      <div class="sentry-controls">
        <label>From ${sel('from', from.id)}</label>
        <label>To ${sel('to', to.id)}</label>
      </div>
      ${from.id === to.id ? '<p class="sentry-empty">Pick two different months.</p>' : `
      ${verdict(from, to, from.label, to.label)}
      ${table([{ label: 'Measure (per day)' }, { label: from.label, num: true }, { label: to.label, num: true }, { label: 'Change', num: true }], rows)}`}`;
  }

  function renderMonthly(ms, budgetPerDay) {
    if (!ms.length) return '<p class="sentry-empty">No monthly live data yet.</p>';
    const rows = ms.map((m, i) => {
      const mom = i === 0 ? null : pctChange(ms[i - 1].attemptedPerDay, m.attemptedPerDay);
      const cls = !isNum(mom) ? '' : mom < 0 ? 'sentry-good' : 'sentry-bad';
      return `<tr>
        <td>${esc(m.label)}</td><td class="num">${m.days}</td>
        <td class="num">${fmtM(m.accepted)}</td><td class="num">${fmtM(m.quotaDropped)}</td>
        <td class="num">${fmtM(m.attempted)}</td><td class="num">${fmtM(m.attemptedPerDay)}</td>
        <td class="num ${cls}">${fmtPct(mom)}</td>
        <td class="num">${budgetPerDay ? `${(m.attemptedPerDay / budgetPerDay).toFixed(0)}x` : '—'}</td>
        <td class="num">${isNum(m.quotaShare) ? `${m.quotaShare.toFixed(1)}%` : '—'}</td>
      </tr>`;
    });
    return table([
      { label: 'Month' }, { label: 'Days', num: true }, { label: 'Accepted', num: true }, { label: 'Quota-dropped', num: true },
      { label: 'Attempted', num: true }, { label: 'Attempted/day', num: true }, { label: 'vs prior month', num: true },
      { label: 'vs daily budget', num: true }, { label: 'Quota-dropped share', num: true },
    ], rows);
  }

  function metric(name, value, target, why, src, ok) {
    const tone = ok === true ? 'sentry-good' : ok === false ? 'sentry-bad' : '';
    return `<tr><td>${esc(name)}</td><td class="num ${tone}">${esc(value)}</td><td class="num">${esc(target)}</td><td>${esc(why)}</td><td>${esc(src)}</td></tr>`;
  }

  function renderMetrics(budgetPerDay) {
    const { features, spans, totalDays, elapsed } = planModel();
    const daily = (LIVE?.daily || []).slice(0, -1);
    const last7 = daily.length >= 7 ? windowStats(daily.slice(-7)) : null;
    const projected = isNum(spans.used) && elapsed ? (spans.used / elapsed) * totalDays : null;
    const hasUsage = features.some((f) => isNum(f.used));
    const overFeatures = features.filter((f) => f.included != null && isNum(f.used) && f.used > f.included).length;
    const errs = LIVE?.error_outcomes_30d || null;
    const errDropped = errs
      ? Object.entries(errs).filter(([k]) => k !== 'accepted' && k !== 'client_discard').reduce((a, [, v]) => a + v, 0)
      : null;
    const projects = LIVE?.projects_period || [];
    const projTotal = projects.reduce((a, r) => a + r.accepted, 0);
    const top = projects[0];
    const opRows = Object.entries(LIVE?.span_ops_30d || {}).map(([project, ops]) => {
      const total = Object.values(ops).reduce((a, b) => a + b, 0);
      const [op, n] = Object.entries(ops).sort((a, b) => b[1] - a[1])[0] || ['—', 0];
      return metric(`Top span op share (${project})`, total ? `${op}: ${pct(n, total).toFixed(1)}%` : '—', '< 20%', 'Largest stored span op. Instrumentation lever', 'events, dataset spans, 30 days', total ? pct(n, total) < 20 : undefined);
    });

    return table(
      [{ label: 'Metric' }, { label: 'Live value', num: true }, { label: 'Target', num: true }, { label: 'Why it matters' }, { label: 'Source' }],
      [
        metric('Billed spans vs cap (this period)', `${fmtM(spans.used)} / ${fmtM(spans.included)}`, 'Under cap', 'Drives the span extra spend', 'stats_v2, span, accepted', isNum(spans.used) ? spans.used <= spans.included : undefined),
        metric('Projected spans this period', fmtM(projected), fmtM(spans.included), 'Where the period ends at the current rate', 'stats_v2, span, accepted', isNum(projected) ? projected <= spans.included : undefined),
        metric('Features over plan', hasUsage ? String(overFeatures) : '—', '0', 'Each one adds extra spend', 'stats_v2 per category', hasUsage ? overFeatures === 0 : undefined),
        metric('Attempted spans / day (last 7 days)', last7 ? fmtM(last7.attemptedPerDay) : '—', fmt(budgetPerDay), 'What the apps send. Must fall to the daily budget', 'stats_v2, span, all outcomes', last7 ? last7.attemptedPerDay <= budgetPerDay : undefined),
        metric('Accepted spans / day (last 7 days)', last7 ? fmt(last7.acceptedPerDay) : '—', '> 0, under budget', 'Zero means ingestion is blocked by quota', 'stats_v2, span, accepted', last7 ? last7.acceptedPerDay > 0 : undefined),
        metric('Quota-dropped share (last 7 days)', last7 && isNum(last7.quotaShare) ? `${last7.quotaShare.toFixed(1)}%` : '—', '0%', 'Ingestion is restored at 0%', 'stats_v2, reason span_usage_exceeded', last7 && isNum(last7.quotaShare) ? last7.quotaShare === 0 : undefined),
        metric('Error events dropped by Sentry (30 days)', isNum(errDropped) ? fmt(errDropped) : '—', '0', 'Must stay at zero. Span sampling does not affect errors', 'stats_v2, error, non-accepted outcomes', isNum(errDropped) ? errDropped === 0 : undefined),
        metric('Top project share of billed spans', top ? `${top.project}: ${pct(top.accepted, projTotal).toFixed(1)}%` : '—', 'Balanced', 'Where to cut first', 'stats_v2, span, by project'),
        ...opRows,
      ],
    );
  }

  function renderChanges() {
    const actions = (CONFIG?.actions || []).map((a) => `<tr>
      <td>${esc(a.id)}</td><td>${esc(a.action)}</td><td>${esc(a.project)}</td>
      <td><span class="sentry-status sentry-status--${esc(a.status)}">${esc(a.status)}</span></td></tr>`);
    const log = (CONFIG?.changes || []).map((c) => `<li>
      <span class="sentry-tag">${esc(c.date)}</span><span class="sentry-tag">${esc(c.project)}</span>
      ${esc(c.change)} <span class="sentry-status sentry-status--${esc(c.status)}">${esc(c.status)}</span></li>`).join('');
    return `${table([{ label: 'ID' }, { label: 'Action' }, { label: 'Project' }, { label: 'Status' }], actions)}
      <ul class="sentry-changelog">${log || '<li>No changes logged yet.</li>'}</ul>`;
  }

  function renderBody() {
    const ms = (LIVE?.months || []).map(periodStats);
    const { spans, totalDays } = planModel();
    const budgetPerDay = spans.included ? spans.included / totalDays : null;
    if (FROM_ID == null || !ms.some((m) => m.id === FROM_ID)) FROM_ID = ms.length > 1 ? ms[ms.length - 2].id : ms[0]?.id;
    if (TO_ID == null || !ms.some((m) => m.id === TO_ID)) TO_ID = ms[ms.length - 1]?.id;

    return `
      ${renderLiveStatus()}
      <section class="sentry-block" aria-label="Plan and cap">
        <div class="sentry-block__head"><h3>1. Plan cap and usage</h3></div>
        ${renderPlan()}
      </section>
      <section class="sentry-block" aria-label="Span sources">
        <div class="sentry-block__head"><h3>2. Which service produces the spans</h3></div>
        ${renderSources()}
      </section>
      <section class="sentry-block" aria-label="Recent trend">
        <div class="sentry-block__head"><h3>3. Did spans drop?</h3></div>
        ${renderWeek()}
        ${renderCompare(ms)}
      </section>
      <section class="sentry-block" aria-label="Monthly trend">
        <div class="sentry-block__head"><h3>4. Month by month</h3></div>
        ${renderMonthly(ms, budgetPerDay)}
        <p class="sentry-note">Attempted = accepted + all dropped. Per-day rates, so partial months compare fairly.</p>
      </section>
      <section class="sentry-block" aria-label="Tracking metrics">
        <div class="sentry-block__head"><h3>5. Tracking metrics</h3></div>
        ${renderMetrics(budgetPerDay)}
      </section>
      <section class="sentry-block" aria-label="Actions and change log">
        <div class="sentry-block__head"><h3>6. Actions and change log</h3></div>
        ${renderChanges()}
      </section>`;
  }

  async function render() {
    const body = document.getElementById('sentry-body');
    if (!body) return;
    if (!LOADED) body.innerHTML = '<p class="sentry-empty">Loading Sentry usage…</p>';
    await loadData();
    if (!CONFIG && !LIVE) {
      body.innerHTML = '<p class="sentry-empty">Could not load Sentry data (data/sentry-live.json, data/sentry-config.json).</p>';
      return;
    }
    body.innerHTML = renderBody();
    body.querySelectorAll('[data-sentry-select]').forEach((sel) => {
      sel.addEventListener('change', () => {
        if (sel.dataset.sentrySelect === 'from') FROM_ID = sel.value;
        else TO_ID = sel.value;
        render();
      });
    });
  }

  window.SentryUsage = { render };
})();
