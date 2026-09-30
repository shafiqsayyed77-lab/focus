import os
import re
from datetime import datetime, date
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from database import get_db, init_db, seed_user_sample_data
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_optional_current_user,
)
from ai_service import (
    generate_study_plan,
    explain_topic,
    generate_quiz,
    is_ai_connected,
)

# Initialize database schema
init_db()

app = FastAPI(title="FocusFlow - Student Productivity Platform", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Mount static directory for CSS, JS, assets
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ----------------- Pydantic Models -----------------
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=120)
    password: str = Field(..., min_length=6, max_length=100)

class LoginRequest(BaseModel):
    email: str
    password: str

class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    color: Optional[str] = Field("#6366f1", max_length=20)
    description: Optional[str] = Field(None, max_length=300)

class SubjectUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    color: Optional[str] = Field("#6366f1", max_length=20)
    description: Optional[str] = Field(None, max_length=300)

class TaskCreate(BaseModel):
    subject_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    priority: str = Field("Medium")  # Low, Medium, High
    due_date: Optional[str] = None   # YYYY-MM-DD

class TaskUpdate(BaseModel):
    subject_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    priority: str = Field("Medium")
    due_date: Optional[str] = None
    completed: Optional[bool] = None

class StudyPlanRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=150)
    topics: str = Field(..., min_length=1, max_length=500)
    available_time: int = Field(60, ge=15, le=480)
    energy_level: str = Field("Normal")  # Low, Normal, Good, Highly Focused
    priority: str = Field("Medium")      # Low, Medium, High

class ExplainTopicRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    subject: Optional[str] = None

class GenerateQuizRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=150)
    topic: str = Field(..., min_length=1, max_length=200)
    num_questions: int = Field(4, ge=1, le=10)

# ----------------- HTML Page Routes -----------------
@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    user = get_optional_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@app.get("/login", response_class=FileResponse)
async def login_page(request: Request):
    user = get_optional_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    login_path = os.path.join(STATIC_DIR, "login.html")
    return FileResponse(login_path)

@app.get("/signup", response_class=FileResponse)
async def signup_page(request: Request):
    user = get_optional_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    signup_path = os.path.join(STATIC_DIR, "signup.html")
    return FileResponse(signup_path)

@app.get("/dashboard", response_class=FileResponse)
async def dashboard_page(request: Request):
    # Protected page
    token_user = get_optional_current_user(request)
    if not token_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    dash_path = os.path.join(STATIC_DIR, "dashboard.html")
    return FileResponse(dash_path)

@app.get("/tasks", response_class=FileResponse)
async def tasks_page(request: Request):
    # Protected page
    token_user = get_optional_current_user(request)
    if not token_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    dash_path = os.path.join(STATIC_DIR, "dashboard.html")
    return FileResponse(dash_path)

@app.get("/ai", response_class=FileResponse)
async def ai_page(request: Request):
    # Protected page
    token_user = get_optional_current_user(request)
    if not token_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    dash_path = os.path.join(STATIC_DIR, "dashboard.html")
    return FileResponse(dash_path)

# ----------------- MODULE 1: Authentication APIs -----------------
EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

@app.post("/api/auth/signup")
async def signup(payload: SignupRequest, response: Response):
    # Email format validation
    if not re.match(EMAIL_REGEX, payload.email.strip()):
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")
    
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    clean_email = payload.email.strip().lower()
    clean_name = payload.name.strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (clean_email,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    hashed = hash_password(payload.password)
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, streak, study_minutes_today) VALUES (?, ?, ?, ?, ?)",
        (clean_name, clean_email, hashed, 5, 165)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    # Seed sample subjects and study tasks for the new student
    seed_user_sample_data(user_id)

    token = create_access_token({"sub": user_id, "email": clean_email, "name": clean_name})
    
    # Set cookie for direct browser navigation
    response.set_cookie(
        key="focusflow_token",
        value=token,
        httponly=False,
        max_age=7 * 24 * 3600,
        samesite="lax",
        secure=False
    )

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user_id,
            "name": clean_name,
            "email": clean_email,
            "streak": 5,
            "study_minutes_today": 165
        }
    }

@app.post("/api/auth/login")
async def login(payload: LoginRequest, response: Response):
    clean_email = payload.email.strip().lower()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (clean_email,))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token({"sub": user["id"], "email": user["email"], "name": user["name"]})

    response.set_cookie(
        key="focusflow_token",
        value=token,
        httponly=False,
        max_age=7 * 24 * 3600,
        samesite="lax",
        secure=False
    )

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "streak": user["streak"],
            "study_minutes_today": user["study_minutes_today"]
        }
    }

@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("focusflow_token")
    return {"success": True, "message": "Logged out successfully."}

@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"success": True, "user": current_user}

