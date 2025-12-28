from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
from datetime import datetime

class User(Base):
    """Enhanced User model with RBAC support"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Role-Based Access Control
    role = Column(String, default="developer")  # admin, developer, viewer
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relations
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Permission:
    """Role-based permissions"""
    ADMIN = ["*"]  # Full access
    DEVELOPER = [
        "projects:create",
        "projects:read",
        "projects:update",
        "projects:delete",
        "projects:deploy",
        "domains:create",
        "domains:read",
        "domains:delete"
    ]
    VIEWER = [
        "projects:read",
        "domains:read"
    ]
    
    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        """Check if role has permission"""
        role_perms = getattr(cls, role.upper(), [])
        if "*" in role_perms:
            return True
        return permission in role_perms
