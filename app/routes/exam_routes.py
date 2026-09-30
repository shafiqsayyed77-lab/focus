import json
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.models import ExamCreateRequest, ExamUpdateRequest, ExamResponse
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api/exams", tags=["Exam Preparation Mode"])

def _calculate_exam_metrics(cursor, exam_row, user_id: int) -> dict:
    """Calculates real readiness, days remaining, weak topics, and study hours."""
    d = dict(exam_row)
    subject_id = d["subject_id"]

    # Days remaining
    today = date.today()
    try:
        exam_dt = datetime.strptime(d["exam_date"], "%Y-%m-%d").date()
        days_left = (exam_dt - today).days
    except Exception:
        days_left = 0
    d["days_remaining"] = max(0, days_left)

    # Topics stats
    cursor.execute(
        """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN is_weak = 1 OR needs_revision = 1 THEN 1 ELSE 0 END) as weak
        FROM topics
        WHERE subject_id = ? AND user_id = ?
        """,
        (subject_id, user_id)
    )
    top_row = cursor.fetchone()
    total_top = top_row["total"] or 0
    comp_top = top_row["completed"] or 0
    weak_top = top_row["weak"] or 0

    d["topics_total"] = total_top
    d["topics_completed"] = comp_top
    d["topics_remaining"] = max(0, total_top - comp_top)
    d["weak_topics_count"] = weak_top
    d["revision_pending_count"] = weak_top

    # Study time
    cursor.execute(
        "SELECT COALESCE(SUM(duration_minutes), 0) as total_mins FROM focus_sessions WHERE subject_id = ? AND user_id = ?",
        (subject_id, user_id)
    )
    study_mins = cursor.fetchone()["total_mins"] or 0
    d["study_hours"] = round(study_mins / 60.0, 1)

    # Mock test average
    cursor.execute(
        "SELECT AVG(percentage) as avg_score FROM mock_tests WHERE (subject_id = ? OR subject_name = ?) AND user_id = ?",
        (subject_id, d.get("subject_name", ""), user_id)
    )
    mock_avg = cursor.fetchone()["avg_score"]
    d["mock_test_avg"] = int(mock_avg) if mock_avg is not None else None

    # Readiness calculation
    # Syllabus: 45% weight
    syllabus_ratio = (comp_top / total_top) if total_top > 0 else 0.0
    # Mock test: 35% weight
    mock_ratio = (mock_avg / 100.0) if mock_avg is not None else 0.5
    # Weakness penalty: up to -15%
    weak_penalty = min(0.2, (weak_top * 0.05))

    readiness = int(((syllabus_ratio * 0.50) + (mock_ratio * 0.35) + min(0.15, (study_mins / 300.0) * 0.15) - weak_penalty) * 100)
    d["readiness_percent"] = max(5, min(100, readiness))

    return d

def _generate_initial_roadmap(cursor, subject_id: int, user_id: int, days_left: int) -> str:
    """Generates an actionable day-by-day exam preparation roadmap."""
    cursor.execute(
        "SELECT id, title, is_completed, is_weak FROM topics WHERE subject_id = ? AND user_id = ? ORDER BY is_completed ASC, order_index ASC",
        (subject_id, user_id)
    )
    topics = cursor.fetchall()

    days_plan = max(3, min(30, days_left if days_left > 0 else 7))
    roadmap = []

    remaining_topics = [t["title"] for t in topics if not t["is_completed"]]
    weak_topics = [t["title"] for t in topics if t["is_weak"]]
    completed_topics = [t["title"] for t in topics if t["is_completed"]]

    pool = remaining_topics if remaining_topics else (weak_topics if weak_topics else completed_topics)
    if not pool:
        pool = ["Review Core Concepts", "Solve Sample Question Bank", "Mock Test Practice"]

    topic_idx = 0
    for day in range(1, days_plan + 1):
        if day == days_plan:
            action = "Final Full Mock Test & Formula Sheet Review"
            t_type = "mock"
        elif day == days_plan - 1:
            action = "Comprehensive Revision of all Weak Topics"
            t_type = "revision"
        else:
            t_name = pool[topic_idx % len(pool)]
            action = f"Study & Practice: {t_name}"
            t_type = "study"
            topic_idx += 1

        roadmap.append({
            "day": day,
            "title": f"Day {day}",
            "task": action,
            "type": t_type,
            "completed": False
        })

    return json.dumps(roadmap)

@router.get("", response_model=List[ExamResponse])
def get_exams(current_user: dict = Depends(get_current_user)):
    """Fetches all upcoming exams for the student with live readiness calculations."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT e.*, s.name as subject_name, s.color as subject_color
            FROM exams e
            JOIN subjects s ON e.subject_id = s.id
            WHERE e.user_id = ?
            ORDER BY e.exam_date ASC
            """,
            (current_user["id"],)
        )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            metrics = _calculate_exam_metrics(cursor, r, current_user["id"])
            result.append(ExamResponse(**metrics))
        return result

