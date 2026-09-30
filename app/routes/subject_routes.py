from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.models import (
    SubjectCreateRequest, SubjectUpdateRequest, SubjectResponse,
    TopicCreateRequest, TopicUpdateRequest, TopicResponse
)
from app.database import get_db, seed_starter_topics_for_subject
from app.auth import get_current_user

router = APIRouter(prefix="/api/subjects", tags=["Subjects & Topics"])

class TopicReorderRequest(BaseModel):
    topic_ids: List[int]

@router.get("", response_model=List[SubjectResponse])
def get_subjects(current_user: dict = Depends(get_current_user)):
    """Fetches all subjects belonging to the authenticated user with topic progress and task counts."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.id, s.user_id, s.name, s.color, s.icon, s.description, s.created_at,
                   (SELECT COUNT(*) FROM tasks t WHERE t.subject_id = s.id AND t.user_id = s.user_id) as task_count,
                   (SELECT COUNT(*) FROM topics tp WHERE tp.subject_id = s.id AND tp.user_id = s.user_id) as topic_count,
                   (SELECT COUNT(*) FROM topics tp WHERE tp.subject_id = s.id AND tp.user_id = s.user_id AND tp.is_completed = 1) as completed_topics_count,
                   (SELECT COALESCE(SUM(duration_minutes), 0) FROM focus_sessions fs WHERE fs.subject_id = s.id AND fs.user_id = s.user_id) as study_time_minutes,
                   (SELECT percentage FROM mock_tests mt WHERE (mt.subject_id = s.id OR mt.subject_name = s.name) AND mt.user_id = s.user_id ORDER BY mt.id DESC LIMIT 1) as mock_test_score,
                   (SELECT COUNT(*) FROM topics tp WHERE tp.subject_id = s.id AND tp.user_id = s.user_id AND (tp.is_weak = 1 OR tp.needs_revision = 1)) as weak_topics_count
            FROM subjects s
            WHERE s.user_id = ?
            ORDER BY s.id ASC
            """,
            (current_user["id"],)
        )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            top_cnt = d.get("topic_count") or 0
            done_cnt = d.get("completed_topics_count") or 0
            d["progress_percent"] = int((done_cnt / top_cnt) * 100) if top_cnt > 0 else 0
            result.append(SubjectResponse(**d))
        return result

@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject_detail(subject_id: int, current_user: dict = Depends(get_current_user)):
    """Retrieves single subject details with topic progress, study time, and mock test score."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.id, s.user_id, s.name, s.color, s.icon, s.description, s.created_at,
                   (SELECT COUNT(*) FROM tasks t WHERE t.subject_id = s.id AND t.user_id = s.user_id) as task_count,
                   (SELECT COUNT(*) FROM topics tp WHERE tp.subject_id = s.id AND tp.user_id = s.user_id) as topic_count,
                   (SELECT COUNT(*) FROM topics tp WHERE tp.subject_id = s.id AND tp.user_id = s.user_id AND tp.is_completed = 1) as completed_topics_count,
                   (SELECT COALESCE(SUM(duration_minutes), 0) FROM focus_sessions fs WHERE fs.subject_id = s.id AND fs.user_id = s.user_id) as study_time_minutes,
                   (SELECT percentage FROM mock_tests mt WHERE (mt.subject_id = s.id OR mt.subject_name = s.name) AND mt.user_id = s.user_id ORDER BY mt.id DESC LIMIT 1) as mock_test_score,
                   (SELECT COUNT(*) FROM topics tp WHERE tp.subject_id = s.id AND tp.user_id = s.user_id AND (tp.is_weak = 1 OR tp.needs_revision = 1)) as weak_topics_count
            FROM subjects s
            WHERE s.id = ? AND s.user_id = ?
            """,
            (subject_id, current_user["id"])
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Subject not found.")
        d = dict(row)
        top_cnt = d.get("topic_count") or 0
        done_cnt = d.get("completed_topics_count") or 0
        d["progress_percent"] = int((done_cnt / top_cnt) * 100) if top_cnt > 0 else 0
        return SubjectResponse(**d)

