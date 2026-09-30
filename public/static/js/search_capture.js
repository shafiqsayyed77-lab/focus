// FocusFlow Global Search & Quick Capture Controller
const SearchCapture = (() => {

  // ================= GLOBAL SEARCH =================
  let searchTimeout = null;

  function openSearchModal() {
    const modal = document.getElementById('modal-global-search');
    if (!modal) return;
    modal.classList.add('active');
    const input = document.getElementById('global-search-input');
    if (input) {
      input.value = '';
      input.focus();
    }
    const results = document.getElementById('global-search-results');
    if (results) results.innerHTML = '<div style="text-align: center; padding: 24px; color: var(--text-muted);">Type a subject, topic, formula, or task name...</div>';
  }

  function handleSearchInput(e) {
    const query = e.target.value.trim();
    clearTimeout(searchTimeout);
    if (!query) {
      document.getElementById('global-search-results').innerHTML = '<div style="text-align: center; padding: 24px; color: var(--text-muted);">Type a subject, topic, formula, or task name...</div>';
      return;
    }

    searchTimeout = setTimeout(async () => {
      try {
        const data = await API.globalSearch(query);
        renderSearchResults(data);
      } catch (err) {
        console.warn('Search failed:', err);
      }
    }, 200);
  }

  function renderSearchResults(data) {
    const box = document.getElementById('global-search-results');
    if (!box) return;

    const total = data.subjects.length + data.topics.length + data.tasks.length + data.exams.length + data.notes.length;
    if (total === 0) {
      box.innerHTML = `<div style="text-align: center; padding: 32px; color: var(--text-muted);">No matches found for "${App.escapeHTML(data.query)}"</div>`;
      return;
    }

    let html = '';

    if (data.subjects.length > 0) {
      html += `<div style="font-size: 0.78rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; margin: 12px 0 6px;">📚 Subjects</div>`;
      html += data.subjects.map(s => `
        <div class="search-result-item" onclick="SearchCapture.selectResult('subjects', ${s.id})" style="padding: 10px 14px; background: var(--bg-muted); border-radius: var(--radius-sm); margin-bottom: 6px; cursor: pointer; display: flex; align-items: center; justify-content: space-between;">
          <span style="font-weight: 700; color: var(--text-main);">${App.escapeHTML(s.name)}</span>
          <span style="font-size: 0.78rem; color: var(--text-muted);">View Subject →</span>
        </div>
      `).join('');
    }

    if (data.topics.length > 0) {
      html += `<div style="font-size: 0.78rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; margin: 12px 0 6px;">📖 Topics</div>`;
      html += data.topics.map(t => `
        <div class="search-result-item" onclick="SearchCapture.selectResult('topic', ${t.id}, ${t.subject_id})" style="padding: 10px 14px; background: var(--bg-muted); border-radius: var(--radius-sm); margin-bottom: 6px; cursor: pointer; display: flex; align-items: center; justify-content: space-between;">
          <div>
            <span style="font-weight: 700; color: var(--text-main);">${App.escapeHTML(t.title)}</span>
            <span style="font-size: 0.78rem; color: var(--primary-600); margin-left: 8px;">(${App.escapeHTML(t.subject_name)})</span>
          </div>
          <span style="font-size: 0.78rem; color: var(--text-muted);">Study Topic →</span>
        </div>
      `).join('');
    }

    if (data.tasks.length > 0) {
      html += `<div style="font-size: 0.78rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; margin: 12px 0 6px;">📝 Tasks</div>`;
      html += data.tasks.map(t => `
        <div class="search-result-item" onclick="SearchCapture.selectResult('planner')" style="padding: 10px 14px; background: var(--bg-muted); border-radius: var(--radius-sm); margin-bottom: 6px; cursor: pointer; display: flex; align-items: center; justify-content: space-between;">
          <span style="font-weight: 700; color: var(--text-main);">${App.escapeHTML(t.title)}</span>
          <span style="font-size: 0.78rem; color: var(--text-muted);">View in Planner →</span>
        </div>
      `).join('');
    }

    if (data.exams.length > 0) {
      html += `<div style="font-size: 0.78rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; margin: 12px 0 6px;">🎯 Exams</div>`;
      html += data.exams.map(e => `
        <div class="search-result-item" onclick="SearchCapture.selectResult('exams')" style="padding: 10px 14px; background: var(--bg-muted); border-radius: var(--radius-sm); margin-bottom: 6px; cursor: pointer; display: flex; align-items: center; justify-content: space-between;">
          <div>
            <span style="font-weight: 700; color: var(--text-main);">${App.escapeHTML(e.title)}</span>
            <span style="font-size: 0.78rem; color: var(--danger); margin-left: 8px;">(${e.exam_date})</span>
          </div>
          <span style="font-size: 0.78rem; color: var(--text-muted);">Exam Prep →</span>
        </div>
      `).join('');
    }

    if (data.notes.length > 0) {
      html += `<div style="font-size: 0.78rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; margin: 12px 0 6px;">📑 Notes & Formulas</div>`;
      html += data.notes.map(n => `
        <div class="search-result-item" onclick="SearchCapture.selectResult('resources')" style="padding: 10px 14px; background: var(--bg-muted); border-radius: var(--radius-sm); margin-bottom: 6px; cursor: pointer; display: flex; align-items: center; justify-content: space-between;">
          <span style="font-weight: 700; color: var(--text-main);">${App.escapeHTML(n.title)}</span>
          <span style="font-size: 0.78rem; color: var(--text-muted);">Open Resource →</span>
        </div>
      `).join('');
    }

    box.innerHTML = html;
  }

  function selectResult(type, id, parentId) {
    document.getElementById('modal-global-search')?.classList.remove('active');
    if (type === 'subjects') {
      Router.navigate('subjects');
      if (id && typeof SubjectsTasks !== 'undefined') {
        setTimeout(() => SubjectsTasks.openSubjectDetail(id), 100);
      }
    } else if (type === 'topic') {
      Router.navigate('subjects');
      if (parentId && typeof SubjectsTasks !== 'undefined') {
        setTimeout(() => SubjectsTasks.openSubjectDetail(parentId), 100);
      }
    } else if (type === 'planner') {
      Router.navigate('planner');
    } else if (type === 'exams') {
      Router.navigate('exams');
    } else if (type === 'resources') {
      Router.navigate('resources');
    }
  }

  // ================= QUICK CAPTURE =================
  let currentCaptureTab = 'task';

  function openQuickCaptureModal() {
    const modal = document.getElementById('modal-quick-capture');
    if (!modal) return;

    // Populate subjects in quick capture selects
    API.getSubjects().then(subs => {
      const opts = '<option value="">-- No Subject (General) --</option>' +
        subs.map(s => `<option value="${s.id}">${App.escapeHTML(s.name)}</option>`).join('');
      document.querySelectorAll('.qc-subject-select').forEach(sel => {
        sel.innerHTML = opts;
      });
    });

    modal.classList.add('active');
  }

  async function handleQuickCaptureSubmit(e) {
    e.preventDefault();
    const type = currentCaptureTab;
    const data = {};

    if (type === 'task') {
      data.title = document.getElementById('qc-task-title').value.trim();
      data.subject_id = document.getElementById('qc-task-subject').value ? parseInt(document.getElementById('qc-task-subject').value) : null;
      data.priority = document.getElementById('qc-task-priority').value;
      data.estimated_minutes = parseInt(document.getElementById('qc-task-mins').value) || 30;
      if (!data.title) return;
    } else if (type === 'topic') {
      data.title = document.getElementById('qc-topic-title').value.trim();
      data.subject_id = parseInt(document.getElementById('qc-topic-subject').value);
      data.chapter = document.getElementById('qc-topic-chapter').value.trim() || 'General';
      data.priority = 'Medium';
      if (!data.title || !data.subject_id) {
        App.showToast('Please select a subject and enter topic name.', 'warning');
        return;
      }
    } else if (type === 'note') {
      data.title = document.getElementById('qc-note-title').value.trim();
      data.content = document.getElementById('qc-note-content').value.trim();
      data.subject_id = document.getElementById('qc-note-subject').value ? parseInt(document.getElementById('qc-note-subject').value) : null;
      if (!data.title || !data.content) return;
    } else if (type === 'exam') {
      data.title = document.getElementById('qc-exam-title').value.trim();
      data.subject_id = parseInt(document.getElementById('qc-exam-subject').value);
      data.exam_date = document.getElementById('qc-exam-date').value;
      if (!data.title || !data.subject_id || !data.exam_date) return;
    }

    try {
      await API.quickCapture(type, data);
      document.getElementById('modal-quick-capture').classList.remove('active');
      App.showToast(`⚡ ${type.toUpperCase()} captured instantly!`, 'success');
      
      // Refresh current view if applicable
      const r = Router.getCurrentRoute();
      if (r === 'dashboard' && typeof Dashboard !== 'undefined') Dashboard.load();
      if (r === 'planner' && typeof Planner !== 'undefined') Planner.load();
      if (r === 'exams' && typeof Exams !== 'undefined') Exams.load();
      if (r === 'resources' && typeof Resources !== 'undefined') Resources.load();
      if (r === 'subjects' && typeof SubjectsTasks !== 'undefined') SubjectsTasks.loadSubjects();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }

  function initListeners() {
    // Keyboard shortcut '/' or Ctrl+K for search
    window.addEventListener('keydown', (e) => {
      if ((e.key === '/' || (e.ctrlKey && e.key === 'k')) && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        e.preventDefault();
        openSearchModal();
      }
    });

    document.getElementById('btn-header-search')?.addEventListener('click', openSearchModal);
    document.getElementById('global-search-input')?.addEventListener('input', handleSearchInput);

    // Quick Capture
    document.getElementById('btn-quick-add')?.addEventListener('click', openQuickCaptureModal);
    document.getElementById('form-quick-capture')?.addEventListener('submit', handleQuickCaptureSubmit);

    // Quick Capture tab switching
    document.querySelectorAll('.qc-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.qc-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentCaptureTab = btn.dataset.tab;

        document.querySelectorAll('.qc-panel').forEach(p => {
          p.style.display = p.dataset.tab === currentCaptureTab ? 'block' : 'none';
        });
      });
    });
  }

  return {
    openSearchModal,
    openQuickCaptureModal,
    selectResult,
    initListeners
  };
})();
