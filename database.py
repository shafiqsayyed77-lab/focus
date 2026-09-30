import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "focusflow.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        streak INTEGER DEFAULT 5,
        longest_streak INTEGER DEFAULT 5,
        study_minutes_today INTEGER DEFAULT 165,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Ensure longest_streak column exists in case users table was created previously
    cursor.execute("PRAGMA table_info(users);")
    columns = [col["name"] for col in cursor.fetchall()]
    if "longest_streak" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN longest_streak INTEGER DEFAULT 5;")

    # Subjects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        code TEXT,
        color TEXT DEFAULT '#6366f1',
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # Tasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT NOT NULL DEFAULT 'Medium', -- 'Low', 'Medium', 'High'
        due_date TEXT, -- YYYY-MM-DD
        completed INTEGER DEFAULT 0, -- 0 = pending, 1 = completed
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
    );
    """)

    # Focus Sessions table (Module 5 & 6)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS focus_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_id INTEGER,
        subject_id INTEGER,
        duration_minutes INTEGER NOT NULL,
        session_type TEXT DEFAULT 'focus', -- 'focus' or 'break'
        session_date TEXT NOT NULL, -- YYYY-MM-DD
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE SET NULL,
        FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE SET NULL
    );
    """)

    # User Settings table (Module 7)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        theme TEXT DEFAULT 'light', -- 'light' or 'dark'
        default_focus_duration INTEGER DEFAULT 25,
        default_break_duration INTEGER DEFAULT 5,
        notifications_enabled INTEGER DEFAULT 1,
        sound_enabled INTEGER DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()
    seed_demo_user()

