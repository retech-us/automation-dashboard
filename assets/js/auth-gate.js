/**
 * Corporate Authentication & Security Gate for Automation Dashboard.
 * Enforces SHA-256 hashed team passkey verification before unlocking dashboard data.
 */

(function (window) {
  'use strict';

  const AUTH_STORAGE_KEY = 'dashboard.auth_session';
  const ATTEMPTS_KEY = 'dashboard.auth_attempts';
  const SESSION_DURATION_MS = 7 * 24 * 60 * 60 * 1000; // 7 days session
  const MAX_ATTEMPTS = 5;
  const LOCKOUT_MS = 15 * 60 * 1000; // 15 minutes lockout

  // Allowed SHA-256 hashes:
  // 1. RetechQA2026!  -> ce77f54ddf439389a8401a88c0e2ce3699afc983851585d5c7de898e134702e6
  // 2. SymphonyQA2026! -> e7493b1c5a0fc5d33056d70624b250b9abf341989d9eb80298c7ae8ea11413f1
  const VALID_HASHES = [
    'ce77f54ddf439389a8401a88c0e2ce3699afc983851585d5c7de898e134702e6',
    'e7493b1c5a0fc5d33056d70624b250b9abf341989d9eb80298c7ae8ea11413f1'
  ];

  function pureJsSha256(str) {
    function rightRotate(value, amount) {
      return (value >>> amount) | (value << (32 - amount));
    }

    var result = '';
    var words = [];

    var hash = [
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    ];

    var k = [
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
      0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
      0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
      0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
      0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
      0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    ];

    var utf8Str = unescape(encodeURIComponent(str));
    var byteLength = utf8Str.length;
    var bitLength = byteLength * 8;

    for (var i = 0; i < byteLength; i++) {
      words[i >> 2] = (words[i >> 2] || 0) | (utf8Str.charCodeAt(i) << ((3 - (i % 4)) * 8));
    }

    words[byteLength >> 2] = (words[byteLength >> 2] || 0) | (0x80 << ((3 - (byteLength % 4)) * 8));

    var totalWords = (((byteLength + 8) >> 6) + 1) * 16;
    for (var j = (byteLength >> 2) + 1; j < totalWords; j++) {
      words[j] = words[j] || 0;
    }
    words[totalWords - 2] = Math.floor(bitLength / 0x100000000);
    words[totalWords - 1] = bitLength & 0xffffffff;

    for (var chunk = 0; chunk < totalWords; chunk += 16) {
      var w = new Array(64);
      for (var idx = 0; idx < 16; idx++) {
        w[idx] = words[chunk + idx] || 0;
      }
      for (var idx2 = 16; idx2 < 64; idx2++) {
        var w15 = w[idx2 - 15], w2 = w[idx2 - 2];
        var s0 = rightRotate(w15, 7) ^ rightRotate(w15, 18) ^ (w15 >>> 3);
        var s1 = rightRotate(w2, 17) ^ rightRotate(w2, 19) ^ (w2 >>> 10);
        w[idx2] = (w[idx2 - 16] + s0 + w[idx2 - 7] + s1) | 0;
      }

      var a = hash[0], b = hash[1], c = hash[2], d = hash[3],
          e = hash[4], f = hash[5], g = hash[6], h = hash[7];

      for (var idx3 = 0; idx3 < 64; idx3++) {
        var S1 = rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25);
        var ch = (e & f) ^ ((~e) & g);
        var temp1 = (h + S1 + ch + k[idx3] + w[idx3]) | 0;
        var S0 = rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22);
        var maj = (a & b) ^ (a & c) ^ (b & c);
        var temp2 = (S0 + maj) | 0;

        h = g;
        g = f;
        f = e;
        e = (d + temp1) | 0;
        d = c;
        c = b;
        b = a;
        a = (temp1 + temp2) | 0;
      }

      hash[0] = (hash[0] + a) | 0;
      hash[1] = (hash[1] + b) | 0;
      hash[2] = (hash[2] + c) | 0;
      hash[3] = (hash[3] + d) | 0;
      hash[4] = (hash[4] + e) | 0;
      hash[5] = (hash[5] + f) | 0;
      hash[6] = (hash[6] + g) | 0;
      hash[7] = (hash[7] + h) | 0;
    }

    for (var i2 = 0; i2 < 8; i2++) {
      for (var j2 = 3; j2 >= 0; j2--) {
        var byteVal = (hash[i2] >> (j2 * 8)) & 0xff;
        result += (byteVal < 16 ? '0' : '') + byteVal.toString(16);
      }
    }
    return result;
  }

  async function sha256Hex(str) {
    if (window.crypto && window.crypto.subtle && typeof window.crypto.subtle.digest === 'function') {
      try {
        var encoder = new TextEncoder();
        var data = encoder.encode(str);
        var hashBuf = await window.crypto.subtle.digest('SHA-256', data);
        var hashArray = Array.from(new Uint8Array(hashBuf));
        return hashArray.map(function(b) { return b.toString(16).padStart(2, '0'); }).join('');
      } catch (e) {
        // Fall back to pure JS
      }
    }
    return pureJsSha256(str);
  }

  class AuthGate {
    constructor() {
      this.isUnlocked = false;
      this.init();
    }

    getLockoutInfo() {
      try {
        const raw = sessionStorage.getItem(ATTEMPTS_KEY);
        if (!raw) return { count: 0, lockUntil: 0 };
        const parsed = JSON.parse(raw);
        return { count: parsed.count || 0, lockUntil: parsed.lockUntil || 0 };
      } catch {
        return { count: 0, lockUntil: 0 };
      }
    }

    recordFailedAttempt() {
      const info = this.getLockoutInfo();
      info.count += 1;
      if (info.count >= MAX_ATTEMPTS) {
        info.lockUntil = Date.now() + LOCKOUT_MS;
      }
      try {
        sessionStorage.setItem(ATTEMPTS_KEY, JSON.stringify(info));
      } catch {}
      return info;
    }

    clearFailedAttempts() {
      try {
        sessionStorage.removeItem(ATTEMPTS_KEY);
      } catch {}
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
      const siteChrome = document.querySelector('.site-chrome');
      if (mainContent) {
        mainContent.style.display = '';
        mainContent.style.visibility = 'visible';
      }
      if (siteChrome) {
        siteChrome.style.display = '';
        siteChrome.style.visibility = 'visible';
      }

      this.wireLockHeaderButton();
    }

    wireLockHeaderButton() {
      const lockBtn = document.getElementById('btn-auth-lock');
      if (lockBtn && !lockBtn._wired) {
        lockBtn._wired = true;
        lockBtn.addEventListener('click', () => {
          if (confirm('Lock dashboard and sign out?')) {
            this.lock();
          }
        });
      }
    }

    renderLockScreen() {
      const mainContent = document.querySelector('.main-content');
      const siteChrome = document.querySelector('.site-chrome');
      if (mainContent) {
        mainContent.style.display = 'none';
      }
      if (siteChrome) {
        siteChrome.style.display = 'none';
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
            
            <div id="auth-error-msg" class="auth-error-msg" style="display:none;"></div>

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

      // Check lockout status
      const form = document.getElementById('auth-gate-form');
      const submitBtn = document.getElementById('auth-submit-btn');
      const errorMsg = document.getElementById('auth-error-msg');

      const lockout = this.getLockoutInfo();
      if (lockout.lockUntil > Date.now()) {
        const remainingMin = Math.ceil((lockout.lockUntil - Date.now()) / 60000);
        submitBtn.disabled = true;
        passInput.disabled = true;
        if (errorMsg) {
          errorMsg.style.display = 'block';
          errorMsg.textContent = `⛔ Too many failed attempts. Locked for ${remainingMin} minute(s).`;
        }
      }

      const handleUnlock = async () => {
        const currentLock = this.getLockoutInfo();
        if (currentLock.lockUntil > Date.now()) {
          const remainingMin = Math.ceil((currentLock.lockUntil - Date.now()) / 60000);
          if (errorMsg) {
            errorMsg.style.display = 'block';
            errorMsg.textContent = `⛔ Too many failed attempts. Locked for ${remainingMin} minute(s).`;
          }
          return;
        }

        const pass = (passInput.value || '').trim();
        if (!pass) return;

        submitBtn.disabled = true;
        submitBtn.textContent = 'Verifying…';
        if (errorMsg) errorMsg.style.display = 'none';

        const hash = await sha256Hex(pass);
        if (VALID_HASHES.includes(hash)) {
          this.clearFailedAttempts();
          this.saveSession(hash);
          this.isUnlocked = true;
          this.revealDashboard();
          if (typeof window.loadDashboard === 'function') window.loadDashboard();
          if (window.JiraTracker && typeof window.JiraTracker.init === 'function') window.JiraTracker.init();
          if (window.LiveTracker && typeof window.LiveTracker.checkAll === 'function') window.LiveTracker.checkAll();
        } else {
          const attemptInfo = this.recordFailedAttempt();
          submitBtn.disabled = false;
          submitBtn.textContent = 'Unlock Dashboard ⚡';
          
          if (attemptInfo.lockUntil > Date.now()) {
            passInput.disabled = true;
            submitBtn.disabled = true;
            if (errorMsg) {
              errorMsg.style.display = 'block';
              errorMsg.textContent = `⛔ 5 failed attempts reached. Form locked for 15 minutes.`;
            }
          } else {
            const remaining = MAX_ATTEMPTS - attemptInfo.count;
            if (errorMsg) {
              errorMsg.style.display = 'block';
              errorMsg.textContent = `⚠️ Incorrect passkey. ${remaining} attempt(s) remaining.`;
            }
          }
          
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
