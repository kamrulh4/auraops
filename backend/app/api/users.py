from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, Permission
from app.api.projects import get_current_user
from app.core.security import get_password_hash
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()

class UserCreateAdmin(BaseModel):
    email: str
    username: str
    password: str
    role: str = "developer"  # admin, developer, viewer
    is_active: bool = True

class UserUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

from app.api.projects import ProjectResponse

class UserProjectsResponse(BaseModel):
    user_id: int
    username: str
    project_count: int
    projects: list[ProjectResponse]
    
    class Config:
        from_attributes = True

def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin role"""
    if user.role != "admin" and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

@router.get("/", response_model=list[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """List all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/me", response_model=UserResponse)
def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user info"""
    return user

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user by ID"""
    
    # Users can view their own profile, admins can view anyone
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.post("/", response_model=UserResponse)
def create_user(
    user_in: UserCreateAdmin,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Create a new user (admin only)"""
    
    # Check if email exists
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username exists
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Validate role
    if user_in.role not in ["admin", "developer", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        is_active=user_in.is_active,
        is_superuser=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Update user (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent modifying superuser
    if user.is_superuser and admin.id != user.id:
        raise HTTPException(status_code=403, detail="Cannot modify superuser")
    
    # Update fields
    if user_in.email:
        # Check uniqueness
        existing = db.query(User).filter(
            User.email == user_in.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = user_in.email
    
    if user_in.username:
        existing = db.query(User).filter(
            User.username == user_in.username,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already in use")
        user.username = user_in.username
    
    if user_in.role:
        if user_in.role not in ["admin", "developer", "viewer"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = user_in.role
    
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    
    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Delete user (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting superuser
    if user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot delete superuser")
    
    # Prevent self-deletion
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    db.delete(user)
    db.commit()
    
    return {"status": "deleted", "user_id": user_id}

@router.get("/{user_id}/projects", response_model=UserProjectsResponse)
def get_user_projects(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all projects owned by a user"""
    
    # Users can view their own projects, admins can view anyone's
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    from app.models.project import Project
    projects = db.query(Project).filter(Project.owner_id == user_id).all()
    
    return {
        "user_id": user_id,
        "username": user.username,
        "project_count": len(projects),
        "projects": projects
    }
