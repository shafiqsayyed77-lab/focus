// FocusFlow Smart Academic Planner & Calendar Controller
const Planner = (() => {
  let currentFilter = 'all';
  let currentSubject = '';
  let plannerItems = [];

  async function load() {
    await loadItems();
    populateSubjectFilters();
  }

  async function loadItems() {
    const container = document.getElementById('planner-items-container');
    if (!container) return;

    try {
      const params = {};
      if (currentFilter !== 'all' && currentFilter !== 'pending' && currentFilter !== 'completed') {
        params.item_type = currentFilter;
      } else if (currentFilter === 'pending') {
        params.status_filter = 'pending';
      } else if (currentFilter === 'completed') {
        params.status_filter = 'completed';
      }

      if (currentSubject) {
        params.subject_id = currentSubject;
      }

      const items = await API.getTasks(params);
      plannerItems = items;
      renderItems(items);
    } catch (err) {
      container.innerHTML = `<div class="card" style="color: var(--danger); text-align: center;">Failed to load planner: ${App.escapeHTML(err.message)}</div>`;
    }
  }

  function renderItems(items) {
    const container = document.getElementById('planner-items-container');
    if (!container) return;

    if (!items || items.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 48px 24px;">
          <div style="font-size: 3rem; margin-bottom: 12px;">📅</div>
          <h3 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 6px;">Your Planner is Clean</h3>
          <p style="color: var(--text-muted); font-size: 0.9rem; max-width: 440px; margin: 0 auto 20px;">
            Add upcoming assignments, study tasks, projects, or revisions to keep your academic schedule locked in!
          </p>
          <div style="display: flex; gap: 10px; justify-content: center;">
            <button class="btn btn-primary" onclick="Planner.openAddItemModal()">+ Add Study Task</button>
            <button class="btn btn-secondary" onclick="Planner.openPlanMyDayModal()">⚡ Plan My Day</button>
          </div>
        </div>
      `;
      return;
    }

    const typeIcons = {
      task: '📝',
      assignment: '📑',
      exam: '🎯',
      project: '💻',
      revision: '🔄',
      study: '📖'
    };

    container.innerHTML = items.map(item => {
      const icon = typeIcons[item.item_type] || '📝';
      const isDone = item.is_completed;
      const prioColor = item.priority === 'High' ? 'var(--danger)' : (item.priority === 'Medium' ? 'var(--accent-orange)' : 'var(--primary-500)');

      return `
        <div class="card task-item ${isDone ? 'completed' : ''}" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; margin-bottom: 12px; gap: 14px; border-left: 4px solid ${prioColor};">
          <div style="display: flex; align-items: center; gap: 14px; flex: 1;">
            <input type="checkbox" ${isDone ? 'checked' : ''} onchange="Planner.toggleItem(${item.id})" style="width: 20px; height: 20px; cursor: pointer; accent-color: var(--primary-600);">
            <div style="flex: 1;">
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 3px;">
                <span style="font-size: 0.85rem;">${icon}</span>
                <span style="font-size: 0.72rem; text-transform: uppercase; font-weight: 800; padding: 2px 8px; border-radius: var(--radius-full); background: var(--bg-muted); color: var(--text-muted);">
                  ${item.item_type || 'task'}
                </span>
                ${item.subject_name ? `
                  <span class="subject-badge" style="background: ${item.subject_color || '#6C3BFF'}20; color: ${item.subject_color || '#6C3BFF'}; font-size: 0.75rem; font-weight: 700;">
                    ${App.escapeHTML(item.subject_name)}
                  </span>
                ` : ''}
                <span style="font-size: 0.75rem; color: var(--text-muted);">⏱ ${item.estimated_minutes || 30}m</span>
                ${item.deadline ? `<span style="font-size: 0.75rem; color: var(--danger); font-weight: 600;">📅 Due: ${item.deadline}</span>` : ''}
              </div>
              <div style="font-size: 0.95rem; font-weight: 700; ${isDone ? 'text-decoration: line-through; opacity: 0.6;' : 'color: var(--text-main);'}">
                ${App.escapeHTML(item.title)}
              </div>
              ${item.description ? `<p style="font-size: 0.82rem; color: var(--text-muted); margin-top: 4px;">${App.escapeHTML(item.description)}</p>` : ''}
            </div>
          </div>

          <div style="display: flex; align-items: center; gap: 8px;">
            ${!isDone ? `
              <button class="btn btn-sm btn-secondary" onclick="Planner.startTimerForItem('${App.escapeHTML(item.title)}', '${App.escapeHTML(item.subject_name || '')}', ${item.estimated_minutes || 25})" title="Start Focus Session on this task">
                ⏱️ Focus
              </button>
            ` : ''}
            <button class="btn btn-sm btn-icon" onclick="Planner.deleteItem(${item.id})" title="Delete item">✕</button>
          </div>
        </div>
      `;
    }).join('');
  }

  async function toggleItem(id) {
    try {
      await API.toggleTask(id);
      loadItems();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }

  async function deleteItem(id) {
    try {
      await API.deleteTask(id);
      App.showToast('Item deleted.', 'info');
      loadItems();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }

  function startTimerForItem(title, subject, minutes) {
    Router.navigate('timer');
    setTimeout(() => {
      const subjectNameEl = document.getElementById('timer-active-subject-name');
      const taskNameEl = document.getElementById('timer-active-task-name');
      if (subjectNameEl) subjectNameEl.textContent = subject || 'General Study';
      if (taskNameEl) taskNameEl.textContent = title;
      App.showToast(`Locked in for: ${title}`, 'success');
    }, 150);
  }

  function openAddItemModal() {
    const modal = document.getElementById('modal-planner-item');
    if (!modal) return;

    // Populate subject dropdown
    const select = document.getElementById('planner-item-subject');
    if (select) {
      API.getSubjects().then(subs => {
        select.innerHTML = '<option value="">-- No Subject (General) --</option>' +
          subs.map(s => `<option value="${s.id}">${App.escapeHTML(s.name)}</option>`).join('');
      });
    }

    modal.classList.add('active');
  }

  async function handleAddItem(e) {
    e.preventDefault();
    const title = document.getElementById('planner-item-title').value.trim();
    const subjectId = document.getElementById('planner-item-subject').value ? parseInt(document.getElementById('planner-item-subject').value) : null;
    const itemType = document.getElementById('planner-item-type').value;
    const priority = document.getElementById('planner-item-priority').value;
    const estMins = parseInt(document.getElementById('planner-item-mins').value) || 30;
    const deadline = document.getElementById('planner-item-deadline').value || null;
    const desc = document.getElementById('planner-item-desc').value.trim();

    if (!title) {
      App.showToast('Title cannot be empty.', 'warning');
      return;
    }

    try {
      await API.createTask({
        title,
        subject_id: subjectId,
        item_type: itemType,
        priority,
        estimated_minutes: estMins,
        deadline,
        description: desc
      });
      document.getElementById('modal-planner-item').classList.remove('active');
      App.showToast('Item added to your schedule! 🚀', 'success');
      loadItems();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }

  function openPlanMyDayModal() {
    const modal = document.getElementById('modal-plan-my-day');
    if (modal) modal.classList.add('active');
  }

  async function handlePlanMyDay(e) {
    e.preventDefault();
    const hours = parseFloat(document.getElementById('plan-day-hours').value) || 2.0;
    const minutes = Math.round(hours * 60);

    const btn = document.getElementById('btn-submit-plan-day');
    btn.disabled = true;
    btn.textContent = 'Optimizing Schedule...';

    try {
      const plan = await API.planMyDay(minutes);
      btn.disabled = false;
      btn.textContent = '⚡ Optimize Schedule';

      const resultBox = document.getElementById('plan-day-result');
      if (resultBox) {
        resultBox.innerHTML = `
          <div style="margin-top: 20px; padding: 16px; background: var(--bg-muted); border-radius: var(--radius-md);">
            <div style="font-weight: 800; font-size: 1rem; color: var(--primary-700); margin-bottom: 4px;">
              ✨ Daily Lock-In Schedule (${plan.planned_minutes} min total)
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px;">${App.escapeHTML(plan.summary)}</p>

            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${plan.schedule.map(block => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--card-bg); border-radius: var(--radius-sm); border-left: 3px solid ${block.subject_color || '#6C3BFF'};">
                  <div>
                    <span style="font-size: 0.78rem; font-weight: 700; color: var(--text-muted);">${block.time_block}</span>
                    <div style="font-size: 0.92rem; font-weight: 700; color: var(--text-main);">${App.escapeHTML(block.title)}</div>
                    <span style="font-size: 0.75rem; color: ${block.subject_color || 'var(--primary-600)'};">${App.escapeHTML(block.subject)}</span>
                  </div>
                  ${block.type !== 'break' ? `
                    <button class="btn btn-sm btn-primary" onclick="Planner.startTimerForItem('${App.escapeHTML(block.title)}', '${App.escapeHTML(block.subject)}', ${block.duration_minutes})">
                      Start ⏱️
                    </button>
                  ` : `
                    <span style="font-size: 0.82rem; color: var(--accent-orange); font-weight: 700;">Take Break</span>
                  `}
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }
    } catch (err) {
      btn.disabled = false;
      btn.textContent = '⚡ Optimize Schedule';
      App.showToast(err.message, 'danger');
    }
  }

  function populateSubjectFilters() {
    const filterSelect = document.getElementById('planner-filter-subject');
    if (!filterSelect) return;
    API.getSubjects().then(subs => {
      filterSelect.innerHTML = '<option value="">All Subjects</option>' +
        subs.map(s => `<option value="${s.id}">${App.escapeHTML(s.name)}</option>`).join('');
    });
  }

  function initListeners() {
    // Tabs filter clicks
    document.querySelectorAll('.planner-filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.planner-filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentFilter = tab.dataset.filter || 'all';
        loadItems();
      });
    });

    document.getElementById('planner-filter-subject')?.addEventListener('change', (e) => {
      currentSubject = e.target.value;
      loadItems();
    });

    document.getElementById('btn-add-planner-item')?.addEventListener('click', openAddItemModal);
    document.getElementById('btn-open-plan-day')?.addEventListener('click', openPlanMyDayModal);
    document.getElementById('form-planner-item')?.addEventListener('submit', handleAddItem);
    document.getElementById('form-plan-my-day')?.addEventListener('submit', handlePlanMyDay);
  }

  return {
    load,
    openAddItemModal,
    openPlanMyDayModal,
    toggleItem,
    deleteItem,
    startTimerForItem,
    initListeners
  };
})();
