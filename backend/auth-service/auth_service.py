import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr
from shared.database import User, get_db  # Import from shared database module

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", 168))  # 7 days default

# Pydantic models for request/response
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    username: Optional[str] = None
    company_name: Optional[str] = None
    team_size: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    company_name: Optional[str]
    team_size: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    token: str
    user: UserResponse
    message: str

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    
    @staticmethod
    def create_jwt_token(user_data: Dict[str, Any]) -> str:
        """Create a JWT token for the user"""
        payload = {
            "user_id": user_data["id"],
            "email": user_data["email"],
            "username": user_data["username"],
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def verify_jwt_token(token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def validate_team_size(team_size: str) -> bool:
        """Validate team size options"""
        valid_sizes = ["1-10", "11-50", "51-200", "201-1000", "+1000"]
        return team_size in valid_sizes
    
    @staticmethod
    def create_user(db: Session, user_data: UserRegister) -> User:
        """Create a new user"""
        # Check if user already exists
        existing_user = AuthService.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        # Validate team size if provided
        if user_data.team_size and not AuthService.validate_team_size(user_data.team_size):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid team size option"
            )
        
        # Generate username if not provided
        username = user_data.username
        if not username:
            username = user_data.email.split('@')[0]
            # Ensure username is unique
            counter = 1
            base_username = username
            while AuthService.get_user_by_username(db, username):
                username = f"{base_username}{counter}"
                counter += 1
        else:
            # Check if provided username is already taken
            existing_username = AuthService.get_user_by_username(db, username)
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already exists"
                )
        
        # Create new user
        hashed_password = AuthService.hash_password(user_data.password)
        db_user = User(
            email=user_data.email,
            username=username,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            company_name=user_data.company_name,
            team_size=user_data.team_size,
            is_active=True,
            is_verified=False  # In production, require email verification
        )
        
        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return db_user
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = AuthService.get_user_by_email(db, email)
        if not user:
            return None
        
        if not AuthService.verify_password(password, user.password_hash):
            return None
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        return user
    
    @staticmethod
    def login_user(db: Session, login_data: UserLogin) -> LoginResponse:
        """Login user and return token"""
        user = AuthService.authenticate_user(db, login_data.email, login_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create JWT token
        token_data = {
            "id": user.id,
            "email": user.email,
            "username": user.username
        }
        token = AuthService.create_jwt_token(token_data)
        
        # Return response
        user_response = UserResponse.model_validate(user)
        return LoginResponse(
            token=token,
            user=user_response,
            message="Login successful"
        )
    
    @staticmethod
    def register_user(db: Session, register_data: UserRegister) -> LoginResponse:
        """Register new user and return token"""
        # Validate password strength
        if len(register_data.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Additional password validation
        if not any(c.isupper() for c in register_data.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must contain at least one uppercase letter"
            )
        
        if not any(c.islower() for c in register_data.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must contain at least one lowercase letter"
            )
        
        if not any(c.isdigit() for c in register_data.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must contain at least one number"
            )
        
        # Create user
        user = AuthService.create_user(db, register_data)
        
        # Create JWT token
        token_data = {
            "id": user.id,
            "email": user.email,
            "username": user.username
        }
        token = AuthService.create_jwt_token(token_data)
        
        # Return response
        user_response = UserResponse.model_validate(user)
        return LoginResponse(
            token=token,
            user=user_response,
            message="Registration successful"
        )
    
    @staticmethod
    def get_current_user(db: Session, token: str) -> User:
        """Get current user from JWT token"""
        payload = AuthService.verify_jwt_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        return user