from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db.session import Base
from datetime import datetime

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    repo_url = Column(String)
    branch = Column(String, default="main")
    domain = Column(String, unique=True, index=True, nullable=True)
    port = Column(Integer, default=3000)
    
    # Deployment State
    status = Column(String, default="stopped") # stopped, building, running, failed
    last_deployed_at = Column(DateTime, nullable=True)
    
    # Secrets
    webhook_token = Column(String, unique=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
