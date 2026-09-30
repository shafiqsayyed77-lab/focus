import sqlite3
from contextlib import contextmanager
from app.config import DATABASE_PATH

def get_db_connection() -> sqlite3.Connection:
    """Creates a new SQLite database connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    """Context manager for safe database transactions."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initializes SQLite schema for users, subjects, tasks, focus sessions, and settings."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
        """)

        # 2. Subjects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#7C3AED',
                icon TEXT NOT NULL DEFAULT 'book',
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 3. Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject_id INTEGER,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High')),
                deadline TEXT,
                is_completed INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
            );
        """)

        # 4. Focus Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject_id INTEGER,
                task_id INTEGER,
                duration_minutes INTEGER NOT NULL,
                completed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
            );
        """)

        # 5. User Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                theme TEXT NOT NULL DEFAULT 'light' CHECK (theme IN ('light', 'dark')),
                default_focus_duration INTEGER NOT NULL DEFAULT 25,
                default_break_duration INTEGER NOT NULL DEFAULT 5,
                notifications_enabled INTEGER NOT NULL DEFAULT 1,
                sound_enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 6. Topics table (Subject Mini Learning Space)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                is_completed INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 7. Mock Tests table (Persistent Examination Scores)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject_id INTEGER,
                subject_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                percentage INTEGER NOT NULL,
                duration_minutes INTEGER NOT NULL DEFAULT 0,
                topic_names TEXT,
                weak_topics TEXT,
                difficulty TEXT DEFAULT 'Medium',
                details TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
            );
        """)

        # 8. Exams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                target_score INTEGER NOT NULL DEFAULT 90,
                notes TEXT DEFAULT '',
                prep_roadmap TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
        """)

        # 9. Resources & Notes Library table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject_id INTEGER,
                topic_id INTEGER,
                title TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'note',
                content TEXT NOT NULL,
                url TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL
            );
        """)

        # Performance Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subjects_user ON subjects(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_subject ON tasks(subject_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_focus_sessions_user ON focus_sessions(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_focus_sessions_date ON focus_sessions(completed_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topics_subject ON topics(subject_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topics_user ON topics(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mock_tests_user ON mock_tests(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mock_tests_subject ON mock_tests(subject_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exams_user ON exams(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_user ON resources(user_id);")

        run_migrations(cursor)
        conn.commit()
        seed_demo_account(cursor, conn)

def run_migrations(cursor):
    """Safely runs column additions if upgrading from earlier database schemas."""
    def column_exists(table, col):
        cursor.execute(f"PRAGMA table_info({table});")
        cols = [r["name"] for r in cursor.fetchall()]
        return col in cols

    # users migrations
    user_cols = [
        ("course", "TEXT DEFAULT ''"),
        ("institution", "TEXT DEFAULT ''"),
        ("semester", "TEXT DEFAULT ''"),
        ("study_goal_minutes", "INTEGER DEFAULT 60"),
        ("onboarding_completed", "INTEGER DEFAULT 0")
    ]
    for col, col_def in user_cols:
        if not column_exists("users", col):
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def};")

    # topics migrations
    topic_cols = [
        ("chapter", "TEXT DEFAULT 'General'"),
        ("status", "TEXT DEFAULT 'not_started'"),
        ("priority", "TEXT DEFAULT 'Medium'"),
        ("order_index", "INTEGER DEFAULT 0"),
        ("notes", "TEXT DEFAULT ''"),
        ("resources", "TEXT DEFAULT ''"),
        ("is_weak", "INTEGER DEFAULT 0"),
        ("last_studied_at", "TEXT"),
        ("needs_revision", "INTEGER DEFAULT 0"),
        ("revision_reason", "TEXT DEFAULT ''"),
        ("last_mock_score", "INTEGER")
    ]
    for col, col_def in topic_cols:
        if not column_exists("topics", col):
            cursor.execute(f"ALTER TABLE topics ADD COLUMN {col} {col_def};")

    # tasks migrations
    task_cols = [
        ("item_type", "TEXT DEFAULT 'task'"),
        ("estimated_minutes", "INTEGER DEFAULT 30"),
        ("topic_id", "INTEGER"),
        ("planned_date", "TEXT")
    ]
    for col, col_def in task_cols:
        if not column_exists("tasks", col):
            cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col} {col_def};")

    # focus_sessions migrations
    if not column_exists("focus_sessions", "topic_id"):
        cursor.execute("ALTER TABLE focus_sessions ADD COLUMN topic_id INTEGER;")

    # mock_tests migrations
    mock_cols = [
        ("topic_names", "TEXT"),
        ("weak_topics", "TEXT"),
        ("difficulty", "TEXT DEFAULT 'Medium'"),
        ("details", "TEXT")
    ]
    for col, col_def in mock_cols:
        if not column_exists("mock_tests", col):
            cursor.execute(f"ALTER TABLE mock_tests ADD COLUMN {col} {col_def};")

