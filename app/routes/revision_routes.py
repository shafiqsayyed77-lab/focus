from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.models import RevisionItemResponse
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api/revision", tags=["Smart Revision Engine"])

class AddRevisionRequest(BaseModel):
    reason: Optional[str] = "Student Flagged for Review"

@router.get("", response_model=List[RevisionItemResponse])
def get_revision_queue(current_user: dict = Depends(get_current_user)):
    """Gathers all topics needing revision: weak mock-test topics, spaced-repetition (>7 days), or student-queued."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch explicitly flagged weak/revision topics
        cursor.execute(
            """
            SELECT tp.id as topic_id, tp.title as topic_title, tp.chapter,
                   tp.is_weak, tp.needs_revision, tp.revision_reason,
                   tp.last_mock_score, tp.last_studied_at, tp.completed_at,
                   s.id as subject_id, s.name as subject_name, s.color as subject_color
            FROM topics tp
            JOIN subjects s ON tp.subject_id = s.id
            WHERE tp.user_id = ? AND (tp.is_weak = 1 OR tp.needs_revision = 1)
            ORDER BY tp.is_weak DESC, tp.id ASC
            """,
            (current_user["id"],)
        )
        explicit_rows = cursor.fetchall()

        # 2. Check for spaced repetition topics: completed >7 days ago with no recent session
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """
            SELECT tp.id as topic_id, tp.title as topic_title, tp.chapter,
                   tp.is_weak, tp.needs_revision, tp.revision_reason,
                   tp.last_mock_score, tp.last_studied_at, tp.completed_at,
                   s.id as subject_id, s.name as subject_name, s.color as subject_color
            FROM topics tp
            JOIN subjects s ON tp.subject_id = s.id
            WHERE tp.user_id = ? 
              AND tp.is_completed = 1
              AND (tp.is_weak = 0 AND tp.needs_revision = 0)
              AND (tp.last_studied_at IS NULL OR tp.last_studied_at < ?)
              AND (tp.completed_at IS NOT NULL AND tp.completed_at < ?)
            LIMIT 5
            """,
            (current_user["id"], seven_days_ago, seven_days_ago)
        )
        spaced_rows = cursor.fetchall()

        items = []
        seen_ids = set()

        for r in explicit_rows:
            seen_ids.add(r["topic_id"])
            reason = r["revision_reason"] or ("Scored below 60% on Mock Test" if r["is_weak"] else "Due for review")
            items.append(RevisionItemResponse(
                id=r["topic_id"],
                topic_id=r["topic_id"],
                topic_title=r["topic_title"],
                subject_id=r["subject_id"],
                subject_name=r["subject_name"],
                subject_color=r["subject_color"],
                chapter=r["chapter"] or "General",
                reason=reason,
                last_studied=r["last_studied_at"] or r["completed_at"],
                last_score=r["last_mock_score"],
                is_weak=bool(r["is_weak"])
            ))

        for r in spaced_rows:
            if r["topic_id"] not in seen_ids:
                seen_ids.add(r["topic_id"])
                items.append(RevisionItemResponse(
                    id=r["topic_id"],
                    topic_id=r["topic_id"],
                    topic_title=r["topic_title"],
                    subject_id=r["subject_id"],
                    subject_name=r["subject_name"],
                    subject_color=r["subject_color"],
                    chapter=r["chapter"] or "General",
                    reason="Spaced Repetition: Completed >7 days ago",
                    last_studied=r["last_studied_at"] or r["completed_at"],
                    last_score=r["last_mock_score"],
                    is_weak=False
                ))

        return items

@router.post("/add/{topic_id}")
def add_to_revision_queue(topic_id: int, req: AddRevisionRequest, current_user: dict = Depends(get_current_user)):
    """Manually queues a topic for active revision."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM topics WHERE id = ? AND user_id = ?", (topic_id, current_user["id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Topic not found.")

        cursor.execute(
            """
            UPDATE topics SET
                needs_revision = 1,
                revision_reason = ?
            WHERE id = ? AND user_id = ?
            """,
            (req.reason or "Student Flagged", topic_id, current_user["id"])
        )
        conn.commit()
    return {"success": True, "message": "Topic added to revision queue."}

@router.post("/mark-revised/{topic_id}")
def mark_topic_revised(topic_id: int, current_user: dict = Depends(get_current_user)):
    """Marks a topic as successfully revised and clears the revision badge."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM topics WHERE id = ? AND user_id = ?", (topic_id, current_user["id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Topic not found.")

        cursor.execute(
            """
            UPDATE topics SET
                needs_revision = 0,
                is_weak = 0,
                last_studied_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (now_str, topic_id, current_user["id"])
        )
        conn.commit()
    return {"success": True, "message": "Topic marked as revised!"}
