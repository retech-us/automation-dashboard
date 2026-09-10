/**
 * Test Case Generator UI
 * Handles modal for generating BDD scenarios from Jira issues
 */

class TestCaseGenerator {
  constructor() {
    console.log('🚀 TestCaseGenerator constructor called');
    this.isGenerating = false;
    this.jiraIssues = [];
    this.generatedIssueKeys = [];
    this.sprints = new Set();
    this.versions = new Set();
    this.types = new Set();
    this.statuses = new Set();
    this.init();
  }

  async init() {
    console.log('🔧 TestCaseGenerator.init() starting');
    // Create modal HTML
    this.createModal();
    this.wireEventListeners();

    // Add main button to Generate tab
    this.addMainGenerateButton();

    // Also add button to Jira tab header for quick access
    this.addButtonToJiraTab();

    console.log('✓ Test Case Generator initialized');
  }

  addMainGenerateButton() {
    // Use event delegation - attach listener to document
    const self = this;

    // Listen for clicks on the main generate button using event delegation
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('#generate-btn-main');
      if (!btn) return;

      console.log('🔘 Main Generate Test Cases button clicked!');
      console.log('Button element:', btn);
      e.preventDefault();
      e.stopPropagation();

      console.log('Calling openModal()...');
      self.openModal().catch(err => {
        console.error('Error in openModal:', err);
      });
    }, true); // Use capture phase to ensure we catch the click

    console.log('✓ Main button listener attached via event delegation');
  }

  addButtonToJiraTab() {
    // Create the button element (reusable)
    const createButton = () => {
      const btn = document.createElement('button');
      btn.id = 'generate-test-cases-btn';
      btn.className = 'btn';
      btn.type = 'button';
      btn.textContent = '⚡ Generate Test Cases';
      btn.title = 'Generate BDD scenarios from Jira issues using Claude AI';
      btn.style.cssText = 'background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 12px; padding: 10px 18px; cursor: pointer; font-weight: 600; white-space: nowrap;';
      btn.addEventListener('click', () => {
        console.log('🔘 Generate Test Cases button clicked');
        this.openModal();
      });
      return btn;
    };

    // Try to add button, with retries and re-adds since jira-tracker clears headerActions
    const tryAddButton = () => {
      const jiraPanel = document.getElementById('panel-jira');
      if (!jiraPanel) {
        console.log('⏳ Waiting for #panel-jira...');
        setTimeout(tryAddButton, 100);
        return;
      }

      const headerActions = jiraPanel.querySelector('#jira-header-actions');
      if (!headerActions) {
        console.log('⏳ Waiting for #jira-header-actions...');
        setTimeout(tryAddButton, 100);
        return;
      }

      // Check if button already exists
      if (document.getElementById('generate-test-cases-btn')) {
        console.log('✓ Button already exists');
        return;
      }

      // Add button
      const btn = createButton();
      headerActions.appendChild(btn);
      console.log('✓ Button added to #jira-header-actions');
    };

    // Initial add
    tryAddButton();

    // Re-add button periodically (jira-tracker clears headerActions with innerHTML)
    // Check every 2 seconds if button is still there, re-add if missing
    setInterval(() => {
      const headerActions = document.getElementById('jira-header-actions');
      if (headerActions && !document.getElementById('generate-test-cases-btn')) {
        const btn = createButton();
        headerActions.insertBefore(btn, headerActions.firstChild);
        console.log('🔄 Button was removed, re-added to #jira-header-actions');
      }
    }, 2000);
  }

  createModal() {
    console.log('Creating modal...');
    // Create modal overlay
    const modal = document.createElement('div');
    modal.id = 'test-case-generator-modal';
    modal.className = 'modal modal--test-generator';
    console.log('Modal element created:', modal);
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

            <div class="filter-section">
              <h4 class="filter-title">Filter by:</h4>
              <div class="filter-grid">
                <div class="filter-group">
                  <label for="filter-sprint">Sprint:</label>
                  <select id="filter-sprint" class="input filter-select">
                    <option value="">All Sprints</option>
                  </select>
                </div>

                <div class="filter-group">
                  <label for="filter-version">Fix Version:</label>
                  <select id="filter-version" class="input filter-select">
                    <option value="">All Versions</option>
                  </select>
                </div>

                <div class="filter-group">
                  <label for="filter-type">Issue Type:</label>
                  <select id="filter-type" class="input filter-select">
                    <option value="">All Types</option>
                  </select>
                </div>

                <div class="filter-group">
                  <label for="filter-status">Status:</label>
                  <select id="filter-status" class="input filter-select">
                    <option value="">All Statuses</option>
                  </select>
                </div>
              </div>
            </div>

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
              <span id="already-generated" style="color: #10b981; margin-left: 16px; font-size: 12px; display: none;">
                ✓ <span id="already-generated-count">0</span> already have test cases
              </span>
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
    console.log('✓ Modal appended to body');
    console.log('Modal in DOM:', document.getElementById('test-case-generator-modal'));
  }

  wireEventListeners() {
    console.log('Wiring event listeners...');
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
    searchInput.addEventListener('input', (e) => this.filterIssues());

    // Filter dropdowns
    const filterSelects = modal.querySelectorAll('.filter-select');
    filterSelects.forEach(select => {
      select.addEventListener('change', () => this.filterIssues());
    });

    // Select all checkbox
    const selectAllCheckbox = modal.querySelector('#select-all-checkbox');
    selectAllCheckbox.addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));
  }

  async openModal() {
    console.log('📂 openModal() called');

    // Check if modal exists
    const modal = document.getElementById('test-case-generator-modal');
    if (!modal) {
      console.error('❌ Modal not found!');
      alert('Modal not initialized. Please refresh the page.');
      return;
    }
    console.log('✓ Modal found');

    // Always check for valid credentials first
    if (!window.credentialsManager) {
      console.error('❌ credentialsManager not initialized');
      alert('Credentials manager not initialized. Please refresh the page.');
      return;
    }

    console.log('✓ credentialsManager exists');

    // Check if valid session exists
    const isSessionValid = window.credentialsManager.isSessionValid();
    console.log('Session valid?', isSessionValid);

    if (isSessionValid) {
      console.log('✓ Valid session found - opening generator modal');
      // Valid session - open generator directly
      modal.classList.add('is-open');
      console.log('✓ Added is-open class to modal');
      await this.loadJiraIssues();
      this.showStep('select');
    } else {
      console.log('❌ No valid session - opening credentials dialog');
      // No valid session - open credentials dialog
      console.log('Calling credentialsManager.openModal()...');
      window.credentialsManager.openModal();
      console.log('credentialsManager.openModal() returned');
    }
  }

  // Make this method accessible to credentials manager
  openGenerator() {
    const modal = document.getElementById('test-case-generator-modal');
    if (modal) {
      modal.classList.add('is-open');
    }
    this.loadJiraIssues().then(() => {
      this.showStep('select');
    });
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

      // Load already-generated test cases
      try {
        const tcResponse = await fetch('/api/test-cases');
        const tcData = await tcResponse.json();
        this.generatedIssueKeys = (tcData.testCases || []).map(tc => tc.issueKey);
      } catch (e) {
        this.generatedIssueKeys = [];
      }

      // Filter out already-generated issues
      const availableIssues = this.jiraIssues.filter(issue => !this.generatedIssueKeys.includes(issue.key));
      this.jiraIssues = availableIssues;

      // Collect unique values for filters
      this.jiraIssues.forEach(issue => {
        const type = issue.fields?.issuetype?.name;
        if (type) this.types.add(type);
        const status = issue.fields?.status?.name;
        if (status) this.statuses.add(status);
      });

      this.populateFilterDropdowns();
      this.renderIssuesList();

      // Show count of already generated
      if (this.generatedIssueKeys.length > 0) {
        const alreadyGenElement = document.getElementById('already-generated');
        if (alreadyGenElement) {
          alreadyGenElement.style.display = 'inline-block';
          document.getElementById('already-generated-count').textContent = this.generatedIssueKeys.length;
        }
      }
    } catch (error) {
      console.error('Error loading Jira issues:', error);
      const issuesList = document.getElementById('issues-list');
      issuesList.innerHTML = `<div class="error">Failed to load issues: ${error.message}</div>`;
    }
  }

  populateFilterDropdowns() {
    const typeSelect = document.getElementById('filter-type');
    if (typeSelect) {
      Array.from(this.types).sort().forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        typeSelect.appendChild(option);
      });
    }

    const statusSelect = document.getElementById('filter-status');
    if (statusSelect) {
      Array.from(this.statuses).sort().forEach(status => {
        const option = document.createElement('option');
        option.value = status;
        option.textContent = status;
        statusSelect.appendChild(option);
      });
    }
  }

  renderIssuesList() {
    const issuesList = document.getElementById('issues-list');
    const totalCount = document.getElementById('total-count');

    totalCount.textContent = this.jiraIssues.length;

    if (this.jiraIssues.length === 0) {
      issuesList.innerHTML = '<div class="empty-state">No Jira issues available or all have test cases generated</div>';
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
          <div class="issue-meta">
            <span class="issue-type">${issue.fields?.issuetype?.name || 'Unknown'}</span>
            <span class="issue-status">${issue.fields?.status?.name || 'Unknown'}</span>
          </div>
        </div>
      </div>
    `).join('');

    // Wire checkboxes
    issuesList.querySelectorAll('.issue-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', () => this.updateSelectionCount());
    });
  }

  filterIssues() {
    const searchTerm = document.getElementById('issue-search').value.toLowerCase();
    const typeFilter = document.getElementById('filter-type').value;
    const statusFilter = document.getElementById('filter-status').value;

    const issuesList = document.getElementById('issues-list');
    const items = issuesList.querySelectorAll('.issue-item');

    items.forEach(item => {
      const key = item.querySelector('.issue-key').textContent;
      const summary = item.querySelector('.issue-summary').textContent;
      const type = item.querySelector('.issue-type').textContent;
      const status = item.querySelector('.issue-status').textContent;

      const matchesSearch = key.toLowerCase().includes(searchTerm) ||
                           summary.toLowerCase().includes(searchTerm);
      const matchesType = !typeFilter || type === typeFilter;
      const matchesStatus = !statusFilter || status === statusFilter;

      const shouldShow = matchesSearch && matchesType && matchesStatus;
      item.style.display = shouldShow ? '' : 'none';
    });

    this.updateSelectionCount();
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

    // Disable action button during generation
    const actionBtn = document.querySelector('#modal-action-btn');
    if (actionBtn) {
      actionBtn.disabled = true;
      actionBtn.style.opacity = '0.5';
      actionBtn.style.cursor = 'not-allowed';
    }

    // Update progress
    this.updateProgress(0, `Initializing test case generation for ${issueKeys.length} issue(s)...`);

    try {
      // Get credentials from session
      if (!window.credentialsManager) {
        this.showError('Credentials manager not available');
        this.showStep('results');
        return;
      }

      const session = window.credentialsManager.getSession();
      if (!session) {
        this.showError('Session expired. Please enter credentials again.');
        this.showStep('results');
        window.credentialsManager.openModal();
        return;
      }

      this.updateProgress(10, 'Validating credentials...');

      // Prepare request data with credentials
      const requestData = {
        issueKeys: issueKeys,
        maxIssues: issueKeys.length,
        // Jira credentials
        jira_base_url: session.jira_base_url,
        jira_user_email: session.jira_user_email,
        jira_api_token: session.jira_api_token,
        // AI provider
        ai_provider: session.ai_provider
      };

      // Add AI provider credentials
      if (session.ai_provider === 'anthropic') {
        requestData.anthropic_api_key = session.anthropic_api_key;
      } else if (session.ai_provider === 'openai') {
        requestData.openai_api_key = session.openai_api_key;
        if (session.openai_api_base) {
          requestData.openai_api_base = session.openai_api_base;
        }
      }

      this.updateProgress(20, 'Sending request to server...');

      // Start generation
      const response = await fetch('/api/generate-test-cases', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });

      this.updateProgress(50, 'Processing results...');

      const result = await response.json();

      if (response.ok && result.status === 'success') {
        this.updateProgress(90, 'Finalizing...');
        // Show results
        this.displayResults(result.data);
        this.updateProgress(100, 'Complete!');
        this.showStep('results');
      } else {
        const errorMsg = result.message || `Server error: ${response.status}`;
        this.showError(errorMsg);
        this.showStep('results');
      }
    } catch (error) {
      console.error('Error generating test cases:', error);
      this.showError(`Generation failed: ${error.message}`);
      this.showStep('results');
    } finally {
      this.isGenerating = false;
      // Re-enable button
      if (actionBtn) {
        actionBtn.disabled = false;
        actionBtn.style.opacity = '1';
        actionBtn.style.cursor = 'pointer';
      }
    }
  }

  updateProgress(percent, message) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');

    if (progressFill) {
      progressFill.style.width = percent + '%';
    }
    if (progressText) {
      progressText.textContent = message;
    }

    console.log(`Progress: ${percent}% - ${message}`);
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
      preview.innerHTML = data.testCases.map((tc, tcIdx) => `
        <div class="scenario-group">
          <div class="scenario-group-title">
            <strong>${tc.issueKey}</strong>: ${tc.summary}
          </div>
          <div class="scenarios-list" id="scenarios-list-${tcIdx}">
            ${(tc.scenarios || []).slice(0, 3).map((scenario, idx) => `
              <div class="scenario-item">
                <div class="scenario-badge scenario-badge--${scenario.type}">${scenario.type}</div>
                <div class="scenario-title">${scenario.title}</div>
                <div class="scenario-meta">
                  Priority: ${scenario.priority} • Category: ${scenario.category}
                </div>
                <div class="scenario-actions" style="margin-top: 8px; display: flex; gap: 8px;">
                  <button class="scenario-expand-btn" data-scenario-json='${JSON.stringify(scenario).replace(/'/g, "&apos;")}' style="padding: 4px 8px; font-size: 12px; border: 1px solid #0066cc; color: #0066cc; background: white; border-radius: 4px; cursor: pointer;">
                    👁️ View Details
                  </button>
                  <button class="scenario-approve-btn" data-scenario-json='${JSON.stringify(scenario).replace(/'/g, "&apos;")}' style="padding: 4px 8px; font-size: 12px; border: none; background: #4caf50; color: white; border-radius: 4px; cursor: pointer;">
                    ✓ Approve
                  </button>
                  <button class="scenario-reject-btn" data-scenario-json='${JSON.stringify(scenario).replace(/'/g, "&apos;")}' style="padding: 4px 8px; font-size: 12px; border: none; background: #f44336; color: white; border-radius: 4px; cursor: pointer;">
                    ✗ Reject
                  </button>
                </div>
              </div>
            `).join('')}
            ${tc.scenarios && tc.scenarios.length > 3 ? `
              <div class="scenario-more" data-group="${tcIdx}" data-expanded="false">
                <span class="scenario-more-text">+${tc.scenarios.length - 3} more scenarios...</span>
              </div>
              <div class="hidden-scenarios" id="hidden-scenarios-${tcIdx}" style="display: none;">
                ${(tc.scenarios || []).slice(3).map((scenario, idx) => `
                  <div class="scenario-item">
                    <div class="scenario-badge scenario-badge--${scenario.type}">${scenario.type}</div>
                    <div class="scenario-title">${scenario.title}</div>
                    <div class="scenario-meta">
                      Priority: ${scenario.priority} • Category: ${scenario.category}
                    </div>
                    <div class="scenario-actions" style="margin-top: 8px; display: flex; gap: 8px;">
                      <button class="scenario-expand-btn" data-scenario-json='${JSON.stringify(scenario).replace(/'/g, "&apos;")}' style="padding: 4px 8px; font-size: 12px; border: 1px solid #0066cc; color: #0066cc; background: white; border-radius: 4px; cursor: pointer;">
                        👁️ View Details
                      </button>
                      <button class="scenario-approve-btn" data-scenario-json='${JSON.stringify(scenario).replace(/'/g, "&apos;")}' style="padding: 4px 8px; font-size: 12px; border: none; background: #4caf50; color: white; border-radius: 4px; cursor: pointer;">
                        ✓ Approve
                      </button>
                      <button class="scenario-reject-btn" data-scenario-json='${JSON.stringify(scenario).replace(/'/g, "&apos;")}' style="padding: 4px 8px; font-size: 12px; border: none; background: #f44336; color: white; border-radius: 4px; cursor: pointer;">
                        ✗ Reject
                      </button>
                    </div>
                  </div>
                `).join('')}
              </div>
            ` : ''}
          </div>
        </div>
      `).join('');

      // Add click handlers for expanding scenarios
      document.querySelectorAll('.scenario-more').forEach(el => {
        el.style.cursor = 'pointer';
        el.addEventListener('click', (e) => {
          const groupIdx = e.currentTarget.dataset.group;
          const isExpanded = e.currentTarget.dataset.expanded === 'true';
          const hiddenDiv = document.getElementById(`hidden-scenarios-${groupIdx}`);

          if (isExpanded) {
            hiddenDiv.style.display = 'none';
            e.currentTarget.dataset.expanded = 'false';
            e.currentTarget.querySelector('.scenario-more-text').textContent =
              `+${Array.from(hiddenDiv.children).length} more scenarios...`;
          } else {
            hiddenDiv.style.display = 'block';
            e.currentTarget.dataset.expanded = 'true';
            e.currentTarget.querySelector('.scenario-more-text').textContent = 'Show less...';
          }
        });
      });

      // Add handlers for scenario action buttons
      document.querySelectorAll('.scenario-expand-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const scenario = JSON.parse(e.target.dataset.scenarioJson);
          this.showScenarioDetails(scenario);
        });
      });

      document.querySelectorAll('.scenario-approve-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const scenario = JSON.parse(e.target.dataset.scenarioJson);

          // Save approval to session storage
          const approvals = JSON.parse(sessionStorage.getItem('scenario_approvals') || '{}');
          approvals[scenario.title] = { status: 'approved', timestamp: Date.now() };
          sessionStorage.setItem('scenario_approvals', JSON.stringify(approvals));

          // Disable this button and enable reject
          e.target.style.opacity = '0.5';
          e.target.disabled = true;

          // Find sibling reject button and enable it
          const rejectBtn = e.target.parentElement.querySelector('.scenario-reject-btn');
          if (rejectBtn) {
            rejectBtn.style.opacity = '1';
            rejectBtn.disabled = false;
          }

          alert(`✓ Approved: ${scenario.title}\n\nScenario will be ready to sync to Jira.`);
        });
      });

      document.querySelectorAll('.scenario-reject-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const scenario = JSON.parse(e.target.dataset.scenarioJson);

          // Check if already approved
          const approvals = JSON.parse(sessionStorage.getItem('scenario_approvals') || '{}');
          if (approvals[scenario.title]?.status === 'approved') {
            alert('This scenario is already approved. Unapprove it first before rejecting.');
            return;
          }

          const reason = prompt(`Reject: ${scenario.title}\n\nProvide rejection reason:`);
          if (reason) {
            // Save rejection to session storage
            approvals[scenario.title] = { status: 'rejected', reason, timestamp: Date.now() };
            sessionStorage.setItem('scenario_approvals', JSON.stringify(approvals));

            // Disable this button and enable approve
            e.target.style.opacity = '0.5';
            e.target.disabled = true;

            // Find sibling approve button and enable it
            const approveBtn = e.target.parentElement.querySelector('.scenario-approve-btn');
            if (approveBtn) {
              approveBtn.style.opacity = '1';
              approveBtn.disabled = false;
            }

            alert(`✗ Rejected: ${scenario.title}\n\nReason: ${reason}`);
          }
        });
      });

      // Trigger ScenarioManager to display full workflow
      if (window.scenarioManager) {
        window.scenarioManager.displayScenarios(this.flattenScenarios(data.testCases));
      }

      // Dispatch event for ScenarioManager to pick up
      const event = new CustomEvent('scenarios-generated', {
        detail: { testCases: data.testCases }
      });
      document.dispatchEvent(event);
    } else {
      preview.innerHTML = '<div class="empty-state">No test cases generated</div>';
    }
  }

  showScenarioDetails(scenario) {
    const details = `
Scenario: ${scenario.title}

Type: ${scenario.type}
Priority: ${scenario.priority}
Category: ${scenario.category}

Preconditions:
${(scenario.preconditions || []).map((p, i) => `${i + 1}. ${p}`).join('\n')}

Steps:
${(scenario.steps || []).map((s, i) => {
  if (typeof s === 'object' && s.action) {
    return `${s.step || i + 1}. ${s.action}`;
  }
  return `${i + 1}. ${s}`;
}).join('\n')}

Expected Result:
${scenario.expectedResult || scenario.expected_result || 'N/A'}

Automation Hint:
${scenario.automationHint || scenario.automation_hint || 'N/A'}

Tags: ${(scenario.tags || []).join(', ') || 'None'}
    `;
    alert(details);
  }

  flattenScenarios(testCases) {
    return testCases.flatMap(tc =>
      (tc.scenarios || []).map(s => ({
        ...s,
        jira_issue_key: tc.issueKey
      }))
    );
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
    window.testCaseGeneratorUI = window.testCaseGenerator;  // Alias for credentials manager
  });
} else {
  window.testCaseGenerator = new TestCaseGenerator();
  window.testCaseGeneratorUI = window.testCaseGenerator;  // Alias for credentials manager
}
