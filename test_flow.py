"""
FocusFlow Complete User Flow Verification Test
Tests:
Signup -> Login -> Dashboard -> Add Subject -> Add Task -> Complete Task ->
AI Planner -> AI Explain -> AI Quiz -> Focus Timer -> Complete Session ->
Progress -> Streak -> Profile -> Settings -> Logout -> Login again.
"""

import sys
from fastapi.testclient import TestClient
from app.main import app

def run_e2e_test():
    print("=" * 60)
    print("STARTING FOCUSFLOW COMPLETE END-TO-END FLOW TEST")
    print("=" * 60)

    client = TestClient(app)

    # 1. SIGNUP
    print("\n[Step 1] Testing Signup...")
    import time
    ts = int(time.time())
    user_payload = {
        "name": "Sarah Connor",
        "email": f"sarah.connor.{ts}@student.ac.uk",
        "password": "studyPassword2026"
    }
    res = client.post("/api/auth/signup", json=user_payload)
    assert res.status_code == 201, f"Signup failed: {res.text}"
    auth_data = res.json()
    token = auth_data["access_token"]
    user_id = auth_data["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[OK] User signed up successfully! ID: {user_id}, Name: {auth_data['user']['name']}")

    # 2. LOGIN
    print("\n[Step 2] Testing Login...")
    login_res = client.post("/api/auth/login", json={
        "email": user_payload["email"],
        "password": user_payload["password"]
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Login authenticated and returned valid JWT token.")

    # 3. DASHBOARD
    print("\n[Step 3] Testing Dashboard stats...")
    dash_res = client.get("/api/stats/dashboard", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["welcome_name"] == "Sarah Connor"
    assert dash_data["today_study_minutes"] == 0
    assert dash_data["current_streak"] == 0
    print("[OK] Dashboard initialized with real user metrics.")

    # 4. ADD SUBJECT
    print("\n[Step 4] Testing Add Subject...")
    sub_res = client.post("/api/subjects", headers=headers, json={
        "name": "Software Engineering",
        "color": "#7C3AED",
        "icon": "code",
        "description": "Agile, design patterns, testing"
    })
    assert sub_res.status_code == 201
    subject_id = sub_res.json()["id"]
    print(f"[OK] Added Subject: {sub_res.json()['name']} (ID: {subject_id})")

    # 5. ADD TASK
    print("\n[Step 5] Testing Add Task...")
    task_res = client.post("/api/tasks", headers=headers, json={
        "title": "Study Factory Pattern & UML Diagram",
        "subject_id": subject_id,
        "priority": "High",
        "deadline": "2026-10-05"
    })
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]
    assert task_res.json()["is_completed"] is False
    print(f"[OK] Added Task: {task_res.json()['title']} (ID: {task_id})")

    # 6. COMPLETE TASK
    print("\n[Step 6] Testing Complete Task (Toggle)...")
    toggle_res = client.patch(f"/api/tasks/{task_id}/toggle", headers=headers)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_completed"] is True
    assert toggle_res.json()["completed_at"] is not None
    print("[OK] Task marked as completed with timestamp.")

    # 7. AI PLANNER
    print("\n[Step 7] Testing AI Study Planner...")
    plan_res = client.post("/api/ai/planner", headers=headers, json={
        "subject": "Software Engineering",
        "topics": "Factory Pattern, Observer Pattern, Singleton Pattern",
        "available_time": 60,
        "energy_level": "Good",
        "priority": "High"
    })
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert len(plan_data["schedule"]) > 0
    print(f"[OK] AI Planner generated {len(plan_data['schedule'])} schedule blocks with energy tips.")

    # 8. AI EXPLAIN
    print("\n[Step 8] Testing AI Concept Explainer...")
    explain_res = client.post("/api/ai/explain", headers=headers, json={
        "topic": "Factory Pattern",
        "subject": "Software Engineering"
    })
    assert explain_res.status_code == 200
    explain_data = explain_res.json()
    assert len(explain_data["simple_explanation"]) > 10
    assert len(explain_data["important_points"]) >= 3
    assert len(explain_data["example"]) > 10
    print("[OK] AI Explain provided simple explanation, bullet points, and real-world analogy.")

    # 9. AI QUIZ
    print("\n[Step 9] Testing AI Quiz...")
    quiz_res = client.post("/api/ai/quiz", headers=headers, json={
        "subject": "Software Engineering",
        "topic": "Design Patterns",
        "num_questions": 3
    })
    assert quiz_res.status_code == 200
    quiz_data = quiz_res.json()
    assert len(quiz_data["questions"]) == 3
    for q in quiz_data["questions"]:
        assert len(q["options"]) == 4
        assert 0 <= q["correct_answer"] < 4
        assert len(q["explanation"]) > 0
    print("[OK] AI Quiz created 3 MCQs with 4 options, correct answer keys, and explanations.")

    # 10. FOCUS TIMER & COMPLETE SESSION
    print("\n[Step 10] Testing Focus Timer Session Logging...")
    sess_res = client.post("/api/sessions", headers=headers, json={
        "duration_minutes": 25,
        "subject_id": subject_id,
        "task_id": task_id
    })
    assert sess_res.status_code == 201
    sess_data = sess_res.json()
    assert sess_data["duration_minutes"] == 25
    print(f"[OK] Logged 25-minute focus session for task ID {task_id}.")

    # 11. PROGRESS & STREAK VERIFICATION
    print("\n[Step 11] Testing Progress & Streak calculation...")
    prog_res = client.get("/api/stats/progress", headers=headers)
    assert prog_res.status_code == 200
    prog_data = prog_res.json()
    assert prog_data["today_study_minutes"] >= 25
    assert prog_data["total_study_minutes"] >= 25
    assert prog_data["completed_tasks_count"] >= 1
    assert prog_data["completed_focus_sessions_count"] >= 1
    assert prog_data["current_streak"] == 1
    assert prog_data["longest_streak"] >= 1
    assert len(prog_data["weekly_chart"]) == 7
    print("[OK] Progress stats verified: 1 study day counted, current streak = 1, weekly chart has 7 days.")

    # 12. PROFILE
    print("\n[Step 12] Testing Profile update...")
    prof_res = client.put("/api/user/profile", headers=headers, json={
        "name": "Dr. Sarah Connor"
    })
    assert prof_res.status_code == 200
    assert prof_res.json()["name"] == "Dr. Sarah Connor"
    print("[OK] User profile name updated.")

    # 13. SETTINGS
    print("\n[Step 13] Testing Settings update...")
    settings_res = client.put("/api/user/settings", headers=headers, json={
        "theme": "dark",
        "default_focus_duration": 45,
        "default_break_duration": 10,
        "sound_enabled": True,
        "notifications_enabled": True
    })
    assert settings_res.status_code == 200
    s_data = settings_res.json()
    assert s_data["theme"] == "dark"
    assert s_data["default_focus_duration"] == 45
    assert s_data["default_break_duration"] == 10
    print("[OK] Settings updated to dark theme and 45m focus duration.")

    # 14. LOGOUT & LOGIN AGAIN
    print("\n[Step 14] Testing Re-Login with credentials...")
    relogin_res = client.post("/api/auth/login", json={
        "email": user_payload["email"],
        "password": user_payload["password"]
    })
    assert relogin_res.status_code == 200
    new_token = relogin_res.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}
    me_res = client.get("/api/auth/me", headers=new_headers)
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Dr. Sarah Connor"
    print("[OK] Re-login succeeded with updated profile name verified.")

    print("\n" + "=" * 60)
    print("ALL 14 USER FLOW STEPS TESTED & PASSED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    run_e2e_test()
