import urllib.request
import urllib.parse
import json
import time
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_URL = "http://127.0.0.1:8000"

def api_call(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    encoded_data = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else None
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        return e.code, json.loads(content) if content else {"detail": str(e)}

def run_tests():
    print("=== STARTING FULL STUDENT LIFECYCLE VERIFICATION ===")
    
    # 1. Health check
    status, body = api_call("/health")
    assert status == 200, f"Health check failed: {body}"
    print("✓ Server is healthy")

    # 2. Signup new student
    email = f"student_{int(time.time())}@university.edu"
    signup_data = {
        "name": "Jordan Lee",
        "email": email,
        "password": "studyStrong2026!"
    }
    status, user_res = api_call("/api/auth/signup", method="POST", data=signup_data)
    assert status == 201, f"Signup failed: {user_res}"
    token = user_res["access_token"]
    print(f"✓ Registered new student: {user_res['user']['name']} ({email})")

    # 3. Verify brand new student starts with 0 subjects (clean workspace, no fake hardcoded subjects)
    status, subs = api_call("/api/subjects", token=token)
    assert status == 200
    assert len(subs) == 0, f"Expected 0 subjects for fresh user, found {len(subs)}"
    print("✓ Verified clean workspace: new student starts with 0 subjects")

    # 4. Student completes Personal Academic Setup (Onboarding)
    onboarding_data = {
        "course": "BSc Computer Science",
        "institution": "University Institute of Technology",
        "semester": "Semester 4",
        "study_goal_minutes": 90,
        "subjects": [
            "Distributed Systems",
            "Cloud Computing",
            "Machine Learning",
            "Information Security",
            "Compiler Design"
        ],
        "exam_title": "Distributed Systems Mid-term",
        "exam_subject": "Distributed Systems",
        "exam_date": "2026-10-25"
    }
    status, onb_res = api_call("/api/user/onboarding", method="POST", data=onboarding_data, token=token)
    assert status == 200, f"Onboarding failed: {onb_res}"
    print("✓ Successfully completed Academic Onboarding with 5 custom subjects and 1 upcoming exam")

    # 5. Verify subjects are created
    status, subs = api_call("/api/subjects", token=token)
    assert len(subs) == 5, f"Expected 5 subjects, found {len(subs)}"
    sub_map = {s["name"]: s["id"] for s in subs}
    ds_id = sub_map["Distributed Systems"]
    print(f"✓ Verified 5 custom subjects created in database: {list(sub_map.keys())}")

    # 6. Add unlimited topics inside a subject
    topics_to_add = [
        {"title": "RPC Architecture & gRPC", "chapter": "Unit 1: Communication", "priority": "High"},
        {"title": "Raft Consensus Algorithm", "chapter": "Unit 2: Consistency", "priority": "High"},
        {"title": "CAP Theorem & PACELC", "chapter": "Unit 2: Consistency", "priority": "Medium"},
        {"title": "Vector Clocks & Lamport Timestamps", "chapter": "Unit 3: Time & Order", "priority": "Low"}
    ]
    topic_ids = {}
    for t in topics_to_add:
        status, created = api_call(f"/api/subjects/{ds_id}/topics", method="POST", data=t, token=token)
        assert status == 201
        topic_ids[created["title"]] = created["id"]
    print(f"✓ Added 4 custom syllabus topics with chapters & priorities: {list(topic_ids.keys())}")

    # 7. Complete a topic (Raft Consensus Algorithm)
    raft_id = topic_ids["Raft Consensus Algorithm"]
    status, toggled = api_call(f"/api/subjects/topics/{raft_id}/toggle", method="PATCH", token=token)
    assert status == 200
    assert toggled["is_completed"] == True
    print("✓ Student studied and completed: 'Raft Consensus Algorithm'")

    # 8. Check subject progress %
    status, subj_detail = api_call(f"/api/subjects/{ds_id}", token=token)
    assert status == 200
    assert subj_detail["completed_topics_count"] == 1
    assert subj_detail["progress_percent"] == 25
    print(f"✓ Progress dynamically calculated: {subj_detail['progress_percent']}% complete (1/4 topics)")

    # 9. Log a Focus Timer session linked to subject & topic
    session_data = {
        "subject_id": ds_id,
        "topic_id": raft_id,
        "duration_minutes": 25,
        "completed_at": "2026-09-30 18:30:00"
    }
    status, sess = api_call("/api/sessions", method="POST", data=session_data, token=token)
    assert status == 201, f"Focus session failed: {sess}"
    print("✓ Focus Timer recorded 25 minutes linked to Distributed Systems -> Raft Consensus")

    # 10. Planner item creation & Plan My Day
    planner_item = {
        "title": "Implement Raft election timer in Go",
        "subject_id": ds_id,
        "item_type": "assignment",
        "priority": "High",
        "estimated_minutes": 45,
        "deadline": "2026-10-05",
        "description": "Lab exercise on leader election states"
    }
    status, task = api_call("/api/tasks", method="POST", data=planner_item, token=token)
    assert status == 201
    print("✓ Created academic planner item with deadline & priority")

    status, plan = api_call("/api/tasks/plan-my-day", method="POST", data={"available_minutes": 120}, token=token)
    assert status == 200, f"Plan my day failed: {plan}"
    assert len(plan["schedule"]) > 0
    print(f"✓ 'Plan My Day' generated daily schedule: {len(plan['schedule'])} time blocks ({plan['planned_minutes']} min)")

    # 11. Exam Preparation Mode check
    status, exams = api_call("/api/exams", token=token)
    assert status == 200
    assert len(exams) >= 1
    exam = exams[0]
    print(f"✓ Exam Prep Mode active: '{exam['title']}' — {exam['days_remaining']} days remaining, {exam['readiness_percent']}% readiness")

    # 12. Check eligible mock test topics
    status, eligible = api_call(f"/api/mocktests/eligible-topics/{ds_id}", token=token)
    assert status == 200
    assert any(t["title"] == "Raft Consensus Algorithm" for t in eligible["eligible_topics"])
    print("✓ Mock test engine verified: completed topic 'Raft Consensus Algorithm' is eligible for test")

    # 13. Submit Mock Test with weak performance on Raft -> triggers weak topic detection
    mock_result = {
        "subject_id": ds_id,
        "subject_name": "Distributed Systems",
        "score": 2,
        "total_questions": 5,
        "percentage": 40,
        "difficulty": "Medium",
        "topic_names": ["Raft Consensus Algorithm"],
        "weak_topics": ["Raft Consensus Algorithm"],
        "details": json.dumps({"topic_scores": {"Raft Consensus Algorithm": 40}})
    }
    status, test_res = api_call("/api/mocktests", method="POST", data=mock_result, token=token)
    assert status == 201, f"Mock test submission failed: {test_res}"
    print("✓ Submitted Mock Test: scored 40% on Raft Consensus Algorithm")

    # 14. Verify Smart Revision Engine automatically collected the weak topic
    status, rev_queue = api_call("/api/revision", token=token)
    assert status == 200
    assert len(rev_queue) >= 1, "Expected weak topic in revision queue"
    found_weak = any(r["topic_title"] == "Raft Consensus Algorithm" for r in rev_queue)
    assert found_weak, "Raft Consensus Algorithm not found in revision queue!"
    print(f"✓ Smart Revision Engine automatically queued weak topic: '{rev_queue[0]['topic_title']}' (Reason: {rev_queue[0]['reason']})")

    # 15. Mark topic as revised
    status, marked = api_call(f"/api/revision/mark-revised/{raft_id}", method="POST", token=token)
    assert status == 200, f"Mark revised failed: {marked}"
    print("✓ Marked topic as revised -> retention updated")

    # 16. Resource creation & Global Search
    res_data = {
        "title": "Raft State Machine Safety Invariant",
        "subject_id": ds_id,
        "type": "formula",
        "content": "If a leader has applied an entry at given index, no other server will ever apply a different entry for that index.",
        "tags": "raft, consensus, invariant"
    }
    status, saved_res = api_call("/api/resources", method="POST", data=res_data, token=token)
    assert status == 201
    print("✓ Saved formula resource into Academic Library")

    # Global search
    status, search_data = api_call("/api/search?q=Raft", token=token)
    assert status == 200
    assert len(search_data["topics"]) > 0 or len(search_data["notes"]) > 0
    print(f"✓ Global Search for 'Raft' successfully returned {len(search_data['topics'])} topics and {len(search_data['notes'])} notes")

    # 17. Quick Capture
    qc_data = {
        "item_type": "task",
        "data": {
            "title": "Review Vector Clock causality rules",
            "subject_id": ds_id,
            "priority": "Medium",
            "estimated_minutes": 30
        }
    }
    status, qc_res = api_call("/api/quick-capture", method="POST", data=qc_data, token=token)
    assert status == 201
    print("✓ Quick Capture instantly created task")

    # 18. Dashboard stats check
    status, d_stats = api_call("/api/stats/dashboard", token=token)
    assert status == 200
    assert d_stats["welcome_name"] == "Jordan Lee"
    assert d_stats["course"] == "BSc Computer Science"
    assert d_stats["today_study_minutes"] == 25
    print(f"✓ Dashboard stats verified: {d_stats['welcome_name']}, {d_stats['course']}, study minutes: {d_stats['today_study_minutes']}")

    # 19. Analytics & Achievements check
    status, a_stats = api_call("/api/stats/analytics", token=token)
    assert status == 200
    assert len(a_stats["weekly_chart"]) == 7
    assert len(a_stats["achievements"]) == 7
    unlocked = [ach["title"] for ach in a_stats["achievements"] if ach["unlocked"]]
    print(f"✓ Analytics chart rendered: 7 days. Unlocked achievements based on real activity: {unlocked}")

    # 20. AI Coach recommendation
    status, rec = api_call("/api/ai/recommend-next", token=token)
    assert status == 200
    print(f"✓ AI Coach recommended next action: '{rec['headline']}' ({rec['reason']})")

    print("\n=======================================================")
    print("🎉 ALL 20 INTEGRATION TESTS PASSED WITH 100% REAL DATA!")
    print("=======================================================")

if __name__ == "__main__":
    run_tests()
