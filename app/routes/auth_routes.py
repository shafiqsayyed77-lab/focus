from fastapi import APIRouter, HTTPException, status, Depends
from app.models import UserSignupRequest, UserLoginRequest, TokenResponse, UserResponse
from app.database import get_db
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(data: UserSignupRequest):
    """Registers a new user account, creates default preferences and sample subjects."""
    clean_email = data.email.strip().lower()
    clean_name = data.name.strip()
    
    if len(clean_name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters long.")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if email is already taken
        cursor.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE", (clean_email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists. Please log in instead."
            )
        
        # Hash password and create user
        pwd_hash = hash_password(data.password)
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (clean_name, clean_email, pwd_hash)
        )
        user_id = cursor.lastrowid

        # Create default user settings
        cursor.execute(
            """
            INSERT INTO user_settings (user_id, theme, default_focus_duration, default_break_duration, notifications_enabled, sound_enabled)
            VALUES (?, 'light', 25, 5, 1, 1)
            """,
            (user_id,)
        )

        cursor.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,))
        user_row = dict(cursor.fetchone())

    token = create_access_token(data={"sub": str(user_id)})
    return TokenResponse(
        access_token=token,
        token=token,
        token_type="bearer",
        user=UserResponse(**user_row)
    )

@router.post("/login", response_model=TokenResponse)
def login(data: UserLoginRequest):
    """Authenticates a user with email and password, returning a JWT token."""
    clean_email = data.email.strip().lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, email, password_hash, created_at,
                   course, institution, semester, study_goal_minutes, onboarding_completed
            FROM users WHERE email = ? COLLATE NOCASE
            """,
            (clean_email,)
        )
        user = cursor.fetchone()
        
        if not user or not verify_password(data.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. Please verify your credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_row = {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"],
            "course": user["course"] or "",
            "institution": user["institution"] or "",
            "semester": user["semester"] or "",
            "study_goal_minutes": user["study_goal_minutes"] or 60,
            "onboarding_completed": bool(user["onboarding_completed"])
        }

    token = create_access_token(data={"sub": str(user_row["id"])})
    return TokenResponse(
        access_token=token,
        token=token,
        token_type="bearer",
        user=UserResponse(**user_row)
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """Retrieves current authenticated user's profile info."""
    d = dict(current_user)
    d["course"] = d.get("course") or ""
    d["institution"] = d.get("institution") or ""
    d["semester"] = d.get("semester") or ""
    d["study_goal_minutes"] = d.get("study_goal_minutes") or 60
    d["onboarding_completed"] = bool(d.get("onboarding_completed", 0))
    return UserResponse(**d)
