from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from app.models import GlobalSearchResponse
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["Global Search & Quick Capture"])

class QuickCapturePayload(BaseModel):
    item_type: str  # task, topic, note, exam, session
    data: Dict[str, Any]

@router.get("/search", response_model=GlobalSearchResponse)
def global_search(q: str = Query(..., min_length=1), current_user: dict = Depends(get_current_user)):
    """Searches across subjects, topics, tasks, exams, and notes."""
    clean_q = f"%{q.strip().lower()}%"
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Subjects
        cursor.execute(
            """
            SELECT id, name, color, icon, description
            FROM subjects
            WHERE user_id = ? AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ?)
            LIMIT 5
            """,
            (current_user["id"], clean_q, clean_q)
        )
        subjects = [dict(r) for r in cursor.fetchall()]

        # 2. Topics
        cursor.execute(
            """
            SELECT tp.id, tp.title, tp.chapter, tp.is_completed, tp.is_weak, s.id as subject_id, s.name as subject_name
            FROM topics tp
            JOIN subjects s ON tp.subject_id = s.id
            WHERE tp.user_id = ? AND (LOWER(tp.title) LIKE ? OR LOWER(tp.notes) LIKE ? OR LOWER(tp.chapter) LIKE ?)
            LIMIT 10
            """,
            (current_user["id"], clean_q, clean_q, clean_q)
        )
        topics = [dict(r) for r in cursor.fetchall()]

        # 3. Tasks
        cursor.execute(
            """
            SELECT t.id, t.title, t.priority, t.item_type, t.is_completed, s.name as subject_name
            FROM tasks t
            LEFT JOIN subjects s ON t.subject_id = s.id
            WHERE t.user_id = ? AND (LOWER(t.title) LIKE ? OR LOWER(t.description) LIKE ?)
            LIMIT 10
            """,
            (current_user["id"], clean_q, clean_q)
        )
        tasks = [dict(r) for r in cursor.fetchall()]

        # 4. Exams
        cursor.execute(
            """
            SELECT e.id, e.title, e.exam_date, s.name as subject_name
            FROM exams e
            JOIN subjects s ON e.subject_id = s.id
            WHERE e.user_id = ? AND (LOWER(e.title) LIKE ? OR LOWER(e.notes) LIKE ?)
            LIMIT 5
            """,
            (current_user["id"], clean_q, clean_q)
        )
        exams = [dict(r) for r in cursor.fetchall()]

        # 5. Resources / Notes
        cursor.execute(
            """
            SELECT r.id, r.title, r.type, r.tags, s.name as subject_name
            FROM resources r
            LEFT JOIN subjects s ON r.subject_id = s.id
            WHERE r.user_id = ? AND (LOWER(r.title) LIKE ? OR LOWER(r.content) LIKE ? OR LOWER(r.tags) LIKE ?)
            LIMIT 10
            """,
            (current_user["id"], clean_q, clean_q, clean_q)
        )
        notes = [dict(r) for r in cursor.fetchall()]

    return GlobalSearchResponse(
        query=q,
        subjects=subjects,
        topics=topics,
        tasks=tasks,
        exams=exams,
        notes=notes
    )

@router.post("/quick-capture", status_code=status.HTTP_201_CREATED)
def quick_capture(payload: QuickCapturePayload, current_user: dict = Depends(get_current_user)):
    """Fast-creates any academic item in one unified call."""
    t = payload.item_type.lower()
    data = payload.data

    with get_db() as conn:
        cursor = conn.cursor()

        if t == "task":
            cursor.execute(
                """
                INSERT INTO tasks (user_id, subject_id, title, priority, item_type, estimated_minutes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    current_user["id"],
                    data.get("subject_id"),
                    data.get("title", "Untitled Task").strip(),
                    data.get("priority", "Medium"),
                    data.get("item_type", "task"),
                    data.get("estimated_minutes", 30)
                )
            )
        elif t == "topic":
            cursor.execute(
                """
                INSERT INTO topics (user_id, subject_id, title, chapter, priority)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    current_user["id"],
                    data.get("subject_id"),
                    data.get("title", "New Topic").strip(),
                    data.get("chapter", "General").strip(),
                    data.get("priority", "Medium")
                )
            )
        elif t == "note":
            cursor.execute(
                """
                INSERT INTO resources (user_id, subject_id, topic_id, title, type, content)
                VALUES (?, ?, ?, ?, 'note', ?)
                """,
                (
                    current_user["id"],
                    data.get("subject_id"),
                    data.get("topic_id"),
                    data.get("title", "Quick Note").strip(),
                    data.get("content", "").strip()
                )
            )
        elif t == "exam":
            cursor.execute(
                """
                INSERT INTO exams (user_id, subject_id, title, exam_date, target_score)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    current_user["id"],
                    data.get("subject_id"),
                    data.get("title", "Upcoming Exam").strip(),
                    data.get("exam_date"),
                    data.get("target_score", 90)
                )
            )
        elif t == "session":
            cursor.execute(
                """
                INSERT INTO focus_sessions (user_id, subject_id, topic_id, duration_minutes)
                VALUES (?, ?, ?, ?)
                """,
                (
                    current_user["id"],
                    data.get("subject_id"),
                    data.get("topic_id"),
                    data.get("duration_minutes", 25)
                )
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported item type: {t}")

        conn.commit()

    return {"success": True, "type": t, "message": f"{t.capitalize()} captured successfully!"}
