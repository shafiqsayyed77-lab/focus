// FocusFlow Authentication Manager
const Auth = (() => {
  let currentUser = null;

  async function checkAuth() {
    const token = API.getToken();
    if (!token) {
      showAuthScreen();
      return false;
    }

    try {
      const user = await API.getMe();
      currentUser = user;
      updateUserUI(user);
      showAppScreen();
      return true;
    } catch (err) {
      console.warn('Authentication check failed:', err);
      logout(true);
      return false;
    }
  }

  function getCurrentUser() {
    return currentUser;
  }

  function updateUserUI(user) {
    if (!user) return;
    const nameEl = document.getElementById('user-display-name');
    const emailEl = document.getElementById('user-display-email');
    const avatarEl = document.getElementById('user-avatar');
    
    if (nameEl) nameEl.textContent = user.name;
    if (emailEl) emailEl.textContent = user.email;
    if (avatarEl) {
      const initial = user.name ? user.name.charAt(0).toUpperCase() : 'U';
      avatarEl.textContent = initial;
    }
  }

  async function handleLogin(email, password) {
    const errorEl = document.getElementById('login-error');
    if (errorEl) errorEl.style.display = 'none';

    try {
      const res = await API.login(email, password);
      API.setToken(res.access_token);
      currentUser = res.user;
      updateUserUI(res.user);
      showAppScreen();
      Router.navigate('dashboard');
      App.showToast(`Welcome back, ${res.user.name}!`, 'success');
      // Load user preferences
      Settings.loadUserSettings();
    } catch (err) {
      if (errorEl) {
        errorEl.textContent = err.message || 'Login failed. Check your credentials.';
        errorEl.style.display = 'block';
      }
      throw err;
    }
  }

  async function handleSignup(name, email, password) {
    const errorEl = document.getElementById('signup-error');
    if (errorEl) errorEl.style.display = 'none';

    try {
      const res = await API.signup(name, email, password);
      API.setToken(res.access_token);
      currentUser = res.user;
      updateUserUI(res.user);
      showAppScreen();
      Router.navigate('dashboard');
      App.showToast(`Account created! Welcome to FocusFlow, ${res.user.name}!`, 'success');
      Settings.loadUserSettings();
      if (!res.user.onboarding_completed && typeof Onboarding !== 'undefined') {
        Onboarding.openModal();
      }
    } catch (err) {
      if (errorEl) {
        errorEl.textContent = err.message || 'Signup failed. Please try again.';
        errorEl.style.display = 'block';
      }
      throw err;
    }
  }

  function logout(silent = false) {
    const wasLoggedIn = !!currentUser || !!API.getToken();
    API.setToken(null);
    currentUser = null;
    showAuthScreen();
    if (wasLoggedIn && !silent) {
      App.showToast('You have been logged out.', 'info');
    }
  }

  function showAuthScreen() {
    document.getElementById('auth-view').style.display = 'flex';
    document.getElementById('app-layout').style.display = 'none';
  }

  function showAppScreen() {
    document.getElementById('auth-view').style.display = 'none';
    document.getElementById('app-layout').style.display = 'flex';
  }

  function initListeners() {
    // Auth Tabs toggle
    const loginTabBtn = document.getElementById('tab-btn-login');
    const signupTabBtn = document.getElementById('tab-btn-signup');
    const loginForm = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');

    if (loginTabBtn && signupTabBtn) {
      loginTabBtn.addEventListener('click', () => {
        loginTabBtn.classList.add('active');
        signupTabBtn.classList.remove('active');
        loginForm.style.display = 'block';
        signupForm.style.display = 'none';
      });

      signupTabBtn.addEventListener('click', () => {
        signupTabBtn.classList.add('active');
        loginTabBtn.classList.remove('active');
        signupForm.style.display = 'block';
        loginForm.style.display = 'none';
      });
    }

    // Login submit
    if (loginForm) {
      loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        const submitBtn = document.getElementById('login-submit-btn');

        if (!email || !password) {
          App.showToast('Please fill in all fields.', 'warning');
          return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Logging in...';
        try {
          await handleLogin(email, password);
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Sign In';
        }
      });
    }

    // Demo Login button
    const demoBtn = document.getElementById('btn-demo-login');
    if (demoBtn) {
      demoBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        const emailInput = document.getElementById('login-email');
        const passInput = document.getElementById('login-password');
        if (emailInput) emailInput.value = 'alex.student@focusflow.app';
        if (passInput) passInput.value = 'password123';
        
        demoBtn.disabled = true;
        demoBtn.textContent = '⚡ Logging into Demo Student...';
        try {
          await handleLogin('alex.student@focusflow.app', 'password123');
        } catch (err) {
          demoBtn.disabled = false;
          demoBtn.innerHTML = '<span>⚡</span> <span>Instant 1-Click Demo Login (Alex Rivera)</span>';
        }
      });
    }

    // Signup submit
    if (signupForm) {
      signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('signup-name').value.trim();
        const email = document.getElementById('signup-email').value.trim();
        const password = document.getElementById('signup-password').value;
        const submitBtn = document.getElementById('signup-submit-btn');

        if (!name || !email || !password) {
          App.showToast('Please complete all signup fields.', 'warning');
          return;
        }

        if (password.length < 6) {
          App.showToast('Password must be at least 6 characters.', 'warning');
          return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Creating Account...';
        try {
          await handleSignup(name, email, password);
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Create Account';
        }
      });
    }

    // Password visibility toggle
    document.querySelectorAll('.btn-toggle-password').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const inputId = btn.dataset.target;
        const input = document.getElementById(inputId);
        if (!input) return;
        if (input.type === 'password') {
          input.type = 'text';
          btn.textContent = '🙈';
        } else {
          input.type = 'password';
          btn.textContent = '👁️';
        }
      });
    });

    // Logout buttons
    const logoutBtns = document.querySelectorAll('.action-logout');
    logoutBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        logout();
      });
    });

    window.addEventListener('focusflow:unauthorized', () => {
      logout(true);
    });
  }

  return {
    checkAuth,
    getCurrentUser,
    handleLogin,
    handleSignup,
    logout,
    initListeners,
    updateUserUI
  };
})();
