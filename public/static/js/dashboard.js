// FocusFlow Smart Academic Dashboard Controller
const Dashboard = (() => {

  function formatTime(minutes) {
    if (!minutes || minutes === 0) return '0 min';
    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hrs > 0 && mins > 0) return `${hrs}h ${mins}m`;
    if (hrs > 0) return `${hrs}h`;
    return `${mins}m`;
  }

  function getTimeOfDayGreeting() {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) {
      return { greeting: 'Good morning ☀️', message: "Ready to lock in? Let's make today count." };
    } else if (hour >= 12 && hour < 17) {
      return { greeting: 'Good afternoon ⚡', message: "Lock in and crush your study goals today." };
    } else if (hour >= 17 && hour < 22) {
      return { greeting: 'Good evening 🌙', message: "Prime time to wrap up tasks and review concepts." };
    } else {
      return { greeting: 'Late night focus 🦉', message: "Deep work mode activated. Keep hydrated." };
    }
  }

  async function load() {
    try {
      const [stats, subjects, rec] = await Promise.all([
        API.getDashboardStats(),
        API.getSubjects().catch(() => []),
        API.getAIRecommendation().catch(() => null)
      ]);
      render(stats, subjects, rec);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      App.showToast('Could not load dashboard stats.', 'error');
    }
  }

  function render(stats, subjects = [], rec = null) {
    const greetingData = getTimeOfDayGreeting();

    // 1. Welcome Greeting Banner
    const welcomeNameEl = document.getElementById('dash-welcome-name');
    const welcomeMsgEl = document.getElementById('dash-welcome-msg');
    const welcomeCourseEl = document.getElementById('dash-welcome-course');

    if (welcomeNameEl) welcomeNameEl.textContent = `Hey, ${stats.welcome_name || 'Student'} 👋`;
    if (welcomeMsgEl) welcomeMsgEl.textContent = `Ready to lock in? ${greetingData.message}`;
    if (welcomeCourseEl) {
      welcomeCourseEl.textContent = stats.course ? `🎓 ${stats.course}` : '🎓 Academic Workspace';
    }

    // 2. Recommended Action Hero Banner
    renderRecommendationBanner(rec || stats);

    // 3. Today's Focus Card & Overall Progress
    const targetMins = 60;
    const currentMins = stats.today_study_minutes || 0;
    const remainingMins = Math.max(0, targetMins - currentMins);
    const pct = Math.min(100, Math.round((currentMins / targetMins) * 100));

    const focusCountEl = document.getElementById('dash-focus-count');
    const focusBarEl = document.getElementById('dash-focus-bar');
    const focusSubEl = document.getElementById('dash-focus-sub');

    if (focusCountEl) focusCountEl.innerHTML = `🔥 <strong>${currentMins}</strong> / ${targetMins} min`;
    if (focusBarEl) focusBarEl.style.width = `${pct}%`;
    if (focusSubEl) {
      focusSubEl.textContent = (remainingMins === 0)
        ? 'Daily target crushed! Keep the streak burning 🔥'
        : `${remainingMins} minutes to hit your goal`;
    }

    // Overall syllabus progress
    const overallBarEl = document.getElementById('dash-overall-bar');
    const overallPctEl = document.getElementById('dash-overall-pct');
    const overallSubEl = document.getElementById('dash-overall-sub');
    if (overallBarEl) overallBarEl.style.width = `${stats.overall_progress_percent}%`;
    if (overallPctEl) overallPctEl.textContent = `${stats.overall_progress_percent}%`;
    if (overallSubEl) overallSubEl.textContent = `${stats.completed_topics_count} of ${stats.total_topics_count} syllabus topics completed`;

    // 4. Continue Learning Card
    renderContinueLearningCard(subjects, stats);

    // 5. Metric Stat Badges (Streak, Study Time, Tasks Completed, Exams)
    const streakEl = document.getElementById('dash-current-streak');
    const studyTimeEl = document.getElementById('dash-today-studytime');
    const completedTasksEl = document.getElementById('dash-completed-tasks');
    const upcomingExamsCountEl = document.getElementById('dash-upcoming-exams-count');

    if (streakEl) streakEl.textContent = `${stats.current_streak} ${stats.current_streak === 1 ? 'day' : 'days'}`;
    if (studyTimeEl) studyTimeEl.textContent = formatTime(stats.today_study_minutes || 0);
    if (completedTasksEl) completedTasksEl.textContent = `${stats.today_completed_tasks} ${stats.today_completed_tasks === 1 ? 'task' : 'tasks'}`;
    if (upcomingExamsCountEl) upcomingExamsCountEl.textContent = `${(stats.upcoming_exams || []).length} Exams`;

    // Topbar streak badge
    const topStreakPill = document.getElementById('topbar-streak');
    if (topStreakPill) {
      topStreakPill.innerHTML = `🔥 ${stats.current_streak} Day Streak`;
    }

    // 6. Upcoming Exams Widget
    renderUpcomingExams(stats.upcoming_exams || []);

    // 7. Weak Topics Widget
    renderWeakTopicsAlert(stats.weak_topics_count);

    // 8. Study Streak 7-Day Visualizer
    renderStreakWeek(stats.current_streak);

    // 9. Today's Pending Tasks List
    renderPendingTasks(stats.pending_tasks);
  }

  function renderRecommendationBanner(rec) {
    const banner = document.getElementById('dash-ai-recommendation-banner');
    if (!banner) return;

    if (!rec) {
      banner.style.display = 'none';
      return;
    }

    banner.style.display = 'block';
    const headline = rec.headline || rec.recommended_action || "Keep your study momentum going!";
    const reason = rec.reason || "Focusing on unfinished and weak topics delivers the highest academic returns.";
    const actionLabel = rec.suggested_action || "Lock In ⏱️";
    const subName = rec.subject_name || "";
    const topName = rec.topic_title || "";

    banner.innerHTML = `
      <div style="background: linear-gradient(135deg, rgba(108, 59, 255, 0.12), rgba(255, 107, 107, 0.08)); border: 1.5px solid rgba(108, 59, 255, 0.25); border-radius: var(--radius-lg); padding: 18px 22px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; margin-bottom: 24px;">
        <div style="display: flex; align-items: center; gap: 14px;">
          <div style="font-size: 2.2rem; background: var(--card-bg); width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: var(--radius-full); box-shadow: var(--shadow-sm);">
            🎯
          </div>
          <div>
            <div style="font-size: 0.75rem; text-transform: uppercase; font-weight: 800; letter-spacing: 0.05em; color: var(--primary-600);">
              AI COACH RECOMMENDED NEXT ACTION
            </div>
            <h4 style="font-size: 1.15rem; font-weight: 800; color: var(--text-main); margin-top: 2px;">
              ${App.escapeHTML(headline)}
            </h4>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 2px;">
              ${App.escapeHTML(reason)}
            </p>
          </div>
        </div>

        <div>
          <button class="btn btn-primary btn-lg" onclick="Dashboard.executeRecommendation('${App.escapeHTML(subName)}', '${App.escapeHTML(topName)}', '${rec.recommendation_type || ''}')">
            ${App.escapeHTML(actionLabel)} →
          </button>
        </div>
      </div>
    `;
  }

  function executeRecommendation(subjectName, topicTitle, recType) {
    if (recType === 'exam_weakness' || recType === 'weak_topic') {
      Router.navigate('revision');
    } else if (recType === 'exam_prep') {
      Router.navigate('exams');
    } else if (subjectName && topicTitle) {
      Router.navigate('timer');
      setTimeout(() => {
        const subEl = document.getElementById('timer-active-subject-name');
        const taskEl = document.getElementById('timer-active-task-name');
        if (subEl) subEl.textContent = subjectName;
        if (taskEl) taskEl.textContent = topicTitle;
      }, 150);
    } else {
      Router.navigate('subjects');
    }
  }

  function renderContinueLearningCard(subjects, stats) {
    const subjEl = document.getElementById('dash-continue-subject');
    const topicsEl = document.getElementById('dash-continue-topics');
    const barEl = document.getElementById('dash-continue-bar');
    const btnEl = document.getElementById('dash-continue-btn');

    if (!subjEl) return;

    if (!subjects || subjects.length === 0) {
      subjEl.textContent = 'Academic workspace ready 👀';
      topicsEl.textContent = 'Add your subjects and chapters to build your roadmap.';
      if (barEl) barEl.style.width = '0%';
      if (btnEl) {
        btnEl.textContent = '+ Add First Subject';
        btnEl.onclick = () => Router.navigate('subjects');
      }
      return;
    }

    const activeSubj = subjects.find(s => (s.progress_percent || 0) < 100) || subjects[0];
    const icon = activeSubj.icon && activeSubj.icon.length <= 4 ? activeSubj.icon : '📚';

    subjEl.textContent = `${icon} ${activeSubj.name}`;
    topicsEl.textContent = `${activeSubj.completed_topics_count || 0} / ${activeSubj.topic_count || 0} topics completed • ${activeSubj.progress_percent || 0}% syllabus progress`;
    if (barEl) barEl.style.width = `${activeSubj.progress_percent || 0}%`;
    if (btnEl) {
      btnEl.textContent = 'Continue Learning →';
      btnEl.onclick = () => SubjectsTasks.openSubjectDetail(activeSubj.id);
    }
  }

  function renderUpcomingExams(exams) {
    const container = document.getElementById('dash-exams-widget');
    if (!container) return;

    if (!exams || exams.length === 0) {
      container.innerHTML = `
        <div style="font-size: 0.85rem; color: var(--text-muted); text-align: center; padding: 12px 0;">
          No exams scheduled. <a href="javascript:void(0)" onclick="Router.navigate('exams')" style="color: var(--primary-600); font-weight: 700;">Set up an exam target →</a>
        </div>
      `;
      return;
    }

    container.innerHTML = exams.map(e => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--bg-muted); border-radius: var(--radius-md); margin-bottom: 8px;">
        <div>
          <span style="font-weight: 700; font-size: 0.92rem; color: var(--text-main);">${App.escapeHTML(e.title)}</span>
          <div style="font-size: 0.78rem; color: var(--text-muted);">
            ${App.escapeHTML(e.subject_name)} • ${e.exam_date}
          </div>
        </div>
        <div style="text-align: right;">
          <span class="badge" style="background: ${e.days_left <= 7 ? 'var(--danger-subtle)' : 'rgba(108,59,255,0.1)'}; color: ${e.days_left <= 7 ? 'var(--danger)' : 'var(--primary-600)'}; font-weight: 800;">
            ⏳ ${e.days_left}d left
          </span>
          <div style="margin-top: 4px;">
            <button class="btn btn-sm btn-secondary" onclick="Router.navigate('exams')" style="padding: 2px 8px; font-size: 0.75rem;">
              Prep Roadmap →
            </button>
          </div>
        </div>
      </div>
    `).join('');
  }

  function renderWeakTopicsAlert(weakCount) {
    const alertBox = document.getElementById('dash-weak-alert');
    if (!alertBox) return;

    if (!weakCount || weakCount === 0) {
      alertBox.style.display = 'none';
      return;
    }

    alertBox.style.display = 'flex';
    alertBox.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 12px 16px; background: var(--danger-subtle); border-radius: var(--radius-md); border: 1px solid rgba(255, 107, 107, 0.3);">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 1.3rem;">⚠️</span>
          <div>
            <strong style="color: var(--danger); font-size: 0.9rem;">${weakCount} Weak Topics Identified in Practice</strong>
            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 1px;">Review concepts and retest before exam day.</p>
          </div>
        </div>
        <button class="btn btn-sm btn-danger" onclick="Router.navigate('revision')">
          Revise Now →
        </button>
      </div>
    `;
  }

  function renderStreakWeek(streakCount) {
    const container = document.getElementById('dash-streak-week');
    if (!container) return;

    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const now = new Date();
    const jsDay = now.getDay();
    const currentDayIdx = (jsDay === 0 ? 6 : jsDay - 1);

    container.innerHTML = days.map((dayName, idx) => {
      const isToday = (idx === currentDayIdx);
      const isDone = (idx <= currentDayIdx && streakCount > 0 && (currentDayIdx - idx) < streakCount);

      let dayCls = 'streak-day';
      if (isToday) dayCls += ' today';
      if (isDone) dayCls += ' done';

      return `
        <div class="${dayCls}">
          <span class="day-label">${dayName}</span>
          <span class="day-icon">${isDone ? '✓' : (isToday ? '⚡' : '○')}</span>
        </div>
      `;
    }).join('');
  }

  function renderPendingTasks(tasks) {
    const pendingListEl = document.getElementById('dash-pending-tasks-list');
    if (!pendingListEl) return;

    if (!tasks || tasks.length === 0) {
      pendingListEl.innerHTML = `
        <div class="empty-state-card">
          <div style="font-size: 2.4rem; margin-bottom: 8px;">🎉</div>
          <p style="font-weight: 700; font-size: 1.05rem; color: var(--text-main);">No tasks pending today 🎉</p>
          <p style="font-size: 0.88rem; color: var(--text-muted); margin-top: 4px;">
            Your to-do list is clear. Ready to study something new?
          </p>
          <button class="btn btn-sm btn-secondary" onclick="Router.navigate('planner')" style="margin-top: 14px;">
            + Add To-Do Item
          </button>
        </div>
      `;
      return;
    }

    pendingListEl.innerHTML = tasks.map(t => {
      const priorityBadge = t.priority === 'High' ? '🔥 High' : (t.priority === 'Medium' ? '⚡ Medium' : '🌿 Low');
      return `
        <div class="task-item" data-id="${t.id}">
          <button class="task-checkbox" onclick="Dashboard.toggleTask(${t.id})" title="Mark complete">
            ✓
          </button>
          <div class="task-details">
            <div class="task-title">${App.escapeHTML(t.title)}</div>
            <div class="task-meta">
              ${t.subject_name ? `
                <span class="subject-tag" style="border-left: 3px solid ${t.subject_color || '#6c3bff'};">
                  ${App.escapeHTML(t.subject_name)}
                </span>
              ` : ''}
              <span class="badge badge-${t.priority.toLowerCase()}">${priorityBadge}</span>
              ${t.deadline ? `<span>📅 ${t.deadline}</span>` : ''}
            </div>
          </div>
          <div class="task-actions">
            <button class="btn btn-sm btn-primary" onclick="Planner.startTimerForItem('${App.escapeHTML(t.title)}', '${App.escapeHTML(t.subject_name || '')}', ${t.estimated_minutes || 25})" title="Start focus session on this task">
              ⏱ Focus
            </button>
          </div>
        </div>
      `;
    }).join('');
  }

  async function toggleTask(taskId) {
    try {
      await API.toggleTask(taskId);
      App.showToast('One less thing on your mind ✓', 'success');
      load();
    } catch (err) {
      App.showToast('Could not update task.', 'error');
    }
  }

  return {
    load,
    toggleTask,
    executeRecommendation,
    formatTime
  };
})();
