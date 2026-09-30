from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from app.models import FocusSessionCreateRequest, FocusSessionResponse
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["Focus Sessions"])

@router.get("", response_model=List[FocusSessionResponse])
def get_sessions(current_user: dict = Depends(get_current_user)):
    """Retrieves recent focus sessions completed by the user with subject and topic linkage."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT fs.id, fs.user_id, fs.subject_id, fs.topic_id, fs.task_id, fs.duration_minutes,
                   fs.completed_at, fs.created_at,
                   s.name as subject_name,
                   tp.title as topic_title,
                   t.title as task_title
            FROM focus_sessions fs
            LEFT JOIN subjects s ON s.id = fs.subject_id
            LEFT JOIN topics tp ON tp.id = fs.topic_id
            LEFT JOIN tasks t ON t.id = fs.task_id
            WHERE fs.user_id = ?
            ORDER BY fs.completed_at DESC
            LIMIT 50
            """,
            (current_user["id"],)
        )
        rows = cursor.fetchall()
        return [FocusSessionResponse(**dict(r)) for r in rows]

@router.post("", response_model=FocusSessionResponse, status_code=status.HTTP_201_CREATED)
def record_focus_session(data: FocusSessionCreateRequest, current_user: dict = Depends(get_current_user)):
    """Logs a completed focus study session linked to a subject and topic."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cursor = conn.cursor()

        # Validate subject
        if data.subject_id:
            cursor.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (data.subject_id, current_user["id"]))
            if not cursor.fetchone():
                data.subject_id = None

        # Validate topic
        if data.topic_id:
            cursor.execute("SELECT id, subject_id FROM topics WHERE id = ? AND user_id = ?", (data.topic_id, current_user["id"]))
            tp = cursor.fetchone()
            if not tp:
                data.topic_id = None
            elif not data.subject_id and tp["subject_id"]:
                data.subject_id = tp["subject_id"]

        # Validate task
        if data.task_id:
            cursor.execute("SELECT id, subject_id, topic_id FROM tasks WHERE id = ? AND user_id = ?", (data.task_id, current_user["id"]))
            t = cursor.fetchone()
            if not t:
                data.task_id = None
            else:
                if not data.subject_id and t["subject_id"]:
                    data.subject_id = t["subject_id"]
                if not data.topic_id and t["topic_id"]:
                    data.topic_id = t["topic_id"]

        cursor.execute(
            """
            INSERT INTO focus_sessions (user_id, subject_id, topic_id, task_id, duration_minutes, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (current_user["id"], data.subject_id, data.topic_id, data.task_id, data.duration_minutes, now_str)
        )
        session_id = cursor.lastrowid

        # Update topic last_studied_at if linked
        if data.topic_id:
            cursor.execute("UPDATE topics SET last_studied_at = ? WHERE id = ?", (now_str, data.topic_id))

        conn.commit()

        cursor.execute(
            """
            SELECT fs.id, fs.user_id, fs.subject_id, fs.topic_id, fs.task_id, fs.duration_minutes,
                   fs.completed_at, fs.created_at,
                   s.name as subject_name,
                   tp.title as topic_title,
                   t.title as task_title
            FROM focus_sessions fs
            LEFT JOIN subjects s ON s.id = fs.subject_id
            LEFT JOIN topics tp ON tp.id = fs.topic_id
            LEFT JOIN tasks t ON t.id = fs.task_id
            WHERE fs.id = ?
            """,
            (session_id,)
        )
        row = cursor.fetchone()
        return FocusSessionResponse(**dict(row))