@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(data: SubjectCreateRequest, current_user: dict = Depends(get_current_user)):
    """Creates a new study subject for the student."""
    name_clean = data.name.strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Subject name cannot be empty.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO subjects (user_id, name, color, icon, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (current_user["id"], name_clean, data.color or "#6C3BFF", data.icon or "book", data.description or "")
        )
        subject_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
        d = dict(cursor.fetchone())
        d["task_count"] = 0
        d["topic_count"] = 0
        d["completed_topics_count"] = 0
        d["progress_percent"] = 0
        d["study_time_minutes"] = 0
        d["mock_test_score"] = None
        d["weak_topics_count"] = 0
        return SubjectResponse(**d)

@router.put("/{subject_id}", response_model=SubjectResponse)
def update_subject(subject_id: int, data: SubjectUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Updates subject metadata."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subjects WHERE id = ? AND user_id = ?", (subject_id, current_user["id"]))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Subject not found.")

        name = data.name.strip() if data.name is not None else existing["name"]
        color = data.color if data.color is not None else existing["color"]
        icon = data.icon if data.icon is not None else existing["icon"]
        desc = data.description if data.description is not None else existing["description"]

        cursor.execute(
            """
            UPDATE subjects SET name = ?, color = ?, icon = ?, description = ?
            WHERE id = ? AND user_id = ?
            """,
            (name, color, icon, desc, subject_id, current_user["id"])
        )
        conn.commit()

    return get_subject_detail(subject_id, current_user)

@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: int, current_user: dict = Depends(get_current_user)):
    """Deletes a subject and cascades deletion of its topics, tasks, and exams."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (subject_id, current_user["id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Subject not found.")

        cursor.execute("DELETE FROM subjects WHERE id = ? AND user_id = ?", (subject_id, current_user["id"]))
        conn.commit()
    return None

@router.post("/{subject_id}/seed-ai-topics", response_model=List[TopicResponse])
def seed_ai_topics_for_subject(subject_id: int, current_user: dict = Depends(get_current_user)):
    """Suggests and populates standard curriculum topics for a subject."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM subjects WHERE id = ? AND user_id = ?", (subject_id, current_user["id"]))
        sub = cursor.fetchone()
        if not sub:
            raise HTTPException(status_code=404, detail="Subject not found.")

        seed_starter_topics_for_subject(cursor, subject_id, current_user["id"], sub["name"])
        conn.commit()

    return get_topics_for_subject(subject_id, current_user)

