/**
 * Test Case Generator UI
 * Handles modal for generating BDD scenarios from Jira issues
 */

class TestCaseGenerator {
  constructor() {
    this.isGenerating = false;
    this.jiraIssues = [];
    this.init();
  }

  async init() {
    // Create modal HTML
    this.createModal();
    this.wireEventListeners();

    // Add button to Jira tab
    this.addButtonToJiraTab();

    // Load Jira issues when modal opens
    const generateBtn = document.getElementById('generate-test-cases-btn');
    if (generateBtn) {
      generateBtn.addEventListener('click', () => this.openModal());
    }

    console.log('✓ Test Case Generator initialized');
  }

  addButtonToJiraTab() {
    // Try to add button immediately, with retries if panel not ready
    const tryAddButton = () => {
      const jiraPanel = document.getElementById('panel-jira');
      if (!jiraPanel) {
        // Retry after a short delay if panel not found
        setTimeout(tryAddButton, 100);
        return;
      }

      // Check if button already exists
      if (document.getElementById('generate-test-cases-btn')) return;

      // Create button
      const btn = document.createElement('button');
      btn.id = 'generate-test-cases-btn';
      btn.className = 'btn btn--primary';
      btn.type = 'button';
      btn.textContent = '⚡ Generate Test Cases';
      btn.title = 'Generate BDD scenarios from Jira issues using Claude AI';

      // Insert at the top of Jira panel
      const jiraHeader = jiraPanel.querySelector('.tab-panel__header');
      if (jiraHeader) {
        // Add to existing header
        jiraHeader.appendChild(btn);
      } else {
        // Create a toolbar if no header exists
        const jiraContent = jiraPanel.querySelector('#jira-content');
        if (jiraContent) {
          let toolbar = jiraPanel.querySelector('[data-jira-toolbar]');
          if (!toolbar) {
            toolbar = document.createElement('div');
            toolbar.setAttribute('data-jira-toolbar', 'true');
            jiraContent.parentNode.insertBefore(toolbar, jiraContent);
          }
          toolbar.appendChild(btn);
        }
      }
    };

    tryAddButton();
  }