# ----------------- MODULE 2: Dashboard APIs -----------------
@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    conn = get_db()
    cursor = conn.cursor()

    # Total tasks & completed tasks counts
    cursor.execute("SELECT COUNT(*) as total FROM tasks WHERE user_id = ?", (user_id,))
    total_tasks = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as completed FROM tasks WHERE user_id = ? AND completed = 1", (user_id,))
    completed_tasks = cursor.fetchone()["completed"]

    pending_tasks = total_tasks - completed_tasks
    completion_rate = round((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0

    # Today's study time format
    minutes = current_user.get("study_minutes_today", 165)
    hours = minutes // 60
    rem_min = minutes % 60
    formatted_time = f"{hours}h {rem_min:02d}m"

    # Fetch subjects list with task counts
    cursor.execute("""
        SELECT s.id, s.name, s.code, s.color, s.description,
               COUNT(t.id) as total_tasks,
               SUM(CASE WHEN t.completed = 1 THEN 1 ELSE 0 END) as completed_tasks
        FROM subjects s
        LEFT JOIN tasks t ON s.id = t.subject_id
        WHERE s.user_id = ?
        GROUP BY s.id
        ORDER BY s.id ASC
    """, (user_id,))
    subjects = [dict(row) for row in cursor.fetchall()]

    # Fetch today's tasks (or top active tasks for the student)
    cursor.execute("""
        SELECT t.*, s.name as subject_name, s.code as subject_code, s.color as subject_color
        FROM tasks t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.user_id = ?
        ORDER BY t.completed ASC,
                 CASE t.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                 t.due_date ASC,
                 t.id DESC
        LIMIT 6
    """, (user_id,))
    today_tasks = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "success": True,
        "user": current_user,
        "stats": {
            "study_time_today": formatted_time,
            "study_minutes_today": minutes,
            "tasks_completed_today": completed_tasks,
            "tasks_total": total_tasks,
            "tasks_pending": pending_tasks,
            "completion_rate": completion_rate,
            "streak": current_user.get("streak", 5)
        },
        "today_tasks": today_tasks,
        "subjects": subjects
    }

# ----------------- MODULE 3: Subjects APIs -----------------
@app.get("/api/subjects")
async def list_subjects(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*,
               COUNT(t.id) as total_tasks,
               SUM(CASE WHEN t.completed = 0 THEN 1 ELSE 0 END) as pending_tasks,
               SUM(CASE WHEN t.completed = 1 THEN 1 ELSE 0 END) as completed_tasks
        FROM subjects s
        LEFT JOIN tasks t ON s.id = t.subject_id
        WHERE s.user_id = ?
        GROUP BY s.id
        ORDER BY s.id DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    subjects = []
    for r in rows:
        d = dict(r)
        d["pending_tasks"] = d["pending_tasks"] or 0
        d["completed_tasks"] = d["completed_tasks"] or 0
        subjects.append(d)
    return {"success": True, "subjects": subjects}

@app.post("/api/subjects")
async def create_subject(payload: SubjectCreate, current_user: dict = Depends(get_current_user)):
    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Subject name must be at least 2 characters.")

    code = payload.code.strip() if payload.code else ""
    color = payload.color.strip() if payload.color else "#6366f1"
    desc = payload.description.strip() if payload.description else ""

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO subjects (user_id, name, code, color, description) VALUES (?, ?, ?, ?, ?)",
        (current_user["id"], name, code, color, desc)
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.execute("SELECT * FROM subjects WHERE id = ?", (new_id,))
    subj = dict(cursor.fetchone())
    conn.close()

    subj["total_tasks"] = 0
    subj["pending_tasks"] = 0
    subj["completed_tasks"] = 0
    return {"success": True, "subject": subj}

@app.put("/api/subjects/{subject_id}")
async def update_subject(subject_id: int, payload: SubjectUpdate, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (subject_id, current_user["id"]))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Subject not found or unauthorized.")

    name = payload.name.strip()
    code = payload.code.strip() if payload.code else ""
    color = payload.color.strip() if payload.color else "#6366f1"
    desc = payload.description.strip() if payload.description else ""

    cursor.execute(
        "UPDATE subjects SET name = ?, code = ?, color = ?, description = ? WHERE id = ?",
        (name, code, color, desc, subject_id)
    )
    conn.commit()
    cursor.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
    subj = dict(cursor.fetchone())
    conn.close()

    return {"success": True, "subject": subj}

@app.delete("/api/subjects/{subject_id}")
async def delete_subject(subject_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (subject_id, current_user["id"]))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Subject not found or unauthorized.")

    # Delete tasks under subject first (in case SQLite foreign_keys disabled)
    cursor.execute("DELETE FROM tasks WHERE subject_id = ? AND user_id = ?", (subject_id, current_user["id"]))
    cursor.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Subject and all associated tasks deleted."}

# ----------------- MODULE 3: Tasks APIs -----------------
@app.get("/api/tasks")
async def list_tasks(
    subject_id: Optional[int] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None, # 'pending', 'completed', 'all'
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT t.*, s.name as subject_name, s.code as subject_code, s.color as subject_color
        FROM tasks t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.user_id = ?
    """
    params = [user_id]

    if subject_id:
        query += " AND t.subject_id = ?"
        params.append(subject_id)

    if priority and priority in ("Low", "Medium", "High"):
        query += " AND t.priority = ?"
        params.append(priority)

    if status == "pending":
        query += " AND t.completed = 0"
    elif status == "completed":
        query += " AND t.completed = 1"

    query += """
        ORDER BY t.completed ASC,
                 CASE t.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                 t.due_date ASC,
                 t.id DESC
    """

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    tasks = [dict(r) for r in rows]
    return {
        "success": True,
        "tasks": tasks,
        "count": len(tasks),
        "pending_count": sum(1 for t in tasks if not t["completed"]),
        "completed_count": sum(1 for t in tasks if t["completed"])
    }

@app.post("/api/tasks")
async def create_task(payload: TaskCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Task title cannot be empty.")

    priority = payload.priority if payload.priority in ("Low", "Medium", "High") else "Medium"
    due_date = payload.due_date.strip() if payload.due_date else None

    # Verify subject belongs to user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (payload.subject_id, user_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Selected subject does not exist or is invalid.")

    cursor.execute(
        """INSERT INTO tasks (user_id, subject_id, title, description, priority, due_date, completed)
           VALUES (?, ?, ?, ?, ?, ?, 0)""",
        (user_id, payload.subject_id, title, payload.description, priority, due_date)
    )
    conn.commit()
    new_id = cursor.lastrowid

    cursor.execute("""
        SELECT t.*, s.name as subject_name, s.code as subject_code, s.color as subject_color
        FROM tasks t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.id = ?
    """, (new_id,))
    task = dict(cursor.fetchone())
    conn.close()

    return {"success": True, "task": task}

@app.put("/api/tasks/{task_id}")
async def update_task(task_id: int, payload: TaskUpdate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found or unauthorized.")

    # Verify subject belongs to user
    cursor.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (payload.subject_id, user_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid subject selected.")

    title = payload.title.strip()
    if not title:
        conn.close()
        raise HTTPException(status_code=400, detail="Task title cannot be empty.")

    priority = payload.priority if payload.priority in ("Low", "Medium", "High") else "Medium"
    due_date = payload.due_date.strip() if payload.due_date else None
    
    completed_val = existing["completed"]
    completed_at = existing["completed_at"]
    if payload.completed is not None:
        completed_val = 1 if payload.completed else 0
        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if completed_val else None

    cursor.execute("""
        UPDATE tasks
        SET subject_id = ?, title = ?, description = ?, priority = ?, due_date = ?, completed = ?, completed_at = ?
        WHERE id = ?
    """, (payload.subject_id, title, payload.description, priority, due_date, completed_val, completed_at, task_id))
    conn.commit()

    cursor.execute("""
        SELECT t.*, s.name as subject_name, s.code as subject_code, s.color as subject_color
        FROM tasks t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.id = ?
    """, (task_id,))
    task = dict(cursor.fetchone())
    conn.close()

    return {"success": True, "task": task}

@app.patch("/api/tasks/{task_id}/toggle")
async def toggle_task_status(task_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, completed FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    task = cursor.fetchone()
    if not task:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found or unauthorized.")

    new_status = 0 if task["completed"] == 1 else 1
    completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_status == 1 else None

    cursor.execute(
        "UPDATE tasks SET completed = ?, completed_at = ? WHERE id = ?",
        (new_status, completed_at, task_id)
    )
    conn.commit()

    cursor.execute("""
        SELECT t.*, s.name as subject_name, s.code as subject_code, s.color as subject_color
        FROM tasks t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.id = ?
    """, (task_id,))
    updated = dict(cursor.fetchone())
    conn.close()

    return {"success": True, "task": updated}

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found or unauthorized.")

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Task deleted successfully."}

# ----------------- MODULE 4: AI Study Assistant APIs -----------------
@app.get("/api/ai/status")
async def get_ai_status(current_user: dict = Depends(get_current_user)):
    return {
        "success": True,
        "is_connected": is_ai_connected(),
        "mode": "live" if is_ai_connected() else "demo"
    }

@app.post("/api/ai/study-plan")
async def create_study_plan_endpoint(payload: StudyPlanRequest, current_user: dict = Depends(get_current_user)):
    plan = await generate_study_plan(
        subject=payload.subject,
        topics=payload.topics,
        available_time_minutes=payload.available_time,
        energy_level=payload.energy_level,
        priority=payload.priority
    )
    return plan

@app.post("/api/ai/explain")
async def explain_topic_endpoint(payload: ExplainTopicRequest, current_user: dict = Depends(get_current_user)):
    explanation = await explain_topic(
        topic=payload.topic,
        subject=payload.subject
    )
    return explanation

@app.post("/api/ai/quiz")
async def generate_quiz_endpoint(payload: GenerateQuizRequest, current_user: dict = Depends(get_current_user)):
    quiz = await generate_quiz(
        subject=payload.subject,
        topic=payload.topic,
        num_questions=payload.num_questions
    )
    return quiz

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
