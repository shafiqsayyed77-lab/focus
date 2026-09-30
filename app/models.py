from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field

# =====================================================================
# 1. User & Academic Profile Models
# =====================================================================
class UserSignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=6, max_length=128, description="Password with minimum 6 characters")
    course: Optional[str] = Field(default="", max_length=150)
    institution: Optional[str] = Field(default="", max_length=150)
    semester: Optional[str] = Field(default="", max_length=100)

class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User's registered email")
    password: str = Field(..., min_length=1, description="Password")

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    course: Optional[str] = ""
    institution: Optional[str] = ""
    semester: Optional[str] = ""
    study_goal_minutes: Optional[int] = 60
    onboarding_completed: Optional[bool] = False
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token: Optional[str] = None
    token_type: str = "bearer"
    user: UserResponse

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    course: Optional[str] = Field(None, max_length=150)
    institution: Optional[str] = Field(None, max_length=150)
    semester: Optional[str] = Field(None, max_length=100)
    study_goal_minutes: Optional[int] = Field(None, ge=15, le=720)
    onboarding_completed: Optional[bool] = None

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)

# =====================================================================
# 2. Subject Models
# =====================================================================
class SubjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6C3BFF", max_length=20)
    icon: str = Field(default="book", max_length=30)
    description: Optional[str] = Field(default="", max_length=300)

class SubjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=20)
    icon: Optional[str] = Field(None, max_length=30)
    description: Optional[str] = Field(None, max_length=300)

class SubjectResponse(BaseModel):
    id: int
    user_id: int
    name: str
    color: str
    icon: str
    description: Optional[str] = ""
    created_at: str
    task_count: Optional[int] = 0
    topic_count: Optional[int] = 0
    completed_topics_count: Optional[int] = 0
    progress_percent: Optional[int] = 0
    study_time_minutes: Optional[int] = 0
    mock_test_score: Optional[int] = None
    weak_topics_count: Optional[int] = 0

# =====================================================================
# 3. Topic Models (Roadmap & Mini Learning Space)
# =====================================================================
class TopicCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    chapter: Optional[str] = Field(default="General", max_length=150)
    priority: Optional[str] = Field(default="Medium", pattern="^(Low|Medium|High)$")
    notes: Optional[str] = Field(default="", max_length=5000)
    resources: Optional[str] = Field(default="", max_length=2000)

class TopicUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    chapter: Optional[str] = Field(None, max_length=150)
    status: Optional[str] = Field(None, pattern="^(not_started|in_progress|completed)$")
    priority: Optional[str] = Field(None, pattern="^(Low|Medium|High)$")
    order_index: Optional[int] = None
    is_completed: Optional[bool] = None
    notes: Optional[str] = None
    resources: Optional[str] = None
    is_weak: Optional[bool] = None
    needs_revision: Optional[bool] = None
    revision_reason: Optional[str] = None
    last_mock_score: Optional[int] = None

class TopicResponse(BaseModel):
    id: int
    subject_id: int
    user_id: int
    title: str
    chapter: Optional[str] = "General"
    status: Optional[str] = "not_started"
    priority: Optional[str] = "Medium"
    order_index: Optional[int] = 0
    notes: Optional[str] = ""
    resources: Optional[str] = ""
    is_weak: Optional[bool] = False
    needs_revision: Optional[bool] = False
    revision_reason: Optional[str] = ""
    last_studied_at: Optional[str] = None
    last_mock_score: Optional[int] = None
    is_completed: bool
    completed_at: Optional[str] = None
    created_at: str

# =====================================================================
# 4. Task & Planner Models
# =====================================================================
class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    item_type: Optional[str] = Field(default="task", pattern="^(task|assignment|exam|project|revision|study)$")
    estimated_minutes: Optional[int] = Field(default=30, ge=5, le=480)
    description: Optional[str] = Field(default="", max_length=1000)
    priority: str = Field(default="Medium", pattern="^(Low|Medium|High)$")
    deadline: Optional[str] = None
    planned_date: Optional[str] = None

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    item_type: Optional[str] = Field(None, pattern="^(task|assignment|exam|project|revision|study)$")
    estimated_minutes: Optional[int] = Field(None, ge=5, le=480)
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(Low|Medium|High)$")
    deadline: Optional[str] = None
    planned_date: Optional[str] = None
    is_completed: Optional[bool] = None