DEFAULT_SUBJECT_TOPICS = {
    "network": [
        ("Module 1: Foundations", "IPv4 Addressing & Subnetting", "High"),
        ("Module 1: Foundations", "Address Resolution Protocol (ARP)", "Medium"),
        ("Module 2: Network Layer", "IPv6 Architecture & Headers", "Medium"),
        ("Module 2: Network Layer", "Routing Protocols (RIP, OSPF, BGP)", "High"),
        ("Module 3: Transport Layer", "TCP Flow & Congestion Control", "High")
    ],
    "database": [
        ("Module 1: Modeling", "Entity-Relationship (ER) Modeling", "Medium"),
        ("Module 1: Modeling", "Relational Algebra & Schema Design", "High"),
        ("Module 2: SQL & Optimization", "SQL Joins, Grouping & Subqueries", "High"),
        ("Module 3: Normalization", "Database Normalization (1NF to 3NF)", "High"),
        ("Module 4: Transactions", "ACID Transactions & Concurrency", "Medium")
    ],
    "operat": [
        ("Unit 1: Scheduling", "CPU Scheduling & Priority Queues", "High"),
        ("Unit 1: Scheduling", "Processes, Threads & Fork Mechanism", "Medium"),
        ("Unit 2: Synchronization", "Deadlocks, Mutex & Semaphores", "High"),
        ("Unit 3: Memory", "Virtual Memory, Paging & TLB", "High"),
        ("Unit 4: Storage", "File Systems & I/O Management", "Low")
    ],
    "software": [
        ("Phase 1: Process", "Agile Methodology & Scrum Sprints", "Medium"),
        ("Phase 2: Architecture", "Creational & Behavioral Design Patterns", "High"),
        ("Phase 2: Architecture", "UML Class & Sequence Diagrams", "Medium"),
        ("Phase 3: Quality", "Unit Testing & Test-Driven Development (TDD)", "High"),
        ("Phase 4: Operations", "CI/CD Pipelines & DevOps", "Medium")
    ]
}

def seed_starter_topics_for_subject(cursor, subject_id: int, user_id: int, subject_name: str):
    """Populates realistic syllabus topics for a subject if requested."""
    cursor.execute("SELECT COUNT(*) as count FROM topics WHERE subject_id = ?", (subject_id,))
    if cursor.fetchone()["count"] > 0:
        return

    name_lower = subject_name.lower()
    selected = None
    for key, topic_list in DEFAULT_SUBJECT_TOPICS.items():
        if key in name_lower:
            selected = topic_list
            break

    if not selected:
        selected = [
            ("Chapter 1: Foundations", f"Introduction & Core Concepts of {subject_name}", "High"),
            ("Chapter 2: Architecture", "Key Theoretical Models & Frameworks", "Medium"),
            ("Chapter 3: Application", "Practical Implementation & Problem Sets", "High"),
            ("Chapter 4: Advanced", "Case Studies & System Optimization", "Medium"),
            ("Chapter 5: Exam Review", "Comprehensive Review & Mock Problems", "High")
        ]

    for idx, item in enumerate(selected):
        chapter, title, priority = item
        cursor.execute(
            """
            INSERT INTO topics (subject_id, user_id, title, chapter, priority, order_index, is_completed, status)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'not_started')
            """,
            (subject_id, user_id, title, chapter, priority, idx)
        )

