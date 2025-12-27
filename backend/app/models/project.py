from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from app.db.session import Base
from datetime import datetime

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    port = Column(Integer, default=3000)
    
    # Source Config
    provider = Column(String, default="image") # 'image', 'github'
    repo_url = Column(String) # For 'image' this is image name, for 'github' it's the https url
    build_context = Column(String, default="/", nullable=True) # Path to build context inside repo
    dockerfile_path = Column(String, default="Dockerfile", nullable=True) # Path to Dockerfile
    
    # Deployment State
    status = Column(String, default="stopped") # stopped, building, running, failed
    last_deployed_at = Column(DateTime, nullable=True)
    
    # Secrets
    webhook_token = Column(String, unique=True, index=True)
    env_vars = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
