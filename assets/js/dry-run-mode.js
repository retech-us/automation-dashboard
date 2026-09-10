/**
 * Dry-Run Mode Manager
 * Allows testing sync workflow without modifying Jira
 */

class DryRunModeManager {
  constructor() {
    console.log('🧪 Dry-Run Mode Manager initializing');
    this.enabled = false;
    this.preview = null;
    this.init();
  }

  async init() {
    // Check initial status
    await this.checkStatus();

    // Create UI toggle
    this.createToggle();
  }

  async checkStatus() {
    try {
      const response = await fetch('/api/dry-run/status');
      const data = await response.json();
      this.enabled = data.dry_run_enabled;
      console.log(`🧪 Dry-run status: ${this.enabled ? 'ENABLED' : 'DISABLED'}`);
    } catch (error) {
      console.warn('Could not check dry-run status:', error);
    }
  }

  createToggle() {
    // Find or create toggle container
    let toggleContainer = document.getElementById('dry-run-toggle-container');

    if (!toggleContainer) {
      toggleContainer = document.createElement('div');
      toggleContainer.id = 'dry-run-toggle-container';
      toggleContainer.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        background: white;
        border: 2px solid #EBECF0;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
      `;
      document.body.appendChild(toggleContainer);
    }

    const innerHTML = `
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 18px;">🧪</span>
        <div>
          <div style="font-size: 12px; color: #7C8AA2;">Test Mode</div>
          <div style="font-size: 14px; font-weight: 600; color: ${this.enabled ? '#216E4E' : '#626F86'};">
            ${this.enabled ? '✓ DRY-RUN' : '○ LIVE'}
          </div>
        </div>
        <button
          id="dry-run-toggle-btn"
          style="
            padding: 8px 12px;
            border: 1px solid #EBECF0;
            border-radius: 4px;
            background: ${this.enabled ? '#DFFCF0' : '#F6F8FA'};
            color: ${this.enabled ? '#216E4E' : '#626F86'};
            cursor: pointer;
            font-weight: 600;
            font-size: 12px;
            transition: all 0.2s;
          "
        >
          ${this.enabled ? 'Disable' : 'Enable'}
        </button>
        <button
          id="dry-run-preview-btn"
          style="
            padding: 8px 12px;
            border: 1px solid #EBECF0;
            border-radius: 4px;
            background: #F6F8FA;
            color: #0055CC;
            cursor: pointer;
            font-weight: 600;
            font-size: 12px;
            transition: all 0.2s;
            ${!this.enabled ? 'opacity: 0.5; cursor: not-allowed;' : ''}
          "
          ${!this.enabled ? 'disabled' : ''}
        >
          Preview
        </button>
      </div>
    `;

    toggleContainer.innerHTML = innerHTML;

    // Add event listeners
    document.getElementById('dry-run-toggle-btn').addEventListener('click', () => {
      this.toggle();
    });

    document.getElementById('dry-run-preview-btn').addEventListener('click', () => {
      this.showPreview();
    });
  }

  async toggle() {
    try {
      const endpoint = this.enabled ? '/api/dry-run/disable' : '/api/dry-run/enable';

      const response = await fetch(endpoint, { method: 'POST' });
      const data = await response.json();

      this.enabled = data.mode === 'DRY-RUN';

      console.log(`🧪 Dry-run mode: ${this.enabled ? 'ENABLED ✓' : 'DISABLED'}`);
      console.log(`📝 ${data.message}`);

      // Show notification
      this.showNotification(
        this.enabled
          ? '✓ Dry-run mode enabled - No changes will be made to Jira'
          : '○ Back to live mode - Changes will be synced to Jira',
        this.enabled ? 'success' : 'info'
      );

      // Update UI
      this.createToggle();
    } catch (error) {
      console.error('❌ Error toggling dry-run mode:', error);
      this.showNotification('Error toggling dry-run mode', 'error');
    }
  }

  async showPreview() {
    if (!this.enabled) {
      this.showNotification('Enable dry-run mode first', 'warning');
      return;
    }

    try {
      const response = await fetch('/api/dry-run/preview');
      const preview = await response.json();

      // Show preview modal
      this.showPreviewModal(preview);
    } catch (error) {
      console.error('❌ Error getting preview:', error);
      this.showNotification('Error loading preview', 'error');
    }
  }

  showPreviewModal(preview) {
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0,0,0,0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10001;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
      background: white;
      border-radius: 12px;
      max-width: 600px;
      max-height: 80vh;
      overflow-y: auto;
      padding: 24px;
      box-shadow: 0 12px 48px rgba(0,0,0,0.3);
    `;

    const summary = preview.summary || {};
    const details = preview.details || {};

    content.innerHTML = `
      <div style="margin-bottom: 20px;">
        <h2 style="margin: 0 0 8px 0; color: #161B22;">🧪 Dry-Run Preview</h2>
        <p style="margin: 0; color: #7C8AA2; font-size: 12px;">
          ${preview.warning}
        </p>
      </div>

      <div style="background: #DFFCF0; border: 1px solid #216E4E; border-radius: 6px; padding: 12px; margin-bottom: 16px;">
        <div style="color: #216E4E; font-weight: 600; margin-bottom: 8px;">Summary</div>
        <div style="color: #216E4E; font-size: 13px;">
          <div>📝 Total actions: ${summary.total_actions || 0}</div>
          <div>✨ Issues to create: ${summary.issues_to_create || 0}</div>
          <div>🔗 Links to create: ${summary.links_to_create || 0}</div>
          <div>📋 Fields to update: ${summary.fields_to_update || 0}</div>
        </div>
      </div>

      ${details.created_issues && details.created_issues.length > 0 ? `
        <div style="margin-bottom: 16px;">
          <h3 style="margin: 0 0 8px 0; font-size: 14px; color: #161B22;">Issues to Create</h3>
          ${details.created_issues.map(issue => `
            <div style="background: #F6F8FA; border: 1px solid #EBECF0; border-radius: 4px; padding: 8px; margin-bottom: 8px; font-size: 12px;">
              <div style="color: #0055CC; font-weight: 600;">${issue.key}</div>
              <div style="color: #626F86;">${issue.summary}</div>
            </div>
          `).join('')}
        </div>
      ` : ''}

      ${details.linked_issues && details.linked_issues.length > 0 ? `
        <div style="margin-bottom: 16px;">
          <h3 style="margin: 0 0 8px 0; font-size: 14px; color: #161B22;">Links to Create</h3>
          ${details.linked_issues.map(link => `
            <div style="background: #F6F8FA; border: 1px solid #EBECF0; border-radius: 4px; padding: 8px; margin-bottom: 8px; font-size: 12px;">
              <div style="color: #626F86;">
                <strong>${link.from_key}</strong> → <strong>${link.to_key}</strong>
                <div style="color: #7C8AA2; margin-top: 4px;">Type: ${link.link_type}</div>
              </div>
            </div>
          `).join('')}
        </div>
      ` : ''}

      <div style="border-top: 1px solid #EBECF0; padding-top: 16px; margin-top: 16px;">
        <button
          onclick="this.parentElement.parentElement.parentElement.remove()"
          style="
            width: 100%;
            padding: 10px;
            background: #0055CC;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
          "
        >
          Close Preview
        </button>
      </div>
    `;

    modal.appendChild(content);

    // Close on overlay click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });

    document.body.appendChild(modal);
  }

  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      bottom: 20px;
      left: 20px;
      padding: 12px 16px;
      border-radius: 6px;
      font-size: 14px;
      z-index: 10002;
      animation: slideIn 0.3s ease;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
    `;

    const colors = {
      success: { bg: '#DFFCF0', color: '#216E4E' },
      error: { bg: '#FFECEB', color: '#AE2A19' },
      warning: { bg: '#FFF7D6', color: '#974F0C' },
      info: { bg: '#DEEBFF', color: '#0055CC' }
    };

    const style = colors[type] || colors.info;
    notification.style.background = style.bg;
    notification.style.color = style.color;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => notification.remove(), 4000);
  }
}

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.dryRunMode = new DryRunModeManager();
  });
} else {
  window.dryRunMode = new DryRunModeManager();
}
