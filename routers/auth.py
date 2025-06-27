from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from models.schemas import UserCreate, UserLogin, GoogleLogin, Token, UserResponse
from database.connection import get_db_connection
from utils.auth import hash_password, verify_password, create_access_token
from psycopg2.extras import RealDictCursor
import json

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    """Register a new user"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password and create user
        hashed_password = hash_password(user.password)
        cursor.execute("""
            INSERT INTO users (email, password_hash, full_name, phone, role)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, email, full_name, phone, role, is_active, created_at
        """, (user.email, hashed_password, user.full_name, user.phone, "customer"))
        
        new_user = cursor.fetchone()
        conn.commit()
        
        # Create access token
        access_token = create_access_token(
            data={"sub": str(new_user["id"]), "role": new_user["role"]}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": dict(new_user)
        }

@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    """Login user with email and password"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, email, password_hash, full_name, phone, role, is_active, created_at
            FROM users WHERE email = %s AND is_active = TRUE
        """, (user.email,))
        
        db_user = cursor.fetchone()
        if not db_user or not verify_password(user.password, db_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": str(db_user["id"]), "role": db_user["role"]}
        )
        
        user_data = dict(db_user)
        del user_data["password_hash"]  # Remove password hash from response
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_data
        }

@router.post("/google", response_model=Token)
async def google_login(google_data: GoogleLogin):
    """Login/Register with Google"""
    # Note: In production, you should verify the Google token
    # For now, this is a placeholder implementation
    
    # Extract user info from Google token (implement Google token verification)
    # This is a simplified version - implement proper Google OAuth verification
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google authentication not implemented yet"
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user information"""
    from utils.auth import get_current_user_id
    
    user_id = get_current_user_id(credentials.credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, email, full_name, phone, role, is_active, created_at
            FROM users WHERE id = %s AND is_active = TRUE
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return dict(user)
