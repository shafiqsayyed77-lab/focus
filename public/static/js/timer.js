// FocusFlow Professional Focus Timer & Break Controller
const Timer = (() => {
  // State
  let mode = 'focus'; // 'focus' or 'break'
  let totalSeconds = 25 * 60;
  let remainingSeconds = 25 * 60;
  let intervalId = null;
  let isRunning = false;
  let isPaused = false;

  let selectedSubjectId = null;
  let selectedSubjectName = 'General';
  let selectedTopicId = null;
  let selectedTopicTitle = 'General Study';
  let selectedTaskId = null;
  let selectedTaskTitle = 'General';

  const CIRCLE_CIRCUMFERENCE = 2 * Math.PI * 110; // radius = 110 in SVG

  function load() {
    loadSubjectsAndTopics();
    loadTaskOptions();
    resetTimerUI();
  }

  async function loadSubjectsAndTopics() {
    const subjSelect = document.getElementById('timer-subject-select');
    if (!subjSelect) return;

    try {
      const subs = await API.getSubjects();
      subjSelect.innerHTML = '<option value="">-- No Specific Subject --</option>' +
        subs.map(s => `<option value="${s.id}">${App.escapeHTML(s.name)}</option>`).join('');

      if (selectedSubjectId) {
        subjSelect.value = selectedSubjectId;
        loadTopicsForSubject(selectedSubjectId);
      }
    } catch (e) {
      console.warn('Failed to load subjects for timer:', e);
    }
  }

  async function loadTopicsForSubject(subjectId) {
    const topicSelect = document.getElementById('timer-topic-select');
    if (!topicSelect) return;

    if (!subjectId) {
      topicSelect.innerHTML = '<option value="">-- No Specific Topic --</option>';
      return;
    }

    try {
      const topics = await API.getSubjectTopics(subjectId);
      topicSelect.innerHTML = '<option value="">-- No Specific Topic --</option>' +
        topics.map(t => `<option value="${t.id}">${App.escapeHTML(t.title)}</option>`).join('');

      if (selectedTopicId) {
        topicSelect.value = selectedTopicId;
      }
    } catch (e) {
      console.warn('Failed to load topics for timer:', e);
    }
  }

  async function loadTaskOptions() {
    try {
      const tasks = await API.getTasks({ status_filter: 'pending' });
      const select = document.getElementById('timer-task-select');
      if (!select) return;

      select.innerHTML = '<option value="">-- No Specific Task (General Study) --</option>';
      tasks.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.id;
        opt.dataset.title = t.title;
        opt.dataset.subjectId = t.subject_id || '';
        opt.dataset.subjectName = t.subject_name || '';
        opt.textContent = `${t.title} ${t.subject_name ? `(${t.subject_name})` : ''}`;
        select.appendChild(opt);
      });

      if (selectedTaskId) {
        select.value = selectedTaskId;
      }
    } catch (e) {
      console.warn('Failed to load tasks for timer selector:', e);
    }
  }

  function startWithTask(taskId, taskTitle, subjectId, subjectName) {
    selectedTaskId = taskId;
    selectedTaskTitle = taskTitle || 'Study Session';
    selectedSubjectId = subjectId || null;
    selectedSubjectName = subjectName || 'General';

    Router.navigate('timer');

    const select = document.getElementById('timer-task-select');
    if (select) select.value = taskId;

    updateSessionInfoLabels();
  }

  function startManual(durationMinutes, taskTitle, subjectName, topicTitle = null) {
    selectedTaskId = null;
    selectedTaskTitle = taskTitle || 'Focused Deep Work';
    selectedSubjectName = subjectName || 'General';
    selectedTopicTitle = topicTitle || 'General Study';

    setDuration(durationMinutes);
    Router.navigate('timer');
    updateSessionInfoLabels();
    startTimer();
  }

  function updateSessionInfoLabels() {
    const subjInfoEl = document.getElementById('timer-active-subject-name');
    const topicInfoEl = document.getElementById('timer-active-topic-name');
    const taskInfoEl = document.getElementById('timer-active-task-name');

    if (subjInfoEl) subjInfoEl.textContent = selectedSubjectName || 'All Subjects';
    if (topicInfoEl) topicInfoEl.textContent = selectedTopicTitle || 'General Study';
    if (taskInfoEl) taskInfoEl.textContent = selectedTaskTitle || 'General Focus';
  }

  function setDuration(minutes) {
    if (isRunning) {
      if (!confirm('A timer is currently running. Changing duration will reset the timer. Continue?')) {
        return;
      }
      stopTimer();
    }
    mode = 'focus';
    totalSeconds = minutes * 60;
    remainingSeconds = totalSeconds;

    // Update pill highlights
    document.querySelectorAll('.duration-pill').forEach(pill => {
      pill.classList.remove('active');
      if (parseInt(pill.dataset.mins) === minutes) {
        pill.classList.add('active');
      }
    });

    updateDisplay();
    updateModeLabel('LOCKED IN 🔥');
    resetProgressRing();
  }

  function updateDisplay() {
    const mins = Math.floor(remainingSeconds / 60);
    const secs = remainingSeconds % 60;
    const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    const displayEl = document.getElementById('timer-display');
    if (displayEl) displayEl.textContent = timeStr;

    // Document title for background awareness
    const label = mode === 'focus' ? 'Focus' : 'Break';
    document.title = isRunning ? `(${timeStr}) ${label} - FocusFlow` : 'FocusFlow';

    updateProgressRing();
  }

  function updateProgressRing() {
    const circle = document.getElementById('timer-progress-ring');
    if (!circle) return;

    if (totalSeconds <= 0) return;
    const progress = (totalSeconds - remainingSeconds) / totalSeconds;
    const offset = CIRCLE_CIRCUMFERENCE * (1 - progress);
    circle.style.strokeDashoffset = offset;
  }

  function resetProgressRing() {
    const circle = document.getElementById('timer-progress-ring');
    if (circle) {
      circle.style.strokeDasharray = CIRCLE_CIRCUMFERENCE;
      circle.style.strokeDashoffset = CIRCLE_CIRCUMFERENCE;
    }
  }

  function updateModeLabel(text) {
    const labelEl = document.getElementById('timer-mode-label');
    if (labelEl) labelEl.textContent = text;
  }

  function startTimer() {
    if (isRunning && !isPaused) return;

    isRunning = true;
    isPaused = false;
    toggleControlButtons();

    // Hide previous break celebration if visible
    const breakBanner = document.getElementById('timer-break-banner');
    if (breakBanner) breakBanner.style.display = 'none';

    intervalId = setInterval(() => {
      if (remainingSeconds > 0) {
        remainingSeconds--;
        updateDisplay();
      } else {
        completeTimer();
      }
    }, 1000);
  }

  function pauseTimer() {
    if (!isRunning || isPaused) return;
    clearInterval(intervalId);
    isPaused = true;
    toggleControlButtons();
    updateModeLabel('PAUSED ⏸');
  }

  function resumeTimer() {
    if (!isRunning || !isPaused) return;
    startTimer();
    updateModeLabel(mode === 'focus' ? 'LOCKED IN 🔥' : 'BREAK TIME ☕');
  }

  function resetTimer() {
    if (isRunning) {
      if (!confirm('Are you sure you want to reset the current timer?')) return;
    }
    stopTimer();
    remainingSeconds = totalSeconds;
    updateDisplay();
    resetProgressRing();
    updateModeLabel(mode === 'focus' ? 'READY TO LOCK IN' : 'BREAK TIME');
    toggleControlButtons();
  }

  function endSessionEarly() {
    if (!confirm('End this focus session now and save the minutes you have completed?')) return;
    const elapsedMinutes = Math.floor((totalSeconds - remainingSeconds) / 60);
    stopTimer();

    if (elapsedMinutes >= 1 && mode === 'focus') {
      recordCompletedSession(elapsedMinutes);
    } else {
      App.showToast('Session ended (under 1 minute, not logged).', 'info');
      resetTimer();
    }
  }

  function stopTimer() {
    clearInterval(intervalId);
    intervalId = null;
    isRunning = false;
    isPaused = false;
    document.title = 'FocusFlow';
    toggleControlButtons();
  }

  async function completeTimer() {
    stopTimer();

    // Sound chime
    if (typeof Sound !== 'undefined') {
      Sound.playChime();
    }

    if (mode === 'focus') {
      const minutesCompleted = Math.round(totalSeconds / 60);
      await recordCompletedSession(minutesCompleted);
      triggerCelebration(minutesCompleted);
    } else {
      App.showToast('Break finished! Ready to lock back in? 🚀', 'success');
      setDuration(25);
    }
  }

  async function recordCompletedSession(minutes) {
    try {
      await API.recordSession(minutes, selectedSubjectId, selectedTopicId, selectedTaskId);
      App.showToast(`🔥 Great lock-in! Logged +${minutes} min study time.`, 'success');

      if (typeof Dashboard !== 'undefined') Dashboard.load();
      if (typeof Progress !== 'undefined') Progress.load();
    } catch (err) {
      console.warn('Failed to record focus session:', err);
    }
  }

  function triggerCelebration(minutes) {
    const breakBanner = document.getElementById('timer-break-banner');
    if (breakBanner) {
      breakBanner.innerHTML = `
        <div class="card celebration-card" style="text-align: center; padding: 24px; animation: bounceIn 0.5s ease; border: 2px solid var(--accent-orange); background: linear-gradient(135deg, rgba(108, 59, 255, 0.08), rgba(255, 159, 67, 0.08));">
          <div style="font-size: 2.8rem; margin-bottom: 8px;">🎉</div>
          <h3 style="font-size: 1.5rem; font-weight: 800; color: var(--text-main); margin-bottom: 4px;">
            SESSION COMPLETE!
          </h3>
          <p style="font-size: 1rem; color: var(--text-muted); margin-bottom: 18px;">
            +${minutes} min added to your study stats. You're building serious momentum.
          </p>
          <div style="display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;">
            <button class="btn btn-primary btn-lg" id="btn-break-5" onclick="Timer.startBreak(5)">
              ☕ Take 5 min Break
            </button>
            <button class="btn btn-accent btn-lg" id="btn-break-10" onclick="Timer.startBreak(10)">
              🚶 10 min Break
            </button>
            <button class="btn btn-secondary btn-lg" id="btn-break-skip" onclick="Timer.skipBreak()">
              Skip Break
            </button>
          </div>
        </div>
      `;
      breakBanner.style.display = 'block';
    }
  }

  function startBreak(minutes) {
    const breakBanner = document.getElementById('timer-break-banner');
    if (breakBanner) breakBanner.style.display = 'none';

    mode = 'break';
    totalSeconds = minutes * 60;
    remainingSeconds = totalSeconds;
    updateDisplay();
    updateModeLabel(`☕ Break (${minutes}m)`);
    startTimer();
    App.showToast(`Starting ${minutes}-minute break. Rest your eyes! 🧘`, 'info');
  }

  function skipBreak() {
    const breakBanner = document.getElementById('timer-break-banner');
    if (breakBanner) breakBanner.style.display = 'none';
    setDuration(25);
    App.showToast('Break skipped. Ready for another focus session!', 'info');
  }

  function toggleControlButtons() {
    const btnStart = document.getElementById('btn-timer-start');
    const btnPause = document.getElementById('btn-timer-pause');
    const btnResume = document.getElementById('btn-timer-resume');
    const btnReset = document.getElementById('btn-timer-reset');
    const btnEnd = document.getElementById('btn-timer-end');

    if (!btnStart) return;

    if (!isRunning) {
      btnStart.style.display = 'inline-flex';
      btnPause.style.display = 'none';
      btnResume.style.display = 'none';
      btnReset.disabled = (remainingSeconds === totalSeconds);
      btnEnd.disabled = (remainingSeconds === totalSeconds);
    } else if (isPaused) {
      btnStart.style.display = 'none';
      btnPause.style.display = 'none';
      btnResume.style.display = 'inline-flex';
      btnReset.disabled = false;
      btnEnd.disabled = false;
    } else {
      btnStart.style.display = 'none';
      btnPause.style.display = 'inline-flex';
      btnResume.style.display = 'none';
      btnReset.disabled = false;
      btnEnd.disabled = false;
    }
  }

  function resetTimerUI() {
    const circle = document.getElementById('timer-progress-ring');
    if (circle) {
      circle.style.strokeDasharray = CIRCLE_CIRCUMFERENCE;
      circle.style.strokeDashoffset = 0;
    }
    updateDisplay();
    toggleControlButtons();
  }

  function initListeners() {
    // Duration pills
    document.querySelectorAll('.duration-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        setDuration(parseInt(pill.dataset.mins));
      });
    });

    // Controls
    document.getElementById('btn-timer-start')?.addEventListener('click', startTimer);
    document.getElementById('btn-timer-pause')?.addEventListener('click', pauseTimer);
    document.getElementById('btn-timer-resume')?.addEventListener('click', resumeTimer);
    document.getElementById('btn-timer-reset')?.addEventListener('click', resetTimer);
    document.getElementById('btn-timer-end')?.addEventListener('click', endSessionEarly);

    // Subject select change
    const subjSelect = document.getElementById('timer-subject-select');
    if (subjSelect) {
      subjSelect.addEventListener('change', (e) => {
        if (e.target.value) {
          selectedSubjectId = parseInt(e.target.value);
          selectedSubjectName = subjSelect.options[subjSelect.selectedIndex].textContent;
          loadTopicsForSubject(selectedSubjectId);
        } else {
          selectedSubjectId = null;
          selectedSubjectName = 'General';
          selectedTopicId = null;
          selectedTopicTitle = 'General Study';
          const topSelect = document.getElementById('timer-topic-select');
          if (topSelect) topSelect.innerHTML = '<option value="">-- No Specific Topic --</option>';
        }
        updateSessionInfoLabels();
      });
    }

    // Topic select change
    const topicSelect = document.getElementById('timer-topic-select');
    if (topicSelect) {
      topicSelect.addEventListener('change', (e) => {
        if (e.target.value) {
          selectedTopicId = parseInt(e.target.value);
          selectedTopicTitle = topicSelect.options[topicSelect.selectedIndex].textContent;
        } else {
          selectedTopicId = null;
          selectedTopicTitle = 'General Study';
        }
        updateSessionInfoLabels();
      });
    }

    // Task selector change
    const taskSelect = document.getElementById('timer-task-select');
    if (taskSelect) {
      taskSelect.addEventListener('change', (e) => {
        const selectedOpt = taskSelect.options[taskSelect.selectedIndex];
        if (e.target.value) {
          selectedTaskId = parseInt(e.target.value);
          selectedTaskTitle = selectedOpt.dataset.title || 'Focus Task';
          if (selectedOpt.dataset.subjectId) {
            selectedSubjectId = parseInt(selectedOpt.dataset.subjectId);
            selectedSubjectName = selectedOpt.dataset.subjectName || 'General';
            if (subjSelect) subjSelect.value = selectedSubjectId;
          }
        } else {
          selectedTaskId = null;
          selectedTaskTitle = 'General Study';
        }
        updateSessionInfoLabels();
      });
    }
  }

  return {
    load,
    setDuration,
    startWithTask,
    startManual,
    startBreak,
    skipBreak,
    initListeners
  };
})();
