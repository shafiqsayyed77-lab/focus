// FocusFlow Academic Roadmap, Subjects & Topics Controller
const SubjectsTasks = (() => {
  let subjects = [];
  let tasks = [];
  let activeDetailSubject = null;
  let activeSubjectTopics = [];

  async function load() {
    await Promise.all([loadSubjects(), loadTasks()]);
  }

  async function loadSubjects() {
    try {
      subjects = await API.getSubjects();
      renderSubjects();
      populateSubjectDropdowns();
    } catch (err) {
      console.error('Failed to load subjects:', err);
    }
  }

  async function loadTasks() {
    try {
      tasks = await API.getTasks();
    } catch (err) {
      console.error('Failed to load tasks:', err);
    }
  }

  function getSubjectsList() {
    return subjects;
  }

  function renderSubjects() {
    const container = document.getElementById('subjects-container');
    if (!container) return;

    if (subjects.length === 0) {
      container.innerHTML = `
        <div class="card empty-state-card" style="grid-column: 1/-1; text-align: center; padding: 48px 24px;">
          <div style="font-size: 3rem; margin-bottom: 12px;">📚</div>
          <h3 style="font-size: 1.3rem; font-weight: 800; margin-bottom: 6px;">Your Academic Workspace is Fresh</h3>
          <p style="font-size: 0.92rem; color: var(--text-muted); max-width: 480px; margin: 0 auto 20px;">
            Add your course subjects (e.g. Computer Networks, Data Structures, Mathematics, DBMS) to build your visual roadmap, track chapter completion, and unlock mock tests!
          </p>
          <button class="btn btn-primary btn-lg" onclick="SubjectsTasks.openAddSubjectModal()">
            + Add Your First Subject
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = subjects.map(s => {
      const topCount = s.topic_count || 0;
      const doneCount = s.completed_topics_count || 0;
      const pct = s.progress_percent || 0;
      const studyMins = s.study_time_minutes || 0;
      const score = (s.mock_test_score !== null && s.mock_test_score !== undefined)
        ? `${s.mock_test_score}%`
        : 'Not tested yet';
      const weakBadge = s.weak_topics_count > 0 ? `<span class="badge" style="background: var(--danger-subtle); color: var(--danger); font-size: 0.72rem; font-weight: 800;">${s.weak_topics_count} Weak Topics</span>` : '';

      return `
        <div class="card subject-card" style="border-top-color: ${s.color || '#6C3BFF'};">
          <div class="subject-card-top">
            <div class="subject-card-info">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span style="font-size: 1.4rem;">${s.icon === 'code' ? '💻' : (s.icon === 'database' ? '🗄️' : (s.icon === 'network' ? '🌐' : '📚'))}</span>
                  <h3 style="font-size: 1.2rem; font-weight: 800;">${App.escapeHTML(s.name)}</h3>
                </div>
                ${weakBadge}
              </div>
              <p style="margin-top: 6px; font-size: 0.86rem; color: var(--text-muted); line-height: 1.4;">
                ${App.escapeHTML(s.description || 'Interactive syllabus, chapter roadmap, and mock test space.')}
              </p>
            </div>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-sm btn-icon" onclick="SubjectsTasks.openEditSubjectModal(${s.id})" title="Edit subject">✏️</button>
              <button class="btn btn-sm btn-icon" onclick="SubjectsTasks.deleteSubject(${s.id})" title="Delete subject">✕</button>
            </div>
          </div>

          <div class="subject-card-stats">
            <div class="subj-stat-pill">
              <span class="stat-pill-label">Syllabus Progress</span>
              <span class="stat-pill-val">${doneCount} / ${topCount} Topics</span>
            </div>
            <div class="subj-stat-pill">
              <span class="stat-pill-label">Study Time</span>
              <span class="stat-pill-val">⏱ ${studyMins} min</span>
            </div>
            <div class="subj-stat-pill">
              <span class="stat-pill-label">Mock Score</span>
              <span class="stat-pill-val" style="color: ${s.mock_test_score ? 'var(--primary-600)' : 'var(--text-muted)'}; font-weight: 800;">
                🎯 ${score}
              </span>
            </div>
          </div>

          <div class="progress-bar-bg" style="height: 8px; margin: 14px 0 18px;">
            <div class="progress-bar-fill" style="width: ${pct}%; background: linear-gradient(90deg, ${s.color || '#6C3BFF'}, #FF6B6B);"></div>
          </div>

          <div class="subject-card-footer">
            <button class="btn btn-secondary btn-sm" onclick="MockTest.startTest(decodeURIComponent('${encodeURIComponent(s.name)}'), ${s.id})">
              🎯 Take Mock Test
            </button>
            <button class="btn btn-primary btn-sm" onclick="SubjectsTasks.openSubjectDetail(${s.id})">
              Open Roadmap →
            </button>
          </div>
        </div>
      `;
    }).join('');
  }

  async function openSubjectDetail(subjectId) {
    try {
      const [subject, topics, allTasks] = await Promise.all([
        API.getSubjectDetail(subjectId),
        API.getSubjectTopics(subjectId),
        API.getTasks({ subject_id: subjectId })
      ]);

      activeDetailSubject = subject;
      activeSubjectTopics = topics;

      document.getElementById('subjects-main-view').style.display = 'none';
      const detailView = document.getElementById('subject-detail-view');
      detailView.style.display = 'block';

      renderSubjectDetailView(subject, topics, allTasks);
    } catch (err) {
      App.showToast('Failed to load subject details.', 'error');
    }
  }

  function closeSubjectDetail() {
    activeDetailSubject = null;
    activeSubjectTopics = [];
    const mainView = document.getElementById('subjects-main-view');
    const detailView = document.getElementById('subject-detail-view');
    if (mainView) mainView.style.display = 'block';
    if (detailView) detailView.style.display = 'none';
  }

  function renderSubjectDetailView(s = activeDetailSubject, topics = activeSubjectTopics, subjectTasks = []) {
    const detailView = document.getElementById('subject-detail-view');
    if (!detailView || !s) return;

    const topCount = topics.length;
    const doneCount = topics.filter(t => t.is_completed).length;
    const remainingCount = topCount - doneCount;
    const pct = topCount > 0 ? Math.round((doneCount / topCount) * 100) : 0;
    const studyMins = s.study_time_minutes || 0;
    const score = s.mock_test_score !== null ? `${s.mock_test_score}%` : 'Not tested yet';

    // Group topics by chapter
    const chapters = {};
    topics.forEach(t => {
      const ch = t.chapter || 'General Foundations';
      if (!chapters[ch]) chapters[ch] = [];
      chapters[ch].push(t);
    });

    // Determine "What should I study next?"
    const nextTopic = topics.find(t => !t.is_completed);

    detailView.innerHTML = `
      <div style="margin-bottom: 24px;">
        <button id="btn-back-to-subjects" class="btn btn-sm btn-secondary" onclick="SubjectsTasks.closeSubjectDetail()" style="margin-bottom: 16px;">
          ← Back to All Subjects
        </button>

        <!-- Learning Space Hero Banner -->
        <div class="subject-space-hero" style="border-left: 5px solid ${s.color}; background: var(--card-bg); padding: 24px; border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); margin-bottom: 24px;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
            <div>
              <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 2.2rem;">${s.icon === 'code' ? '💻' : (s.icon === 'database' ? '🗄️' : (s.icon === 'network' ? '🌐' : '📚'))}</span>
                <div>
                  <h2 style="font-size: 1.8rem; font-weight: 800;">${App.escapeHTML(s.name)}</h2>
                  <p style="font-size: 0.95rem; color: var(--text-muted); margin-top: 4px;">
                    ${App.escapeHTML(s.description || 'Personal syllabus space & chapter mastery roadmap.')}
                  </p>
                </div>
              </div>

              <!-- Space Key Stats -->
              <div style="display: flex; gap: 14px; margin-top: 18px; flex-wrap: wrap;">
                <div style="background: rgba(108, 59, 255, 0.08); padding: 10px 16px; border-radius: var(--radius-md);">
                  <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Study Time</span>
                  <div style="font-size: 1.15rem; font-weight: 800; color: var(--primary-600);">⏱ ${studyMins} min</div>
                </div>
                <div style="background: rgba(255, 159, 67, 0.1); padding: 10px 16px; border-radius: var(--radius-md);">
                  <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Mock Test Score</span>
                  <div style="font-size: 1.15rem; font-weight: 800; color: var(--accent-orange);">🎯 ${score}</div>
                </div>
                <div style="background: var(--bg-muted); padding: 10px 16px; border-radius: var(--radius-md);">
                  <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Syllabus Status</span>
                  <div style="font-size: 1.15rem; font-weight: 800; color: var(--text-main);">${doneCount}/${topCount} Done (${remainingCount} Left)</div>
                </div>
              </div>
            </div>

            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
              <button class="btn btn-secondary btn-lg" onclick="Timer.startManual(25, decodeURIComponent('${encodeURIComponent('Study ' + s.name)}'), decodeURIComponent('${encodeURIComponent(s.name)}'))">
                ⏱ Start Focus
              </button>
              <button class="btn btn-accent btn-lg" onclick="MockTest.startTest(decodeURIComponent('${encodeURIComponent(s.name)}'), ${s.id})">
                🎯 Take Mock Test
              </button>
            </div>
          </div>

          <!-- Progress Bar inside Hero -->
          <div style="margin-top: 24px; padding-top: 18px; border-top: 1px solid var(--border-color);">
            <div style="display: flex; justify-content: space-between; font-weight: 800; font-size: 0.95rem; margin-bottom: 8px;">
              <span>Syllabus Mastery: ${doneCount} of ${topCount} Topics Mastered</span>
              <span style="color: var(--primary-600);">${pct}%</span>
            </div>
            <div class="progress-bar-bg" style="height: 12px;">
              <div class="progress-bar-fill" style="width: ${pct}%; background: linear-gradient(90deg, #6C3BFF, #FF6B6B);"></div>
            </div>
          </div>
        </div>

        <!-- Roadmap Guidance Widget: Where am I? What next? -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px;">
          <div class="card" style="padding: 16px 20px;">
            <div style="font-size: 0.75rem; text-transform: uppercase; font-weight: 800; color: var(--primary-600);">📍 Where am I?</div>
            <div style="font-size: 1.1rem; font-weight: 800; color: var(--text-main); margin-top: 4px;">
              ${pct === 100 ? '🎉 Syllabus 100% Completed!' : `${pct}% of ${s.name} mastered`}
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 2px;">
              ${remainingCount > 0 ? `${remainingCount} topics left to cover across ${Object.keys(chapters).length} chapters.` : 'All chapters finished. Ready for final mock examination!'}
            </p>
          </div>

          <div class="card" style="padding: 16px 20px;">
            <div style="font-size: 0.75rem; text-transform: uppercase; font-weight: 800; color: var(--accent-orange);">🎯 What should I study next?</div>
            <div style="font-size: 1.1rem; font-weight: 800; color: var(--text-main); margin-top: 4px;">
              ${nextTopic ? App.escapeHTML(nextTopic.title) : 'Practice Review & Mock Test'}
            </div>
            <div style="margin-top: 8px;">
              ${nextTopic ? `
                <button class="btn btn-sm btn-primary" onclick="SubjectsTasks.quickFocusTopic('${App.escapeHTML(nextTopic.title)}', '${App.escapeHTML(s.name)}')">
                  ⏱️ Lock In on Next Topic →
                </button>
              ` : `
                <button class="btn btn-sm btn-accent" onclick="MockTest.startTest('${App.escapeHTML(s.name)}', ${s.id})">
                  ⚡ Launch Mock Test →
                </button>
              `}
            </div>
          </div>
        </div>

        <!-- Chapters & Topics Roadmap -->
        <div class="card" style="margin-bottom: 24px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; flex-wrap: wrap; gap: 10px;">
            <div>
              <h3 style="font-size: 1.3rem; font-weight: 800;">Academic Syllabus Roadmap</h3>
              <p style="font-size: 0.85rem; color: var(--text-muted);">
                Organize chapters and topics. Completed topics automatically unlock in this subject's Mock Tests!
              </p>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-sm btn-secondary" onclick="SubjectsTasks.seedAITopicsForActiveSubject()">
                ✨ AI Suggest Topics
              </button>
              <button class="btn btn-sm btn-primary" onclick="SubjectsTasks.openAddTopicModal()">
                + Add Topic
              </button>
            </div>
          </div>

          ${topics.length === 0 ? `
            <div style="text-align: center; padding: 36px 16px; color: var(--text-muted);">
              <div style="font-size: 2.2rem; margin-bottom: 8px;">📑</div>
              <p style="font-weight: 700; color: var(--text-main);">No topics added to ${App.escapeHTML(s.name)} yet.</p>
              <p style="font-size: 0.85rem; margin: 4px 0 16px;">Add your own syllabus chapters or click "AI Suggest Topics" to populate standard curriculum!</p>
              <button class="btn btn-primary" onclick="SubjectsTasks.openAddTopicModal()">+ Add Topic</button>
              <button class="btn btn-secondary" onclick="SubjectsTasks.seedAITopicsForActiveSubject()" style="margin-left: 8px;">✨ AI Suggest Topics</button>
            </div>
          ` : Object.keys(chapters).map(chName => `
            <div class="chapter-block" style="margin-bottom: 20px;">
              <div style="font-weight: 800; font-size: 0.95rem; color: var(--primary-700); text-transform: uppercase; letter-spacing: 0.05em; padding-bottom: 6px; border-bottom: 1.5px solid var(--border-color); margin-bottom: 10px;">
                📂 ${App.escapeHTML(chName)}
              </div>

              <div class="topics-list" style="display: flex; flex-direction: column; gap: 8px;">
                ${chapters[chName].map(top => `
                  <div class="topic-row ${top.is_completed ? 'completed' : ''}" style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: var(--bg-muted); border-radius: var(--radius-md); gap: 12px;">
                    <div style="display: flex; align-items: center; gap: 14px; flex: 1;">
                      <button class="topic-check-btn" onclick="SubjectsTasks.toggleTopicCompletion(${top.id})" title="Toggle completion" style="width: 24px; height: 24px; border-radius: var(--radius-sm); border: 2px solid var(--border-color); background: ${top.is_completed ? 'var(--primary-600)' : 'transparent'}; color: #fff; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; justify-content: center;">
                        ${top.is_completed ? '✓' : ''}
                      </button>
                      <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                          <span class="topic-title ${top.is_completed ? 'strike' : ''}" style="font-weight: 700; font-size: 0.95rem; color: var(--text-main);">
                            ${App.escapeHTML(top.title)}
                          </span>
                          <span class="badge" style="font-size: 0.72rem; padding: 2px 6px; background: var(--card-bg); color: ${top.priority === 'High' ? 'var(--danger)' : 'var(--text-muted)'};">
                            ${top.priority || 'Medium'}
                          </span>
                          ${top.is_weak ? `<span class="badge" style="background: var(--danger-subtle); color: var(--danger); font-size: 0.7rem; font-weight: 800;">⚠️ Weak Area</span>` : ''}
                          ${top.is_completed ? `<span class="badge" style="background: rgba(108, 59, 255, 0.15); color: var(--primary-600); font-size: 0.7rem; font-weight: 700;">✓ In Mock Test</span>` : ''}
                        </div>
                        ${top.notes ? `<p style="font-size: 0.82rem; color: var(--text-muted); margin-top: 4px;">📝 ${App.escapeHTML(top.notes)}</p>` : ''}
                      </div>
                    </div>

                    <div style="display: flex; align-items: center; gap: 6px;">
                      <button class="btn btn-sm btn-secondary" onclick="SubjectsTasks.quickFocusTopic('${App.escapeHTML(top.title)}', '${App.escapeHTML(s.name)}')">
                        ⏱️ Focus
                      </button>
                      <button class="btn btn-sm btn-secondary" onclick="SubjectsTasks.quickExplainTopic('${App.escapeHTML(top.title)}', '${App.escapeHTML(s.name)}')">
                        💡 Explain
                      </button>
                      <button class="btn btn-sm btn-icon" onclick="SubjectsTasks.deleteTopic(${top.id})" title="Delete topic">
                        ✕
                      </button>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  async function toggleTopicCompletion(topicId) {
    try {
      const updated = await API.toggleTopic(topicId);
      const top = activeSubjectTopics.find(t => t.id === topicId);
      if (top) {
        top.is_completed = updated.is_completed;
        top.status = updated.status;
      }
      App.showToast(updated.is_completed ? 'Topic completed! Added to Mock Test pool 🔥' : 'Topic marked pending', 'success');
      renderSubjectDetailView();
      loadSubjects();
    } catch (e) {
      App.showToast('Could not update topic status.', 'error');
    }
  }

  function quickFocusTopic(topic, subject) {
    Router.navigate('timer');
    setTimeout(() => {
      const sEl = document.getElementById('timer-active-subject-name');
      const tEl = document.getElementById('timer-active-task-name');
      if (sEl) sEl.textContent = subject;
      if (tEl) tEl.textContent = topic;
      App.showToast(`Locked in for: ${topic}`, 'success');
    }, 150);
  }

  function quickExplainTopic(topic, subject) {
    Router.navigate('ai');
    setTimeout(() => {
      document.querySelector('.ai-feature-card[data-tab="explain"]')?.click();
      const input = document.getElementById('ai-explain-topic');
      if (input) input.value = topic;
      document.getElementById('btn-explain-topic')?.click();
    }, 150);
  }

  async function seedAITopicsForActiveSubject() {
    if (!activeDetailSubject) return;
    try {
      const topics = await API.seedAITopics(activeDetailSubject.id);
      activeSubjectTopics = topics;
      App.showToast('Curriculum syllabus topics populated! 📚', 'success');
      renderSubjectDetailView();
      loadSubjects();
    } catch (e) {
      App.showToast('Failed to suggest topics.', 'error');
    }
  }

  function openAddTopicModal() {
    const modal = document.getElementById('modal-add-topic');
    if (modal) modal.classList.add('active');
  }

  async function handleAddTopic(e) {
    e.preventDefault();
    if (!activeDetailSubject) return;

    const title = document.getElementById('new-topic-title').value.trim();
    const chapter = document.getElementById('new-topic-chapter').value.trim() || 'General';
    const priority = document.getElementById('new-topic-priority').value;
    const notes = document.getElementById('new-topic-notes').value.trim();

    if (!title) {
      App.showToast('Topic title cannot be empty.', 'warning');
      return;
    }

    try {
      const newTopic = await API.addSubjectTopic(activeDetailSubject.id, {
        title,
        chapter,
        priority,
        notes
      });
      activeSubjectTopics.push(newTopic);
      document.getElementById('modal-add-topic').classList.remove('active');
      App.showToast(`Added "${newTopic.title}" to syllabus!`, 'success');
      renderSubjectDetailView();
      loadSubjects();
    } catch (e) {
      App.showToast('Failed to add topic.', 'error');
    }
  }

  async function deleteTopic(topicId) {
    if (!confirm('Are you sure you want to remove this topic?')) return;
    try {
      await API.deleteTopic(topicId);
      activeSubjectTopics = activeSubjectTopics.filter(t => t.id !== topicId);
      App.showToast('Topic removed.', 'info');
      renderSubjectDetailView();
      loadSubjects();
    } catch (e) {
      App.showToast('Failed to remove topic.', 'error');
    }
  }

  // Subject Modals
  function openAddSubjectModal() {
    document.getElementById('subject-modal-title').textContent = 'Add New Subject';
    document.getElementById('subject-modal-id').value = '';
    document.getElementById('subject-modal-name').value = '';
    document.getElementById('subject-modal-color').value = '#6C3BFF';
    document.getElementById('subject-modal-desc').value = '';
    document.getElementById('modal-subject').classList.add('active');
  }

  function openEditSubjectModal(id) {
    const s = subjects.find(sub => sub.id === id);
    if (!s) return;
    document.getElementById('subject-modal-title').textContent = 'Edit Subject';
    document.getElementById('subject-modal-id').value = s.id;
    document.getElementById('subject-modal-name').value = s.name;
    document.getElementById('subject-modal-color').value = s.color || '#6C3BFF';
    document.getElementById('subject-modal-desc').value = s.description || '';
    document.getElementById('modal-subject').classList.add('active');
  }

  async function handleSubjectFormSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('subject-modal-id').value;
    const name = document.getElementById('subject-modal-name').value.trim();
    const color = document.getElementById('subject-modal-color').value;
    const description = document.getElementById('subject-modal-desc').value.trim();

    if (!name) return;

    try {
      if (id) {
        await API.updateSubject(id, { name, color, description });
        App.showToast('Subject updated!', 'success');
      } else {
        await API.createSubject({ name, color, description });
        App.showToast('Subject created! Now add topics to build your roadmap. 🚀', 'success');
      }
      document.getElementById('modal-subject').classList.remove('active');
      loadSubjects();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  }

  async function deleteSubject(id) {
    if (!confirm('Are you sure you want to delete this subject and all its topics?')) return;
    try {
      await API.deleteSubject(id);
      App.showToast('Subject deleted.', 'info');
      loadSubjects();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  }

  function populateSubjectDropdowns() {
    const selects = [
      document.getElementById('task-modal-subject'),
      document.getElementById('planner-item-subject'),
      document.getElementById('timer-subject-select'),
      document.getElementById('ai-planner-subject'),
      document.getElementById('ai-explain-subject'),
      document.getElementById('ai-quiz-subject')
    ];

    selects.forEach(select => {
      if (!select) return;
      const currentVal = select.value;
      select.innerHTML = '<option value="">-- No Subject (General) --</option>';

      subjects.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id;
        opt.textContent = s.name;
        select.appendChild(opt);
      });

      if (currentVal) select.value = currentVal;
    });
  }

  function initListeners() {
    document.getElementById('btn-add-subject')?.addEventListener('click', openAddSubjectModal);
    document.getElementById('form-subject')?.addEventListener('submit', handleSubjectFormSubmit);
    document.getElementById('form-add-topic')?.addEventListener('submit', handleAddTopic);
  }

  return {
    load,
    loadSubjects,
    getSubjectsList,
    openSubjectDetail,
    closeSubjectDetail,
    toggleTopicCompletion,
    quickFocusTopic,
    quickExplainTopic,
    seedAITopicsForActiveSubject,
    openAddTopicModal,
    deleteTopic,
    openAddSubjectModal,
    openEditSubjectModal,
    deleteSubject,
    initListeners
  };
})();
