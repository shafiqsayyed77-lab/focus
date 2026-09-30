// FocusFlow Router & View Controller
const Router = (() => {
  const routes = {
    dashboard: {
      title: 'Student Dashboard',
      init: () => { if (typeof Dashboard !== 'undefined') Dashboard.load(); }
    },
    subjects: {
      title: 'Academic Roadmap & Subjects',
      init: () => {
        if (typeof SubjectsTasks !== 'undefined') {
          SubjectsTasks.closeSubjectDetail();
          SubjectsTasks.loadSubjects();
        }
      }
    },
    roadmap: {
      title: 'Academic Roadmap & Subjects',
      init: () => {
        if (typeof SubjectsTasks !== 'undefined') {
          SubjectsTasks.closeSubjectDetail();
          SubjectsTasks.loadSubjects();
        }
      }
    },
    planner: {
      title: 'Daily Planner & Calendar',
      init: () => { if (typeof Planner !== 'undefined') Planner.load(); }
    },
    tasks: {
      title: 'Daily Planner & Calendar',
      init: () => { if (typeof Planner !== 'undefined') Planner.load(); }
    },
    exams: {
      title: 'Exam Preparation Mode',
      init: () => { if (typeof Exams !== 'undefined') Exams.load(); }
    },
    revision: {
      title: 'Smart Revision Engine',
      init: () => { if (typeof Revision !== 'undefined') Revision.load(); }
    },
    mocktest: {
      title: 'Subject Examination & Mock Tests',
      init: () => { if (typeof MockTest !== 'undefined') MockTest.init(); }
    },
    timer: {
      title: 'Flow-State Focus Timer',
      init: () => { if (typeof Timer !== 'undefined') Timer.load(); }
    },
    ai: {
      title: 'AI Academic Coach',
      init: () => { if (typeof AIStudy !== 'undefined') AIStudy.load(); }
    },
    analytics: {
      title: 'Analytics & Achievements',
      init: () => { if (typeof Progress !== 'undefined') Progress.load(); }
    },
    progress: {
      title: 'Analytics & Achievements',
      init: () => { if (typeof Progress !== 'undefined') Progress.load(); }
    },
    resources: {
      title: 'Resources & Notes Library',
      init: () => { if (typeof Resources !== 'undefined') Resources.load(); }
    },
    profile: {
      title: 'Academic Profile',
      init: () => { if (typeof Settings !== 'undefined') Settings.loadProfile(); }
    },
    settings: {
      title: 'Application Preferences',
      init: () => { if (typeof Settings !== 'undefined') Settings.loadUserSettings(); }
    }
  };

  let currentRoute = 'dashboard';

  function navigate(routeName) {
    if (!routes[routeName]) {
      routeName = 'dashboard';
    }

    currentRoute = routeName;
    window.location.hash = routeName;

    // Update Topbar Title
    const titleEl = document.getElementById('current-page-title');
    if (titleEl) {
      titleEl.textContent = routes[routeName].title;
    }

    // Toggle View Sections
    const views = document.querySelectorAll('.view-section');
    views.forEach(v => {
      v.classList.remove('active');
      if (v.id === `view-${routeName}` || (routeName === 'tasks' && v.id === 'view-planner') || (routeName === 'progress' && v.id === 'view-analytics') || (routeName === 'roadmap' && v.id === 'view-subjects')) {
        v.classList.add('active');
      }
    });

    // Update Nav Link Active States
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
      item.classList.remove('active');
      const r = item.dataset.route;
      if (r === routeName || (routeName === 'tasks' && r === 'planner') || (routeName === 'progress' && r === 'analytics') || (routeName === 'roadmap' && r === 'subjects')) {
        item.classList.add('active');
      }
    });

    // Update Mobile Bottom Nav States
    document.querySelectorAll('.mobile-bottom-nav-item').forEach(item => {
      item.classList.remove('active');
      const r = item.dataset.route;
      if (r === routeName || (routeName === 'tasks' && r === 'planner') || (routeName === 'progress' && r === 'analytics') || (routeName === 'roadmap' && r === 'subjects')) {
        item.classList.add('active');
      }
    });

    // Close Mobile Drawer
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.remove('mobile-open');

    // Run view initializer if authenticated
    try {
      if (API.getToken()) {
        routes[routeName].init();
      }
    } catch (e) {
      console.warn(`View init failed for ${routeName}:`, e);
    }
  }

  function getCurrentRoute() {
    return currentRoute;
  }

  function init() {
    // Nav button clicks
    document.querySelectorAll('.nav-item[data-route]').forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const route = item.dataset.route;
        navigate(route);
      });
    });

    // Hash change handler
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.replace('#', '');
      if (hash && routes[hash] && hash !== currentRoute) {
        navigate(hash);
      }
    });

    // Mobile sidebar toggle
    const toggleBtn = document.getElementById('mobile-toggle-btn');
    const sidebar = document.getElementById('sidebar');
    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('mobile-open');
      });
    }

    // Initial route check
    const initialHash = window.location.hash.replace('#', '');
    if (initialHash && routes[initialHash]) {
      navigate(initialHash);
    } else {
      navigate('dashboard');
    }
  }

  return {
    navigate,
    getCurrentRoute,
    init
  };
})();