def calculate_user_streak(user_id: int) -> Dict[str, int]:
    """
    Calculates current streak and longest streak based on distinct dates in focus_sessions:
    - At least 1 focus session in a day counts as a study day.
    - Multiple sessions in the same day count as 1 streak day.
    - Consecutive study days increase the streak.
    - A missed day breaks the current streak.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT session_date
        FROM focus_sessions
        WHERE user_id = ? AND session_type = 'focus' AND duration_minutes > 0
        ORDER BY session_date DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"current_streak": 0, "longest_streak": 0}

    # Parse distinct dates in descending order
    dates = []
    for r in rows:
        try:
            d = datetime.strptime(r["session_date"], "%Y-%m-%d").date()
            dates.append(d)
        except Exception:
            continue

    if not dates:
        return {"current_streak": 0, "longest_streak": 0}

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Current streak calculation
    current_streak = 0
    # Streak is active if the most recent session is today or yesterday
    if dates[0] == today or dates[0] == yesterday:
        current_streak = 1
        expected_prev = dates[0] - timedelta(days=1)
        for d in dates[1:]:
            if d == expected_prev:
                current_streak += 1
                expected_prev = d - timedelta(days=1)
            else:
                break
    else:
        current_streak = 0

    # Longest streak calculation across all time
    # Sort chronological ascending
    sorted_dates = sorted(dates)
    longest_streak = 1 if sorted_dates else 0
    run = 1
    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] == sorted_dates[i-1] + timedelta(days=1):
            run += 1
            if run > longest_streak:
                longest_streak = run
        else:
            run = 1

    longest_streak = max(longest_streak, current_streak)

    # Sync into users table
    conn = get_db()
    conn.execute("UPDATE users SET streak = ?, longest_streak = ? WHERE id = ?", (current_streak, longest_streak, user_id))
    conn.commit()
    conn.close()

    return {"current_streak": current_streak, "longest_streak": longest_streak}

def get_user_progress(user_id: int) -> Dict[str, Any]:
    """Retrieve full progress metrics, weekly chart data, and recent sessions."""
    conn = get_db()
    cursor = conn.cursor()

    # Recalculate streak
    streaks = calculate_user_streak(user_id)

    today_str = date.today().isoformat()

    # Today's study time
    cursor.execute("""
        SELECT COALESCE(SUM(duration_minutes), 0) as mins
        FROM focus_sessions
        WHERE user_id = ? AND session_type = 'focus' AND session_date = ?
    """, (user_id, today_str))
    today_mins = cursor.fetchone()["mins"]

    # Total study time
    cursor.execute("""
        SELECT COALESCE(SUM(duration_minutes), 0) as mins
        FROM focus_sessions
        WHERE user_id = ? AND session_type = 'focus'
    """, (user_id,))
    total_mins = cursor.fetchone()["mins"]

    # Completed tasks count
    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE user_id = ? AND completed = 1", (user_id,))
    completed_tasks = cursor.fetchone()["count"]

    # Total completed focus sessions count
    cursor.execute("SELECT COUNT(*) as count FROM focus_sessions WHERE user_id = ? AND session_type = 'focus'", (user_id,))
    completed_sessions = cursor.fetchone()["count"]

    # Weekly chart data (last 7 days)
    weekly_chart = []
    for i in range(6, -1, -1):
        target_day = date.today() - timedelta(days=i)
        day_str = target_day.isoformat()
        day_label = target_day.strftime("%a") # Mon, Tue, etc.
        date_short = target_day.strftime("%b %d")

        cursor.execute("""
            SELECT COALESCE(SUM(duration_minutes), 0) as mins
            FROM focus_sessions
            WHERE user_id = ? AND session_type = 'focus' AND session_date = ?
        """, (user_id, day_str))
        day_mins = cursor.fetchone()["mins"]

        weekly_chart.append({
            "day": day_label,
            "date": day_str,
            "date_short": date_short,
            "minutes": day_mins,
            "formatted": f"{day_mins // 60}h {day_mins % 60:02d}m" if day_mins >= 60 else f"{day_mins}m",
            "is_today": (day_str == today_str)
        })

    # Recent 5 sessions
    cursor.execute("""
        SELECT fs.*, s.name as subject_name, s.color as subject_color, t.title as task_title
        FROM focus_sessions fs
        LEFT JOIN subjects s ON fs.subject_id = s.id
        LEFT JOIN tasks t ON fs.task_id = t.id
        WHERE fs.user_id = ? AND fs.session_type = 'focus'
        ORDER BY fs.id DESC
        LIMIT 6
    """, (user_id,))
    recent_sessions = [dict(r) for r in cursor.fetchall()]

    conn.close()

    def fmt_time(m):
        h = m // 60
        rem = m % 60
        return f"{h}h {rem:02d}m" if h > 0 else f"{rem}m"

    return {
        "today_minutes": today_mins,
        "today_formatted": fmt_time(today_mins),
        "total_minutes": total_mins,
        "total_formatted": fmt_time(total_mins),
        "completed_tasks": completed_tasks,
        "completed_sessions": completed_sessions,
        "current_streak": streaks["current_streak"],
        "longest_streak": streaks["longest_streak"],
        "weekly_chart": weekly_chart,
        "recent_sessions": recent_sessions
    }

def seed_user_sample_data(user_id: int):
    """Seed sample subjects, tasks, user settings, and focus sessions for a new student user."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if user already has subjects
    cursor.execute("SELECT COUNT(*) as count FROM subjects WHERE user_id = ?", (user_id,))
    if cursor.fetchone()["count"] > 0:
        conn.close()
        return

    # Sample subjects
    sample_subjects = [
        ("Data Structures & Algorithms", "DSA-301", "#6366f1", "Binary trees, dynamic programming, and complexity analysis."),
        ("Database Management Systems", "DBMS-202", "#f97316", "Relational algebra, SQL joins, normalization, and ACID properties."),
        ("Full-Stack Web Engineering", "WEB-401", "#10b981", "FastAPI backend, RESTful APIs, responsive UI architecture."),
        ("Computer Networks", "NET-205", "#8b5cf6", "TCP/IP layers, routing algorithms, DNS, and socket programming.")
    ]

    subject_ids = {}
    for name, code, color, desc in sample_subjects:
        cursor.execute(
            "INSERT INTO subjects (user_id, name, code, color, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, name, code, color, desc)
        )
        subject_ids[code] = cursor.lastrowid

    today_str = date.today().isoformat()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Sample tasks
    sample_tasks = [
        (subject_ids["DSA-301"], "Implement Red-Black Tree insertion algorithm", "Prepare for lab practical exam next Tuesday.", "High", today_str, 0, None),
        (subject_ids["DBMS-202"], "Design E-R diagram for library management", "Include cardinality constraints and 3NF normalization notes.", "Medium", today_str, 0, None),
        (subject_ids["WEB-401"], "Review RESTful API endpoints & JWT auth flow", "Check security headers and status codes for BSc IT submission.", "High", today_str, 1, now_str),
        (subject_ids["NET-205"], "Solve TCP sliding window protocol problem set", "Exercises 4.1 to 4.8 from Kurose & Ross textbook.", "Low", today_str, 0, None),
        (subject_ids["WEB-401"], "Test responsive sidebar navigation on mobile viewports", "Ensure touch targets are at least 44px.", "Medium", today_str, 1, now_str),
        (subject_ids["DSA-301"], "Solve 3 LeetCode medium graph traversal questions", "BFS and DFS variations.", "High", today_str, 1, now_str)
    ]

    for subj_id, title, desc, priority, due_date, completed, completed_at in sample_tasks:
        cursor.execute(
            """INSERT INTO tasks (user_id, subject_id, title, description, priority, due_date, completed, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, subj_id, title, desc, priority, due_date, completed, completed_at)
        )

    # Seed Default User Settings (Module 7)
    cursor.execute("""
        INSERT OR IGNORE INTO user_settings (user_id, theme, default_focus_duration, default_break_duration, notifications_enabled, sound_enabled)
        VALUES (?, 'light', 25, 5, 1, 1)
    """, (user_id,))

    # Seed 5 consecutive days of focus sessions leading up to today (Module 5 & 6)
    # Today + previous 4 days gives a real 5-day streak!
    # Minutes: 30, 25, 30, 35, 45 = 165 minutes total, perfectly matching today_study_minutes!
    daily_mins = [30, 25, 30, 35, 45]
    for i, mins in enumerate(daily_mins):
        days_ago = len(daily_mins) - 1 - i
        s_date = (date.today() - timedelta(days=days_ago)).isoformat()
        cursor.execute("""
            INSERT INTO focus_sessions (user_id, subject_id, duration_minutes, session_type, session_date, completed_at)
            VALUES (?, ?, ?, 'focus', ?, ?)
        """, (user_id, subject_ids["DSA-301" if i % 2 == 0 else "WEB-401"], mins, s_date, f"{s_date} 15:30:00"))

    conn.commit()
    conn.close()

    # Recalculate streak
    calculate_user_streak(user_id)

def seed_demo_user():
    """Create a default demo student user if not already present."""
    import bcrypt
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = 'alex.student@focusflow.edu'")
    existing = cursor.fetchone()
    if not existing:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(b"Student123!", salt).decode('utf-8')
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, streak, longest_streak, study_minutes_today) VALUES (?, ?, ?, ?, ?, ?)",
            ("Alex Student", "alex.student@focusflow.edu", hashed, 5, 5, 165)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        seed_user_sample_data(user_id)
    else:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