def seed_demo_account(cursor, conn):
    """Seeds a rich demonstration student account so the user can immediately experience the UI with data."""
    import bcrypt
    from datetime import datetime, timedelta

    demo_email = "alex.student@focusflow.app"
    salt = bcrypt.gensalt(rounds=12)
    pwd_hash = bcrypt.hashpw("password123".encode("utf-8"), salt).decode("utf-8")

    cursor.execute("SELECT id FROM users WHERE email = ?", (demo_email,))
    existing = cursor.fetchone()
    if existing:
        user_id = existing["id"]
        cursor.execute(
            """
            UPDATE users SET
                course = COALESCE(NULLIF(course, ''), 'BSc IT (Information Technology)'),
                institution = COALESCE(NULLIF(institution, ''), 'Metropolitan University'),
                semester = COALESCE(NULLIF(semester, ''), 'Semester 4'),
                study_goal_minutes = 60,
                onboarding_completed = 1
            WHERE id = ?
            """,
            (user_id,)
        )
    else:
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, course, institution, semester, study_goal_minutes, onboarding_completed)
            VALUES (?, ?, ?, 'BSc IT (Information Technology)', 'Metropolitan University', 'Semester 4', 60, 1)
            """,
            ("Alex Rivera", demo_email, pwd_hash)
        )
        user_id = cursor.lastrowid

        cursor.execute(
            "INSERT OR IGNORE INTO user_settings (user_id, theme, default_focus_duration, default_break_duration) VALUES (?, 'light', 25, 5)",
            (user_id,)
        )

    # Ensure demo subjects exist
    cursor.execute("SELECT COUNT(*) as cnt FROM subjects WHERE user_id = ?", (user_id,))
    if cursor.fetchone()["cnt"] == 0:
        demo_subs = [
            ("Computer Networks", "#6C3BFF", "network", "Protocols, routing, IP addressing & architecture"),
            ("Database Systems", "#8B5CF6", "database", "Relational algebra, SQL, normalization & ACID transactions"),
            ("Operating Systems", "#FF9F43", "code", "Processes, memory management, threads & file systems"),
            ("Software Engineering", "#FF6B6B", "book", "Design patterns, Agile methodologies & UML diagrams")
        ]
        for s_name, s_color, s_icon, s_desc in demo_subs:
            cursor.execute(
                "INSERT INTO subjects (user_id, name, color, icon, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, s_name, s_color, s_icon, s_desc)
            )
            sub_id = cursor.lastrowid
            seed_starter_topics_for_subject(cursor, sub_id, user_id, s_name)

        # Mark 3 topics completed for Computer Networks & 1 weak topic
        cursor.execute("SELECT id FROM subjects WHERE user_id = ? AND name = 'Computer Networks'", (user_id,))
        cn_row = cursor.fetchone()
        if cn_row:
            cn_id = cn_row["id"]
            cursor.execute("SELECT id FROM topics WHERE subject_id = ? ORDER BY id ASC LIMIT 3", (cn_id,))
            top_ids = [r["id"] for r in cursor.fetchall()]
            for t_id in top_ids:
                cursor.execute("UPDATE topics SET is_completed = 1, status = 'completed' WHERE id = ?", (t_id,))

            # Flag weak topic needing revision
            cursor.execute(
                """
                UPDATE topics SET
                    is_weak = 1,
                    needs_revision = 1,
                    revision_reason = 'Mock Test Accuracy: 40% on Subnet Masks',
                    last_mock_score = 40
                WHERE subject_id = ? AND title LIKE '%IPv4%'
                """,
                (cn_id,)
            )

            # Add tasks with item_type
            cursor.execute(
                "INSERT INTO tasks (user_id, subject_id, title, priority, item_type, estimated_minutes, is_completed) VALUES (?, ?, ?, ?, 'revision', 45, ?)",
                (user_id, cn_id, "Revise IPv4 vs IPv6 headers & subnet masks", "High", 0)
            )
            cursor.execute(
                "INSERT INTO tasks (user_id, subject_id, title, priority, item_type, estimated_minutes, is_completed) VALUES (?, ?, ?, ?, 'assignment', 60, ?)",
                (user_id, cn_id, "Practice ARP packet analysis in Wireshark", "Medium", 1)
            )
            cursor.execute(
                "INSERT INTO tasks (user_id, subject_id, title, priority, item_type, estimated_minutes, is_completed) VALUES (?, ?, ?, ?, 'task', 30, ?)",
                (user_id, cn_id, "Study Dijkstra Shortest Path algorithm for routing", "High", 0)
            )

            # Record focus sessions
            today = datetime.now()
            cursor.execute(
                "INSERT INTO focus_sessions (user_id, subject_id, duration_minutes, completed_at) VALUES (?, ?, 42, ?)",
                (user_id, cn_id, today.strftime("%Y-%m-%d %H:%M:%S"))
            )
            for i in range(1, 7):
                past_date = today - timedelta(days=i)
                cursor.execute(
                    "INSERT INTO focus_sessions (user_id, subject_id, duration_minutes, completed_at) VALUES (?, ?, 30, ?)",
                    (user_id, cn_id, past_date.strftime("%Y-%m-%d 14:00:00"))
                )

            # Record Mock Test score
            cursor.execute(
                """
                INSERT INTO mock_tests (user_id, subject_id, subject_name, score, total_questions, percentage, duration_minutes, topic_names, weak_topics, difficulty)
                VALUES (?, ?, ?, 17, 20, 85, 14, '["IPv4 Addressing & Subnetting", "Address Resolution Protocol (ARP)", "IPv6 Architecture & Headers"]', '["IPv4 Addressing & Subnetting"]', 'Medium')
                """,
                (user_id, cn_id, "Computer Networks")
            )

            # Add upcoming exam
            exam_date = (today + timedelta(days=12)).strftime("%Y-%m-%d")
            cursor.execute(
                """
                INSERT INTO exams (user_id, subject_id, title, exam_date, target_score, notes)
                VALUES (?, ?, 'Computer Networks Final University Exam', ?, 95, 'Covers Modules 1 to 4 with focus on routing and addressing.')
                """,
                (user_id, cn_id, exam_date)
            )

            # Add sample resource / note
            cursor.execute(
                """
                INSERT INTO resources (user_id, subject_id, title, type, content, tags)
                VALUES (?, ?, 'IPv4 Subnetting Cheatsheet & CIDR Table', 'formula', 'CIDR /24 = 255.255.255.0 (256 IPs)\nCIDR /25 = 255.255.255.128 (128 IPs)\nCIDR /26 = 255.255.255.192 (64 IPs)\nCIDR /27 = 255.255.255.224 (32 IPs)', 'networking, subnetting, formulas')
                """,
                (user_id, cn_id)
            )

            conn.commit()


