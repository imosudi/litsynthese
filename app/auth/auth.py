import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

# Configuration settings (can be overridden via environment variables)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "litsynthese_super_secret_key_2026_research_assistant_auth")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days expiration for convenient academic workflows

# OAuth2 scheme config. Note: auto_error=False allows us to return custom 401 JSON exceptions.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token containing target claims and expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """FastAPI dependency injecting the authorized User model. Validates incoming JWT Bearer tokens."""
    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials or session expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise unauthorized_exception
        
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise unauthorized_exception
    except jwt.PyJWTError:
        raise unauthorized_exception
        
    # Check if the user exists in the database
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise unauthorized_exception
        
    return user
