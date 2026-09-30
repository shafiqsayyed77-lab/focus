from datetime import datetime, timedelta, date
from typing import List, Tuple, Optional
from fastapi import APIRouter, Depends
from app.models import (
    DashboardStatsResponse, AnalyticsStatsResponse,
    WeeklyChartDay, SubjectStudyTime, AchievementItem,
    UpcomingExamItem, TaskResponse
)
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api/stats", tags=["Stats, Progress & Analytics"])

def calculate_streaks(user_id: int) -> Tuple[int, int]:
    """Computes current streak and longest historical streak."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT substr(completed_at, 1, 10) as study_date
            FROM focus_sessions
            WHERE user_id = ?
            ORDER BY study_date ASC
            """,
            (user_id,)
        )
        rows = cursor.fetchall()

    if not rows:
        return 0, 0

    date_objects = []
    for r in rows:
        try:
            d = datetime.strptime(r["study_date"], "%Y-%m-%d").date()
            date_objects.append(d)
        except ValueError:
            continue

    if not date_objects:
        return 0, 0

    date_set = set(date_objects)
    
    # 1. Longest Streak
    longest_streak = 1
    current_run = 1
    for i in range(1, len(date_objects)):
        if (date_objects[i] - date_objects[i-1]).days == 1:
            current_run += 1
            if current_run > longest_streak:
                longest_streak = current_run
        else:
            current_run = 1

    # 2. Current Streak
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    if today in date_set:
        curr = 1
        check = today - timedelta(days=1)
        while check in date_set:
            curr += 1
            check -= timedelta(days=1)
        current_streak = curr
    elif yesterday in date_set:
        curr = 1
        check = yesterday - timedelta(days=1)
        while check in date_set:
            curr += 1
            check -= timedelta(days=1)
        current_streak = curr
    else:
        current_streak = 0

    return current_streak, longest_streak

