from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.models import (
    UserResponse, ProfileUpdateRequest, PasswordChangeRequest,
    UserSettingsResponse, UserSettingsUpdateRequest
)
from app.database import get_db, seed_starter_topics_for_subject
from app.auth import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/user", tags=["User Profile & Settings"])

class OnboardingRequest(BaseModel):
    course: str
    institution: Optional[str] = ""
    semester: Optional[str] = ""
    study_goal_minutes: Optional[int] = 60
    subjects: Optional[List[str]] = []
    exam_title: Optional[str] = None
    exam_date: Optional[str] = None
    exam_subject: Optional[str] = None

@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: dict = Depends(get_current_user)):
    """Fetches user profile details including academic workspace fields."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, course, institution, semester, study_goal_minutes, onboarding_completed, created_at FROM users WHERE id = ?", (current_user["id"],))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found.")
        d = dict(row)
        d["onboarding_completed"] = bool(d.get("onboarding_completed", 0))
        return UserResponse(**d)

@router.put("/profile", response_model=UserResponse)
def update_profile(data: ProfileUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Updates user display name and academic setup (course, institution, semester, goal)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (current_user["id"],))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="User not found.")

        name = data.name.strip() if data.name is not None else existing["name"]
        if len(name) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters long.")

        course = data.course if data.course is not None else (existing["course"] or "")
        institution = data.institution if data.institution is not None else (existing["institution"] or "")
        semester = data.semester if data.semester is not None else (existing["semester"] or "")
        goal = data.study_goal_minutes if data.study_goal_minutes is not None else (existing["study_goal_minutes"] or 60)
        onboarding = (1 if data.onboarding_completed else 0) if data.onboarding_completed is not None else (existing["onboarding_completed"] or 0)

        cursor.execute(
            """
            UPDATE users SET
                name = ?,
                course = ?,
                institution = ?,
                semester = ?,
                study_goal_minutes = ?,
                onboarding_completed = ?
            WHERE id = ?
            """,
            (name, course, institution, semester, goal, onboarding, current_user["id"])
        )

        cursor.execute("SELECT id, name, email, course, institution, semester, study_goal_minutes, onboarding_completed, created_at FROM users WHERE id = ?", (current_user["id"],))
        updated = dict(cursor.fetchone())
        updated["onboarding_completed"] = bool(updated.get("onboarding_completed", 0))
        return UserResponse(**updated)

@router.post("/onboarding")
def complete_onboarding(data: OnboardingRequest, current_user: dict = Depends(get_current_user)):
    """Creates the student's initial academic workspace: course, semester, custom subjects, and optional exam."""
    with get_db() as conn:
        cursor = conn.cursor()
        # 1. Update academic profile
        cursor.execute(
            """
            UPDATE users SET
                course = ?,
                institution = ?,
                semester = ?,
                study_goal_minutes = ?,
                onboarding_completed = 1
            WHERE id = ?
            """,
            (
                data.course.strip(),
                (data.institution or "").strip(),
                (data.semester or "").strip(),
                data.study_goal_minutes or 60,
                current_user["id"]
            )
        )

        # 2. Add custom subjects
        created_subject_ids = {}
        colors = ["#6C3BFF", "#8B5CF6", "#FF6B6B", "#FF9F43", "#06B6D4", "#10B981"]
        for idx, sub_name in enumerate(data.subjects or []):
            name_clean = sub_name.strip()
            if name_clean:
                color = colors[idx % len(colors)]
                cursor.execute(
                    "INSERT INTO subjects (user_id, name, color, icon) VALUES (?, ?, ?, 'book')",
                    (current_user["id"], name_clean, color)
                )
                sub_id = cursor.lastrowid
                created_subject_ids[name_clean.lower()] = sub_id

        # 3. Add exam if specified
        if data.exam_title and data.exam_date:
            target_sub_id = None
            if data.exam_subject and data.exam_subject.strip().lower() in created_subject_ids:
                target_sub_id = created_subject_ids[data.exam_subject.strip().lower()]
            elif created_subject_ids:
                target_sub_id = list(created_subject_ids.values())[0]

            if target_sub_id:
                cursor.execute(
                    """
                    INSERT INTO exams (user_id, subject_id, title, exam_date, target_score, notes)
                    VALUES (?, ?, ?, ?, 90, 'Initial target exam created during onboarding')
                    """,
                    (current_user["id"], target_sub_id, data.exam_title.strip(), data.exam_date.strip())
                )

        conn.commit()
    return {"success": True, "message": "Academic workspace created successfully!"}

@router.post("/password")
def change_password(data: PasswordChangeRequest, current_user: dict = Depends(get_current_user)):
    """Securely updates user password after verifying the existing password."""
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (current_user["id"],))
        user_row = cursor.fetchone()
        
        if not user_row or not verify_password(data.current_password, user_row["password_hash"]):
            raise HTTPException(status_code=400, detail="Current password does not match.")

        new_hash = hash_password(data.new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, current_user["id"]))

    return {"message": "Password changed successfully."}

@router.get("/settings", response_model=UserSettingsResponse)
def get_settings(current_user: dict = Depends(get_current_user)):
    """Retrieves user application preferences."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (current_user["id"],))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                """
                INSERT INTO user_settings (user_id, theme, default_focus_duration, default_break_duration, notifications_enabled, sound_enabled)
                VALUES (?, 'light', 25, 5, 1, 1)
                """,
                (current_user["id"],)
            )
            cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (current_user["id"],))
            row = cursor.fetchone()

        d = dict(row)
        d["notifications_enabled"] = bool(d["notifications_enabled"])
        d["sound_enabled"] = bool(d["sound_enabled"])
        return UserSettingsResponse(**d)

@router.put("/settings", response_model=UserSettingsResponse)
def update_settings(data: UserSettingsUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Updates user theme, timer defaults, and notification preferences."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (current_user["id"],))
        existing = cursor.fetchone()

        theme = data.theme if data.theme is not None else (existing["theme"] if existing else "light")
        focus_dur = data.default_focus_duration if data.default_focus_duration is not None else (existing["default_focus_duration"] if existing else 25)
        break_dur = data.default_break_duration if data.default_break_duration is not None else (existing["default_break_duration"] if existing else 5)
        notifications = (1 if data.notifications_enabled else 0) if data.notifications_enabled is not None else (existing["notifications_enabled"] if existing else 1)
        sound = (1 if data.sound_enabled else 0) if data.sound_enabled is not None else (existing["sound_enabled"] if existing else 1)

        cursor.execute(
            """
            INSERT INTO user_settings (user_id, theme, default_focus_duration, default_break_duration, notifications_enabled, sound_enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(user_id) DO UPDATE SET
                theme = excluded.theme,
                default_focus_duration = excluded.default_focus_duration,
                default_break_duration = excluded.default_break_duration,
                notifications_enabled = excluded.notifications_enabled,
                sound_enabled = excluded.sound_enabled,
                updated_at = excluded.updated_at
            """,
            (current_user["id"], theme, focus_dur, break_dur, notifications, sound)
        )

        cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (current_user["id"],))
        updated = dict(cursor.fetchone())
        updated["notifications_enabled"] = bool(updated["notifications_enabled"])
        updated["sound_enabled"] = bool(updated["sound_enabled"])
        return UserSettingsResponse(**updated)
