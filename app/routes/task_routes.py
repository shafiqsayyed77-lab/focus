from typing import List, Optional, Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel, Field
from app.models import TaskCreateRequest, TaskUpdateRequest, TaskResponse
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api/tasks", tags=["Tasks & Planner"])

class PlanMyDayRequest(BaseModel):
    available_minutes: int = Field(default=120, ge=15, le=720)

@router.get("", response_model=List[TaskResponse])
def get_tasks(
    subject_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query("all", pattern="^(all|pending|completed)$"),
    priority: Optional[str] = Query(None, pattern="^(Low|Medium|High)$"),
    item_type: Optional[str] = Query(None),
    planned_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves tasks and planner items for the current user with flexible filters."""
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT t.id, t.user_id, t.subject_id, t.topic_id, t.title, t.description, t.priority,
                   t.deadline, t.planned_date, t.item_type, t.estimated_minutes,
                   t.is_completed, t.completed_at, t.created_at,
                   s.name as subject_name, s.color as subject_color
            FROM tasks t
            LEFT JOIN subjects s ON s.id = t.subject_id
            WHERE t.user_id = ?
        """
        params = [current_user["id"]]

        if subject_id is not None:
            query += " AND t.subject_id = ?"
            params.append(subject_id)

        if status_filter == "pending":
            query += " AND t.is_completed = 0"
        elif status_filter == "completed":
            query += " AND t.is_completed = 1"

        if priority is not None:
            query += " AND t.priority = ?"
            params.append(priority)

        if item_type is not None:
            query += " AND t.item_type = ?"
            params.append(item_type)

        if planned_date is not None:
            query += " AND t.planned_date = ?"
            params.append(planned_date)

        query += " ORDER BY t.is_completed ASC, CASE t.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END ASC, t.deadline ASC NULLS LAST, t.created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["is_completed"] = bool(d["is_completed"])
            result.append(TaskResponse(**d))
        return result

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreateRequest, current_user: dict = Depends(get_current_user)):
    """Creates a new study task / assignment / revision / project planner item."""
    clean_title = data.title.strip()
    if not clean_title:
        raise HTTPException(status_code=400, detail="Task title cannot be empty.")

    with get_db() as conn:
        cursor = conn.cursor()
        if data.subject_id:
            cursor.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (data.subject_id, current_user["id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="Selected subject does not exist or does not belong to you.")

        cursor.execute(
            """
            INSERT INTO tasks (user_id, subject_id, topic_id, title, description, priority, deadline, planned_date, item_type, estimated_minutes, is_completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                current_user["id"], data.subject_id, data.topic_id, clean_title,
                data.description or "", data.priority, data.deadline, data.planned_date,
                data.item_type or "task", data.estimated_minutes or 30
            )
        )
        task_id = cursor.lastrowid
        conn.commit()

        cursor.execute(
            """
            SELECT t.id, t.user_id, t.subject_id, t.topic_id, t.title, t.description, t.priority,
                   t.deadline, t.planned_date, t.item_type, t.estimated_minutes,
                   t.is_completed, t.completed_at, t.created_at,
                   s.name as subject_name, s.color as subject_color
            FROM tasks t
            LEFT JOIN subjects s ON s.id = t.subject_id
            WHERE t.id = ?
            """,
            (task_id,)
        )
        row = dict(cursor.fetchone())
        row["is_completed"] = bool(row["is_completed"])
        return TaskResponse(**row)

@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, data: TaskUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Updates an existing task."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, current_user["id"]))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found.")

        title = data.title.strip() if data.title is not None else existing["title"]
        subject_id = data.subject_id if data.subject_id is not None else existing["subject_id"]
        topic_id = data.topic_id if data.topic_id is not None else existing["topic_id"]
        description = data.description if data.description is not None else existing["description"]
        priority = data.priority if data.priority is not None else existing["priority"]
        deadline = data.deadline if data.deadline is not None else existing["deadline"]
        planned_date = data.planned_date if data.planned_date is not None else existing["planned_date"]
        item_type = data.item_type if data.item_type is not None else existing["item_type"]
        estimated_minutes = data.estimated_minutes if data.estimated_minutes is not None else existing["estimated_minutes"]

        is_completed = existing["is_completed"]
        completed_at = existing["completed_at"]
        if data.is_completed is not None:
            is_completed = 1 if data.is_completed else 0
            if is_completed and not existing["is_completed"]:
                completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elif not is_completed:
                completed_at = None

        cursor.execute(
            """
            UPDATE tasks SET
                title = ?, subject_id = ?, topic_id = ?, description = ?,
                priority = ?, deadline = ?, planned_date = ?, item_type = ?,
                estimated_minutes = ?, is_completed = ?, completed_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                title, subject_id, topic_id, description,
                priority, deadline, planned_date, item_type,
                estimated_minutes, is_completed, completed_at,
                task_id, current_user["id"]
            )
        )
        conn.commit()

        cursor.execute(
            """
            SELECT t.id, t.user_id, t.subject_id, t.topic_id, t.title, t.description, t.priority,
                   t.deadline, t.planned_date, t.item_type, t.estimated_minutes,
                   t.is_completed, t.completed_at, t.created_at,
                   s.name as subject_name, s.color as subject_color
            FROM tasks t
            LEFT JOIN subjects s ON s.id = t.subject_id
            WHERE t.id = ?
            """,
            (task_id,)
        )
        row = dict(cursor.fetchone())
        row["is_completed"] = bool(row["is_completed"])
        return TaskResponse(**row)

@router.patch("/{task_id}/toggle", response_model=TaskResponse)
def toggle_task(task_id: int, current_user: dict = Depends(get_current_user)):
    """Toggles completion state of a task."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, is_completed FROM tasks WHERE id = ? AND user_id = ?", (task_id, current_user["id"]))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found.")

        new_status = 0 if row["is_completed"] else 1
        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_status == 1 else None

        cursor.execute(
            "UPDATE tasks SET is_completed = ?, completed_at = ? WHERE id = ? AND user_id = ?",
            (new_status, completed_at, task_id, current_user["id"])
        )
        conn.commit()

        cursor.execute(
            """
            SELECT t.id, t.user_id, t.subject_id, t.topic_id, t.title, t.description, t.priority,
                   t.deadline, t.planned_date, t.item_type, t.estimated_minutes,
                   t.is_completed, t.completed_at, t.created_at,
                   s.name as subject_name, s.color as subject_color
            FROM tasks t
            LEFT JOIN subjects s ON s.id = t.subject_id
            WHERE t.id = ?
            """,
            (task_id,)
        )
        d = dict(cursor.fetchone())
        d["is_completed"] = bool(d["is_completed"])
        return TaskResponse(**d)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, current_user: dict = Depends(get_current_user)):
    """Deletes a task."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tasks WHERE id = ? AND user_id = ?", (task_id, current_user["id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Task not found.")

        cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, current_user["id"]))
        conn.commit()
    return None

