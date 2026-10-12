(function (window, document) {
  'use strict';

  const TAB_CONTEXTS = {
    overview: {
      label: 'Overview',
      placeholder: 'Ask about release readiness or overall quality…',
      questions: ['Are we ready to release?', 'Give me an overview of current quality.', 'What needs attention?'],
    },
    attention: {
      label: 'Needs attention',
      placeholder: 'Ask about failures, defects, or flaky candidates…',
      questions: ['Summarize the current failures.', 'Which failures look flaky?', 'How are failures triaged?'],
    },
    trends: {
      label: 'Trends & AI usage',
      placeholder: 'Ask about quality trends or AI healing…',
      questions: ['What do the latest trends show?', 'Summarize AI healing usage.', 'What is the AI heal success rate?'],
    },
    suites: {
      label: 'Suite details',
      placeholder: 'Ask about suite health, coverage, or broken tests…',
      questions: ['Summarize suite health.', 'Where are the coverage gaps?', 'Which failures look flaky?'],
    },
    jira: {
      label: 'Jira Quality & Delivery',
      placeholder: 'Ask about Jira defects, blockers, priorities, or status…',
      questions: ['How many defects are open?', 'How many blockers are there?', 'Summarize Jira status.'],
    },
    ir: {
      label: 'Intelligent Reset',
      placeholder: 'Ask about the selected task’s actions, compliance, or duration…',
      questions: ['Why is Action Taken “-” on this task?', 'How long did this reset take?', 'Which required actions are still unconfirmed?'],
    },
    sentry: {
      label: 'Sentry',
      placeholder: 'Ask about Sentry spans, spend, quota, or reduction actions…',
      questions: ['What is our Sentry extra spend?', 'What is the span allowance and usage?', 'Which reduction actions are open?'],
    },
    'ir-studio': {
      label: 'Intelligent Reset Studio',
      placeholder: 'Ask about the selected Intelligent Reset task…',
      questions: ['Analyze the selected reset.', 'What challenges were found?', 'What action types were generated?'],
    },
    'shelf-mobile': {
      label: 'Shelf-Reset Mobile Assistant',
      placeholder: 'Ask about the selected reset’s associate actions…',
      questions: ['What did the associate perform?', 'Which actions are unconfirmed?', 'How long did the reset take?'],
    },
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function addText(parent, tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    parent.appendChild(element);
    return element;
  }

  function setOpen(open) {
    const panel = byId('agent-center-panel');
    const toggle = byId('agent-center-toggle');
    if (!panel || !toggle) return;
    panel.hidden = !open;
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) {
      updateTabContext();
      byId('agent-center-question')?.focus();
    }
  }

  function activeTab() {
    return document.querySelector('.tab-btn[aria-selected="true"]')?.getAttribute('data-tab') || 'overview';
  }

  function updateTabContext() {
    const context = TAB_CONTEXTS[activeTab()] || TAB_CONTEXTS.overview;
    const label = byId('agent-center-context');
    const input = byId('agent-center-question');
    const chips = byId('agent-center-chips');
    if (label) label.textContent = `Using ${context.label} tab evidence.`;
    if (input) input.placeholder = context.placeholder;
    if (!chips) return;
    chips.replaceChildren();
    context.questions.forEach((question) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.textContent = question;
      chip.addEventListener('click', () => {
        if (input) input.value = question;
        askQuestion(question);
      });
      chips.appendChild(chip);
    });
  }

  function renderError(message) {
    const target = byId('agent-center-result');
    if (!target) return;
    target.replaceChildren();
    const card = addText(target, 'div', 'agent-result-error', message);
    card.setAttribute('role', 'alert');
  }

  function evidenceText(evidence) {
    if (!Array.isArray(evidence) || !evidence.length) return '';
    return evidence.map((item) => {
      const value = typeof item.value === 'string' ? item.value : JSON.stringify(item.value);
      return `${item.source}: ${value}`;
    }).join(' · ');
  }

  function renderResult(result) {
    const target = byId('agent-center-result');
    if (!target) return;
    target.replaceChildren();

    const header = document.createElement('div');
    header.className = 'agent-result-header';
    const heading = document.createElement('div');
    addText(heading, 'span', 'agent-result-mode', `${result.mode} · ${result.access}`);
    addText(heading, 'h3', '', result.agent_name || 'Dashboard analyst');
    if (result.context_label) addText(heading, 'span', 'agent-result-context', `${result.context_label} tab`);
    const verdict = addText(header, 'span', `agent-verdict agent-verdict--${result.verdict}`, result.verdict);
    header.prepend(heading);
    verdict.title = `Confidence: ${result.confidence}`;
    target.appendChild(header);
    if (result.question) addText(target, 'p', 'agent-result-question', `You asked: ${result.question}`);
    addText(target, 'p', 'agent-result-answer', result.answer || result.summary || '');
    if (result.model_note) addText(target, 'p', 'agent-result-run-id', result.model_note);

    const findings = Array.isArray(result.findings) ? result.findings : [];
    if (findings.length) {
      addText(target, 'h4', '', 'Evidence');
      const list = document.createElement('div');
      list.className = 'agent-findings';
      findings.forEach((finding) => {
        const item = document.createElement('article');
        item.className = `agent-finding agent-finding--${finding.severity || 'info'}`;
        addText(item, 'strong', '', finding.title || 'Finding');
        addText(item, 'p', '', finding.detail || '');
        const evidence = evidenceText(finding.evidence);
        if (evidence) addText(item, 'small', '', evidence);
        list.appendChild(item);
      });
      target.appendChild(list);
    }

    const recommendations = Array.isArray(result.recommendations) ? result.recommendations : [];
    if (recommendations.length) {
      addText(target, 'h4', '', 'Recommended next steps');
      const list = document.createElement('ol');
      recommendations.forEach((recommendation) => addText(list, 'li', '', recommendation));
      target.appendChild(list);
    }

    addText(target, 'p', 'agent-result-sources', `Sources: ${(result.sources || []).join(' · ') || 'No sources returned'}`);
    addText(target, 'p', 'agent-result-run-id', `Run ${result.run_id} · ${new Date(result.generated_at).toLocaleString()}`);
  }

  async function askQuestion(questionText) {
    const question = (questionText || byId('agent-center-question')?.value || '').trim();
    const button = byId('agent-center-run');
    const target = byId('agent-center-result');
    if (!button || !target) return;
    if (!question) {
      renderError('Enter a question first.');
      byId('agent-center-question')?.focus();
      return;
    }

    const payload = {
      question,
      active_tab: activeTab(),
      instance: byId('ir-instance-picker')?.value || '',
      task_id: byId('ir-simple-task-input')?.value || '',
    };
    button.disabled = true;
    button.textContent = 'Analyzing…';
    target.replaceChildren();
    addText(target, 'p', 'data-note', 'Reading the connected evidence for your question…');
    try {
      const response = await fetch('/api/runner/agents/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok || data.status !== 'success') {
        throw new Error(data.error?.message || data.message || `Agent request failed (${response.status})`);
      }
      renderResult(data);
    } catch (error) {
      renderError(error.message || 'The analyst could not answer.');
    } finally {
      button.disabled = false;
      button.textContent = 'Analyze';
    }
  }

  function init() {
    byId('agent-center-toggle')?.addEventListener('click', () => setOpen(byId('agent-center-panel')?.hidden));
    byId('agent-center-close')?.addEventListener('click', () => setOpen(false));
    byId('agent-center-form')?.addEventListener('submit', (event) => {
      event.preventDefault();
      askQuestion();
    });
    byId('agent-center-question')?.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        askQuestion();
      }
    });
    document.addEventListener('click', (event) => {
      if (event.target.closest('.tab-btn')) updateTabContext();
    });
    updateTabContext();
  }

  window.DashboardAgents = { open: () => setOpen(true), ask: askQuestion };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window, document);
