// FocusFlow Modern Examination & Mock Test Controller
const MockTest = (() => {
  let activeTest = null;
  let currentQIndex = 0;
  let timerInterval = null;
  let elapsedSeconds = 0;
  let totalTimeSeconds = 15 * 60; // 15 min default test timer

  async function startTest(subjectName, subjectId = null, forceAll = false) {
    Router.navigate('mocktest');
    const container = document.getElementById('mocktest-container');
    if (!container) return;

    container.innerHTML = `
      <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 3rem; margin-bottom: 16px; animation: pulse 1.5s infinite;">🎯</div>
        <h3 style="font-size: 1.4rem; font-weight: 800; margin-bottom: 8px;">Preparing Mock Test</h3>
        <p style="color: var(--text-muted); font-size: 0.95rem;">
          Checking completed syllabus topics on <strong>${App.escapeHTML(subjectName)}</strong>...
        </p>
      </div>
    `;

    try {
      // 1. Resolve subjectId if not provided
      let sId = subjectId;
      if (!sId) {
        const allSubjects = await API.getSubjects().catch(() => []);
        const found = allSubjects.find(s => s.name.toLowerCase() === subjectName.toLowerCase());
        if (found) sId = found.id;
      }

      // 2. Fetch completed topics for this subject
      let completedTopics = [];
      let allTopics = [];
      if (sId) {
        allTopics = await API.getSubjectTopics(sId).catch(() => []);
        completedTopics = allTopics.filter(t => t.is_completed);
      }

      // If student hasn't completed any topic yet and hasn't forced all topics
      if (sId && completedTopics.length === 0 && !forceAll) {
        container.innerHTML = `
          <div class="card" style="max-width: 620px; margin: 40px auto; text-align: center; padding: 48px 24px;">
            <div style="font-size: 3.2rem; margin-bottom: 16px;">🔒</div>
            <h3 style="font-size: 1.5rem; font-weight: 800; margin-bottom: 8px;">Lock in a topic first!</h3>
            <p style="color: var(--text-muted); font-size: 0.95rem; margin-bottom: 24px; line-height: 1.6;">
              You haven't marked any topics as completed in <strong>${App.escapeHTML(subjectName)}</strong> yet.<br>
              FocusFlow mock tests are designed to test you on topics you have <strong>actually studied</strong>.
            </p>
            <div style="display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;">
              <button class="btn btn-primary btn-lg" onclick="SubjectsTasks.openSubjectDetail(${sId})">
                ✓ Open Syllabus &amp; Check Off Topics
              </button>
              <button class="btn btn-secondary btn-lg" onclick="MockTest.startTest(decodeURIComponent('${encodeURIComponent(subjectName)}'), ${sId}, true)">
                ⚡ Take Full Diagnostic Test
              </button>
            </div>
          </div>
        `;
        return;
      }

      const testedTopicNames = completedTopics.length > 0 
        ? completedTopics.map(t => t.title)
        : (allTopics.length > 0 ? allTopics.map(t => t.title) : [subjectName]);

      const topicQuery = testedTopicNames.slice(0, 5).join(', ');
      const qCount = Math.min(5, Math.max(3, testedTopicNames.length));

      // 3. Fetch questions using AI quiz service
      const quizRes = await API.generateQuiz(subjectName, topicQuery, qCount);
      
      // Enhance questions with topic tags
      const enrichedQuestions = quizRes.questions.map((q, idx) => ({
        ...q,
        topic_tag: q.topic_tag || testedTopicNames[idx % testedTopicNames.length],
        userAnswer: null,
        isFlagged: false
      }));

      activeTest = {
        subjectId: sId,
        subject: subjectName,
        testedTopics: testedTopicNames,
        questions: enrichedQuestions,
        startTime: Date.now()
      };

      currentQIndex = 0;
      elapsedSeconds = 0;
      totalTimeSeconds = Math.max(10, enrichedQuestions.length * 2) * 60;

      startTimer();
      renderExamUI();
    } catch (err) {
      console.error('Failed to generate mock test:', err);
      App.showToast('Could not load mock test questions. Please try again.', 'error');
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px;">
          <p style="color: var(--danger); font-weight: 600;">Failed to generate mock test.</p>
          <button class="btn btn-primary" onclick="Router.navigate('subjects')" style="margin-top: 14px;">
            ← Return to Subjects
          </button>
        </div>
      `;
    }
  }

  function startTimer() {
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      elapsedSeconds++;
      updateTimerDisplay();
      if (elapsedSeconds >= totalTimeSeconds) {
        clearInterval(timerInterval);
        App.showToast('Time is up! Submitting your test...', 'info');
        submitTest();
      }
    }, 1000);
  }

  function updateTimerDisplay() {
    const timerEl = document.getElementById('exam-timer-display');
    if (!timerEl) return;
    const remaining = Math.max(0, totalTimeSeconds - elapsedSeconds);
    const m = Math.floor(remaining / 60);
    const s = remaining % 60;
    timerEl.textContent = `⏱ ${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  function renderExamUI() {
    const container = document.getElementById('mocktest-container');
    if (!container || !activeTest) return;

    const totalQ = activeTest.questions.length;
    const q = activeTest.questions[currentQIndex];
    const progressPercent = Math.round(((currentQIndex + 1) / totalQ) * 100);

    container.innerHTML = `
      <div class="exam-wrapper">
        <!-- Top Bar -->
        <div class="exam-header-bar">
          <div>
            <div class="exam-subject-badge">${App.escapeHTML(activeTest.subject)}</div>
            <h3 style="font-size: 1.25rem; font-weight: 800; margin-top: 4px;">Mock Examination</h3>
          </div>
          <div style="display: flex; align-items: center; gap: 14px;">
            <div class="exam-timer-badge" id="exam-timer-display">⏱ 15:00</div>
            <button class="btn btn-sm btn-accent" onclick="MockTest.confirmSubmit()">Submit Test</button>
          </div>
        </div>

        <!-- Topics in this test info -->
        <div style="background: rgba(108, 59, 255, 0.08); border-radius: var(--radius-sm); padding: 10px 14px; margin-bottom: 16px; font-size: 0.85rem; color: var(--primary-600); font-weight: 700;">
          🎯 Tested Syllabus Topics: ${activeTest.testedTopics.map(t => App.escapeHTML(t)).join(' • ')}
        </div>

        <!-- Progress Indicator -->
        <div style="margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; margin-bottom: 6px;">
            <span>Question ${String(currentQIndex + 1).padStart(2, '0')} of ${String(totalQ).padStart(2, '0')}</span>
            <span style="color: var(--primary-600);">${progressPercent}% Completed</span>
          </div>
          <div class="progress-bar-bg" style="height: 8px;">
            <div class="progress-bar-fill" style="width: ${progressPercent}%; transition: width 0.3s ease;"></div>
          </div>
        </div>

        <!-- Main Question & Options Card -->
        <div class="card exam-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
            <span class="badge" style="background: rgba(108, 59, 255, 0.1); color: var(--primary-600); font-weight: 700;">
              📌 Topic: ${App.escapeHTML(q.topic_tag || activeTest.subject)}
            </span>
            <button class="btn-flag ${q.isFlagged ? 'flagged' : ''}" onclick="MockTest.toggleFlag()" title="Mark for Review">
              🚩 ${q.isFlagged ? 'Marked for Review' : 'Mark for Review'}
            </button>
          </div>

          <h2 class="exam-question-title">${App.escapeHTML(q.question)}</h2>

          <div class="exam-options-grid">
            ${q.options.map((opt, optIdx) => {
              const isSelected = (q.userAnswer === optIdx);
              const letters = ['A', 'B', 'C', 'D'];
              return `
                <div class="exam-opt-card ${isSelected ? 'selected' : ''}" onclick="MockTest.selectOption(${optIdx})">
                  <span class="opt-prefix">${letters[optIdx]}</span>
                  <span class="opt-text">${App.escapeHTML(opt.replace(/^[A-D]\)\s*/, ''))}</span>
                </div>
              `;
            }).join('')}
          </div>
        </div>

        <!-- Question Navigation Bar -->
        <div class="exam-nav-bar">
          <button class="btn btn-secondary" onclick="MockTest.prevQuestion()" ${currentQIndex === 0 ? 'disabled' : ''}>
            ← Previous
          </button>

          <!-- Question Palette Pills -->
          <div class="palette-container">
            ${activeTest.questions.map((item, idx) => {
              let cls = '';
              if (idx === currentQIndex) cls = 'current';
              else if (item.isFlagged) cls = 'flagged';
              else if (item.userAnswer !== null) cls = 'answered';

              return `
                <button class="palette-pill ${cls}" onclick="MockTest.jumpToQuestion(${idx})" title="Go to Question ${idx + 1}">
                  ${idx + 1}
                </button>
              `;
            }).join('')}
          </div>

          ${currentQIndex < totalQ - 1 ? `
            <button class="btn btn-primary" onclick="MockTest.nextQuestion()">
              Next →
            </button>
          ` : `
            <button class="btn btn-accent" onclick="MockTest.confirmSubmit()">
              Submit Test ✓
            </button>
          `}
        </div>
      </div>
    `;

    updateTimerDisplay();
  }

  function selectOption(optIndex) {
    if (!activeTest) return;
    activeTest.questions[currentQIndex].userAnswer = optIndex;
    renderExamUI();
  }

  function toggleFlag() {
    if (!activeTest) return;
    const q = activeTest.questions[currentQIndex];
    q.isFlagged = !q.isFlagged;
    renderExamUI();
  }

  function nextQuestion() {
    if (!activeTest) return;
    if (currentQIndex < activeTest.questions.length - 1) {
      currentQIndex++;
      renderExamUI();
    }
  }

  function prevQuestion() {
    if (!activeTest) return;
    if (currentQIndex > 0) {
      currentQIndex--;
      renderExamUI();
    }
  }

  function jumpToQuestion(idx) {
    if (!activeTest || idx < 0 || idx >= activeTest.questions.length) return;
    currentQIndex = idx;
    renderExamUI();
  }

  function confirmSubmit() {
    if (!activeTest) return;
    const answered = activeTest.questions.filter(q => q.userAnswer !== null).length;
    const flagged = activeTest.questions.filter(q => q.isFlagged).length;
    const total = activeTest.questions.length;
    const unanswered = total - answered;

    let promptMsg = `Ready to submit your examination?\n\n• Answered: ${answered} / ${total}\n• Unanswered: ${unanswered}\n• Flagged for review: ${flagged}`;
    if (unanswered > 0) {
      promptMsg += `\n\n⚠️ You have ${unanswered} unanswered question(s). Are you sure you want to finish?`;
    }

    if (confirm(promptMsg)) {
      submitTest();
    }
  }

  async function submitTest() {
    clearInterval(timerInterval);
    if (!activeTest) return;

    let correctCount = 0;
    const totalQuestions = activeTest.questions.length;
    const topicStats = {};

    activeTest.questions.forEach(q => {
      const isCorrect = (q.userAnswer === q.correct_answer);
      if (isCorrect) correctCount++;

      const tag = q.topic_tag || 'General Concepts';
      if (!topicStats[tag]) {
        topicStats[tag] = { total: 0, correct: 0 };
      }
      topicStats[tag].total++;
      if (isCorrect) topicStats[tag].correct++;
    });

    const scorePercent = Math.round((correctCount / totalQuestions) * 100);
    const durationMinutes = Math.max(1, Math.round(elapsedSeconds / 60));

    // Identify weak topics (performance < 70%)
    const weakTopics = [];
    Object.keys(topicStats).forEach(tag => {
      const pct = Math.round((topicStats[tag].correct / topicStats[tag].total) * 100);
      if (pct < 70) {
        weakTopics.push(tag);
      }
    });

    // 1. Record test result in SQLite database
    try {
      await API.recordMockTest({
        subject_id: activeTest.subjectId,
        subject_name: activeTest.subject,
        score: correctCount,
        total_questions: totalQuestions,
        percentage: scorePercent,
        duration_minutes: durationMinutes
      });
    } catch (e) {
      console.warn('Failed to record mock test:', e);
    }

    // 2. Also record study session for time spent
    API.recordSession(durationMinutes, activeTest.subjectId, null).catch(() => {});

    App.showToast('Brain gains unlocked 🧠 Mock test submitted!', 'success');
    renderResultScreen({
      subjectId: activeTest.subjectId,
      subject: activeTest.subject,
      correctCount,
      totalQuestions,
      scorePercent,
      durationMinutes,
      topicStats,
      weakTopics,
      questions: activeTest.questions
    });
  }

  function renderResultScreen(res) {
    const container = document.getElementById('mocktest-container');
    if (!container) return;

    let headline = '🎯 NICE WORK!';
    let feedback = "You're getting there 🔥";
    if (res.scorePercent >= 80) {
      headline = '🏆 OUTSTANDING PERFORMANCE!';
      feedback = 'Absolute mastery! Ready for exam day 🚀';
    } else if (res.scorePercent < 50) {
      headline = '📚 PRACTICE MAKES PERFECT!';
      feedback = 'Good diagnostic run. Review weak areas below!';
    }

    container.innerHTML = `
      <div class="result-card-wrapper">
        <div class="card result-card">
          <!-- Score Header -->
          <div style="text-align: center; margin-bottom: 24px;">
            <div style="font-size: 2.8rem; margin-bottom: 8px;">🎯</div>
            <h2 style="font-size: 1.8rem; font-weight: 800; color: var(--text-main);">${headline}</h2>
            <p style="font-size: 1.05rem; color: var(--accent-500); font-weight: 700; margin-top: 4px;">
              ${feedback}
            </p>
          </div>

          <!-- Big Stat Badges -->
          <div class="result-score-banner">
            <div class="result-big-num">${res.correctCount} / ${res.totalQuestions}</div>
            <div class="result-big-pct">${res.scorePercent}%</div>
          </div>

          <div class="result-metrics-grid">
            <div class="result-metric-box">
              <span style="color: var(--success); font-size: 1.3rem;">✓</span>
              <div>
                <div style="font-weight: 800; font-size: 1.1rem;">${res.correctCount}</div>
                <div style="font-size: 0.78rem; color: var(--text-muted);">Correct</div>
              </div>
            </div>
            <div class="result-metric-box">
              <span style="color: var(--danger); font-size: 1.3rem;">✕</span>
              <div>
                <div style="font-weight: 800; font-size: 1.1rem;">${res.totalQuestions - res.correctCount}</div>
                <div style="font-size: 0.78rem; color: var(--text-muted);">Incorrect</div>
              </div>
            </div>
            <div class="result-metric-box">
              <span style="color: var(--primary-600); font-size: 1.3rem;">⏱</span>
              <div>
                <div style="font-weight: 800; font-size: 1.1rem;">${res.durationMinutes} min</div>
                <div style="font-size: 0.78rem; color: var(--text-muted);">Time Taken</div>
              </div>
            </div>
          </div>

          <!-- Topic Performance Breakdown -->
          <div style="margin-top: 32px;">
            <h4 style="font-size: 0.95rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 16px;">
              📊 Topic Performance Breakdown
            </h4>
            <div style="display: flex; flex-direction: column; gap: 14px;">
              ${Object.keys(res.topicStats).map(t => {
                const stat = res.topicStats[t];
                const pct = Math.round((stat.correct / stat.total) * 100);
                return `
                  <div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 700; margin-bottom: 6px;">
                      <span>${App.escapeHTML(t)}</span>
                      <span>${pct}% (${stat.correct}/${stat.total})</span>
                    </div>
                    <div class="progress-bar-bg" style="height: 10px;">
                      <div class="progress-bar-fill" style="width: ${pct}%; background: ${pct >= 70 ? 'var(--success)' : 'var(--accent-500)'};"></div>
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>

          <!-- Weak Topics Alert -->
          ${res.weakTopics.length > 0 ? `
            <div class="weak-topics-banner">
              <div style="font-weight: 700; font-size: 0.95rem; color: var(--accent-700); margin-bottom: 8px;">
                👀 These topics deserve another look:
              </div>
              <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px;">
                ${res.weakTopics.map(w => `
                  <span class="badge" style="background: rgba(255, 107, 107, 0.15); color: var(--accent-600); font-weight: 700; font-size: 0.88rem; padding: 6px 12px;">
                    ${App.escapeHTML(w)}
                  </span>
                `).join('')}
              </div>
              <button class="btn btn-accent" onclick="MockTest.reviseWeakTopics(decodeURIComponent('${encodeURIComponent(res.weakTopics[0])}'), decodeURIComponent('${encodeURIComponent(res.subject)}'))">
                📖 Revise Weak Topics with AI
              </button>
            </div>
          ` : `
            <div style="padding: 16px; background: rgba(16, 185, 129, 0.1); border-radius: var(--radius-md); margin-top: 24px; text-align: center; color: var(--success); font-weight: 700;">
              ✨ No major weak areas detected! Incredible consistency.
            </div>
          `}

          <!-- Question-by-Question Detailed Review -->
          <div style="margin-top: 36px; padding-top: 24px; border-top: 1px solid var(--border-subtle);">
            <h4 style="font-size: 1rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 18px;">
              📝 Detailed Answer Review
            </h4>
            <div style="display: flex; flex-direction: column; gap: 18px;">
              ${res.questions.map((q, idx) => {
                const isCorrect = (q.userAnswer === q.correct_answer);
                const letters = ['A', 'B', 'C', 'D'];
                return `
                  <div class="card" style="padding: 18px; border-left: 4px solid ${isCorrect ? 'var(--success)' : 'var(--danger)'}; background: var(--bg-surface);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                      <span style="font-size: 0.82rem; font-weight: 800; color: var(--text-muted);">
                        QUESTION ${idx + 1} • ${App.escapeHTML(q.topic_tag || 'Concept')}
                      </span>
                      <span class="badge" style="background: ${isCorrect ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 107, 107, 0.15)'}; color: ${isCorrect ? 'var(--success)' : 'var(--danger)'}; font-weight: 800;">
                        ${isCorrect ? '✓ Correct (+1)' : '✕ Incorrect'}
                      </span>
                    </div>

                    <div style="font-weight: 700; font-size: 0.98rem; margin-bottom: 12px; color: var(--text-main);">
                      ${App.escapeHTML(q.question)}
                    </div>

                    <div style="font-size: 0.88rem; margin-bottom: 8px;">
                      <strong>Your Answer:</strong> 
                      <span style="color: ${isCorrect ? 'var(--success)' : 'var(--danger)'}; font-weight: 700;">
                        ${q.userAnswer !== null ? `${letters[q.userAnswer]}) ${App.escapeHTML(q.options[q.userAnswer].replace(/^[A-D]\)\s*/, ''))}` : 'Skipped'}
                      </span>
                    </div>

                    ${!isCorrect ? `
                      <div style="font-size: 0.88rem; margin-bottom: 8px;">
                        <strong>Correct Answer:</strong> 
                        <span style="color: var(--success); font-weight: 700;">
                          ${letters[q.correct_answer]}) ${App.escapeHTML(q.options[q.correct_answer].replace(/^[A-D]\)\s*/, ''))}
                        </span>
                      </div>
                    ` : ''}

                    <div style="font-size: 0.85rem; color: var(--text-muted); background: var(--bg-muted); padding: 10px 14px; border-radius: var(--radius-sm); margin-top: 8px;">
                      💡 <strong>Explanation:</strong> ${App.escapeHTML(q.explanation || 'Review topic fundamentals for details.')}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>

          <!-- Actions -->
          <div style="display: flex; justify-content: center; gap: 14px; margin-top: 32px; flex-wrap: wrap;">
            <button class="btn btn-secondary btn-lg" onclick="Router.navigate('subjects')">
              ← Return to Subjects
            </button>
            <button class="btn btn-primary btn-lg" onclick="MockTest.startTest(decodeURIComponent('${encodeURIComponent(res.subject)}'), ${res.subjectId || 'null'}, true)">
              🔄 Retake Test
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function reviseWeakTopics(topicName, subjectName) {
    Router.navigate('ai');
    const explainTabBtn = document.querySelector('.ai-feature-card[data-tab="explain"]');
    if (explainTabBtn) explainTabBtn.click();
    const topicInput = document.getElementById('ai-explain-topic');
    if (topicInput) {
      topicInput.value = topicName;
      topicInput.focus();
    }
  }

  async function renderLauncher() {
    const container = document.getElementById('mocktest-container');
    if (!container) return;

    const subjects = await API.getSubjects().catch(() => []);
    const recents = await API.getRecentMockTests(5).catch(() => []);

    if (subjects.length === 0) {
      container.innerHTML = `
        <div class="card" style="max-width: 600px; margin: 40px auto; text-align: center; padding: 48px 24px;">
          <div style="font-size: 3rem; margin-bottom: 12px;">🎯</div>
          <h3 style="font-size: 1.3rem; font-weight: 800; margin-bottom: 6px;">No Subjects Found</h3>
          <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 20px;">
            Create your subjects and study topics first. FocusFlow mock tests are dynamically generated from your studied curriculum!
          </p>
          <button class="btn btn-primary" onclick="Router.navigate('subjects')">+ Add Subject</button>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div style="max-width: 800px; margin: 0 auto;">
        <!-- Configuration Card -->
        <div class="card" style="padding: 32px; margin-bottom: 24px;">
          <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 18px;">
            <div style="font-size: 2.5rem;">🎯</div>
            <div>
              <h2 style="font-size: 1.5rem; font-weight: 800; color: var(--text-main);">Subject Examination &amp; Mock Tests</h2>
              <p style="font-size: 0.88rem; color: var(--text-muted);">
                Test your knowledge under real exam conditions with instant scoring, question palette, and weak topic diagnostic review!
              </p>
            </div>
          </div>

          <form id="form-launch-mocktest">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 20px;">
              <div class="form-group" style="margin: 0;">
                <label class="form-label" for="mock-select-subject">Select Subject</label>
                <select id="mock-select-subject" required style="font-weight: 700;">
                  ${subjects.map(s => `<option value="${s.id}" data-name="${App.escapeHTML(s.name)}">${App.escapeHTML(s.name)} (${s.completed_topics_count || 0} completed)</option>`).join('')}
                </select>
              </div>

              <div class="form-group" style="margin: 0;">
                <label class="form-label" for="mock-select-difficulty">Difficulty</label>
                <select id="mock-select-difficulty">
                  <option value="Medium" selected>Medium</option>
                  <option value="Easy">Easy</option>
                  <option value="Hard">Hard (Exam Level)</option>
                </select>
              </div>

              <div class="form-group" style="margin: 0;">
                <label class="form-label" for="mock-select-count">Questions</label>
                <select id="mock-select-count">
                  <option value="5" selected>5 Questions</option>
                  <option value="10">10 Questions</option>
                  <option value="15">15 Questions</option>
                </select>
              </div>
            </div>

            <!-- Eligible Completed Topics Box -->
            <div id="mock-eligible-topics-box" style="margin-bottom: 20px; padding: 16px; background: var(--bg-muted); border-radius: var(--radius-md);">
              <span style="font-size: 0.82rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 8px;">
                ELIGIBLE COMPLETED TOPICS INCLUDED:
              </span>
              <div id="mock-eligible-topics-list" style="display: flex; flex-wrap: wrap; gap: 8px;">
                Loading topics...
              </div>
            </div>

            <button type="submit" id="btn-start-mock-exam" class="btn btn-primary btn-lg" style="width: 100%;">
              🚀 Launch Mock Examination
            </button>
          </form>
        </div>

        <!-- Recent Mock Tests History -->
        ${recents.length > 0 ? `
          <div class="card" style="padding: 24px;">
            <h4 style="font-size: 1.05rem; font-weight: 800; margin-bottom: 14px;">Recent Examination History</h4>
            <div style="display: flex; flex-direction: column; gap: 10px;">
              ${recents.map(r => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--bg-muted); border-radius: var(--radius-sm);">
                  <div>
                    <span style="font-weight: 700; color: var(--text-main); font-size: 0.92rem;">${App.escapeHTML(r.subject_name)}</span>
                    <span style="font-size: 0.78rem; color: var(--text-muted); margin-left: 8px;">(${r.difficulty || 'Medium'} • ${r.created_at ? r.created_at.slice(0, 10) : ''})</span>
                  </div>
                  <div style="display: flex; align-items: center; gap: 12px;">
                    <span class="badge" style="background: ${r.percentage >= 75 ? 'rgba(16,185,129,0.15)' : 'rgba(255,107,107,0.15)'}; color: ${r.percentage >= 75 ? 'var(--success)' : 'var(--danger)'}; font-weight: 800;">
                      ${r.percentage}% (${r.score}/${r.total_questions})
                    </span>
                    <button class="btn btn-sm btn-secondary" onclick="MockTest.startTest('${App.escapeHTML(r.subject_name)}', ${r.subject_id || 'null'}, true)">Retest</button>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;

    const subjSel = document.getElementById('mock-select-subject');
    if (subjSel) {
      subjSel.addEventListener('change', () => updateEligibleTopicsList(parseInt(subjSel.value)));
      if (subjSel.value) updateEligibleTopicsList(parseInt(subjSel.value));
    }

    const form = document.getElementById('form-launch-mocktest');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const selectedSubjOpt = subjSel.options[subjSel.selectedIndex];
        const sName = selectedSubjOpt.dataset.name;
        const sId = parseInt(subjSel.value);
        const diff = document.getElementById('mock-select-difficulty').value;
        const count = parseInt(document.getElementById('mock-select-count').value) || 5;

        const checked = Array.from(document.querySelectorAll('.mock-topic-checkbox:checked')).map(cb => cb.value);
        startCustomTest(sName, sId, checked, diff, count);
      });
    }
  }

  async function updateEligibleTopicsList(subjectId) {
    const listEl = document.getElementById('mock-eligible-topics-list');
    if (!listEl) return;

    try {
      const data = await API.getEligibleMockTopics(subjectId);
      if (data.eligible_topics.length === 0) {
        listEl.innerHTML = `
          <div style="font-size: 0.85rem; color: var(--text-muted);">
            No topics marked completed in this subject yet. 
            <a href="javascript:void(0)" onclick="SubjectsTasks.openSubjectDetail(${subjectId})" style="color: var(--primary-600); font-weight: 700;">Complete topics in syllabus</a> to test them, or proceed with full curriculum.
          </div>
        `;
      } else {
        listEl.innerHTML = data.eligible_topics.map(t => `
          <label style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; background: var(--card-bg); border-radius: var(--radius-sm); border: 1px solid var(--border-color); font-size: 0.82rem; font-weight: 600; cursor: pointer;">
            <input type="checkbox" class="mock-topic-checkbox" value="${App.escapeHTML(t.title)}" checked style="accent-color: var(--primary-600);">
            <span>${App.escapeHTML(t.title)}</span>
          </label>
        `).join('');
      }
    } catch (e) {
      listEl.innerHTML = '<span style="font-size: 0.82rem; color: var(--text-muted);">Curriculum diagnostic test</span>';
    }
  }

  async function startCustomTest(subjectName, subjectId, topicTitles, difficulty, numQuestions) {
    Router.navigate('mocktest');
    const container = document.getElementById('mocktest-container');
    if (!container) return;

    container.innerHTML = `
      <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 3rem; margin-bottom: 16px; animation: pulse 1.5s infinite;">🎯</div>
        <h3 style="font-size: 1.4rem; font-weight: 800; margin-bottom: 8px;">Generating Mock Examination</h3>
        <p style="color: var(--text-muted); font-size: 0.95rem;">
          Synthesizing ${numQuestions} questions on <strong>${App.escapeHTML(subjectName)}</strong> (${difficulty} difficulty)...
        </p>
      </div>
    `;

    try {
      const quizRes = await API.generateMockQuestions(subjectId, topicTitles, difficulty, numQuestions);
      const enrichedQuestions = quizRes.questions.map((q, idx) => ({
        ...q,
        topic_tag: q.topic_tag || (topicTitles[idx % topicTitles.length] || subjectName),
        userAnswer: null,
        isFlagged: false
      }));

      activeTest = {
        subjectId: subjectId,
        subject: subjectName,
        difficulty: difficulty,
        testedTopics: topicTitles,
        questions: enrichedQuestions,
        startTime: Date.now()
      };

      currentQIndex = 0;
      elapsedSeconds = 0;
      totalTimeSeconds = Math.max(10, enrichedQuestions.length * 2) * 60;

      startTimer();
      renderExamUI();
    } catch (err) {
      App.showToast('Could not load customized test. Loading standard diagnostic.', 'warning');
      startTest(subjectName, subjectId, true);
    }
  }

  function init() {
    renderLauncher();
  }

  return {
    init,
    startTest,
    selectOption,
    toggleFlag,
    nextQuestion,
    prevQuestion,
    jumpToQuestion,
    confirmSubmit,
    submitTest,
    reviseWeakTopics
  };
})();
