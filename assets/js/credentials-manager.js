/**
 * Credentials Manager
 * Handles user credentials input, session management, and form validation
 */

class CredentialsManager {
  constructor() {
    this.sessionStorageKey = 'jira_ai_session';
    this.sessionExpiryKey = 'jira_ai_session_expiry';
    this.initializeUI();
  }

  initializeUI() {
    const form = document.getElementById('credentials-form');
    const submitBtn = document.getElementById('credentials-submit');
    const cancelBtn = document.getElementById('credentials-cancel');
    const closeBtn = document.getElementById('credentials-modal-close');
    const modal = document.getElementById('credentials-modal');

    // AI Provider toggle
    const aiProviderRadios = document.querySelectorAll('input[name="ai_provider"]');
    aiProviderRadios.forEach(radio => {
      radio.addEventListener('change', (e) => this.handleProviderChange(e));
    });

    // Form submission
    submitBtn?.addEventListener('click', () => this.handleSubmit(form));

    // Close modal
    cancelBtn?.addEventListener('click', () => this.closeModal());
    closeBtn?.addEventListener('click', () => this.closeModal());
    modal?.addEventListener('click', (e) => {
      if (e.target === modal) this.closeModal();
    });

    // Enter key to submit
    form?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        this.handleSubmit(form);
      }
    });
  }

  handleProviderChange(event) {
    const anthropicGroup = document.getElementById('anthropic-key-group');
    const openaiGroup = document.getElementById('openai-key-group');
    const openaiBaseUrlGroup = document.getElementById('openai-base-url-group');

    if (event.target.value === 'anthropic') {
      anthropicGroup.style.display = 'block';
      openaiGroup.style.display = 'none';
      openaiBaseUrlGroup.style.display = 'none';
    } else {
      anthropicGroup.style.display = 'none';
      openaiGroup.style.display = 'block';
      openaiBaseUrlGroup.style.display = 'block';
    }
  }

  async handleSubmit(form) {
    const errorDiv = document.getElementById('credentials-error');
    errorDiv.style.display = 'none';

    // Validate form
    const validation = this.validateForm(form);
    if (!validation.valid) {
      this.showError(validation.message);
      return;
    }

    // Get form data
    const credentials = this.getFormData(form);

    // Verify credentials by making a test API call
    try {
      const isValid = await this.verifyCredentials(credentials);
      if (!isValid) {
        this.showError('Invalid credentials. Please check your Jira URL, email, token, and AI API key.');
        return;
      }

      // Save credentials to session
      this.saveSession(credentials);

      // Close modal
      this.closeModal();

      // Trigger test case generation
      if (window.testCaseGeneratorUI) {
        window.testCaseGeneratorUI.openGenerator();
      }
    } catch (error) {
      this.showError(`Error: ${error.message}`);
    }
  }

  validateForm(form) {
    const jiraUrl = form.querySelector('#jira-url').value.trim();
    const jiraEmail = form.querySelector('#jira-email').value.trim();
    const jiraToken = form.querySelector('#jira-token').value.trim();
    const aiProvider = form.querySelector('input[name="ai_provider"]:checked').value;

    if (!jiraUrl || !jiraEmail || !jiraToken) {
      return { valid: false, message: 'Jira URL, email, and token are required.' };
    }

    if (!jiraUrl.startsWith('http://') && !jiraUrl.startsWith('https://')) {
      return { valid: false, message: 'Jira URL must start with http:// or https://' };
    }

    if (aiProvider === 'anthropic') {
      const anthropicKey = form.querySelector('#anthropic-key').value.trim();
      if (!anthropicKey) {
        return { valid: false, message: 'Claude API key is required.' };
      }
      if (!anthropicKey.startsWith('sk-ant-')) {
        return { valid: false, message: 'Claude API key must start with sk-ant-' };
      }
    } else if (aiProvider === 'openai') {
      const openaiKey = form.querySelector('#openai-key').value.trim();
      if (!openaiKey) {
        return { valid: false, message: 'OpenAI API key is required.' };
      }
      if (!openaiKey.startsWith('sk-')) {
        return { valid: false, message: 'OpenAI API key must start with sk-' };
      }
    }

    return { valid: true };
  }

  getFormData(form) {
    const aiProvider = form.querySelector('input[name="ai_provider"]:checked').value;
    const credentials = {
      jira_base_url: form.querySelector('#jira-url').value.trim().replace(/\/$/, ''),
      jira_user_email: form.querySelector('#jira-email').value.trim(),
      jira_api_token: form.querySelector('#jira-token').value.trim(),
      ai_provider: aiProvider,
      session_duration: parseInt(form.querySelector('#session-duration').value),
    };

    if (aiProvider === 'anthropic') {
      credentials.anthropic_api_key = form.querySelector('#anthropic-key').value.trim();
    } else {
      credentials.openai_api_key = form.querySelector('#openai-key').value.trim();
      const baseUrl = form.querySelector('#openai-base-url').value.trim();
      if (baseUrl) {
        credentials.openai_api_base = baseUrl;
      }
    }

    return credentials;
  }

  async verifyCredentials(credentials) {
    try {
      const response = await fetch('/api/verify-credentials', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          jira_base_url: credentials.jira_base_url,
          jira_user_email: credentials.jira_user_email,
          jira_api_token: credentials.jira_api_token,
          ai_provider: credentials.ai_provider,
          anthropic_api_key: credentials.anthropic_api_key,
          openai_api_key: credentials.openai_api_key,
        }),
      });

      const data = await response.json();
      return data.valid === true;
    } catch (error) {
      console.error('Credential verification error:', error);
      return false;
    }
  }

  saveSession(credentials) {
    const sessionData = {
      ...credentials,
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + credentials.session_duration * 1000).toISOString(),
    };

    // Store in sessionStorage (more secure than localStorage for credentials)
    sessionStorage.setItem(this.sessionStorageKey, JSON.stringify(sessionData));
    sessionStorage.setItem(this.sessionExpiryKey, sessionData.expires_at);

    console.log(`✓ Session saved. Expires at: ${sessionData.expires_at}`);
  }

  getSession() {
    try {
      const sessionData = sessionStorage.getItem(this.sessionStorageKey);
      const expiry = sessionStorage.getItem(this.sessionExpiryKey);

      if (!sessionData || !expiry) {
        return null;
      }

      // Check if session has expired
      if (new Date() > new Date(expiry)) {
        this.clearSession();
        return null;
      }

      return JSON.parse(sessionData);
    } catch (error) {
      console.error('Error reading session:', error);
      return null;
    }
  }

  clearSession() {
    sessionStorage.removeItem(this.sessionStorageKey);
    sessionStorage.removeItem(this.sessionExpiryKey);
    console.log('Session cleared');
  }

  isSessionValid() {
    const session = this.getSession();
    return session !== null;
  }

  getSessionExpiry() {
    const expiry = sessionStorage.getItem(this.sessionExpiryKey);
    if (!expiry) return null;

    const expiryDate = new Date(expiry);
    const now = new Date();
    const remainingMs = expiryDate - now;

    if (remainingMs <= 0) {
      return null;
    }

    const hours = Math.floor(remainingMs / 3600000);
    const minutes = Math.floor((remainingMs % 3600000) / 60000);

    return { hours, minutes, ms: remainingMs };
  }

  showError(message) {
    const errorDiv = document.getElementById('credentials-error');
    if (errorDiv) {
      errorDiv.textContent = message;
      errorDiv.style.display = 'block';
    }
  }

  openModal() {
    const modal = document.getElementById('credentials-modal');
    if (modal) {
      modal.style.display = 'flex';
      // Focus first input
      const firstInput = modal.querySelector('input[type="url"]');
      if (firstInput) {
        setTimeout(() => firstInput.focus(), 100);
      }
    }
  }

  closeModal() {
    const modal = document.getElementById('credentials-modal');
    if (modal) {
      modal.style.display = 'none';
    }
  }

  updateSessionStatus() {
    const session = this.getSession();
    if (!session) {
      console.log('No active session');
      return null;
    }

    const expiry = this.getSessionExpiry();
    if (!expiry) {
      console.log('Session expired');
      this.clearSession();
      return null;
    }

    return {
      user: session.jira_user_email,
      provider: session.ai_provider,
      expiresIn: `${expiry.hours}h ${expiry.minutes}m`,
    };
  }
}

// Initialize on page load
let credentialsManager;
document.addEventListener('DOMContentLoaded', () => {
  credentialsManager = new CredentialsManager();

  // Check if session exists and is valid
  const session = credentialsManager.getSession();
  if (session) {
    const status = credentialsManager.updateSessionStatus();
    if (status) {
      console.log(`✓ Active session for ${status.user} (${status.provider}), expires in ${status.expiresIn}`);
    }
  }
});

// Export for use in other scripts
window.credentialsManager = credentialsManager;
