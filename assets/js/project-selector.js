/**
 * Project Selector
 * Displays available Jira projects for user selection after authentication
 */

class ProjectSelector {
  constructor() {
    console.log('🎯 ProjectSelector initialized');
    this.selectedProject = null;
    this.projects = [];
    this.createModal();
  }

  createModal() {
    const modal = document.createElement('div');
    modal.id = 'project-selector-modal';
    modal.className = 'modal modal--project-selector';
    modal.innerHTML = `
      <div class="modal__overlay"></div>
      <div class="modal__content">
        <div class="modal__header">
          <h2 class="modal__title">📁 Select Jira Project</h2>
        </div>

        <div class="modal__body">
          <p class="modal__description">Choose a project to generate test cases for:</p>

          <div id="projects-loading" class="loading">
            <div class="spinner"></div>
            Fetching projects...
          </div>

          <div id="projects-list" class="projects-list" style="display: none;">
            <!-- Projects will be populated here -->
          </div>

          <div id="projects-error" class="error-box" style="display: none;"></div>
        </div>

        <div class="modal__footer">
          <button class="btn btn--ghost" id="project-selector-cancel" type="button">Cancel</button>
          <button class="btn btn--primary" id="project-selector-confirm" type="button" disabled>
            Select Project
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    this.wireEventListeners();
  }

  wireEventListeners() {
    const modal = document.getElementById('project-selector-modal');
    const cancelBtn = modal.querySelector('#project-selector-cancel');
    const confirmBtn = modal.querySelector('#project-selector-confirm');
    const overlay = modal.querySelector('.modal__overlay');

    cancelBtn.addEventListener('click', () => this.closeModal());
    confirmBtn.addEventListener('click', () => this.confirmSelection());
    overlay.addEventListener('click', () => this.closeModal());
  }

  async openModal(credentials) {
    console.log('🎯 ProjectSelector.openModal() called');
    const modal = document.getElementById('project-selector-modal');
    modal.classList.add('is-open');

    // Fetch projects
    await this.fetchProjects(credentials);
  }

  async fetchProjects(credentials) {
    try {
      console.log('🔄 Fetching Jira projects...');
      const loadingDiv = document.getElementById('projects-loading');
      const errorDiv = document.getElementById('projects-error');

      // Hide error
      errorDiv.style.display = 'none';

      const response = await fetch('/api/jira-projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jira_base_url: credentials.jira_base_url,
          jira_email: credentials.jira_user_email,
          jira_api_token: credentials.jira_api_token,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch projects');
      }

      if (!data.projects || data.projects.length === 0) {
        throw new Error('No projects found. Make sure your Jira account has access to at least one project.');
      }

      this.projects = data.projects;
      console.log(`✓ Fetched ${this.projects.length} projects`);

      // Hide loading
      loadingDiv.style.display = 'none';

      // Display projects
      this.displayProjects();
    } catch (error) {
      console.error('Error fetching projects:', error);
      document.getElementById('projects-loading').style.display = 'none';
      document.getElementById('projects-error').style.display = 'block';
      document.getElementById('projects-error').textContent = `❌ ${error.message}`;
    }
  }

  displayProjects() {
    const projectsList = document.getElementById('projects-list');
    projectsList.style.display = 'block';

    projectsList.innerHTML = this.projects
      .sort((a, b) => a.key.localeCompare(b.key))
      .map(
        (project) => `
      <div class="project-item" data-key="${project.key}">
        <div class="project-radio">
          <input
            type="radio"
            name="project"
            value="${project.key}"
            id="project-${project.key}"
          />
        </div>
        <div class="project-info">
          <label for="project-${project.key}" class="project-name">${project.key}</label>
          <div class="project-details">${project.name}</div>
          <div class="project-type">${project.projectTypeKey || 'Unknown'}</div>
        </div>
      </div>
    `
      )
      .join('');

    // Wire radio button listeners
    projectsList.querySelectorAll('input[name="project"]').forEach((radio) => {
      radio.addEventListener('change', (e) => {
        this.selectedProject = e.target.value;
        document.getElementById('project-selector-confirm').disabled = false;
        console.log(`Selected project: ${this.selectedProject}`);
      });
    });
  }

  confirmSelection() {
    if (!this.selectedProject) {
      alert('Please select a project');
      return;
    }

    console.log(`🎯 Project confirmed: ${this.selectedProject}`);
    this.closeModal();

    // Get selected project details
    const selectedProjectData = this.projects.find((p) => p.key === this.selectedProject);

    // Store project in session
    const session = window.credentialsManager?.getSession();
    if (session) {
      session.selected_project_key = this.selectedProject;
      session.selected_project_name = selectedProjectData?.name || this.selectedProject;
      sessionStorage.setItem('jira_ai_session', JSON.stringify(session));
      console.log(`✓ Saved selected project to session: ${this.selectedProject}`);
    }

    // Trigger test case generator
    if (window.testCaseGeneratorUI) {
      console.log('Calling testCaseGeneratorUI.openGenerator()...');
      window.testCaseGeneratorUI.openGenerator();
    }
  }

  closeModal() {
    const modal = document.getElementById('project-selector-modal');
    if (modal) {
      modal.classList.remove('is-open');
    }
  }

  getSelectedProject() {
    return this.selectedProject;
  }

  reset() {
    this.selectedProject = null;
    const confirmBtn = document.getElementById('project-selector-confirm');
    if (confirmBtn) {
      confirmBtn.disabled = true;
    }
    document.querySelectorAll('input[name="project"]').forEach((radio) => {
      radio.checked = false;
    });
  }
}

// Initialize on page load
let projectSelector;
document.addEventListener('DOMContentLoaded', () => {
  console.log('🎯 ProjectSelector: DOMContentLoaded event fired');
  projectSelector = new ProjectSelector();
  window.projectSelector = projectSelector;
  console.log('🎯 ProjectSelector: Exported to window.projectSelector');
});
