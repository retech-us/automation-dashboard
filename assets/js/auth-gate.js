/**
 * Corporate Authentication & Security Gate for Automation Dashboard.
 * Enforces SHA-256 hashed team passkey verification before unlocking dashboard data.
 */

(function (window) {
  'use strict';

  const AUTH_STORAGE_KEY = 'dashboard.auth_session';
  const SESSION_DURATION_MS = 7 * 24 * 60 * 60 * 1000; // 7 days session

  // Allowed SHA-256 hashes:
  // 1. RetechQA2026!  -> ce77f54ddf439389a8401a88c0e2ce3699afc983851585d5c7de898e134702e6
  // 2. SymphonyQA2026! -> e7493b1c5a0fc5d33056d70624b250b9abf341989d9eb80298c7ae8ea11413f1
  const VALID_HASHES = [
    'ce77f54ddf439389a8401a88c0e2ce3699afc983851585d5c7de898e134702e6',
    'e7493b1c5a0fc5d33056d70624b250b9abf341989d9eb80298c7ae8ea11413f1'
  ];

  async function sha256Hex(str) {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    const hashBuf = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuf));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  class AuthGate {
    constructor() {
      this.isUnlocked = false;
      this.init();
    }

    isAuthenticated() {
      try {
        const raw = localStorage.getItem(AUTH_STORAGE_KEY);
        if (!raw) return false;
        const session = JSON.parse(raw);
        if (!session || !session.timestamp || !session.token) return false;
        const elapsed = Date.now() - session.timestamp;
        if (elapsed > SESSION_DURATION_MS) {
          this.lock();
          return false;
        }
        return VALID_HASHES.includes(session.token);
      } catch (e) {
        return false;
      }
    }

    saveSession(hash) {
      try {
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({
          token: hash,
          timestamp: Date.now()
        }));
      } catch (e) {}
    }

    lock() {
      try {
        localStorage.removeItem(AUTH_STORAGE_KEY);
      } catch (e) {}
      this.isUnlocked = false;
      this.renderLockScreen();
    }

    init() {
      if (this.isAuthenticated()) {
        this.isUnlocked = true;
        this.revealDashboard();
      } else {
        this.isUnlocked = false;
        this.renderLockScreen();
      }
    }

    revealDashboard() {
      const lockOverlay = document.getElementById('auth-gate-overlay');
      if (lockOverlay) {
        lockOverlay.style.opacity = '0';
        setTimeout(() => {
          if (lockOverlay.parentNode) lockOverlay.parentNode.removeChild(lockOverlay);
        }, 300);
      }

      const mainContent = document.querySelector('.main-content');
      if (mainContent) {
        mainContent.style.display = '';
        mainContent.style.visibility = 'visible';
      }

      this.injectLockHeaderButton();
    }

    injectLockHeaderButton() {
      if (document.getElementById('btn-auth-lock')) return;
      const chromeNav = document.querySelector('.site-chrome__nav');
      if (!chromeNav) return;

      const lockBtn = document.createElement('button');
      lockBtn.id = 'btn-auth-lock';
      lockBtn.type = 'button';
      lockBtn.className = 'btn btn--ghost btn--sm';
      lockBtn.title = 'Lock Dashboard (Sign Out)';
      lockBtn.style.cssText = 'font-size:12px;display:inline-flex;align-items:center;gap:4px;padding:5px 10px;border-radius:8px;';
      lockBtn.innerHTML = '🔒 <span class="auth-lock-text">Lock</span>';
      lockBtn.addEventListener('click', () => {
        if (confirm('Lock dashboard and sign out?')) {
          this.lock();
        }
      });

      chromeNav.appendChild(lockBtn);
    }

    renderLockScreen() {
      const mainContent = document.querySelector('.main-content');
      if (mainContent) {
        mainContent.style.display = 'none';
      }

      const existing = document.getElementById('auth-gate-overlay');
      if (existing) existing.remove();

      const overlay = document.createElement('div');
      overlay.id = 'auth-gate-overlay';
      overlay.className = 'auth-gate-overlay';
      overlay.innerHTML = `
        <div class="auth-gate-card">
          <div class="auth-gate-icon">🛡️</div>
          <div class="auth-gate-badge">INTERNAL ACCESS ONLY</div>
          <h2 class="auth-gate-title">SymphonyAI / Retech QA Portal</h2>
          <p class="auth-gate-desc">
            This dashboard contains internal quality engineering metrics, test execution pipelines, and Jira defect tracking. Please enter your team passkey to continue.
          </p>

          <form id="auth-gate-form" class="auth-gate-form" onsubmit="return false;">
            <div class="auth-input-wrapper">
              <input
                type="password"
                id="auth-passkey-input"
                class="auth-input"
                placeholder="Enter team passkey..."
                autocomplete="current-password"
                required
                autofocus
              />
              <button type="button" id="auth-toggle-visibility" class="auth-visibility-btn" title="Show/Hide Passkey">👁️</button>
            </div>
            
            <div id="auth-error-msg" class="auth-error-msg" style="display:none;">
              ⚠️ Incorrect passkey. Please check with your QA lead.
            </div>

            <button type="submit" id="auth-submit-btn" class="auth-submit-btn">
              Unlock Dashboard ⚡
            </button>
          </form>

          <div class="auth-gate-footer">
            <span>🔒 Protected with SHA-256 Web Crypto</span>
          </div>
        </div>
      `;

      document.body.appendChild(overlay);

      // Handle visibility toggle
      const toggleBtn = document.getElementById('auth-toggle-visibility');
      const passInput = document.getElementById('auth-passkey-input');
      if (toggleBtn && passInput) {
        toggleBtn.addEventListener('click', () => {
          if (passInput.type === 'password') {
            passInput.type = 'text';
            toggleBtn.textContent = '🙈';
          } else {
            passInput.type = 'password';
            toggleBtn.textContent = '👁️';
          }
        });
      }

      // Handle form submission
      const form = document.getElementById('auth-gate-form');
      const submitBtn = document.getElementById('auth-submit-btn');
      const errorMsg = document.getElementById('auth-error-msg');

      const handleUnlock = async () => {
        const pass = (passInput.value || '').trim();
        if (!pass) return;

        submitBtn.disabled = true;
        submitBtn.textContent = 'Verifying…';
        if (errorMsg) errorMsg.style.display = 'none';

        const hash = await sha256Hex(pass);
        if (VALID_HASHES.includes(hash)) {
          this.saveSession(hash);
          this.isUnlocked = true;
          this.revealDashboard();
          if (typeof window.loadDashboard === 'function') window.loadDashboard();
          if (window.JiraTracker && typeof window.JiraTracker.init === 'function') window.JiraTracker.init();
          if (window.LiveTracker && typeof window.LiveTracker.checkAll === 'function') window.LiveTracker.checkAll();
        } else {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Unlock Dashboard ⚡';
          if (errorMsg) errorMsg.style.display = 'block';
          
          const card = document.querySelector('.auth-gate-card');
          if (card) {
            card.classList.remove('auth-shake');
            void card.offsetWidth; // trigger reflow
            card.classList.add('auth-shake');
          }
          passInput.focus();
          passInput.select();
        }
      };

      if (form) form.addEventListener('submit', (e) => { e.preventDefault(); handleUnlock(); });
      if (submitBtn) submitBtn.addEventListener('click', handleUnlock);
    }
  }

  window.AuthGate = new AuthGate();

})(window);
