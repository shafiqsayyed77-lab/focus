// FocusFlow Smart Revision Engine Controller
const Revision = (() => {
  let revisionQueue = [];

  async function load() {
    const container = document.getElementById('revision-queue-container');
    if (!container) return;

    container.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">Scanning syllabus & mock tests for revision areas...</div>';

    try {
      const items = await API.getRevisionQueue();
      revisionQueue = items;
      renderQueue(items);
    } catch (err) {
      container.innerHTML = `<div class="card" style="color: var(--danger); text-align: center; padding: 24px;">Failed to load revision queue: ${App.escapeHTML(err.message)}</div>`;
    }
  }

  function renderQueue(items) {
    const container = document.getElementById('revision-queue-container');
    if (!container) return;

    if (!items || items.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 48px 24px;">
          <div style="font-size: 3rem; margin-bottom: 12px;">🎉</div>
          <h3 style="font-size: 1.3rem; font-weight: 800; margin-bottom: 6px;">Zero Topics Pending Revision</h3>
          <p style="color: var(--text-muted); font-size: 0.9rem; max-width: 460px; margin: 0 auto 20px;">
            Your academic retention is looking strong! As you take mock tests or let time pass without study, FocusFlow's spaced-repetition engine will queue topics automatically here.
          </p>
          <button class="btn btn-secondary" onclick="Revision.openManualAddModal()">+ Queue Topic Manually</button>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
        <div>
          <span style="font-weight: 800; font-size: 1.1rem; color: var(--text-main);">${items.length} Topics Need Your Attention</span>
          <p style="font-size: 0.85rem; color: var(--text-muted);">Revising weak areas before testing produces the fastest GPA gains.</p>
        </div>
        <button class="btn btn-sm btn-secondary" onclick="Revision.openManualAddModal()">+ Queue Topic</button>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
        ${items.map(item => `
          <div class="card revision-card" style="border-left: 4px solid ${item.is_weak ? 'var(--danger)' : 'var(--accent-orange)'};">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <span class="subject-badge" style="background: ${item.subject_color}20; color: ${item.subject_color}; font-weight: 700;">
                ${App.escapeHTML(item.subject_name)}
              </span>
              ${item.is_weak ? `
                <span class="badge" style="background: var(--danger-subtle); color: var(--danger); font-size: 0.72rem; font-weight: 800;">
                  🔥 WEAK AREA
                </span>
              ` : `
                <span class="badge" style="background: var(--warning-subtle); color: var(--accent-orange); font-size: 0.72rem; font-weight: 800;">
                  ⏳ REVISION DUE
                </span>
              `}
            </div>

            <h4 style="font-size: 1.15rem; font-weight: 800; margin-bottom: 4px;">
              ${App.escapeHTML(item.topic_title)}
            </h4>
            <div style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 12px;">
              📂 ${App.escapeHTML(item.chapter || 'General')}
            </div>

            <div style="background: var(--bg-muted); padding: 10px 14px; border-radius: var(--radius-sm); font-size: 0.82rem; margin-bottom: 16px;">
              <div style="color: var(--danger); font-weight: 700;">⚠️ ${App.escapeHTML(item.reason)}</div>
              ${item.last_score !== null ? `<div style="color: var(--text-muted); margin-top: 2px;">Last Test Score: <strong>${item.last_score}%</strong></div>` : ''}
              ${item.last_studied ? `<div style="color: var(--text-muted); margin-top: 2px;">Last Studied: ${item.last_studied}</div>` : ''}
            </div>

            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <button class="btn btn-sm btn-primary" onclick="Revision.reviseWithAI('${App.escapeHTML(item.topic_title)}', '${App.escapeHTML(item.subject_name)}')">
                💡 AI Explainer
              </button>
              <button class="btn btn-sm btn-secondary" onclick="Revision.focusOnTopic('${App.escapeHTML(item.topic_title)}', '${App.escapeHTML(item.subject_name)}')">
                ⏱️ Focus 25m
              </button>
              <button class="btn btn-sm btn-accent" onclick="MockTest.startTest('${App.escapeHTML(item.subject_name)}')">
                🎯 Retest
              </button>
              <button class="btn btn-sm btn-icon" onclick="Revision.markRevised(${item.topic_id})" title="Mark Revised">
                ✓
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  function reviseWithAI(topic, subject) {
    Router.navigate('ai');
    setTimeout(() => {
      // Switch to explain tab
      document.querySelector('.ai-feature-card[data-tab="explain"]')?.click();
      const topicInput = document.getElementById('ai-explain-topic');
      if (topicInput) topicInput.value = topic;
      document.getElementById('btn-explain-topic')?.click();
    }, 150);
  }

  function focusOnTopic(topic, subject) {
    Router.navigate('timer');
    setTimeout(() => {
      const subjectNameEl = document.getElementById('timer-active-subject-name');
      const taskNameEl = document.getElementById('timer-active-task-name');
      if (subjectNameEl) subjectNameEl.textContent = subject;
      if (taskNameEl) taskNameEl.textContent = `Revision: ${topic}`;
      App.showToast(`Locked in for revision: ${topic}`, 'success');
    }, 150);
  }

  async function markRevised(topicId) {
    try {
      await API.markTopicRevised(topicId);
      App.showToast('Topic marked as revised! Retention updated. ✨', 'success');
      load();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }

  function openManualAddModal() {
    const modal = document.getElementById('modal-add-revision');
    if (!modal) return;

    const topicSelect = document.getElementById('revision-modal-topic');
    if (topicSelect) {
      API.getSubjects().then(subs => {
        let options = '';
        Promise.all(subs.map(s => API.getSubjectTopics(s.id).then(top => ({ sub: s, topics: top }))))
          .then(results => {
            results.forEach(res => {
              if (res.topics.length > 0) {
                options += `<optgroup label="${App.escapeHTML(res.sub.name)}">`;
                res.topics.forEach(t => {
                  options += `<option value="${t.id}">${App.escapeHTML(t.title)}</option>`;
                });
                options += `</optgroup>`;
              }
            });
            topicSelect.innerHTML = options || '<option value="">No topics found</option>';
          });
      });
    }

    modal.classList.add('active');
  }

  async function handleManualAdd(e) {
    e.preventDefault();
    const topicId = parseInt(document.getElementById('revision-modal-topic').value);
    const reason = document.getElementById('revision-modal-reason').value.trim() || 'Student Flagged for Review';

    if (!topicId) {
      App.showToast('Please select a topic.', 'warning');
      return;
    }

    try {
      await API.addTopicToRevision(topicId, reason);
      document.getElementById('modal-add-revision').classList.remove('active');
      App.showToast('Topic queued for revision! 🔄', 'success');
      load();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }

  function initListeners() {
    document.getElementById('form-add-revision')?.addEventListener('submit', handleManualAdd);
  }

  return {
    load,
    reviseWithAI,
    focusOnTopic,
    markRevised,
    openManualAddModal,
    initListeners
  };
})();