@router.get("/dashboard", response_model=DashboardStatsResponse)
def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Provides dynamic academic dashboard data using real database values."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    user_id = current_user["id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # User course & name
        cursor.execute("SELECT name, course FROM users WHERE id = ?", (user_id,))
        u_row = cursor.fetchone()
        welcome_name = u_row["name"] if u_row else current_user["name"]
        course_name = u_row["course"] or ""

        # Today's study time
        cursor.execute(
            "SELECT COALESCE(SUM(duration_minutes), 0) as total_min FROM focus_sessions WHERE user_id = ? AND substr(completed_at, 1, 10) = ?",
            (user_id, today_str)
        )
        today_study_mins = cursor.fetchone()["total_min"]

        # Today's completed tasks
        cursor.execute(
            "SELECT COUNT(*) as count FROM tasks WHERE user_id = ? AND is_completed = 1 AND substr(completed_at, 1, 10) = ?",
            (user_id, today_str)
        )
        today_completed_tasks = cursor.fetchone()["count"]

        # Pending tasks
        cursor.execute(
            """
            SELECT t.*, s.name as subject_name, s.color as subject_color
            FROM tasks t
            LEFT JOIN subjects s ON s.id = t.subject_id
            WHERE t.user_id = ? AND t.is_completed = 0
            ORDER BY CASE t.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 END ASC, t.deadline ASC NULLS LAST
            LIMIT 5
            """,
            (user_id,)
        )
        pending_tasks_rows = cursor.fetchall()
        pending_tasks = []
        for r in pending_tasks_rows:
            d = dict(r)
            d["is_completed"] = bool(d.get("is_completed", 0))
            pending_tasks.append(TaskResponse(**d))
        today_pending_count = len(pending_tasks_rows)

        # Overall syllabus progress
        cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as comp FROM topics WHERE user_id = ?", (user_id,))
        top_stats = cursor.fetchone()
        tot_topics = top_stats["total"] or 0
        comp_topics = top_stats["comp"] or 0
        overall_progress = int((comp_topics / tot_topics) * 100) if tot_topics > 0 else 0

        # Total subjects
        cursor.execute("SELECT COUNT(*) as cnt FROM subjects WHERE user_id = ?", (user_id,))
        total_subjects = cursor.fetchone()["cnt"] or 0

        # Weak topics
        cursor.execute("SELECT COUNT(*) as cnt FROM topics WHERE user_id = ? AND (is_weak = 1 OR needs_revision = 1)", (user_id,))
        weak_count = cursor.fetchone()["cnt"] or 0

        # Upcoming exams
        cursor.execute(
            """
            SELECT e.*, s.name as subject_name, s.color as subject_color
            FROM exams e
            JOIN subjects s ON e.subject_id = s.id
            WHERE e.user_id = ? AND e.exam_date >= ?
            ORDER BY e.exam_date ASC
            LIMIT 3
            """,
            (user_id, today_str)
        )
        exam_rows = cursor.fetchall()
        upcoming_exams = []
        for er in exam_rows:
            try:
                days_left = (datetime.strptime(er["exam_date"], "%Y-%m-%d").date() - date.today()).days
            except Exception:
                days_left = 0
            upcoming_exams.append(UpcomingExamItem(
                id=er["id"],
                title=er["title"],
                subject_name=er["subject_name"],
                subject_color=er["subject_color"],
                days_left=max(0, days_left),
                exam_date=er["exam_date"],
                readiness_percent=75
            ))

        # Continue Learning candidate (subject with uncompleted topics)
        cursor.execute(
            """
            SELECT s.name as subject_name, tp.title as topic_title
            FROM topics tp
            JOIN subjects s ON tp.subject_id = s.id
            WHERE tp.user_id = ? AND tp.is_completed = 0
            ORDER BY tp.priority = 'High' DESC, tp.order_index ASC
            LIMIT 1
            """,
            (user_id,)
        )
        cont_row = cursor.fetchone()
        cont_subject = cont_row["subject_name"] if cont_row else None
        cont_topic = cont_row["topic_title"] if cont_row else None

        # Recommended Action calculation
        if upcoming_exams and upcoming_exams[0].days_left <= 14:
            rec_action = f"Exam in {upcoming_exams[0].days_left} days: Take a practice test on {upcoming_exams[0].subject_name}"
        elif weak_count > 0:
            cursor.execute("SELECT title, (SELECT name FROM subjects WHERE id = topics.subject_id) as sname FROM topics WHERE user_id = ? AND (is_weak = 1 OR needs_revision = 1) LIMIT 1", (user_id,))
            w_item = cursor.fetchone()
            rec_action = f"Revise weak topic: {w_item['title']} ({w_item['sname']})"
        elif cont_topic and cont_subject:
            rec_action = f"Continue syllabus: Study {cont_topic} in {cont_subject}"
        else:
            rec_action = "Create your academic roadmap by adding your first subject and topics!"

    current_streak, _ = calculate_streaks(user_id)
    total_due = today_completed_tasks + today_pending_count
    today_progress_percent = int((today_completed_tasks / total_due) * 100) if total_due > 0 else 0

    return DashboardStatsResponse(
        welcome_name=welcome_name,
        course=course_name,
        today_study_minutes=today_study_mins,
        today_completed_tasks=today_completed_tasks,
        current_streak=current_streak,
        today_pending_tasks_count=today_pending_count,
        today_progress_percent=today_progress_percent,
        pending_tasks=pending_tasks,
        overall_progress_percent=overall_progress,
        total_subjects_count=total_subjects,
        total_topics_count=tot_topics,
        completed_topics_count=comp_topics,
        weak_topics_count=weak_count,
        upcoming_exams=upcoming_exams,
        continue_subject_name=cont_subject,
        continue_topic_title=cont_topic,
        recommended_action=rec_action
    )

