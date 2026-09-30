import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.models import MockTestRecordRequest, MockTestRecordResponse, AIQuizQuestion, AIQuizRequest
from app.database import get_db
from app.auth import get_current_user
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/mocktests", tags=["Subject Mock Test System"])

class MockTestGenerateRequest(BaseModel):
    subject_id: int
    topic_titles: List[str]
    difficulty: Optional[str] = "Medium"
    num_questions: Optional[int] = 5

@router.get("/eligible-topics/{subject_id}")
def get_eligible_topics(subject_id: int, current_user: dict = Depends(get_current_user)):
    """Returns only completed/studied topics for a subject that are eligible for mock tests."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM subjects WHERE id = ? AND user_id = ?", (subject_id, current_user["id"]))
        sub = cursor.fetchone()
        if not sub:
            raise HTTPException(status_code=404, detail="Subject not found.")

        cursor.execute(
            """
            SELECT id, title, chapter, is_completed, is_weak, last_mock_score
            FROM topics
            WHERE subject_id = ? AND user_id = ? AND is_completed = 1
            ORDER BY order_index ASC, id ASC
            """,
            (subject_id, current_user["id"])
        )
        completed = [dict(r) for r in cursor.fetchall()]

        # Also get all topics for reference
        cursor.execute(
            "SELECT COUNT(*) as total FROM topics WHERE subject_id = ? AND user_id = ?",
            (subject_id, current_user["id"])
        )
        total_count = cursor.fetchone()["total"]

        return {
            "subject_id": subject_id,
            "subject_name": sub["name"],
            "eligible_topics": completed,
            "eligible_count": len(completed),
            "total_topics_count": total_count
        }

@router.post("/generate-questions")
async def generate_mock_questions(req: MockTestGenerateRequest, current_user: dict = Depends(get_current_user)):
    """Generates custom mock examination questions tailored to student-selected completed topics."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM subjects WHERE id = ? AND user_id = ?", (req.subject_id, current_user["id"]))
        sub = cursor.fetchone()
        if not sub:
            raise HTTPException(status_code=404, detail="Subject not found.")
        subject_name = sub["name"]

    selected_topics = req.topic_titles if req.topic_titles else [f"Core {subject_name} Principles"]
    total_q = max(3, min(20, req.num_questions or 5))

    # Divide questions across chosen topics
    questions = []
    q_id = 1
    per_topic = max(1, total_q // len(selected_topics))

    for t_name in selected_topics:
        count = min(total_q - len(questions), per_topic)
        if count <= 0:
            break
        quiz_res = await AIService.generate_quiz(AIQuizRequest(subject=subject_name, topic=t_name, num_questions=count))
        for q in quiz_res.questions:
            q_dict = q.dict()
            q_dict["id"] = q_id
            q_dict["topic_tag"] = t_name
            q_dict["difficulty"] = req.difficulty
            questions.append(q_dict)
            q_id += 1
            if len(questions) >= total_q:
                break

    return {
        "subject_name": subject_name,
        "difficulty": req.difficulty,
        "total_questions": len(questions),
        "questions": questions
    }

@router.post("", response_model=MockTestRecordResponse, status_code=status.HTTP_201_CREATED)
def record_mock_test(data: MockTestRecordRequest, current_user: dict = Depends(get_current_user)):
    """Records a completed mock test, flags weak topics (<60%), and clears revision flags on strong topics."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        subj_id = data.subject_id
        if subj_id:
            cursor.execute("SELECT id FROM subjects WHERE id = ? AND user_id = ?", (subj_id, current_user["id"]))
            if not cursor.fetchone():
                subj_id = None

        topic_names_json = json.dumps(data.topic_names or [])
        weak_topics_json = json.dumps(data.weak_topics or [])

        cursor.execute(
            """
            INSERT INTO mock_tests (user_id, subject_id, subject_name, score, total_questions, percentage, duration_minutes, topic_names, weak_topics, difficulty, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_user["id"],
                subj_id,
                data.subject_name.strip(),
                data.score,
                data.total_questions,
                data.percentage,
                data.duration_minutes or 0,
                topic_names_json,
                weak_topics_json,
                data.difficulty or "Medium",
                data.details or ""
            )
        )
        test_id = cursor.lastrowid

        # Update topics table based on results
        if subj_id and data.weak_topics:
            for w_topic in data.weak_topics:
                cursor.execute(
                    """
                    UPDATE topics SET
                        is_weak = 1,
                        needs_revision = 1,
                        revision_reason = ?,
                        last_mock_score = ?
                    WHERE user_id = ? AND subject_id = ? AND title = ?
                    """,
                    (f"Scored low ({data.percentage}%) on Mock Test", data.percentage, current_user["id"], subj_id, w_topic)
                )

        # Clear weakness on topics with strong performance (>= 75%)
        if subj_id and data.topic_names and data.percentage >= 75:
            for s_topic in data.topic_names:
                if not data.weak_topics or s_topic not in data.weak_topics:
                    cursor.execute(
                        """
                        UPDATE topics SET
                            is_weak = 0,
                            last_mock_score = ?
                        WHERE user_id = ? AND subject_id = ? AND title = ?
                        """,
                        (data.percentage, current_user["id"], subj_id, s_topic)
                    )

        conn.commit()

        cursor.execute("SELECT * FROM mock_tests WHERE id = ?", (test_id,))
        row = cursor.fetchone()
        return MockTestRecordResponse(**dict(row))

@router.get("/recent", response_model=List[MockTestRecordResponse])
def get_recent_mock_tests(limit: int = 10, current_user: dict = Depends(get_current_user)):
    """Fetches user's recently completed mock tests."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM mock_tests
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (current_user["id"], max(1, min(50, limit)))
        )
        rows = cursor.fetchall()
        return [MockTestRecordResponse(**dict(r)) for r in rows]
