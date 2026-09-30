// FocusFlow Exam Preparation Mode Controller
const Exams = (() => {
  let examsList = [];

  async function load() {
    const container = document.getElementById('exams-list-container');
    if (!container) return;

    container.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">Loading exam preparation spaces...</div>';

    try {
      const exams = await API.getExams();
      examsList = exams;
      renderExams(exams);
    } catch (err) {
      container.innerHTML = `<div class="card" style="color: var(--danger); text-align: center; padding: 24px;">Failed to load exams: ${App.escapeHTML(err.message)}</div>`;
    }
  }

  function renderExams(exams) {
    const container = document.getElementById('exams-list-container');
    if (!container) return;

    if (!exams || exams.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 48px 24px;">
          <div style="font-size: 3rem; margin-bottom: 12px;">🏆</div>
          <h3 style="font-size: 1.3rem; font-weight: 800; margin-bottom: 6px;">No Upcoming Exams Scheduled</h3>
          <p style="color: var(--text-muted); font-size: 0.9rem; max-width: 460px; margin: 0 auto 20px;">
            Set up an upcoming university exam or class test to unlock day-by-day study roadmaps, readiness tracking, and targeted revision!
          </p>
          <button class="btn btn-primary" onclick="Exams.openAddExamModal()">+ Schedule Your First Exam</button>
        </div>
      `;
      return;
    }

    container.innerHTML = exams.map(exam => {
      let roadmap = [];
      try {
        if (exam.prep_roadmap) {
          roadmap = typeof exam.prep_roadmap === 'string' ? JSON.parse(exam.prep_roadmap) : exam.prep_roadmap;
        }
      } catch (e) {
        roadmap = [];
      }

      const urgencyColor = exam.days_remaining <= 7 ? 'var(--danger)' : (exam.days_remaining <= 14 ? 'var(--accent-orange)' : 'var(--primary-600)');

      return `
        <div class="card exam-card" style="margin-bottom: 24px; border-left: 5px solid ${exam.subject_color || 'var(--primary-500)'};">
          <!-- Top Header -->
          <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; margin-bottom: 16px;">
            <div>
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <span class="subject-badge" style="background: ${exam.subject_color}20; color: ${exam.subject_color}; font-weight: 700;">
                  ${App.escapeHTML(exam.subject_name)}
                </span>
                <span style="font-size: 0.8rem; color: var(--text-muted);">Target: ${exam.target_score}%</span>
              </div>
              <h3 style="font-size: 1.35rem; font-weight: 800;">${App.escapeHTML(exam.title)}</h3>
              <div style="font-size: 0.85rem; color: var(--text-muted);">
                📅 Scheduled: <strong>${exam.exam_date}</strong>
              </div>
            </div>

            <div style="text-align: right;">
              <div class="stat-pill" style="background: ${urgencyColor}15; color: ${urgencyColor}; font-weight: 800; font-size: 1.1rem; padding: 6px 14px; border-radius: var(--radius-full); display: inline-block;">
                ⏳ ${exam.days_remaining} Days Remaining
              </div>
              <div style="margin-top: 6px;">
                <button class="btn btn-sm btn-secondary" onclick="Exams.deleteExam(${exam.id})" title="Delete Exam">🗑️ Delete</button>
              </div>
            </div>
          </div>

          <!-- Readiness Progress Bar -->
          <div style="background: var(--bg-muted); padding: 14px 18px; border-radius: var(--radius-md); margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-size: 0.88rem; font-weight: 700;">Preparation Readiness</span>
              <span style="font-size: 1rem; font-weight: 900; color: var(--primary-600);">${exam.readiness_percent}%</span>
            </div>
            <div class="progress-bar-bg" style="height: 12px;">
              <div class="progress-bar-fill" style="width: ${exam.readiness_percent}%; background: linear-gradient(90deg, #6C3BFF, #FF6B6B);"></div>
            </div>
          </div>

          <!-- Key Exam Metrics Grid -->
          <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px;">
            <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 12px; text-align: center;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Syllabus Done</div>
              <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-main); margin-top: 2px;">${exam.topics_completed} / ${exam.topics_total}</div>
            </div>

            <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 12px; text-align: center;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Remaining</div>
              <div style="font-size: 1.25rem; font-weight: 800; color: var(--accent-orange); margin-top: 2px;">${exam.topics_remaining} Topics</div>
            </div>

            <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 12px; text-align: center;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Weak Topics</div>
              <div style="font-size: 1.25rem; font-weight: 800; color: var(--danger); margin-top: 2px;">${exam.weak_topics_count}</div>
            </div>

            <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 12px; text-align: center;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Mock Avg</div>
              <div style="font-size: 1.25rem; font-weight: 800; color: var(--primary-600); margin-top: 2px;">${exam.mock_test_avg !== null ? exam.mock_test_avg + '%' : 'None'}</div>
            </div>

            <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 12px; text-align: center;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Study Time</div>
              <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-main); margin-top: 2px;">${exam.study_hours} hrs</div>
            </div>
          </div>

          <!-- Interactive Prep Roadmap -->
          <div style="border-top: 1px solid var(--border-color); padding-top: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <div style="font-weight: 800; font-size: 0.95rem; color: var(--text-main);">
                🗺️ Day-by-Day Preparation Roadmap
              </div>
              <button class="btn btn-sm btn-secondary" onclick="Exams.regenerateRoadmap(${exam.id})" title="Regenerate plan based on latest syllabus">
                ⚡ Optimize Roadmap
              </button>
            </div>

            <div class="exam-roadmap-track" style="display: flex; flex-direction: column; gap: 8px;">
              ${roadmap.map((step, idx) => `
                <div class="exam-roadmap-step" style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: var(--bg-muted); border-radius: var(--radius-md); font-size: 0.88rem;">
                  <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-weight: 800; color: var(--primary-600); width: 60px;">${App.escapeHTML(step.title || 'Day ' + step.day)}</span>
                    <span style="color: var(--text-main); font-weight: 600;">${App.escapeHTML(step.task)}</span>
                  </div>
                  <div>
                    ${step.type === 'mock' ? `
                      <button class="btn btn-sm btn-primary" onclick="MockTest.startTest('${App.escapeHTML(exam.subject_name)}')">
                        Take Mock →
                      </button>
                    ` : `
                      <button class="btn btn-sm btn-secondary" onclick="Router.navigate('timer')">
                        Lock In ⏱️
                      </button>
                    `}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function openAddExamModal() {
    const modal = document.getElementById('modal-exam');
    if (!modal) return;

    // Populate subjects dropdown
    const select = document.getElementById('exam-modal-subject');
    if (select) {
      API.getSubjects().then(subs => {
        select.innerHTML = subs.map(s => `<option value="${s.id}">${App.escapeHTML(s.name)}</option>`).join('');
      });
    }

    // Default date: 14 days from now
    const dateInput = document.getElementById('exam-modal-date');
    if (dateInput) {
      const d = new Date();
      d.setDate(d.getDate() + 14);
      dateInput.value = d.toISOString().split('T')[0];
    }

    modal.classList.add('active');
  }

  async function handleAddExam(e) {
    e.preventDefault();
    const subjectId = parseInt(document.getElementById('exam-modal-subject').value);
    const title = document.getElementById('exam-modal-title').value.trim();
    const examDate = document.getElementById('exam-modal-date').value;
    const targetScore = parseInt(document.getElementById('exam-modal-target').value) || 90;
    const notes = document.getElementById('exam-modal-notes').value.trim();

    if (!title || !examDate || !subjectId) {
      App.showToast('Please fill in required exam fields.', 'warning');
      return;
    }

    try {
      await API.createExam({
        subject_id: subjectId,
        title,
        exam_date: examDate,
        target_score: targetScore,
        notes
      });
      document.getElementById('modal-exam').classList.remove('active');
      App.showToast('Exam created and preparation roadmap generated! 🎯', 'success');
      load();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }

  async function deleteExam(id) {
    if (!confirm('Are you sure you want to remove this exam?')) return;
    try {
      await API.deleteExam(id);
      App.showToast('Exam removed.', 'info');
      load();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }

  async function regenerateRoadmap(id) {
    try {
      await API.regenerateExamRoadmap(id);
      App.showToast('Preparation roadmap updated based on latest syllabus progress!', 'success');
      load();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }

  function initListeners() {
    document.getElementById('btn-add-exam')?.addEventListener('click', openAddExamModal);
    document.getElementById('form-exam')?.addEventListener('submit', handleAddExam);
  }

  return {
    load,
    openAddExamModal,
    deleteExam,
    regenerateRoadmap,
    initListeners
  };
})();
