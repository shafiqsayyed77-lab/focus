// FocusFlow Application Core & UI Orchestration
const App = (() => {

  function escapeHTML(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };

    toast.innerHTML = `
      <span>${icons[type] || 'ℹ️'}</span>
      <span style="flex: 1;">${escapeHTML(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(40px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('active');
    }
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('active');
    }
  }

  function initModalBackdrops() {
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          overlay.classList.remove('active');
        }
      });
    });

    document.querySelectorAll('.modal-close').forEach(btn => {
      btn.addEventListener('click', () => {
        const overlay = btn.closest('.modal-overlay');
        if (overlay) overlay.classList.remove('active');
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
      }
    });
  }

  async function init() {
    // 1. Initialize modal backdrops & listeners
    initModalBackdrops();

    // 2. Initialize module event listeners
    Auth.initListeners();
    SubjectsTasks.initListeners();
    if (typeof Planner !== 'undefined') Planner.initListeners();
    if (typeof Exams !== 'undefined') Exams.initListeners();
    if (typeof Revision !== 'undefined') Revision.initListeners();
    if (typeof Resources !== 'undefined') Resources.initListeners();
    if (typeof SearchCapture !== 'undefined') SearchCapture.initListeners();
    if (typeof Onboarding !== 'undefined') Onboarding.initListeners();
    AIStudy.initListeners();
    Timer.initListeners();
    Settings.initListeners();
    Router.init();

    // 3. Verify user session
    const isAuthed = await Auth.checkAuth();
    if (isAuthed) {
      await Settings.loadUserSettings();
      const user = Auth.getCurrentUser();
      if (user && !user.onboarding_completed) {
        if (typeof Onboarding !== 'undefined') Onboarding.openModal();
      }
      Dashboard.load();
    }
  }

  return {
    init,
    escapeHTML,
    showToast,
    openModal,
    closeModal
  };
})();

// Boot application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
