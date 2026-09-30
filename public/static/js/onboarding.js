// FocusFlow Professional Academic Onboarding Controller
const Onboarding = (() => {
  let subjectChips = [];

  function openModal() {
    const modal = document.getElementById('modal-onboarding');
    if (!modal) return;
    subjectChips = [];
    renderChips();
    modal.classList.add('active');
  }

  function closeModal() {
    const modal = document.getElementById('modal-onboarding');
    if (modal) modal.classList.remove('active');
  }

  function addSubjectChip(name) {
    const trimmed = name.trim();
    if (!trimmed) return;
    if (subjectChips.includes(trimmed)) return;
    subjectChips.push(trimmed);
    renderChips();
  }

  function removeSubjectChip(index) {
    subjectChips.splice(index, 1);
    renderChips();
  }

  function renderChips() {
    const container = document.getElementById('onboard-subjects-chips');
    if (!container) return;

    if (subjectChips.length === 0) {
      container.innerHTML = '<span style="font-size: 0.85rem; color: var(--text-muted); font-style: italic;">No subjects added yet. Type below and press Enter or click + Add</span>';
      return;
    }

    container.innerHTML = subjectChips.map((sub, idx) => `
      <span class="subject-chip" style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; background: rgba(108, 59, 255, 0.12); color: var(--primary-600); border-radius: var(--radius-full); font-size: 0.85rem; font-weight: 700; margin: 3px;">
        <span>📚 ${App.escapeHTML(sub)}</span>
        <button type="button" onclick="Onboarding.removeSubjectChip(${idx})" style="background: none; border: none; cursor: pointer; color: var(--text-muted); font-size: 0.9rem; line-height: 1;" title="Remove">✕</button>
      </span>
    `).join('');
  }

  async function handleSubmit(e) {
    if (e) e.preventDefault();
    const course = (document.getElementById('onboard-course')?.value || '').trim() || 'General Studies';
    const institution = (document.getElementById('onboard-institution')?.value || '').trim();
    const semester = (document.getElementById('onboard-semester')?.value || '').trim();
    const goalMins = parseInt(document.getElementById('onboard-goal-mins')?.value) || 60;

    const examTitle = (document.getElementById('onboard-exam-title')?.value || '').trim();
    const examSubject = (document.getElementById('onboard-exam-subject')?.value || '').trim();
    const examDate = (document.getElementById('onboard-exam-date')?.value || '').trim();

    // Check if user has added an input in the field without pressing Add
    const pendingSub = (document.getElementById('onboard-subject-input')?.value || '').trim();
    if (pendingSub && !subjectChips.includes(pendingSub)) {
      subjectChips.push(pendingSub);
    }

    const payload = {
      course,
      institution,
      semester,
      study_goal_minutes: goalMins,
      subjects: subjectChips,
      exam_title: examTitle || null,
      exam_subject: examSubject || null,
      exam_date: examDate || null
    };

    const submitBtn = document.getElementById('btn-onboard-submit');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Building Your Workspace...';
    }

    try {
      await API.completeOnboarding(payload);
      closeModal();
      App.showToast(`🎉 Academic workspace configured for ${course}!`, 'success');
      
      // Update local currentUser flag
      const user = Auth.getCurrentUser();
      if (user) {
        user.course = course;
        user.institution = institution;
        user.semester = semester;
        user.onboarding_completed = true;
      }

      // Reload views
      if (typeof Dashboard !== 'undefined') Dashboard.load();
      if (typeof SubjectsTasks !== 'undefined') SubjectsTasks.loadSubjects();
      if (typeof Planner !== 'undefined') Planner.load();
      if (typeof Exams !== 'undefined') Exams.load();
    } catch (err) {
      App.showToast(err.message || 'Failed to complete onboarding.', 'danger');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Launch FocusFlow 🚀';
      }
    }
  }

  async function skip() {
    try {
      await API.completeOnboarding({
        course: 'General Studies',
        subjects: [],
        study_goal_minutes: 60
      });
      closeModal();
      App.showToast('You can customize subjects anytime from the Subjects page!', 'info');
      if (typeof Dashboard !== 'undefined') Dashboard.load();
      if (typeof SubjectsTasks !== 'undefined') SubjectsTasks.loadSubjects();
    } catch (err) {
      closeModal();
    }
  }

  function initListeners() {
    const input = document.getElementById('onboard-subject-input');
    const addBtn = document.getElementById('btn-onboard-add-sub');
    const form = document.getElementById('form-onboarding');
    const skipBtn = document.getElementById('btn-onboard-skip');

    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          addSubjectChip(input.value);
          input.value = '';
        }
      });
    }

    if (addBtn && input) {
      addBtn.addEventListener('click', (e) => {
        e.preventDefault();
        addSubjectChip(input.value);
        input.value = '';
        input.focus();
      });
    }

    if (form) {
      form.addEventListener('submit', handleSubmit);
    }

    if (skipBtn) {
      skipBtn.addEventListener('click', skip);
    }
  }

  return {
    openModal,
    closeModal,
    addSubjectChip,
    removeSubjectChip,
    skip,
    initListeners
  };
})();
