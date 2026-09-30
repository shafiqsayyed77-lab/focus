// FocusFlow Professional Academic Analytics & Achievements Controller
const Progress = (() => {

  async function load() {
    try {
      const [stats, sessions, subjects] = await Promise.all([
        API.getAnalyticsStats(),
        API.getSessions(),
        API.getSubjects()
      ]);
      renderStats(stats, subjects);
      renderChart(stats.weekly_chart);
      renderSubjectBreakdown(stats.subject_study_times || []);
      renderWeakAndStrongTopics(stats.weak_topics_list || [], stats.strong_topics_list || []);
      renderInsights(stats);
      renderAchievements(stats.achievements || []);
      renderSessions(sessions);
    } catch (err) {
      console.error('Failed to load progress stats:', err);
      App.showToast('Could not load analytics data.', 'error');
    }
  }

  function renderStats(stats, subjects) {
    const heroHoursEl = document.getElementById('prog-hero-hours');
    if (heroHoursEl) {
      heroHoursEl.textContent = Dashboard.formatTime(stats.total_study_minutes);
    }

    const todayMinsEl = document.getElementById('prog-today-mins');
    const totalMinsEl = document.getElementById('prog-total-mins');
    const doneTasksEl = document.getElementById('prog-completed-tasks');
    const doneSessionsEl = document.getElementById('prog-completed-sessions');
    const currentStreakEl = document.getElementById('prog-current-streak');
    const longestStreakEl = document.getElementById('prog-longest-streak');

    if (todayMinsEl) todayMinsEl.textContent = Dashboard.formatTime(stats.today_study_minutes);
    if (totalMinsEl) totalMinsEl.textContent = Dashboard.formatTime(stats.total_study_minutes);
    if (doneTasksEl) doneTasksEl.textContent = stats.completed_tasks_count;
    if (doneSessionsEl) doneSessionsEl.textContent = stats.completed_focus_sessions_count;
    if (currentStreakEl) currentStreakEl.textContent = `${stats.current_streak} ${stats.current_streak === 1 ? 'day' : 'days'}`;
    if (longestStreakEl) longestStreakEl.textContent = `${stats.longest_streak} ${stats.longest_streak === 1 ? 'day' : 'days'}`;
  }

  function renderChart(weeklyData) {
    const canvas = document.getElementById('weekly-chart-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.parentElement.clientWidth || 600;
    const height = canvas.height = 220;

    ctx.clearRect(0, 0, width, height);

    if (!weeklyData || weeklyData.length === 0) return;

    const maxMinutes = Math.max(...weeklyData.map(d => d.minutes), 60);
    const barWidth = Math.min(48, Math.floor((width - 80) / weeklyData.length));
    const spacing = Math.floor((width - 60) / weeklyData.length);
    const chartBottom = height - 40;
    const chartHeight = height - 80;

    // Draw baseline
    ctx.strokeStyle = document.body.getAttribute('data-theme') === 'dark' ? '#1e293b' : '#e2e8f0';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(30, chartBottom);
    ctx.lineTo(width - 20, chartBottom);
    ctx.stroke();

    weeklyData.forEach((d, i) => {
      const x = 40 + (i * spacing);
      const barH = d.minutes > 0 ? Math.max(8, (d.minutes / maxMinutes) * chartHeight) : 4;
      const y = chartBottom - barH;

      const isToday = (i === weeklyData.length - 1);
      const gradient = ctx.createLinearGradient(0, y, 0, chartBottom);
      if (isToday) {
        gradient.addColorStop(0, '#FF6B6B');
        gradient.addColorStop(1, '#FF9F43');
      } else {
        gradient.addColorStop(0, '#8B5CF6');
        gradient.addColorStop(1, '#6C3BFF');
      }

      ctx.fillStyle = d.minutes > 0 ? gradient : (document.body.getAttribute('data-theme') === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(203, 213, 225, 0.4)');
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barH, [6, 6, 0, 0]);
      ctx.fill();

      // Label on top
      if (d.minutes > 0) {
        ctx.fillStyle = isToday ? '#FF6B6B' : '#6C3BFF';
        ctx.font = '700 11px "Plus Jakarta Sans", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`${d.minutes}m`, x + barWidth / 2, y - 6);
      }

      // Day label below
      ctx.fillStyle = isToday ? '#FF6B6B' : (document.body.getAttribute('data-theme') === 'dark' ? '#94a3b8' : '#64748b');
      ctx.font = isToday ? '800 12px "Plus Jakarta Sans", sans-serif' : '600 12px "Plus Jakarta Sans", sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(d.day_name, x + barWidth / 2, height - 14);
    });
  }

  function renderSubjectBreakdown(subjectTimes) {
    const container = document.getElementById('prog-subject-times');
    if (!container) return;

    if (!subjectTimes || subjectTimes.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.88rem;">No study sessions logged yet.</p>';
      return;
    }

    container.innerHTML = subjectTimes.map(st => `
      <div style="margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; font-size: 0.88rem; font-weight: 700; margin-bottom: 4px;">
          <span>${App.escapeHTML(st.subject_name)}</span>
          <span style="color: var(--primary-600);">${st.minutes} min (${st.percentage}%)</span>
        </div>
        <div class="progress-bar-bg" style="height: 8px;">
          <div class="progress-bar-fill" style="width: ${st.percentage}%; background: ${st.color || '#6C3BFF'};"></div>
        </div>
      </div>
    `).join('');
  }

  function renderWeakAndStrongTopics(weakList, strongList) {
    const weakContainer = document.getElementById('prog-weak-topics');
    const strongContainer = document.getElementById('prog-strong-topics');

    if (weakContainer) {
      if (weakList.length === 0) {
        weakContainer.innerHTML = '<p style="color: var(--text-muted); font-size: 0.88rem;">No weak topics detected! High comprehension across subjects. 🌟</p>';
      } else {
        weakContainer.innerHTML = weakList.map(w => `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: var(--bg-muted); border-radius: var(--radius-sm); margin-bottom: 6px; border-left: 3px solid var(--danger);">
            <span style="font-size: 0.88rem; font-weight: 700; color: var(--text-main);">${App.escapeHTML(w)}</span>
            <button class="btn btn-sm btn-secondary" onclick="Revision.reviseWithAI('${App.escapeHTML(w)}', '')">Revise</button>
          </div>
        `).join('');
      }
    }

    if (strongContainer) {
      if (strongList.length === 0) {
        strongContainer.innerHTML = '<p style="color: var(--text-muted); font-size: 0.88rem;">Complete topics to build your strong mastery bank.</p>';
      } else {
        strongContainer.innerHTML = strongList.map(s => `
          <div style="padding: 8px 12px; background: var(--bg-muted); border-radius: var(--radius-sm); margin-bottom: 6px; border-left: 3px solid var(--success); font-size: 0.88rem; font-weight: 700; color: var(--text-main);">
            ✓ ${App.escapeHTML(s)}
          </div>
        `).join('');
      }
    }
  }

  function renderInsights(stats) {
    const prodDayEl = document.getElementById('prog-productive-day');
    const attnSubEl = document.getElementById('prog-attention-subject');
    const avgScoreEl = document.getElementById('prog-avg-mock-score');

    if (prodDayEl) prodDayEl.textContent = stats.most_productive_day || 'Wednesday';
    if (attnSubEl) attnSubEl.textContent = stats.attention_subject || 'None';
    if (avgScoreEl) avgScoreEl.textContent = stats.average_mock_score ? `${stats.average_mock_score}%` : 'N/A';
  }

  function renderAchievements(achievements) {
    const container = document.getElementById('prog-achievements-grid');
    if (!container) return;

    container.innerHTML = achievements.map(ach => `
      <div class="card achievement-card ${ach.unlocked ? 'unlocked' : 'locked'}" style="text-align: center; padding: 18px 14px; opacity: ${ach.unlocked ? '1' : '0.55'}; border: 1.5px solid ${ach.unlocked ? 'var(--primary-400)' : 'var(--border-color)'};">
        <div style="font-size: 2.4rem; margin-bottom: 6px; filter: ${ach.unlocked ? 'none' : 'grayscale(100%)'};">
          ${ach.icon}
        </div>
        <div style="font-weight: 800; font-size: 0.95rem; color: var(--text-main); margin-bottom: 2px;">
          ${App.escapeHTML(ach.title)}
        </div>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 8px; line-height: 1.3;">
          ${App.escapeHTML(ach.description)}
        </p>
        <span class="badge" style="background: ${ach.unlocked ? 'rgba(108, 59, 255, 0.15)' : 'var(--bg-muted)'}; color: ${ach.unlocked ? 'var(--primary-600)' : 'var(--text-muted)'}; font-weight: 800; font-size: 0.72rem;">
          ${ach.unlocked ? '✓ UNLOCKED' : ach.progress_text}
        </span>
      </div>
    `).join('');
  }

  function renderSessions(sessions) {
    const listEl = document.getElementById('prog-sessions-list');
    if (!listEl) return;

    if (!sessions || sessions.length === 0) {
      listEl.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 24px;">No focus sessions completed yet. Jump into the Focus Timer to start logging real study minutes!</p>';
      return;
    }

    listEl.innerHTML = `
      <div style="overflow-x: auto;">
        <table class="data-table" style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.88rem;">
          <thead>
            <tr style="border-bottom: 2px solid var(--border-color); color: var(--text-muted); font-size: 0.78rem; text-transform: uppercase;">
              <th style="padding: 10px 14px;">Date</th>
              <th style="padding: 10px 14px;">Subject</th>
              <th style="padding: 10px 14px;">Topic / Task</th>
              <th style="padding: 10px 14px;">Duration</th>
            </tr>
          </thead>
          <tbody>
            ${sessions.slice(0, 15).map(s => `
              <tr style="border-bottom: 1px solid var(--border-color);">
                <td style="padding: 12px 14px; color: var(--text-muted);">${s.completed_at ? s.completed_at.slice(0, 16) : 'Recently'}</td>
                <td style="padding: 12px 14px; font-weight: 700; color: var(--text-main);">${App.escapeHTML(s.subject_name || 'General')}</td>
                <td style="padding: 12px 14px; color: var(--text-muted);">${App.escapeHTML(s.topic_title || s.task_title || 'General Focus')}</td>
                <td style="padding: 12px 14px; font-weight: 800; color: var(--primary-600);">⏱ ${s.duration_minutes} min</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  return {
    load
  };
})();
