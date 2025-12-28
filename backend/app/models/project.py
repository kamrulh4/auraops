from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base
from datetime import datetime

class Project(Base):
    """Enhanced Project model supporting multiple deployment types"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Deployment Type
    deployment_type = Column(String, default="docker_image")
    # Options: docker_image, dockerfile, docker_compose, static_build, service
    
    # Source Configuration
    provider = Column(String, default="image")  # image, github, upload
    repo_url = Column(String, nullable=True)  # Docker image name OR Git repo URL
    branch = Column(String, default="main", nullable=True)
    
    # Docker Configuration
    dockerfile_path = Column(String, default="Dockerfile", nullable=True)
    build_context = Column(String, default="/", nullable=True)
    compose_file = Column(Text, nullable=True)  # Full docker-compose.yml content
    
    # Static Build Configuration
    install_command = Column(String, nullable=True)  # e.g., "npm install"
    build_command = Column(String, nullable=True)  # e.g., "npm run build"
    static_dir = Column(String, nullable=True)  # e.g., "dist", "out", "build"
    
    # Runtime Configuration
    port = Column(Integer, default=3000)
    env_vars = Column(JSON, default={})
    
    # Deployment State
    status = Column(String, default="stopped")
    # Options: stopped, building, running, failed, deploying
    last_deployed_at = Column(DateTime, nullable=True)
    build_logs = Column(Text, nullable=True)
    
    # Secrets
    webhook_token = Column(String, unique=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    owner = relationship("User", back_populates="projects")
    domains = relationship("Domain", back_populates="project", cascade="all, delete-orphan")
    
    @property
    def internal_url(self):
        """Generate internal URL for service-to-service communication"""
        return f"http://auraops-app-{self.id}:{self.port}"
    
    @property
    def is_static(self):
        """Check if project is a static build"""
        return self.deployment_type == "static_build"
    
    @property
    def is_service(self):
        """Check if project is a managed service (DB, cache, etc.)"""
        return self.deployment_type == "service"