class TaskResponse(BaseModel):
    id: int
    user_id: int
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    subject_color: Optional[str] = None
    topic_id: Optional[int] = None
    item_type: Optional[str] = "task"
    estimated_minutes: Optional[int] = 30
    title: str
    description: Optional[str] = ""
    priority: str
    deadline: Optional[str] = None
    planned_date: Optional[str] = None
    is_completed: bool
    completed_at: Optional[str] = None
    created_at: str

# =====================================================================
# 5. Exam Preparation Models
# =====================================================================
class ExamCreateRequest(BaseModel):
    subject_id: int = Field(..., description="Target subject ID")
    title: str = Field(..., min_length=1, max_length=150)
    exam_date: str = Field(..., description="YYYY-MM-DD")
    target_score: Optional[int] = Field(default=90, ge=1, le=100)
    notes: Optional[str] = Field(default="", max_length=2000)

class ExamUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    exam_date: Optional[str] = None
    target_score: Optional[int] = Field(None, ge=1, le=100)
    notes: Optional[str] = None
    prep_roadmap: Optional[str] = None

class ExamResponse(BaseModel):
    id: int
    user_id: int
    subject_id: int
    subject_name: str
    subject_color: str
    title: str
    exam_date: str
    target_score: int
    notes: Optional[str] = ""
    prep_roadmap: Optional[str] = None
    days_remaining: int
    topics_total: int
    topics_completed: int
    topics_remaining: int
    weak_topics_count: int
    revision_pending_count: int
    mock_test_avg: Optional[int] = None
    study_hours: float
    readiness_percent: int
    created_at: str

# =====================================================================
# 6. Revision Engine Models
# =====================================================================
class RevisionItemResponse(BaseModel):
    id: int
    topic_id: int
    topic_title: str
    subject_id: int
    subject_name: str
    subject_color: str
    chapter: str
    reason: str
    last_studied: Optional[str] = None
    last_score: Optional[int] = None
    is_weak: bool

# =====================================================================
# 7. Focus Session Models
# =====================================================================
class FocusSessionCreateRequest(BaseModel):
    duration_minutes: int = Field(..., ge=1, le=240, description="Duration in minutes")
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    task_id: Optional[int] = None

class FocusSessionResponse(BaseModel):
    id: int
    user_id: int
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    topic_id: Optional[int] = None
    topic_title: Optional[str] = None
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    duration_minutes: int
    completed_at: str
    created_at: str

# =====================================================================
# 8. Resources & Notes Library Models
# =====================================================================
class ResourceCreateRequest(BaseModel):
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    type: str = Field(default="note", pattern="^(note|link|formula|file|reminder)$")
    content: str = Field(..., min_length=1)
    url: Optional[str] = Field(default="", max_length=500)
    tags: Optional[str] = Field(default="", max_length=200)

class ResourceUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    subject_id: Optional[int] = None
    topic_id: Optional[int] = None
    type: Optional[str] = Field(None, pattern="^(note|link|formula|file|reminder)$")
    content: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[str] = None

class ResourceResponse(BaseModel):
    id: int
    user_id: int
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    topic_id: Optional[int] = None
    topic_title: Optional[str] = None
    title: str
    type: str
    content: str
    url: Optional[str] = ""
    tags: Optional[str] = ""
    created_at: str

# =====================================================================
# 9. Mock Test Models
# =====================================================================
class MockTestRecordRequest(BaseModel):
    subject_id: Optional[int] = None
    subject_name: str = Field(..., min_length=1, max_length=150)
    score: int = Field(..., ge=0)
    total_questions: int = Field(..., gt=0)
    percentage: int = Field(..., ge=0, le=100)
    duration_minutes: Optional[int] = Field(default=0, ge=0)
    topic_names: Optional[List[str]] = Field(default=[])
    weak_topics: Optional[List[str]] = Field(default=[])
    difficulty: Optional[str] = Field(default="Medium")
    details: Optional[str] = None

class MockTestRecordResponse(BaseModel):
    id: int
    user_id: int
    subject_id: Optional[int] = None
    subject_name: str
    score: int
    total_questions: int
    percentage: int
    duration_minutes: int
    topic_names: Optional[str] = None
    weak_topics: Optional[str] = None
    difficulty: Optional[str] = "Medium"
    created_at: str

# =====================================================================
# 10. Settings Models
# =====================================================================
class UserSettingsResponse(BaseModel):
    id: int
    user_id: int
    theme: str
    default_focus_duration: int
    default_break_duration: int
    notifications_enabled: bool
    sound_enabled: bool

