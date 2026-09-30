// FocusFlow Centralized API Client Layer
const API = (() => {
  const TOKEN_KEY = 'focusflow_token';

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setToken(token) {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }

  async function request(endpoint, options = {}) {
    const token = getToken();
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(endpoint, {
        ...options,
        headers
      });

      if (response.status === 204) {
        return null;
      }

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        if (response.status === 401) {
          setToken(null);
          window.dispatchEvent(new CustomEvent('focusflow:unauthorized'));
        }
        const errorMsg = (data && data.detail) || response.statusText || 'An unexpected error occurred.';
        throw new Error(errorMsg);
      }

      return data;
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  }

  return {
    getToken,
    setToken,

    // Authentication
    signup: (name, email, password, course = '', institution = '', semester = '') => request('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ name, email, password, course, institution, semester })
    }),
    login: (email, password) => request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    }),
    getMe: () => request('/api/auth/me'),

    // Academic Profile & Onboarding
    getProfile: () => request('/api/user/profile'),
    updateProfile: (profileData) => request('/api/user/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData)
    }),
    completeOnboarding: (onboardingData) => request('/api/user/onboarding', {
      method: 'POST',
      body: JSON.stringify(onboardingData)
    }),
    changePassword: (current_password, new_password) => request('/api/user/password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password })
    }),
    getSettings: () => request('/api/user/settings'),
    updateSettings: (settings) => request('/api/user/settings', {
      method: 'PUT',
      body: JSON.stringify(settings)
    }),

    // Subjects & Roadmap
    getSubjects: () => request('/api/subjects'),
    getSubjectDetail: (id) => request(`/api/subjects/${id}`),
    createSubject: (subject) => request('/api/subjects', {
      method: 'POST',
      body: JSON.stringify(subject)
    }),
    updateSubject: (id, subject) => request(`/api/subjects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(subject)
    }),
    deleteSubject: (id) => request(`/api/subjects/${id}`, {
      method: 'DELETE'
    }),
    seedAITopics: (subjectId) => request(`/api/subjects/${subjectId}/seed-ai-topics`, {
      method: 'POST'
    }),

    // Topics & Chapters (Mini Learning Spaces)
    getSubjectTopics: (subjectId) => request(`/api/subjects/${subjectId}/topics`),
    addSubjectTopic: (subjectId, topicData) => request(`/api/subjects/${subjectId}/topics`, {
      method: 'POST',
      body: JSON.stringify(typeof topicData === 'string' ? { title: topicData } : topicData)
    }),
    updateTopic: (topicId, data) => request(`/api/subjects/topics/${topicId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    }),
    toggleTopic: (topicId) => request(`/api/subjects/topics/${topicId}/toggle`, {
      method: 'PATCH'
    }),
    deleteTopic: (topicId) => request(`/api/subjects/topics/${topicId}`, {
      method: 'DELETE'
    }),
    reorderTopics: (subjectId, topicIds) => request(`/api/subjects/${subjectId}/topics/reorder`, {
      method: 'PUT',
      body: JSON.stringify({ topic_ids: topicIds })
    }),

    // Tasks & Daily Planner
    getTasks: (params = {}) => {
      const query = new URLSearchParams();
      if (params.subject_id) query.append('subject_id', params.subject_id);
      if (params.status_filter) query.append('status_filter', params.status_filter);
      if (params.priority) query.append('priority', params.priority);
      if (params.item_type) query.append('item_type', params.item_type);
      if (params.planned_date) query.append('planned_date', params.planned_date);
      const qStr = query.toString() ? `?${query.toString()}` : '';
      return request(`/api/tasks${qStr}`);
    },
    createTask: (task) => request('/api/tasks', {
      method: 'POST',
      body: JSON.stringify(task)
    }),
    updateTask: (id, task) => request(`/api/tasks/${id}`, {
      method: 'PUT',
      body: JSON.stringify(task)
    }),
    toggleTask: (id) => request(`/api/tasks/${id}/toggle`, {
      method: 'PATCH'
    }),
    deleteTask: (id) => request(`/api/tasks/${id}`, {
      method: 'DELETE'
    }),
    planMyDay: (availableMinutes = 120) => request('/api/tasks/plan-my-day', {
      method: 'POST',
      body: JSON.stringify({ available_minutes: availableMinutes })
    }),

    // Exam Preparation Mode
    getExams: () => request('/api/exams'),
    getExamDetail: (id) => request(`/api/exams/${id}`),
    createExam: (exam) => request('/api/exams', {
      method: 'POST',
      body: JSON.stringify(exam)
    }),
    updateExam: (id, exam) => request(`/api/exams/${id}`, {
      method: 'PUT',
      body: JSON.stringify(exam)
    }),
    deleteExam: (id) => request(`/api/exams/${id}`, {
      method: 'DELETE'
    }),
    regenerateExamRoadmap: (id) => request(`/api/exams/${id}/regenerate-roadmap`, {
      method: 'POST'
    }),

    // Smart Revision Engine
    getRevisionQueue: () => request('/api/revision'),
    addTopicToRevision: (topicId, reason = 'Student Flagged') => request(`/api/revision/add/${topicId}`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    }),
    markTopicRevised: (topicId) => request(`/api/revision/mark-revised/${topicId}`, {
      method: 'POST'
    }),

    // Subject Mock Test System
    getEligibleMockTopics: (subjectId) => request(`/api/mocktests/eligible-topics/${subjectId}`),
    generateMockQuestions: (subjectId, topicTitles, difficulty = 'Medium', numQuestions = 5) => request('/api/mocktests/generate-questions', {
      method: 'POST',
      body: JSON.stringify({ subject_id: subjectId, topic_titles: topicTitles, difficulty, num_questions: numQuestions })
    }),
    recordMockTest: (data) => request('/api/mocktests', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
    getRecentMockTests: (limit = 10) => request(`/api/mocktests/recent?limit=${limit}`),

    // Focus Sessions
    getSessions: () => request('/api/sessions'),
    recordSession: (duration_minutes, subject_id = null, topic_id = null, task_id = null) => request('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ duration_minutes, subject_id, topic_id, task_id })
    }),

    // Resources & Notes Library
    getResources: (params = {}) => {
      const query = new URLSearchParams();
      if (params.subject_id) query.append('subject_id', params.subject_id);
      if (params.topic_id) query.append('topic_id', params.topic_id);
      if (params.type) query.append('type', params.type);
      const qStr = query.toString() ? `?${query.toString()}` : '';
      return request(`/api/resources${qStr}`);
    },
    createResource: (res) => request('/api/resources', {
      method: 'POST',
      body: JSON.stringify(res)
    }),
    updateResource: (id, res) => request(`/api/resources/${id}`, {
      method: 'PUT',
      body: JSON.stringify(res)
    }),
    deleteResource: (id) => request(`/api/resources/${id}`, {
      method: 'DELETE'
    }),

    // Global Search & Quick Capture
    globalSearch: (query) => request(`/api/search?q=${encodeURIComponent(query)}`),
    quickCapture: (itemType, data) => request('/api/quick-capture', {
      method: 'POST',
      body: JSON.stringify({ item_type: itemType, data })
    }),

    // Stats, Dashboard & Analytics
    getDashboardStats: () => request('/api/stats/dashboard'),
    getProgressStats: () => request('/api/stats/analytics'),
    getAnalyticsStats: () => request('/api/stats/analytics'),

    // AI Study Coach
    generatePlan: (subject, topics, available_time, energy_level, priority) => request('/api/ai/planner', {
      method: 'POST',
      body: JSON.stringify({ subject, topics, available_time, energy_level, priority })
    }),
    explainTopic: (topic, subject) => request('/api/ai/explain', {
      method: 'POST',
      body: JSON.stringify({ topic, subject })
    }),
    generateQuiz: (subject, topic, num_questions = 5) => request('/api/ai/quiz', {
      method: 'POST',
      body: JSON.stringify({ subject, topic, num_questions })
    }),
    generateDiagram: (topic) => request('/api/ai/diagram', {
      method: 'POST',
      body: JSON.stringify({ topic })
    }),
    generateViva: (topic) => request('/api/ai/viva', {
      method: 'POST',
      body: JSON.stringify({ topic })
    }),
    analyzeWeakness: (subject, score, weak_topics) => request('/api/ai/weakness', {
      method: 'POST',
      body: JSON.stringify({ subject, score, weak_topics })
    }),
    getAIRecommendation: () => request('/api/ai/recommend-next')
  };
})();
