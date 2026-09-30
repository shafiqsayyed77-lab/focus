// FocusFlow Gen-Z AI Study Assistant Controller
const AIStudy = (() => {
  let activeTab = 'planner'; // 'planner', 'explain', 'quiz', 'diagram', 'viva'
  let currentQuizData = null;
  let quizUserAnswers = {};

  function load() {
    SubjectsTasks.loadSubjects();
    setPlannerTime(60);
    switchTab(activeTab);
  }

  function switchTab(tabName) {
    activeTab = tabName;

    // Update feature card selection
    document.querySelectorAll('.ai-feature-card').forEach(c => {
      c.classList.remove('active');
      if (c.dataset.tab === tabName) {
        c.classList.add('active');
      }
    });

    // Update panel visibility
    document.querySelectorAll('.ai-feature-panel').forEach(panel => {
      panel.classList.remove('active');
      if (panel.id === `ai-panel-${tabName}`) {
        panel.classList.add('active');
      }
    });
  }

  function setPlannerTime(minutes) {
    const hiddenInput = document.getElementById('ai-planner-time');
    if (hiddenInput) hiddenInput.value = minutes;
    const pills = document.querySelectorAll('.ai-time-pill');
    pills.forEach(p => {
      p.classList.remove('active');
      if (parseInt(p.dataset.mins) === minutes) {
        p.classList.add('active');
      }
    });
  }

  // --- 1. AI Study Planner ---
  async function handleGeneratePlan(e) {
    e.preventDefault();
    const subjectSelect = document.getElementById('ai-planner-subject');
    const subjectName = subjectSelect.options[subjectSelect.selectedIndex]?.text || 'General Studies';
    const topics = document.getElementById('ai-planner-topics').value.trim();
    const available_time = parseInt(document.getElementById('ai-planner-time').value) || 60;
    const energy_level = document.getElementById('ai-planner-energy').value;
    const priority = document.getElementById('ai-planner-priority').value;

    if (!topics) {
      App.showToast('Please enter at least one topic to study.', 'warning');
      return;
    }

    const btn = document.getElementById('btn-generate-plan');
    const resultContainer = document.getElementById('ai-planner-result');
    btn.disabled = true;
    btn.innerHTML = '⏳ Generating Plan...';
    resultContainer.innerHTML = `
      <div style="text-align: center; padding: 30px; color: var(--text-muted);">
        <p>Analyzing topics and balancing study intervals based on ${energy_level} energy...</p>
      </div>
    `;

    try {
      const plan = await API.generatePlan(subjectName, topics, available_time, energy_level, priority);
      renderPlanResult(plan, subjectSelect.value);
    } catch (err) {
      App.showToast(err.message || 'Failed to generate study plan.', 'error');
      resultContainer.innerHTML = `<p style="color: var(--danger);">Failed to generate plan. Please try again.</p>`;
    } finally {
      btn.disabled = false;
      btn.innerHTML = '✨ Generate Study Plan';
    }
  }

  function renderPlanResult(plan, subjectId) {
    const container = document.getElementById('ai-planner-result');
    if (!container) return;

    container.innerHTML = `
      <div class="card" style="margin-top: 24px; border-left: 4px solid var(--primary-600); animation: fadeIn 0.3s ease;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
          <div>
            <h3 style="font-size: 1.3rem; font-weight: 800; color: var(--text-main);">
              🎯 ${App.escapeHTML(plan.subject)} Study Schedule
            </h3>
            <p style="font-size: 0.9rem; color: var(--text-muted); margin-top: 4px;">
              ${App.escapeHTML(plan.strategy_summary)}
            </p>
          </div>
          <div style="display: flex; gap: 8px;">
            <span class="badge" style="background: rgba(124, 58, 237, 0.12); color: var(--primary-600);">
              ⏱ ${plan.total_minutes} Minutes Total
            </span>
            <span class="badge" style="background: rgba(255, 107, 74, 0.15); color: var(--accent-600);">
              ⚡ ${plan.energy_level} Energy
            </span>
          </div>
        </div>

        <div style="padding: 12px 16px; background-color: var(--bg-muted); border-radius: var(--radius-md); font-size: 0.88rem; margin-bottom: 20px;">
          💡 <strong>Energy Strategy:</strong> ${App.escapeHTML(plan.energy_advice)}
        </div>

        <h4 style="font-size: 1rem; font-weight: 700; margin-bottom: 12px;">Step-by-Step Breakdown:</h4>
        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${plan.schedule.map((item, idx) => `
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-radius: var(--radius-md); background-color: var(--bg-surface-elevated); border: 1px solid var(--border-color); flex-wrap: wrap; gap: 12px;">
              <div style="display: flex; align-items: center; gap: 14px;">
                <span style="width: 28px; height: 28px; border-radius: var(--radius-full); background: var(--primary-100); color: var(--primary-700); font-weight: 700; font-size: 0.85rem; display: flex; align-items: center; justify-content: center;">
                  ${idx + 1}
                </span>
                <div>
                  <div style="font-weight: 700; font-size: 0.95rem;">${App.escapeHTML(item.topic)}</div>
                  <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 2px;">
                    ${App.escapeHTML(item.activity)} ${item.tips ? `• <em>${App.escapeHTML(item.tips)}</em>` : ''}
                  </div>
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 10px;">
                <span class="badge" style="background: var(--bg-muted); color: var(--text-main); font-size: 0.82rem;">
                  ⏱ ${item.duration_minutes} min
                </span>
                <button class="btn btn-sm btn-secondary" onclick="AIStudy.convertBlockToTask(decodeURIComponent('${encodeURIComponent(item.topic)}'), ${subjectId || 'null'}, ${item.duration_minutes})">
                  + Add as Task
                </button>
                <button class="btn btn-sm btn-primary" onclick="Timer.startManual(${item.duration_minutes}, decodeURIComponent('${encodeURIComponent(item.topic)}'), decodeURIComponent('${encodeURIComponent(plan.subject)}'))">
                  ⏱ Focus Now
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  async function convertBlockToTask(topic, subjectId, duration) {
    try {
      await API.createTask({
        title: `Study: ${topic}`,
        subject_id: subjectId,
        description: `Scheduled focus block (${duration} minutes).`,
        priority: 'Medium'
      });
      App.showToast(`Added "${topic}" to your tasks!`, 'success');
    } catch (e) {
      App.showToast('Could not add task.', 'error');
    }
  }

  // --- 2. AI Explain ---
  async function handleExplainSubmit(e) {
    e.preventDefault();
    const topic = document.getElementById('ai-explain-topic').value.trim();
    const subjectSelect = document.getElementById('ai-explain-subject');
    const subject = subjectSelect.options[subjectSelect.selectedIndex]?.text || '';

    if (!topic) {
      App.showToast('Please enter a concept or topic to explain.', 'warning');
      return;
    }

    const btn = document.getElementById('btn-explain-topic');
    const resultContainer = document.getElementById('ai-explain-result');
    btn.disabled = true;
    btn.innerHTML = '⏳ Explaining...';
    resultContainer.innerHTML = `
      <div style="text-align: center; padding: 30px; color: var(--text-muted);">
        <p>Formulating simple explanation and examples for "${App.escapeHTML(topic)}"...</p>
      </div>
    `;

    try {
      const res = await API.explainTopic(topic, subject);
      renderExplainResult(res);
    } catch (err) {
      App.showToast(err.message || 'Failed to explain topic.', 'error');
      resultContainer.innerHTML = `<p style="color: var(--danger);">Failed to get explanation.</p>`;
    } finally {
      btn.disabled = false;
      btn.innerHTML = '💡 Explain Clearly';
    }
  }

  function renderExplainResult(data) {
    const container = document.getElementById('ai-explain-result');
    if (!container) return;

    container.innerHTML = `
      <div class="card" style="margin-top: 24px; animation: fadeIn 0.3s ease;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
          <span style="font-size: 1.6rem;">💡</span>
          <h3 style="font-size: 1.35rem; font-weight: 800; color: var(--text-main);">
            ${App.escapeHTML(data.topic)}
          </h3>
        </div>

        <div style="margin-bottom: 20px;">
          <h4 style="font-size: 0.92rem; text-transform: uppercase; color: var(--primary-600); font-weight: 700; margin-bottom: 6px;">
            Intuitive Explanation
          </h4>
          <p style="font-size: 1.02rem; line-height: 1.6; color: var(--text-main);">
            ${App.escapeHTML(data.simple_explanation)}
          </p>
        </div>

        <div style="margin-bottom: 20px;">
          <h4 style="font-size: 0.92rem; text-transform: uppercase; color: var(--primary-600); font-weight: 700; margin-bottom: 8px;">
            Key Takeaways
          </h4>
          <ul style="padding-left: 20px; display: flex; flex-direction: column; gap: 6px;">
            ${data.important_points.map(pt => `
              <li style="font-size: 0.95rem; color: var(--text-main);">${App.escapeHTML(pt)}</li>
            `).join('')}
          </ul>
        </div>

        <div style="padding: 16px 20px; background: linear-gradient(135deg, rgba(255, 107, 74, 0.08), rgba(249, 115, 22, 0.04)); border: 1.5px solid rgba(255, 107, 74, 0.25); border-radius: var(--radius-md); margin-bottom: 16px;">
          <h4 style="font-size: 0.92rem; font-weight: 700; color: var(--accent-600); margin-bottom: 4px;">
            🌟 Practical Analogy / Example
          </h4>
          <p style="font-size: 0.94rem; line-height: 1.5; color: var(--text-main);">
            ${App.escapeHTML(data.example)}
          </p>
        </div>

        ${data.memory_tip ? `
          <div style="padding: 12px 16px; background-color: var(--bg-muted); border-radius: var(--radius-md); font-size: 0.88rem; color: var(--text-muted);">
            🧠 <strong>Memory Trigger:</strong> ${App.escapeHTML(data.memory_tip)}
          </div>
        ` : ''}
      </div>
    `;
  }

  // --- 3. AI Quiz ---
  async function handleQuizSubmit(e) {
    e.preventDefault();
    const subjectSelect = document.getElementById('ai-quiz-subject');
    const subject = subjectSelect.options[subjectSelect.selectedIndex]?.text || 'Computer Science';
    const topic = document.getElementById('ai-quiz-topic').value.trim();
    const num_questions = parseInt(document.getElementById('ai-quiz-count').value) || 3;

    if (!topic) {
      App.showToast('Please enter a topic for the quiz.', 'warning');
      return;
    }

    const btn = document.getElementById('btn-generate-quiz');
    const resultContainer = document.getElementById('ai-quiz-result');
    btn.disabled = true;
    btn.innerHTML = '⏳ Generating MCQs...';
    resultContainer.innerHTML = `
      <div style="text-align: center; padding: 30px; color: var(--text-muted);">
        <p>Creating ${num_questions} targeted multiple choice questions on ${App.escapeHTML(topic)}...</p>
      </div>
    `;

    try {
      const quiz = await API.generateQuiz(subject, topic, num_questions);
      currentQuizData = quiz;
      quizUserAnswers = {};
      renderQuiz(quiz);
    } catch (err) {
      App.showToast(err.message || 'Failed to generate quiz.', 'error');
      resultContainer.innerHTML = `<p style="color: var(--danger);">Failed to load quiz.</p>`;
    } finally {
      btn.disabled = false;
      btn.innerHTML = '📝 Generate Interactive Quiz';
    }
  }

  function renderQuiz(quiz) {
    const container = document.getElementById('ai-quiz-result');
    if (!container) return;

    container.innerHTML = `
      <div style="margin-top: 24px; animation: fadeIn 0.3s ease;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
          <div>
            <h3 style="font-size: 1.25rem; font-weight: 800;">
              📝 Quiz: ${App.escapeHTML(quiz.topic)}
            </h3>
            <p style="font-size: 0.85rem; color: var(--text-muted);">
              Subject: ${App.escapeHTML(quiz.subject)} • ${quiz.questions.length} Questions
            </p>
          </div>
          <div id="quiz-live-score" class="badge" style="font-size: 0.9rem; padding: 6px 14px; background: var(--bg-muted); color: var(--text-main);">
            Score: 0 / ${quiz.questions.length}
          </div>
        </div>

        <div style="display: flex; flex-direction: column; gap: 20px;">
          ${quiz.questions.map((q, qIndex) => `
            <div class="card quiz-card" id="quiz-q-${qIndex}">
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <span class="badge" style="background: var(--primary-100); color: var(--primary-700);">Q${qIndex + 1}</span>
              </div>
              <div class="quiz-question-text">${App.escapeHTML(q.question)}</div>
              <div class="quiz-options">
                ${q.options.map((opt, optIndex) => `
                  <button class="quiz-opt-btn" onclick="AIStudy.selectQuizOption(${qIndex}, ${optIndex})" id="quiz-btn-${qIndex}-${optIndex}">
                    ${App.escapeHTML(opt)}
                  </button>
                `).join('')}
              </div>
              <div class="quiz-explanation" id="quiz-exp-${qIndex}" style="display: none;">
                <strong>Explanation:</strong> ${App.escapeHTML(q.explanation)}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  function selectQuizOption(qIndex, selectedOptIndex) {
    if (!currentQuizData || quizUserAnswers[qIndex] !== undefined) return;

    quizUserAnswers[qIndex] = selectedOptIndex;
    const q = currentQuizData.questions[qIndex];
    const isCorrect = (selectedOptIndex === q.correct_answer);

    for (let i = 0; i < q.options.length; i++) {
      const btn = document.getElementById(`quiz-btn-${qIndex}-${i}`);
      if (btn) {
        btn.disabled = true;
        if (i === q.correct_answer) {
          btn.classList.add('correct');
        } else if (i === selectedOptIndex && !isCorrect) {
          btn.classList.add('incorrect');
        }
      }
    }

    const expEl = document.getElementById(`quiz-exp-${qIndex}`);
    if (expEl) expEl.style.display = 'block';

    let correctCount = 0;
    Object.keys(quizUserAnswers).forEach(idx => {
      const question = currentQuizData.questions[parseInt(idx)];
      if (question && quizUserAnswers[idx] === question.correct_answer) {
        correctCount++;
      }
    });

    const scoreEl = document.getElementById('quiz-live-score');
    if (scoreEl) {
      scoreEl.textContent = `Score: ${correctCount} / ${currentQuizData.questions.length}`;
      if (correctCount > 0) {
        scoreEl.style.background = 'var(--success-subtle)';
        scoreEl.style.color = 'var(--success)';
      }
    }

    if (isCorrect) {
      App.showToast('Correct! Great job! 🎉', 'success');
    } else {
      App.showToast('Not quite! Check the explanation below.', 'warning');
    }
  }

  // --- 4. AI Diagram & Visual Breakdown ---
  async function handleDiagramSubmit(e) {
    e.preventDefault();
    const topic = document.getElementById('ai-diagram-topic').value.trim();
    if (!topic) return;

    const btn = document.getElementById('btn-diagram-submit');
    const resultBox = document.getElementById('ai-diagram-result');
    btn.disabled = true;
    btn.textContent = 'Generating Visual Map...';

    // Generate smart structured visual concept flowchart
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = '💡 Generate Visual Map';
      resultBox.innerHTML = `
        <div class="card" style="margin-top: 20px; animation: fadeIn 0.3s ease;">
          <h3 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 6px;">🗺️ Concept Flow: ${App.escapeHTML(topic)}</h3>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 20px;">Visual step-by-step mental model</p>
          
          <div class="concept-flowchart">
            <div class="flow-step">
              <span class="flow-num">1</span>
              <div>
                <strong>Input / Initialization</strong>
                <p>System triggers operation with parameters & environmental state for ${App.escapeHTML(topic)}.</p>
              </div>
            </div>
            <div class="flow-arrow">↓</div>
            <div class="flow-step">
              <span class="flow-num">2</span>
              <div>
                <strong>Core Processing & Verification</strong>
                <p>Logic evaluates protocol constraints, validates inputs, and resolves routing / data states.</p>
              </div>
            </div>
            <div class="flow-arrow">↓</div>
            <div class="flow-step">
              <span class="flow-num">3</span>
              <div>
                <strong>State Transition & Output</strong>
                <p>Produces verified response, updates persistent cache/records, and emits confirmation packet.</p>
              </div>
            </div>
          </div>
        </div>
      `;
    }, 500);
  }

  // --- 5. AI Viva Preparation ---
  async function handleVivaSubmit(e) {
    e.preventDefault();
    const topic = document.getElementById('ai-viva-topic').value.trim();
    if (!topic) return;

    const btn = document.getElementById('btn-viva-submit');
    const resultBox = document.getElementById('ai-viva-result');
    btn.disabled = true;
    btn.textContent = 'Preparing Viva Questions...';

    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = '🎤 Generate Viva Q&A';
      resultBox.innerHTML = `
        <div class="card" style="margin-top: 20px; animation: fadeIn 0.3s ease;">
          <h3 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 4px;">🎓 Viva Voce Prep: ${App.escapeHTML(topic)}</h3>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 20px;">Top questions professors ask during project evaluations</p>

          <div style="display: flex; flex-direction: column; gap: 16px;">
            <div style="padding: 16px; background: var(--bg-muted); border-radius: var(--radius-md);">
              <div style="font-weight: 700; color: var(--primary-700); margin-bottom: 4px;">Q1: What is the fundamental problem ${App.escapeHTML(topic)} solves?</div>
              <p style="font-size: 0.92rem; color: var(--text-main);"><strong>Model Answer:</strong> Explain the bottleneck or vulnerability that exists without it, emphasizing fault-tolerance, efficiency, or abstraction.</p>
            </div>
            <div style="padding: 16px; background: var(--bg-muted); border-radius: var(--radius-md);">
              <div style="font-weight: 700; color: var(--primary-700); margin-bottom: 4px;">Q2: What happens in an edge case or failure scenario?</div>
              <p style="font-size: 0.92rem; color: var(--text-main);"><strong>Model Answer:</strong> Detail how timeouts, packet drops, or retries are handled gracefully to prevent cascading failure.</p>
            </div>
            <div style="padding: 16px; background: var(--bg-muted); border-radius: var(--radius-md);">
              <div style="font-weight: 700; color: var(--primary-700); margin-bottom: 4px;">Q3: How would you scale this in production?</div>
              <p style="font-size: 0.92rem; color: var(--text-main);"><strong>Model Answer:</strong> Propose horizontal replication, caching strategies, or asynchronous queuing.</p>
            </div>
          </div>
        </div>
      `;
    }, 500);
  }

  function initListeners() {
    // Feature Cards Clicks
    document.querySelectorAll('.ai-feature-card').forEach(card => {
      card.addEventListener('click', () => {
        const tab = card.dataset.tab;
        switchTab(tab);
      });
    });

    // Time pills for planner
    document.querySelectorAll('.ai-time-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        setPlannerTime(parseInt(pill.dataset.mins));
      });
    });

    // Forms
    document.getElementById('form-ai-planner')?.addEventListener('submit', handleGeneratePlan);
    document.getElementById('form-ai-explain')?.addEventListener('submit', handleExplainSubmit);
    document.getElementById('form-ai-quiz')?.addEventListener('submit', handleQuizSubmit);
    document.getElementById('form-ai-diagram')?.addEventListener('submit', handleDiagramSubmit);
    document.getElementById('form-ai-viva')?.addEventListener('submit', handleVivaSubmit);
  }

  return {
    load,
    switchTab,
    convertBlockToTask,
    selectQuizOption,
    initListeners
  };
})();