@router.post("/plan-my-day")
def plan_my_day(
    req: Optional[PlanMyDayRequest] = Body(None),
    available_minutes: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Intelligently organizes a student's day using pending tasks, weak topics, and available time."""
    target_minutes = 120
    if req and req.available_minutes:
        target_minutes = req.available_minutes
    elif available_minutes:
        target_minutes = available_minutes

    with get_db() as conn:
        cursor = conn.cursor()
        # Pending tasks
        cursor.execute(
            """
            SELECT t.*, s.name as subject_name, s.color as subject_color
            FROM tasks t
            LEFT JOIN subjects s ON t.subject_id = s.id
            WHERE t.user_id = ? AND t.is_completed = 0
            ORDER BY CASE t.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 END ASC, t.deadline ASC NULLS LAST
            LIMIT 10
            """,
            (current_user["id"],)
        )
        tasks = cursor.fetchall()

        # Weak topics
        cursor.execute(
            """
            SELECT tp.*, s.name as subject_name, s.color as subject_color
            FROM topics tp
            JOIN subjects s ON tp.subject_id = s.id
            WHERE tp.user_id = ? AND (tp.is_weak = 1 OR tp.needs_revision = 1)
            LIMIT 3
            """,
            (current_user["id"],)
        )
        weak_topics = cursor.fetchall()

    budget = target_minutes
    schedule = []
    used_mins = 0

    # First add weak topic revision if any
    for wt in weak_topics:
        if used_mins + 25 <= budget:
            schedule.append({
                "time_block": f"{used_mins}m - {used_mins + 25}m",
                "duration_minutes": 25,
                "title": f"Revise Weak Topic: {wt['title']}",
                "subject": wt["subject_name"],
                "subject_color": wt["subject_color"],
                "type": "revision",
                "priority": "High"
            })
            used_mins += 25
            if used_mins + 5 <= budget:
                schedule.append({
                    "time_block": f"{used_mins}m - {used_mins + 5}m",
                    "duration_minutes": 5,
                    "title": "☕ Quick Hydration Break",
                    "subject": "Rest",
                    "subject_color": "#FF9F43",
                    "type": "break",
                    "priority": "Low"
                })
                used_mins += 5

    # Then schedule pending tasks
    for t in tasks:
        task_mins = min(60, max(15, t["estimated_minutes"] or 30))
        if used_mins + task_mins <= budget:
            schedule.append({
                "time_block": f"{used_mins}m - {used_mins + task_mins}m",
                "duration_minutes": task_mins,
                "title": t["title"],
                "subject": t["subject_name"] or "General",
                "subject_color": t["subject_color"] or "#6C3BFF",
                "type": t["item_type"] or "task",
                "priority": t["priority"]
            })
            used_mins += task_mins
            if used_mins + 5 <= budget:
                schedule.append({
                    "time_block": f"{used_mins}m - {used_mins + 5}m",
                    "duration_minutes": 5,
                    "title": "🌿 Stretch & Rest Break",
                    "subject": "Rest",
                    "subject_color": "#FF9F43",
                    "type": "break",
                    "priority": "Low"
                })
                used_mins += 5

    # If remaining time
    if budget - used_mins >= 20:
        rem = budget - used_mins
        schedule.append({
            "time_block": f"{used_mins}m - {budget}m",
            "duration_minutes": rem,
            "title": "🎯 Active Recall & Practice Problems",
            "subject": "Deep Work",
            "subject_color": "#8B5CF6",
            "type": "study",
            "priority": "Medium"
        })
        used_mins = budget

    return {
        "available_minutes": budget,
        "planned_minutes": used_mins,
        "schedule": schedule,
        "summary": f"Organized {len(schedule)} focused blocks tailored to your pending workload."
    }