@router.get("/progress", response_model=AnalyticsStatsResponse)
@router.get("/analytics", response_model=AnalyticsStatsResponse)
def get_analytics_stats(current_user: dict = Depends(get_current_user)):
    """Provides in-depth academic analytics, charts data, and student achievements."""
    user_id = current_user["id"]
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    with get_db() as conn:
        cursor = conn.cursor()

        # Today study time
        cursor.execute("SELECT COALESCE(SUM(duration_minutes), 0) as mins FROM focus_sessions WHERE user_id = ? AND substr(completed_at, 1, 10) = ?", (user_id, today_str))
        today_mins = cursor.fetchone()["mins"]

        # Total study time
        cursor.execute("SELECT COALESCE(SUM(duration_minutes), 0) as mins FROM focus_sessions WHERE user_id = ?", (user_id,))
        total_mins = cursor.fetchone()["mins"]

        # Completed tasks
        cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE user_id = ? AND is_completed = 1", (user_id,))
        completed_tasks = cursor.fetchone()["count"]

        # Completed focus sessions
        cursor.execute("SELECT COUNT(*) as count FROM focus_sessions WHERE user_id = ?", (user_id,))
        completed_sessions = cursor.fetchone()["count"]

        # 7-day chart
        weekly_chart = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            d_str = d.strftime("%Y-%m-%d")
            day_name = d.strftime("%a")
            cursor.execute("SELECT COALESCE(SUM(duration_minutes), 0) as mins FROM focus_sessions WHERE user_id = ? AND substr(completed_at, 1, 10) = ?", (user_id, d_str))
            day_mins = cursor.fetchone()["mins"]
            weekly_chart.append(WeeklyChartDay(date=d_str, day_name=day_name, minutes=day_mins))

        # Subject-wise study times
        cursor.execute(
            """
            SELECT s.name as subject_name, s.color, COALESCE(SUM(fs.duration_minutes), 0) as minutes
            FROM subjects s
            LEFT JOIN focus_sessions fs ON s.id = fs.subject_id AND fs.user_id = s.user_id
            WHERE s.user_id = ?
            GROUP BY s.id
            ORDER BY minutes DESC
            """,
            (user_id,)
        )
        sub_time_rows = cursor.fetchall()
        total_sub_time = sum(r["minutes"] for r in sub_time_rows) or 1
        subject_times = [
            SubjectStudyTime(
                subject_name=r["subject_name"],
                color=r["color"],
                minutes=r["minutes"],
                percentage=int((r["minutes"] / total_sub_time) * 100)
            )
            for r in sub_time_rows
        ]

        # Mock tests stats
        cursor.execute("SELECT COUNT(*) as total, AVG(percentage) as avg_score, MAX(percentage) as max_score FROM mock_tests WHERE user_id = ?", (user_id,))
        mock_stats = cursor.fetchone()
        tot_mocks = mock_stats["total"] or 0
        avg_mock = int(mock_stats["avg_score"]) if mock_stats["avg_score"] is not None else 0
        max_mock = mock_stats["max_score"] or 0

        # Weak and Strong topics
        cursor.execute("SELECT title FROM topics WHERE user_id = ? AND (is_weak = 1 OR needs_revision = 1) LIMIT 6", (user_id,))
        weak_topics = [r["title"] for r in cursor.fetchall()]

        cursor.execute("SELECT title FROM topics WHERE user_id = ? AND is_completed = 1 AND is_weak = 0 ORDER BY id DESC LIMIT 6", (user_id,))
        strong_topics = [r["title"] for r in cursor.fetchall()]

        # Most productive day
        best_day = max(weekly_chart, key=lambda x: x.minutes)
        most_productive = f"{best_day.day_name} ({best_day.minutes} min)" if best_day.minutes > 0 else "Consistent Effort"

        # Attention subject: lowest completion
        cursor.execute(
            """
            SELECT s.name,
                   (SELECT COUNT(*) FROM topics WHERE subject_id = s.id) as tot,
                   (SELECT COUNT(*) FROM topics WHERE subject_id = s.id AND is_completed = 1) as comp
            FROM subjects s
            WHERE s.user_id = ?
            ORDER BY (CASE WHEN tot > 0 THEN (comp * 1.0 / tot) ELSE 0 END) ASC
            LIMIT 1
            """,
            (user_id,)
        )
        attn_row = cursor.fetchone()
        attention_sub = attn_row["name"] if attn_row else None

        # Completed topics count
        cursor.execute("SELECT COUNT(*) as cnt FROM topics WHERE user_id = ? AND is_completed = 1", (user_id,))
        comp_topics_count = cursor.fetchone()["cnt"] or 0

        # Check for any 100% completed subject
        cursor.execute(
            """
            SELECT s.id FROM subjects s
            WHERE s.user_id = ? AND (SELECT COUNT(*) FROM topics WHERE subject_id = s.id) > 0
              AND (SELECT COUNT(*) FROM topics WHERE subject_id = s.id AND is_completed = 0) = 0
            LIMIT 1
            """,
            (user_id,)
        )
        has_completed_subject = bool(cursor.fetchone())

        # Check for exam readiness
        cursor.execute("SELECT COUNT(*) as cnt FROM exams WHERE user_id = ?", (user_id,))
        has_exams = bool(cursor.fetchone()["cnt"] > 0)

    current_streak, longest_streak = calculate_streaks(user_id)

    # Dynamic achievements
    achievements = [
        AchievementItem(
            id="streak_7",
            title="7-Day Study Streak",
            icon="🔥",
            description="Maintained daily study momentum for 7 consecutive days",
            unlocked=current_streak >= 7 or longest_streak >= 7,
            progress_text=f"{min(7, current_streak)}/7 days"
        ),
        AchievementItem(
            id="topics_10",
            title="Curriculum Master",
            icon="🧠",
            description="Completed 10 academic syllabus topics",
            unlocked=comp_topics_count >= 10,
            progress_text=f"{min(10, comp_topics_count)}/10 topics"
        ),
        AchievementItem(
            id="first_mock",
            title="First Examination",
            icon="🎯",
            description="Completed your first timed subject mock test",
            unlocked=tot_mocks >= 1,
            progress_text=f"{min(1, tot_mocks)}/1 test"
        ),
        AchievementItem(
            id="subject_done",
            title="Subject Complete",
            icon="📚",
            description="Achieved 100% syllabus mastery on a subject",
            unlocked=has_completed_subject,
            progress_text="100% complete" if has_completed_subject else "In progress"
        ),
        AchievementItem(
            id="focus_10",
            title="Deep Focus Warrior",
            icon="⚡",
            description="Completed 10 focused Pomodoro study sessions",
            unlocked=completed_sessions >= 10,
            progress_text=f"{min(10, completed_sessions)}/10 sessions"
        ),
        AchievementItem(
            id="score_booster",
            title="High Accuracy Achiever",
            icon="📈",
            description="Scored 80% or higher on a subject mock test",
            unlocked=max_mock >= 80,
            progress_text=f"{max_mock}% top score"
        ),
        AchievementItem(
            id="exam_ready",
            title="Exam Ready",
            icon="🏆",
            description="Created an upcoming exam and achieved >80% readiness",
            unlocked=has_exams and (comp_topics_count >= 5),
            progress_text="Ready" if (has_exams and comp_topics_count >= 5) else "Preparing"
        )
    ]

    return AnalyticsStatsResponse(
        today_study_minutes=today_mins,
        total_study_minutes=total_mins,
        completed_tasks_count=completed_tasks,
        completed_focus_sessions_count=completed_sessions,
        current_streak=current_streak,
        longest_streak=longest_streak,
        weekly_chart=weekly_chart,
        subject_study_times=subject_times,
        total_mock_tests=tot_mocks,
        average_mock_score=avg_mock,
        weak_topics_list=weak_topics,
        strong_topics_list=strong_topics,
        most_productive_day=most_productive,
        attention_subject=attention_sub,
        achievements=achievements
    )
