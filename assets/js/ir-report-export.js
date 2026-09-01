/**
 * Shared Excel (CSV) export for Intelligent Reset HTML reports.
 * Auto-injects export button on Action Count & State Transition dashboards.
 */
(function () {
  if (window.__irExportReady) return;
  window.__irExportReady = true;

  function csvEscape(text) {
    return `"${String(text || '').replace(/"/g, '""').replace(/\r?\n/g, ' ').trim()}"`;
  }

  function appendTableCsv(csv, sectionTitle, table) {
    if (!table || !table.rows.length) return csv;
    csv += `\r\n${csvEscape(`--- ${sectionTitle} ---`)}\r\n`;
    for (const row of table.rows) {
      const cells = [...row.cells].map((c) => csvEscape(c.innerText));
      if (cells.length) csv += `${cells.join(',')}\r\n`;
    }
    return csv;
  }

  function extractTaskId() {
    const p = document.querySelector('.header-left p, .header-title p')?.innerText || '';
    const fromP = p.match(/Task\s*#(\d+)/i);
    if (fromP) return fromP[1];
    const fromTitle = document.title.match(/Task\s*#(\d+)/i);
    if (fromTitle) return fromTitle[1];
    const fromFile = window.location.pathname.match(/Task[_-](\d+)/i);
    return fromFile ? fromFile[1] : 'report';
  }

  function isE2EReport(title) {
    return /Action Count|Resumption Audit/i.test(title);
  }

  function exportReportToExcel() {
    let csv = '\uFEFF';
    const taskId = extractTaskId();
    const reportTitle = document.querySelector('h1')?.innerText || 'IR Report';
    csv += `${csvEscape('Report')},${csvEscape(reportTitle)}\r\n`;
    csv += `${csvEscape('Task ID')},${csvEscape(taskId)}\r\n`;

    document.querySelectorAll('.kpi-card').forEach((card) => {
      csv += `${csvEscape(card.querySelector('.kpi-label')?.innerText)},${csvEscape(card.querySelector('.kpi-value')?.innerText)}\r\n`;
    });

    if (isE2EReport(reportTitle)) {
      document.querySelectorAll('.main-card').forEach((card, idx) => {
        const title = (card.querySelector('.card-title')?.innerText || `Section ${idx + 1}`)
          .replace(/\s+/g, ' ')
          .trim();
        const tables = card.querySelectorAll('table');
        tables.forEach((table, tidx) => {
          const suffix = tables.length > 1 ? ` (${tidx + 1})` : '';
          csv = appendTableCsv(csv, title + suffix, table);
        });
      });
      ['actionsTable', 'trafficTable'].forEach((id) => {
        const table = document.getElementById(id);
        if (table) csv = appendTableCsv(csv, id, table);
      });
    } else {
      document.querySelectorAll('.tab-content').forEach((tab) => {
        const tabLabel = tab.id || 'tab';
        tab.querySelectorAll('table.report-table, table#masterTable, table#masterTestTable').forEach((table, idx) => {
          if (table.closest('.phone-screen')) return;
          csv = appendTableCsv(csv, `${tabLabel} table ${idx + 1}`, table);
        });
      });
    }

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    const suffix = isE2EReport(reportTitle)
      ? 'Action_Count_Resumption_Audit'
      : 'State_Transition_Validation';
    link.download = `IR_Task_${taskId}_${suffix}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }

  window.exportReportToExcel = exportReportToExcel;
  window.exportFullReportToExcel = exportReportToExcel;

  function injectButton() {
    if (document.getElementById('ir-export-excel-btn')) return;
    const title = document.querySelector('h1')?.innerText || '';
    if (!/Intelligent Reset/i.test(title)) return;

    const btn = document.createElement('button');
    btn.id = 'ir-export-excel-btn';
    btn.type = 'button';
    btn.textContent = '📊 Export to Excel';
    btn.title = 'Export all report tables to Excel (CSV)';
    btn.onclick = exportReportToExcel;
    btn.style.cssText = [
      'background:#107C41',
      'color:#fff',
      'border:1px solid #0B5C30',
      'padding:8px 14px',
      'border-radius:8px',
      'font-size:12px',
      'font-weight:700',
      'cursor:pointer',
      'margin-right:8px',
      'white-space:nowrap',
      'font-family:inherit',
    ].join(';');

    const target = document.querySelector('.header-badges') || document.querySelector('.header-meta');
    if (target) {
      target.insertBefore(btn, target.firstChild);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectButton);
  } else {
    injectButton();
  }
})();