  createModal() {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.id = 'test-case-generator-modal';
    modal.className = 'modal modal--test-generator';
    modal.innerHTML = `
      <div class="modal__overlay"></div>
      <div class="modal__content">
        <div class="modal__header">
          <h2 class="modal__title">⚡ Generate Test Cases (BDD Scenarios)</h2>
          <button class="modal__close" type="button" aria-label="Close">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div class="modal__body">
          <!-- Step 1: Select Issues -->
          <div class="generator-step" id="step-select">
            <h3 class="step-title">Step 1: Select Issues to Generate Test Cases For</h3>

            <div class="filter-controls">
              <input
                type="text"
                id="issue-search"
                class="input"
                placeholder="Search issues by key or summary..."
                aria-label="Search issues"
              />
              <label class="checkbox-label">
                <input type="checkbox" id="select-all-checkbox" />
                <span>Select All</span>
              </label>
            </div>

            <div class="issues-list" id="issues-list">
              <div class="loading">Loading issues...</div>
            </div>

            <div class="selection-summary">
              <span id="selected-count">0</span> / <span id="total-count">0</span> issues selected
            </div>
          </div>

          <!-- Step 2: Generation Progress -->
          <div class="generator-step" id="step-progress" style="display: none;">
            <h3 class="step-title">Step 2: Generating BDD Scenarios</h3>

            <div class="progress-container">
              <div class="progress-bar">
                <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
              </div>
              <p class="progress-text" id="progress-text">Initializing...</p>
            </div>

            <div class="generation-status" id="generation-status">
              <div class="status-item">
                <span class="status-label">Issues Processed:</span>
                <span class="status-value" id="status-processed">0</span>
              </div>
              <div class="status-item">
                <span class="status-label">Scenarios Generated:</span>
                <span class="status-value" id="status-scenarios">0</span>
              </div>
              <div class="status-item">
                <span class="status-label">API Provider:</span>
                <span class="status-value" id="status-provider">Claude</span>
              </div>
              <div class="status-item">
                <span class="status-label">Estimated Time:</span>
                <span class="status-value" id="status-time">~2 minutes</span>
              </div>
            </div>
          </div>

          <!-- Step 3: Results -->
          <div class="generator-step" id="step-results" style="display: none;">
            <h3 class="step-title">Step 3: Generation Complete!</h3>

            <div class="results-summary" id="results-summary">
              <div class="summary-card">
                <div class="summary-value" id="result-total">0</div>
                <div class="summary-label">Total Scenarios</div>
              </div>
              <div class="summary-card">
                <div class="summary-value" id="result-success">0</div>
                <div class="summary-label">Successful</div>
              </div>
              <div class="summary-card">
                <div class="summary-value" id="result-failed">0</div>
                <div class="summary-label">Failed</div>
              </div>
            </div>

            <div id="error-message" class="error-box" style="display: none;"></div>

            <h4 class="subsection-title">Generated Scenarios Preview</h4>
            <div class="scenarios-preview" id="scenarios-preview">
              <div class="loading">Loading results...</div>
            </div>
          </div>
        </div>

        <div class="modal__footer">
          <button class="btn btn--ghost" id="modal-cancel-btn" type="button">Cancel</button>
          <button class="btn btn--primary" id="modal-action-btn" type="button">Generate</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
  }

  wireEventListeners() {
    const modal = document.getElementById('test-case-generator-modal');
    const overlay = modal.querySelector('.modal__overlay');
    const closeBtn = modal.querySelector('.modal__close');
    const cancelBtn = modal.querySelector('#modal-cancel-btn');
    const actionBtn = modal.querySelector('#modal-action-btn');

    overlay.addEventListener('click', () => this.closeModal());
    closeBtn.addEventListener('click', () => this.closeModal());
    cancelBtn.addEventListener('click', () => this.closeModal());
    actionBtn.addEventListener('click', () => this.handleActionClick());

    // Issue search
    const searchInput = modal.querySelector('#issue-search');
    searchInput.addEventListener('input', (e) => this.filterIssues(e.target.value));

    // Select all checkbox
    const selectAllCheckbox = modal.querySelector('#select-all-checkbox');
    selectAllCheckbox.addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));
  }

  async openModal() {
    const modal = document.getElementById('test-case-generator-modal');
    modal.classList.add('is-open');

    // Load Jira issues
    await this.loadJiraIssues();
    this.showStep('select');
  }

  closeModal() {
    const modal = document.getElementById('test-case-generator-modal');
    modal.classList.remove('is-open');

    // Reset to step 1
    if (!this.isGenerating) {
      this.showStep('select');
    }
  }

  async loadJiraIssues() {
    try {
      const response = await fetch('/api/jira-issues');
      const data = await response.json();

      this.jiraIssues = data.issues || [];
      this.renderIssuesList();
    } catch (error) {
      console.error('Error loading Jira issues:', error);
      const issuesList = document.getElementById('issues-list');
      issuesList.innerHTML = `<div class="error">Failed to load issues: ${error.message}</div>`;
    }
  }

  renderIssuesList() {
    const issuesList = document.getElementById('issues-list');
    const totalCount = document.getElementById('total-count');

    totalCount.textContent = this.jiraIssues.length;

    if (this.jiraIssues.length === 0) {
      issuesList.innerHTML = '<div class="empty-state">No Jira issues available. Generate mock data first using: python test-local.py</div>';
      return;
    }

    issuesList.innerHTML = this.jiraIssues.map(issue => `
      <div class="issue-item">
        <input
          type="checkbox"
          value="${issue.key}"
          class="issue-checkbox"
          data-summary="${issue.summary}"
        />
        <div class="issue-info">
          <div class="issue-key">${issue.key}</div>
          <div class="issue-summary">${issue.summary}</div>
          <div class="issue-type">${issue.fields?.issuetype?.name || 'Unknown'}</div>
        </div>
      </div>
    `).join('');

    // Wire checkboxes
    issuesList.querySelectorAll('.issue-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', () => this.updateSelectionCount());
    });
  }

  filterIssues(searchTerm) {
    const issuesList = document.getElementById('issues-list');
    const items = issuesList.querySelectorAll('.issue-item');

    items.forEach(item => {
      const key = item.querySelector('.issue-key').textContent;
      const summary = item.querySelector('.issue-summary').textContent;
      const matches = key.toLowerCase().includes(searchTerm.toLowerCase()) ||
                     summary.toLowerCase().includes(searchTerm.toLowerCase());
      item.style.display = matches ? '' : 'none';
    });
  }

  toggleSelectAll(checked) {
    const issuesList = document.getElementById('issues-list');
    const checkboxes = issuesList.querySelectorAll('.issue-checkbox:not(.hidden)');

    checkboxes.forEach(checkbox => {
      if (checkbox.closest('.issue-item').style.display !== 'none') {
        checkbox.checked = checked;
      }
    });

    this.updateSelectionCount();
  }

  updateSelectionCount() {
    const issuesList = document.getElementById('issues-list');
    const checkboxes = issuesList.querySelectorAll('.issue-checkbox');
    const selectedCount = Array.from(checkboxes).filter(cb => cb.checked).length;

    document.getElementById('selected-count').textContent = selectedCount;
  }

  getSelectedIssues() {
    const issuesList = document.getElementById('issues-list');
    const checkboxes = issuesList.querySelectorAll('.issue-checkbox:checked');

    return Array.from(checkboxes).map(cb => cb.value);
  }

  showStep(stepName) {
    const steps = document.querySelectorAll('.generator-step');
    steps.forEach(step => step.style.display = 'none');

    const targetStep = document.getElementById(`step-${stepName}`);
    if (targetStep) {
      targetStep.style.display = 'block';
    }

    // Update action button
    const actionBtn = document.querySelector('#modal-action-btn');
    if (stepName === 'select') {
      actionBtn.textContent = 'Generate';
    } else if (stepName === 'results') {
      actionBtn.textContent = 'Close';
    }
  }

  async handleActionClick() {
    const currentStep = this.getCurrentStep();

    if (currentStep === 'select') {
      const selectedIssues = this.getSelectedIssues();

      if (selectedIssues.length === 0) {
        alert('Please select at least one issue');
        return;
      }

      await this.generateTestCases(selectedIssues);
    } else if (currentStep === 'results') {
      this.closeModal();
    }
  }

  getCurrentStep() {
    const steps = document.querySelectorAll('.generator-step');
    for (let step of steps) {
      if (step.style.display !== 'none') {
        return step.id.replace('step-', '');
      }
    }
    return 'select';
  }

  async generateTestCases(issueKeys) {
    this.isGenerating = true;
    this.showStep('progress');

    try {
      // Start generation
      const response = await fetch('/api/generate-test-cases', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          issueKeys: issueKeys,
          maxIssues: issueKeys.length
        })
      });

      const result = await response.json();

      if (response.ok && result.status === 'success') {
        // Show results
        this.displayResults(result.data);
        this.showStep('results');
      } else {
        this.showError(result.message || 'Unknown error occurred');
        this.showStep('results');
      }
    } catch (error) {
      console.error('Error generating test cases:', error);
      this.showError(`Generation failed: ${error.message}`);
      this.showStep('results');
    } finally {
      this.isGenerating = false;
    }
  }

  displayResults(data) {
    const totalScenarios = data.testCases?.reduce((sum, tc) => sum + (tc.scenarios?.length || 0), 0) || 0;
    const successCount = data.successfulGenerations || 0;
    const failedCount = data.failedGenerations || 0;

    document.getElementById('result-total').textContent = totalScenarios;
    document.getElementById('result-success').textContent = successCount;
    document.getElementById('result-failed').textContent = failedCount;

    // Show scenarios preview
    const preview = document.getElementById('scenarios-preview');
    if (data.testCases && data.testCases.length > 0) {
      preview.innerHTML = data.testCases.map(tc => `
        <div class="scenario-group">
          <div class="scenario-group-title">
            <strong>${tc.issueKey}</strong>: ${tc.summary}
          </div>
          <div class="scenarios-list">
            ${(tc.scenarios || []).slice(0, 3).map((scenario, idx) => `
              <div class="scenario-item">
                <div class="scenario-badge scenario-badge--${scenario.type}">${scenario.type}</div>
                <div class="scenario-title">${scenario.title}</div>
                <div class="scenario-meta">
                  Priority: ${scenario.priority} • Category: ${scenario.category}
                </div>
              </div>
            `).join('')}
            ${tc.scenarios && tc.scenarios.length > 3 ? `
              <div class="scenario-more">+${tc.scenarios.length - 3} more scenarios...</div>
            ` : ''}
          </div>
        </div>
      `).join('');
    } else {
      preview.innerHTML = '<div class="empty-state">No test cases generated</div>';
    }
  }

  showError(message) {
    const errorBox = document.getElementById('error-message');
    errorBox.textContent = message;
    errorBox.style.display = 'block';
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.testCaseGenerator = new TestCaseGenerator();
  });
} else {
  window.testCaseGenerator = new TestCaseGenerator();
}