@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam_detail(exam_id: int, current_user: dict = Depends(get_current_user)):
    """Fetches single exam details including personalized day-by-day roadmap."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT e.*, s.name as subject_name, s.color as subject_color
            FROM exams e
            JOIN subjects s ON e.subject_id = s.id
            WHERE e.id = ? AND e.user_id = ?
            """,
            (exam_id, current_user["id"])
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Exam not found.")

        metrics = _calculate_exam_metrics(cursor, row, current_user["id"])
        return ExamResponse(**metrics)

@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(data: ExamCreateRequest, current_user: dict = Depends(get_current_user)):
    """Creates a new exam target and auto-generates a day-by-day roadmap."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM subjects WHERE id = ? AND user_id = ?", (data.subject_id, current_user["id"]))
        sub = cursor.fetchone()
        if not sub:
            raise HTTPException(status_code=400, detail="Invalid subject ID.")

        # Compute days left
        try:
            exam_dt = datetime.strptime(data.exam_date, "%Y-%m-%d").date()
            days_left = (exam_dt - date.today()).days
        except Exception:
            days_left = 14

        roadmap_json = _generate_initial_roadmap(cursor, data.subject_id, current_user["id"], days_left)

        cursor.execute(
            """
            INSERT INTO exams (user_id, subject_id, title, exam_date, target_score, notes, prep_roadmap)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_user["id"], data.subject_id, data.title.strip(),
                data.exam_date.strip(), data.target_score or 90,
                (data.notes or "").strip(), roadmap_json
            )
        )
        exam_id = cursor.lastrowid
        conn.commit()

        cursor.execute(
            """
            SELECT e.*, s.name as subject_name, s.color as subject_color
            FROM exams e
            JOIN subjects s ON e.subject_id = s.id
            WHERE e.id = ?
            """,
            (exam_id,)
        )
        row = cursor.fetchone()
        metrics = _calculate_exam_metrics(cursor, row, current_user["id"])
        return ExamResponse(**metrics)

@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(exam_id: int, data: ExamUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Updates an exam's title, date, target score, or customized prep roadmap."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exams WHERE id = ? AND user_id = ?", (exam_id, current_user["id"]))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Exam not found.")

        title = data.title.strip() if data.title is not None else existing["title"]
        exam_date = data.exam_date.strip() if data.exam_date is not None else existing["exam_date"]
        target = data.target_score if data.target_score is not None else existing["target_score"]
        notes = data.notes if data.notes is not None else existing["notes"]
        roadmap = data.prep_roadmap if data.prep_roadmap is not None else existing["prep_roadmap"]

        cursor.execute(
            """
            UPDATE exams SET title = ?, exam_date = ?, target_score = ?, notes = ?, prep_roadmap = ?
            WHERE id = ? AND user_id = ?
            """,
            (title, exam_date, target, notes, roadmap, exam_id, current_user["id"])
        )
        conn.commit()

        cursor.execute(
            """
            SELECT e.*, s.name as subject_name, s.color as subject_color
            FROM exams e
            JOIN subjects s ON e.subject_id = s.id
            WHERE e.id = ?
            """,
            (exam_id,)
        )
        row = cursor.fetchone()
        metrics = _calculate_exam_metrics(cursor, row, current_user["id"])
        return ExamResponse(**metrics)

@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: int, current_user: dict = Depends(get_current_user)):
    """Deletes an exam."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM exams WHERE id = ? AND user_id = ?", (exam_id, current_user["id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Exam not found.")

        cursor.execute("DELETE FROM exams WHERE id = ? AND user_id = ?", (exam_id, current_user["id"]))
        conn.commit()
    return None

@router.post("/{exam_id}/regenerate-roadmap", response_model=ExamResponse)
def regenerate_exam_roadmap(exam_id: int, current_user: dict = Depends(get_current_user)):
    """Regenerates a fresh prep roadmap based on latest syllabus progress."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exams WHERE id = ? AND user_id = ?", (exam_id, current_user["id"]))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Exam not found.")

        try:
            exam_dt = datetime.strptime(existing["exam_date"], "%Y-%m-%d").date()
            days_left = (exam_dt - date.today()).days
        except Exception:
            days_left = 10

        new_roadmap = _generate_initial_roadmap(cursor, existing["subject_id"], current_user["id"], days_left)
        cursor.execute("UPDATE exams SET prep_roadmap = ? WHERE id = ?", (new_roadmap, exam_id))
        conn.commit()

        cursor.execute(
            """
            SELECT e.*, s.name as subject_name, s.color as subject_color
            FROM exams e
            JOIN subjects s ON e.subject_id = s.id
            WHERE e.id = ?
            """,
            (exam_id,)
        )
        row = cursor.fetchone()
        metrics = _calculate_exam_metrics(cursor, row, current_user["id"])
        return ExamResponse(**metrics)
