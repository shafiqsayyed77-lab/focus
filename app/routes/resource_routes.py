from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.models import ResourceCreateRequest, ResourceUpdateRequest, ResourceResponse
from app.database import get_db
from app.auth import get_current_user

router = APIRouter(prefix="/api/resources", tags=["Resources & Notes Library"])

@router.get("", response_model=List[ResourceResponse])
def get_resources(
    subject_id: Optional[int] = Query(None),
    topic_id: Optional[int] = Query(None),
    resource_type: Optional[str] = Query(None, alias="type"),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves saved notes, cheat sheets, links, formulas, and reminders."""
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT r.*, s.name as subject_name, tp.title as topic_title
            FROM resources r
            LEFT JOIN subjects s ON r.subject_id = s.id
            LEFT JOIN topics tp ON r.topic_id = tp.id
            WHERE r.user_id = ?
        """
        params = [current_user["id"]]

        if subject_id is not None:
            query += " AND r.subject_id = ?"
            params.append(subject_id)

        if topic_id is not None:
            query += " AND r.topic_id = ?"
            params.append(topic_id)

        if resource_type is not None:
            query += " AND r.type = ?"
            params.append(resource_type)

        query += " ORDER BY r.created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [ResourceResponse(**dict(r)) for r in rows]

@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
def create_resource(data: ResourceCreateRequest, current_user: dict = Depends(get_current_user)):
    """Saves a new note, cheat-sheet formula, or resource link."""
    clean_title = data.title.strip()
    if not clean_title:
        raise HTTPException(status_code=400, detail="Resource title cannot be empty.")

    with get_db() as conn:
        cursor = conn.cursor()
        if data.subject_id:
            cursor.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (data.subject_id, current_user["id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="Subject not found.")

        cursor.execute(
            """
            INSERT INTO resources (user_id, subject_id, topic_id, title, type, content, url, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_user["id"], data.subject_id, data.topic_id, clean_title,
                data.type or "note", data.content, (data.url or "").strip(), (data.tags or "").strip()
            )
        )
        res_id = cursor.lastrowid
        conn.commit()

        cursor.execute(
            """
            SELECT r.*, s.name as subject_name, tp.title as topic_title
            FROM resources r
            LEFT JOIN subjects s ON r.subject_id = s.id
            LEFT JOIN topics tp ON r.topic_id = tp.id
            WHERE r.id = ?
            """,
            (res_id,)
        )
        row = cursor.fetchone()
        return ResourceResponse(**dict(row))

@router.put("/{resource_id}", response_model=ResourceResponse)
def update_resource(resource_id: int, data: ResourceUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Updates an existing resource item."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE id = ? AND user_id = ?", (resource_id, current_user["id"]))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Resource not found.")

        title = data.title.strip() if data.title is not None else existing["title"]
        subject_id = data.subject_id if data.subject_id is not None else existing["subject_id"]
        topic_id = data.topic_id if data.topic_id is not None else existing["topic_id"]
        res_type = data.type if data.type is not None else existing["type"]
        content = data.content if data.content is not None else existing["content"]
        url = data.url if data.url is not None else existing["url"]
        tags = data.tags if data.tags is not None else existing["tags"]

        cursor.execute(
            """
            UPDATE resources SET
                title = ?, subject_id = ?, topic_id = ?, type = ?, content = ?, url = ?, tags = ?
            WHERE id = ? AND user_id = ?
            """,
            (title, subject_id, topic_id, res_type, content, url, tags, resource_id, current_user["id"])
        )
        conn.commit()

        cursor.execute(
            """
            SELECT r.*, s.name as subject_name, tp.title as topic_title
            FROM resources r
            LEFT JOIN subjects s ON r.subject_id = s.id
            LEFT JOIN topics tp ON r.topic_id = tp.id
            WHERE r.id = ?
            """,
            (resource_id,)
        )
        row = cursor.fetchone()
        return ResourceResponse(**dict(row))

@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(resource_id: int, current_user: dict = Depends(get_current_user)):
    """Deletes a resource."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM resources WHERE id = ? AND user_id = ?", (resource_id, current_user["id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Resource not found.")

        cursor.execute("DELETE FROM resources WHERE id = ? AND user_id = ?", (resource_id, current_user["id"]))
        conn.commit()
    return None
