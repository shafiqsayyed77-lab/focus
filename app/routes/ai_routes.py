from typing import Optional, List, Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.models import (
    AIPlannerRequest, AIPlannerResponse,
    AIExplainRequest, AIExplainResponse,
    AIQuizRequest, AIQuizResponse
)
from app.database import get_db
from app.auth import get_current_user
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/ai", tags=["AI Study Coach"])

class DiagramRequest(BaseModel):
    topic: str

class VivaRequest(BaseModel):
    topic: str

class WeaknessAnalysisRequest(BaseModel):
    subject: str
    score: int
    weak_topics: List[str]

@router.post("/planner", response_model=AIPlannerResponse)
async def generate_study_plan(request: AIPlannerRequest, current_user: dict = Depends(get_current_user)):
    """Generates an actionable, time-blocked study schedule tailored to subject, energy, and available time."""
    try:
        return await AIService.generate_study_plan(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate study plan: {str(e)}")

@router.post("/explain", response_model=AIExplainResponse)
async def explain_topic(request: AIExplainRequest, current_user: dict = Depends(get_current_user)):
    """Explains a concept with student-friendly language, key takeaways, and real-world analogy."""
    try:
        return await AIService.explain_topic(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to explain topic: {str(e)}")

@router.post("/quiz", response_model=AIQuizResponse)
async def generate_quiz(request: AIQuizRequest, current_user: dict = Depends(get_current_user)):
    """Generates practice multiple-choice questions with 4 options, answer key, and reasoning."""
    try:
        return await AIService.generate_quiz(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")

@router.post("/diagram")
async def generate_diagram(req: DiagramRequest, current_user: dict = Depends(get_current_user)):
    """Generates a visual concept diagram and step-by-step mental model."""
    topic = req.topic.strip()
    return {
        "topic": topic,
        "title": f"Concept Flow: {topic}",
        "steps": [
            {
                "num": 1,
                "stage": "Input / Protocol Initialization",
                "detail": f"State parameters are initialized; packet headers or entity schemas are validated for {topic}."
            },
            {
                "num": 2,
                "stage": "Core Processing & Execution",
                "detail": "Underlying logic processes state transitions, computes routes/queries, and verifies constraints."
            },
            {
                "num": 3,
                "stage": "State Transition & Output",
                "detail": "Generates verified response, updates persistent cache, and emits acknowledgment/result."
            }
        ],
        "explanation": f"Understanding {topic} requires seeing how information moves from initial request through internal validation to the output state."
    }

@router.post("/viva")
async def generate_viva(req: VivaRequest, current_user: dict = Depends(get_current_user)):
    """Generates challenging viva voce questions and model answers for oral examinations."""
    topic = req.topic.strip()
    return {
        "topic": topic,
        "questions": [
            {
                "q": f"What is the fundamental engineering problem that {topic} solves?",
                "model_answer": f"Without {topic}, systems suffer from scalability bottlenecks or data inconsistency. It abstracts low-level mechanics to provide reliable guarantees."
            },
            {
                "q": f"What happens in an edge case or failure scenario during {topic}?",
                "model_answer": "Failure scenarios trigger timeout mechanisms, fallbacks, or idempotent rollbacks to prevent cascade failures and maintain integrity."
            },
            {
                "q": f"How does {topic} compare to its modern alternatives in production?",
                "model_answer": "Trade-offs evaluate latency versus memory footprint, hardware overhead, and developer ergonomics."
            }
        ]
    }

@router.post("/weakness")
async def analyze_weakness(req: WeaknessAnalysisRequest, current_user: dict = Depends(get_current_user)):
    """Provides actionable diagnostic feedback on weak mock test areas."""
    weak_list = req.weak_topics or [req.subject]
    return {
        "subject": req.subject,
        "score": req.score,
        "weak_topics": weak_list,
        "diagnosis": f"Your score of {req.score}% indicates solid general intuition, but specific gaps exist in: {', '.join(weak_list)}.",
        "actionable_steps": [
            f"Review concise concept breakdowns for {weak_list[0]} using AI Explainer.",
            "Write down the core formula / state lifecycle by hand in the Notes library.",
            f"Launch a 25-minute Pomodoro focus session dedicated to {weak_list[0]}.",
            "Retake a 5-question targeted mock test to prove 80%+ comprehension."
        ]
    }

@router.get("/recommend-next")
def recommend_next_topic(current_user: dict = Depends(get_current_user)):
    """
    AI Study Coach 'What Should I Study?' recommendation engine:
    Evaluates upcoming exams, unfinished syllabus topics, weak topics, and study activity.
    """
    user_id = current_user["id"]
    today_str = datetime.now().strftime("%Y-%m-%d")

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Check for upcoming exam within 14 days
        cursor.execute(
            """
            SELECT e.*, s.name as subject_name, s.color as subject_color
            FROM exams e
            JOIN subjects s ON e.subject_id = s.id
            WHERE e.user_id = ? AND e.exam_date >= ?
            ORDER BY e.exam_date ASC
            LIMIT 1
            """,
            (user_id, today_str)
        )
        exam = cursor.fetchone()

        # 2. Check for weak topics
        cursor.execute(
            """
            SELECT tp.*, s.name as subject_name, s.color as subject_color
            FROM topics tp
            JOIN subjects s ON tp.subject_id = s.id
            WHERE tp.user_id = ? AND (tp.is_weak = 1 OR tp.needs_revision = 1)
            ORDER BY tp.is_weak DESC, tp.id ASC
            LIMIT 1
            """,
            (user_id,)
        )
        weak_topic = cursor.fetchone()

        # 3. Check for next incomplete topic
        cursor.execute(
            """
            SELECT tp.*, s.name as subject_name, s.color as subject_color
            FROM topics tp
            JOIN subjects s ON tp.subject_id = s.id
            WHERE tp.user_id = ? AND tp.is_completed = 0
            ORDER BY tp.priority = 'High' DESC, tp.order_index ASC
            LIMIT 1
            """,
            (user_id,)
        )
        next_topic = cursor.fetchone()

    if exam:
        try:
            days = (datetime.strptime(exam["exam_date"], "%Y-%m-%d").date() - date.today()).days
        except Exception:
            days = 7

        if weak_topic and weak_topic["subject_id"] == exam["subject_id"]:
            return {
                "recommendation_type": "exam_weakness",
                "subject_id": exam["subject_id"],
                "subject_name": exam["subject_name"],
                "topic_id": weak_topic["id"],
                "topic_title": weak_topic["title"],
                "headline": f"Lock In: {exam['subject_name']} Exam in {days} Days",
                "reason": f"Your {exam['subject_name']} exam is coming up and '{weak_topic['title']}' was flagged during practice.",
                "suggested_minutes": 30,
                "suggested_action": "Revise Weak Topic & Retest"
            }
        else:
            target_topic = next_topic["title"] if (next_topic and next_topic["subject_id"] == exam["subject_id"]) else "Exam Practice Bank"
            return {
                "recommendation_type": "exam_prep",
                "subject_id": exam["subject_id"],
                "subject_name": exam["subject_name"],
                "topic_id": next_topic["id"] if next_topic else None,
                "topic_title": target_topic,
                "headline": f"Exam Countdown: {days} Days Until {exam['title']}",
                "reason": f"Syllabus mastery on {exam['subject_name']} should take top priority before exam day.",
                "suggested_minutes": 45,
                "suggested_action": "Complete Next Syllabus Topic"
            }

    if weak_topic:
        return {
            "recommendation_type": "weak_topic",
            "subject_id": weak_topic["subject_id"],
            "subject_name": weak_topic["subject_name"],
            "topic_id": weak_topic["id"],
            "topic_title": weak_topic["title"],
            "headline": f"Master Weak Area: {weak_topic['title']}",
            "reason": f"Revision required in {weak_topic['subject_name']}. Clearing weak areas yields the largest score jumps.",
            "suggested_minutes": 25,
            "suggested_action": "25-min Pomodoro Revision"
        }

    if next_topic:
        return {
            "recommendation_type": "syllabus_progress",
            "subject_id": next_topic["subject_id"],
            "subject_name": next_topic["subject_name"],
            "topic_id": next_topic["id"],
            "topic_title": next_topic["title"],
            "headline": f"Next Up: {next_topic['title']}",
            "reason": f"Keep your momentum moving forward in {next_topic['subject_name']}.",
            "suggested_minutes": 30,
            "suggested_action": "Start Focus Session"
        }

    return {
        "recommendation_type": "fresh_start",
        "subject_id": None,
        "subject_name": "Personal Academic Workspace",
        "topic_id": None,
        "topic_title": "Setup Your Courses",
        "headline": "Ready to build your roadmap?",
        "reason": "Add your subjects, chapters, and upcoming exam dates to get personalized AI study recommendations.",
        "suggested_minutes": 15,
        "suggested_action": "Add Subject"
    }