# =====================================================================
# Topics Management Endpoints (Mini Learning Spaces)
# =====================================================================
@router.get("/{subject_id}/topics", response_model=List[TopicResponse])
def get_topics_for_subject(subject_id: int, current_user: dict = Depends(get_current_user)):
    """Returns all syllabus topics for a subject ordered by chapter and index."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (subject_id, current_user["id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Subject not found.")

        cursor.execute(
            """
            SELECT * FROM topics
            WHERE subject_id = ? AND user_id = ?
            ORDER BY chapter ASC, order_index ASC, id ASC
            """,
            (subject_id, current_user["id"])
        )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["is_completed"] = bool(d["is_completed"])
            d["is_weak"] = bool(d.get("is_weak", 0))
            d["needs_revision"] = bool(d.get("needs_revision", 0))
            result.append(TopicResponse(**d))
        return result

@router.post("/{subject_id}/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic_for_subject(subject_id: int, data: TopicCreateRequest, current_user: dict = Depends(get_current_user)):
    """Creates a new syllabus topic inside a subject chapter."""
    clean_title = data.title.strip()
    if not clean_title:
        raise HTTPException(status_code=400, detail="Topic title cannot be empty.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (subject_id, current_user["id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Subject not found.")

        cursor.execute("SELECT COALESCE(MAX(order_index), -1) + 1 as next_idx FROM topics WHERE subject_id = ?", (subject_id,))
        next_idx = cursor.fetchone()["next_idx"]

        cursor.execute(
            """
            INSERT INTO topics (subject_id, user_id, title, chapter, priority, notes, resources, order_index, is_completed, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'not_started')
            """,
            (
                subject_id, current_user["id"], clean_title,
                (data.chapter or "General").strip(),
                data.priority or "Medium",
                (data.notes or "").strip(),
                (data.resources or "").strip(),
                next_idx
            )
        )
        topic_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
        d = dict(cursor.fetchone())
        d["is_completed"] = bool(d["is_completed"])
        d["is_weak"] = bool(d.get("is_weak", 0))
        d["needs_revision"] = bool(d.get("needs_revision", 0))
        return TopicResponse(**d)

@router.put("/topics/{topic_id}", response_model=TopicResponse)
def update_topic(topic_id: int, data: TopicUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Updates a topic's title, chapter, priority, notes, or revision flags."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM topics WHERE id = ? AND user_id = ?", (topic_id, current_user["id"]))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Topic not found.")

        title = data.title.strip() if data.title is not None else existing["title"]
        chapter = data.chapter.strip() if data.chapter is not None else existing["chapter"]
        priority = data.priority if data.priority is not None else existing["priority"]
        notes = data.notes if data.notes is not None else existing["notes"]
        resources = data.resources if data.resources is not None else existing["resources"]
        order_idx = data.order_index if data.order_index is not None else existing["order_index"]
        
        is_weak = (1 if data.is_weak else 0) if data.is_weak is not None else existing["is_weak"]
        needs_rev = (1 if data.needs_revision else 0) if data.needs_revision is not None else existing["needs_revision"]
        rev_reason = data.revision_reason if data.revision_reason is not None else existing["revision_reason"]
        last_score = data.last_mock_score if data.last_mock_score is not None else existing["last_mock_score"]

        # Completion handling
        is_comp = existing["is_completed"]
        comp_at = existing["completed_at"]
        status_val = existing["status"]

        if data.is_completed is not None:
            is_comp = 1 if data.is_completed else 0
            if is_comp:
                comp_at = comp_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                status_val = "completed"
            else:
                comp_at = None
                status_val = "not_started"
        elif data.status is not None:
            status_val = data.status
            if status_val == "completed":
                is_comp = 1
                comp_at = comp_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                is_comp = 0
                comp_at = None

        cursor.execute(
            """
            UPDATE topics SET
                title = ?, chapter = ?, priority = ?, notes = ?, resources = ?,
                order_index = ?, is_weak = ?, needs_revision = ?, revision_reason = ?,
                last_mock_score = ?, is_completed = ?, completed_at = ?, status = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                title, chapter, priority, notes, resources,
                order_idx, is_weak, needs_rev, rev_reason,
                last_score, is_comp, comp_at, status_val,
                topic_id, current_user["id"]
            )
        )
        conn.commit()

        cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
        d = dict(cursor.fetchone())
        d["is_completed"] = bool(d["is_completed"])
        d["is_weak"] = bool(d.get("is_weak", 0))
        d["needs_revision"] = bool(d.get("needs_revision", 0))
        return TopicResponse(**d)

@router.patch("/topics/{topic_id}/toggle", response_model=TopicResponse)
def toggle_topic_completion(topic_id: int, current_user: dict = Depends(get_current_user)):
    """Toggles completion state of a topic. When completed, topic is automatically eligible for Mock Tests."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM topics WHERE id = ? AND user_id = ?", (topic_id, current_user["id"]))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Topic not found.")

        new_comp = 0 if row["is_completed"] else 1
        comp_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_comp else None
        new_status = "completed" if new_comp else "not_started"

        cursor.execute(
            "UPDATE topics SET is_completed = ?, completed_at = ?, status = ? WHERE id = ? AND user_id = ?",
            (new_comp, comp_at, new_status, topic_id, current_user["id"])
        )
        conn.commit()

        cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
        d = dict(cursor.fetchone())
        d["is_completed"] = bool(d["is_completed"])
        d["is_weak"] = bool(d.get("is_weak", 0))
        d["needs_revision"] = bool(d.get("needs_revision", 0))
        return TopicResponse(**d)

@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(topic_id: int, current_user: dict = Depends(get_current_user)):
    """Deletes a topic."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM topics WHERE id = ? AND user_id = ?", (topic_id, current_user["id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Topic not found.")

        cursor.execute("DELETE FROM topics WHERE id = ? AND user_id = ?", (topic_id, current_user["id"]))
        conn.commit()
    return None

@router.put("/{subject_id}/topics/reorder")
def reorder_topics(subject_id: int, data: TopicReorderRequest, current_user: dict = Depends(get_current_user)):
    """Persists manual student reordering of topics within a subject."""
    with get_db() as conn:
        cursor = conn.cursor()
        for idx, t_id in enumerate(data.topic_ids):
            cursor.execute(
                "UPDATE topics SET order_index = ? WHERE id = ? AND subject_id = ? AND user_id = ?",
                (idx, t_id, subject_id, current_user["id"])
            )
        conn.commit()
    return {"success": True}