class UserSettingsUpdateRequest(BaseModel):
    theme: Optional[str] = Field(None, pattern="^(light|dark)$")
    default_focus_duration: Optional[int] = Field(None, ge=5, le=120)
    default_break_duration: Optional[int] = Field(None, ge=1, le=60)
    notifications_enabled: Optional[bool] = None
    sound_enabled: Optional[bool] = None

# =====================================================================
# 11. AI Models
# =====================================================================
class AIPlannerRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    topics: str = Field(..., min_length=1)
    available_time: int = Field(..., ge=15, le=480, description="Total study time in minutes")
    energy_level: str = Field(default="Normal", pattern="^(Low|Normal|Good|Highly Focused)$")
    priority: str = Field(default="Medium", pattern="^(Low|Medium|High)$")

class AIScheduleItem(BaseModel):
    topic: str
    duration_minutes: int
    activity: str
    tips: Optional[str] = ""

class AIPlannerResponse(BaseModel):
    subject: str
    total_minutes: int
    energy_level: str
    strategy_summary: str
    schedule: List[AIScheduleItem]
    energy_advice: str

class AIExplainRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    subject: Optional[str] = None

class AIExplainResponse(BaseModel):
    topic: str
    simple_explanation: str
    important_points: List[str]
    example: str
    memory_tip: Optional[str] = ""

class AIQuizRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)
    num_questions: int = Field(default=5, ge=1, le=15)

class AIQuizQuestion(BaseModel):
    id: int
    question: str
    options: List[str]
    correct_answer: int
    explanation: str
    topic_tag: Optional[str] = None

class AIQuizResponse(BaseModel):
    subject: str
    topic: str
    questions: List[AIQuizQuestion]

class AIDiagramRequest(BaseModel):
    topic: str = Field(..., min_length=1)

class AIDiagramResponse(BaseModel):
    topic: str
    title: str
    diagram_type: str
    ascii_art: str
    flow_steps: List[str]
    explanation: str

class AIVivaRequest(BaseModel):
    topic: str = Field(..., min_length=1)

class AIVivaResponse(BaseModel):
    topic: str
    questions: List[Dict[str, str]]

class AIWeaknessAnalysisRequest(BaseModel):
    subject: str
    score: int
    weak_topics: List[str]

class AIRecommendStudyRequest(BaseModel):
    energy_level: Optional[str] = "Normal"
    available_time_mins: Optional[int] = 45

# =====================================================================
# 12. Dashboard, Progress, Achievements & Search Models
# =====================================================================
class UpcomingExamItem(BaseModel):
    id: int
    title: str
    subject_name: str
    subject_color: str
    days_left: int
    exam_date: str
    readiness_percent: int

class DashboardStatsResponse(BaseModel):
    welcome_name: str
    course: Optional[str] = ""
    today_study_minutes: int
    today_completed_tasks: int
    current_streak: int
    today_pending_tasks_count: int
    today_progress_percent: int
    pending_tasks: List[TaskResponse]
    overall_progress_percent: int
    total_subjects_count: int
    total_topics_count: int
    completed_topics_count: int
    weak_topics_count: int
    upcoming_exams: List[UpcomingExamItem]
    continue_subject_name: Optional[str] = None
    continue_topic_title: Optional[str] = None
    recommended_action: Optional[str] = None

class WeeklyChartDay(BaseModel):
    date: str
    day_name: str
    minutes: int

class SubjectStudyTime(BaseModel):
    subject_name: str
    color: str
    minutes: int
    percentage: int

class AchievementItem(BaseModel):
    id: str
    title: str
    icon: str
    description: str
    unlocked: bool
    progress_text: str

class AnalyticsStatsResponse(BaseModel):
    today_study_minutes: int
    total_study_minutes: int
    completed_tasks_count: int
    completed_focus_sessions_count: int
    current_streak: int
    longest_streak: int
    weekly_chart: List[WeeklyChartDay]
    subject_study_times: List[SubjectStudyTime]
    total_mock_tests: int
    average_mock_score: int
    weak_topics_list: List[str]
    strong_topics_list: List[str]
    most_productive_day: str
    attention_subject: Optional[str] = None
    achievements: List[AchievementItem]

class GlobalSearchResponse(BaseModel):
    query: str
    subjects: List[Dict[str, Any]]
    topics: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    exams: List[Dict[str, Any]]
    notes: List[Dict[str, Any]]
