// FocusFlow Profile & Settings Controller
const Settings = (() => {

  async function loadProfile() {
    try {
      const user = await API.getProfile();
      document.getElementById('profile-name-input').value = user.name || '';
      document.getElementById('profile-email-display').value = user.email || '';
      document.getElementById('profile-created-display').textContent = `Member since ${user.created_at ? user.created_at.slice(0, 10) : 'recently'}`;
    } catch (err) {
      console.error('Failed to load profile:', err);
    }
  }

  async function loadUserSettings() {
    try {
      const settings = await API.getSettings();
      applyTheme(settings.theme);

      // Populate form
      const themeSelect = document.getElementById('settings-theme');
      const focusSelect = document.getElementById('settings-focus-duration');
      const breakSelect = document.getElementById('settings-break-duration');
      const soundCheck = document.getElementById('settings-sound-toggle');
      const notifCheck = document.getElementById('settings-notif-toggle');

      if (themeSelect) themeSelect.value = settings.theme;
      if (focusSelect) focusSelect.value = settings.default_focus_duration;
      if (breakSelect) breakSelect.value = settings.default_break_duration;
      if (soundCheck) soundCheck.checked = settings.sound_enabled;
      if (notifCheck) notifCheck.checked = settings.notifications_enabled;

      // Update timer default duration
      if (settings.default_focus_duration) {
        Timer.setDuration(settings.default_focus_duration);
      }
    } catch (err) {
      console.warn('Failed to load settings:', err);
    }
  }

  function applyTheme(theme) {
    if (theme === 'dark') {
      document.body.setAttribute('data-theme', 'dark');
      const icon = document.getElementById('theme-toggle-icon');
      if (icon) icon.textContent = '☀️';
    } else {
      document.body.removeAttribute('data-theme');
      const icon = document.getElementById('theme-toggle-icon');
      if (icon) icon.textContent = '🌙';
    }
  }

  function toggleThemeQuick() {
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const newTheme = isDark ? 'light' : 'dark';
    applyTheme(newTheme);

    // Save to settings silently
    API.updateSettings({ theme: newTheme }).catch(() => {});
  }

  async function handleProfileSubmit(e) {
    e.preventDefault();
    const name = document.getElementById('profile-name-input').value.trim();
    if (!name || name.length < 2) {
      App.showToast('Name must be at least 2 characters.', 'warning');
      return;
    }

    try {
      const updated = await API.updateProfile(name);
      Auth.updateUserUI(updated);
      App.showToast('Profile name updated successfully!', 'success');
    } catch (err) {
      App.showToast(err.message || 'Failed to update profile.', 'error');
    }
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault();
    const currPass = document.getElementById('pass-current').value;
    const newPass = document.getElementById('pass-new').value;
    const confirmPass = document.getElementById('pass-confirm').value;

    if (!currPass || !newPass || !confirmPass) {
      App.showToast('Please fill in all password fields.', 'warning');
      return;
    }

    if (newPass.length < 6) {
      App.showToast('New password must be at least 6 characters.', 'warning');
      return;
    }

    if (newPass !== confirmPass) {
      App.showToast('New password and confirmation do not match.', 'error');
      return;
    }

    try {
      await API.changePassword(currPass, newPass);
      App.showToast('Password changed successfully!', 'success');
      document.getElementById('form-password').reset();
    } catch (err) {
      App.showToast(err.message || 'Failed to change password.', 'error');
    }
  }

  async function handleSettingsSubmit(e) {
    e.preventDefault();
    const theme = document.getElementById('settings-theme').value;
    const default_focus_duration = parseInt(document.getElementById('settings-focus-duration').value);
    const default_break_duration = parseInt(document.getElementById('settings-break-duration').value);
    const sound_enabled = document.getElementById('settings-sound-toggle').checked;
    const notifications_enabled = document.getElementById('settings-notif-toggle').checked;

    try {
      const updated = await API.updateSettings({
        theme,
        default_focus_duration,
        default_break_duration,
        sound_enabled,
        notifications_enabled
      });

      applyTheme(updated.theme);
      Timer.setDuration(updated.default_focus_duration);
      App.showToast('Settings saved successfully!', 'success');
    } catch (err) {
      App.showToast(err.message || 'Failed to save settings.', 'error');
    }
  }

  function initListeners() {
    document.getElementById('form-profile')?.addEventListener('submit', handleProfileSubmit);
    document.getElementById('form-password')?.addEventListener('submit', handlePasswordSubmit);
    document.getElementById('form-settings')?.addEventListener('submit', handleSettingsSubmit);
    document.getElementById('btn-quick-theme-toggle')?.addEventListener('click', toggleThemeQuick);
  }

  return {
    loadProfile,
    loadUserSettings,
    applyTheme,
    toggleThemeQuick,
    initListeners
  };
})();
