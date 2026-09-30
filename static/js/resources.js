// FocusFlow Resources & Notes Library Controller
const Resources = (() => {
  let resourcesList = [];
  let currentFilter = 'all';
  let currentSubject = '';

  async function load() {
    await loadResources();
    populateSubjectFilter();
  }

  async function loadResources() {
    const container = document.getElementById('resources-grid-container');
    if (!container) return;

    try {
      const params = {};
      if (currentFilter !== 'all') params.type = currentFilter;
      if (currentSubject) params.subject_id = currentSubject;

      const items = await API.getResources(params);
      resourcesList = items;
      renderResources(items);
    } catch (err) {
      container.innerHTML = `<div class="card" style="color: var(--danger); text-align: center;">Failed to load resources: ${App.escapeHTML(err.message)}</div>`;
    }
  }

  function renderResources(items) {
    const container = document.getElementById('resources-grid-container');
    if (!container) return;

    if (!items || items.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 48px 24px; grid-column: 1 / -1;">
          <div style="font-size: 3rem; margin-bottom: 12px;">📚</div>
          <h3 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 6px;">Resource Library Empty</h3>
          <p style="color: var(--text-muted); font-size: 0.9rem; max-width: 440px; margin: 0 auto 20px;">
            Save lecture notes, exam cheat-sheets, formulas, reference links, and reminders organized by subject.
          </p>
          <button class="btn btn-primary" onclick="Resources.openAddModal()">+ Add Your First Note / Resource</button>
        </div>
      `;
      return;
    }

    const typeIcons = {
      note: '📝 Note',
      formula: '📐 Formula / Cheat Sheet',
      link: '🔗 Web Link',
      reminder: '⏰ Reminder',
      file: '📁 Document'
    };

    container.innerHTML = items.map(res => `
      <div class="card resource-card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <span class="badge" style="background: var(--bg-muted); color: var(--text-muted); font-size: 0.75rem; font-weight: 700;">
              ${typeIcons[res.type] || '📝 Note'}
            </span>
            <button class="btn btn-sm btn-icon" onclick="Resources.deleteResource(${res.id})" title="Delete">✕</button>
          </div>

          <h4 style="font-size: 1.15rem; font-weight: 800; margin-bottom: 4px; color: var(--text-main);">
            ${App.escapeHTML(res.title)}
          </h4>

          ${res.subject_name ? `
            <div style="font-size: 0.8rem; color: var(--primary-600); font-weight: 700; margin-bottom: 10px;">
              📖 ${App.escapeHTML(res.subject_name)}
            </div>
          ` : ''}

          <div style="font-size: 0.88rem; color: var(--text-muted); white-space: pre-wrap; font-family: ${res.type === 'formula' ? 'monospace' : 'inherit'}; background: ${res.type === 'formula' ? 'var(--bg-muted)' : 'transparent'}; padding: ${res.type === 'formula' ? '10px' : '0'}; border-radius: var(--radius-sm); margin-bottom: 12px; line-height: 1.5;">
            ${App.escapeHTML(res.content)}
          </div>

          ${res.url ? `
            <div style="margin-bottom: 10px;">
              <a href="${App.escapeHTML(res.url)}" target="_blank" rel="noopener noreferrer" style="font-size: 0.82rem; color: var(--primary-600); font-weight: 700; text-decoration: underline;">
                🔗 Open Link →
              </a>
            </div>
          ` : ''}
        </div>

        ${res.tags ? `
          <div style="display: flex; gap: 6px; flex-wrap: wrap; border-top: 1px solid var(--border-color); padding-top: 10px; margin-top: 10px;">
            ${res.tags.split(',').map(t => `<span style="font-size: 0.72rem; padding: 2px 6px; background: var(--bg-muted); border-radius: var(--radius-sm); color: var(--text-muted);">#${App.escapeHTML(t.trim())}</span>`).join('')}
          </div>
        ` : ''}
      </div>
    `).join('');
  }

  function openAddModal() {
    const modal = document.getElementById('modal-resource');
    if (!modal) return;

    // Populate subject select
    const select = document.getElementById('resource-modal-subject');
    if (select) {
      API.getSubjects().then(subs => {
        select.innerHTML = '<option value="">-- No Subject (General) --</option>' +
          subs.map(s => `<option value="${s.id}">${App.escapeHTML(s.name)}</option>`).join('');
      });
    }

    modal.classList.add('active');
  }

  async function handleAdd(e) {
    e.preventDefault();
    const title = document.getElementById('resource-modal-title').value.trim();
    const subjectId = document.getElementById('resource-modal-subject').value ? parseInt(document.getElementById('resource-modal-subject').value) : null;
    const type = document.getElementById('resource-modal-type').value;
    const content = document.getElementById('resource-modal-content').value.trim();
    const url = document.getElementById('resource-modal-url').value.trim();
    const tags = document.getElementById('resource-modal-tags').value.trim();

    if (!title || !content) {
      App.showToast('Title and content are required.', 'warning');
      return;
    }

    try {
      await API.createResource({
        title,
        subject_id: subjectId,
        type,
        content,
        url,
        tags
      });
      document.getElementById('modal-resource').classList.remove('active');
      App.showToast('Resource saved to your library! 📖', 'success');
      loadResources();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }

  async function deleteResource(id) {
    try {
      await API.deleteResource(id);
      App.showToast('Resource deleted.', 'info');
      loadResources();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }

  function populateSubjectFilter() {
    const filter = document.getElementById('resource-filter-subject');
    if (!filter) return;
    API.getSubjects().then(subs => {
      filter.innerHTML = '<option value="">All Subjects</option>' +
        subs.map(s => `<option value="${s.id}">${App.escapeHTML(s.name)}</option>`).join('');
    });
  }

  function initListeners() {
    document.querySelectorAll('.resource-filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.resource-filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentFilter = tab.dataset.filter || 'all';
        loadResources();
      });
    });

    document.getElementById('resource-filter-subject')?.addEventListener('change', (e) => {
      currentSubject = e.target.value;
      loadResources();
    });

    document.getElementById('btn-add-resource')?.addEventListener('click', openAddModal);
    document.getElementById('form-resource')?.addEventListener('submit', handleAdd);
  }

  return {
    load,
    openAddModal,
    deleteResource,
    initListeners
  };
})();
