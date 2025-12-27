from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.api.auth import oauth2_scheme
from app.services.docker_service import DockerService
from pydantic import BaseModel
from typing import Optional
from app.core.security import create_access_token # reuse for generating user logic if needed

# Dependency to get current user (checking token)
# Simplified for MVP
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # In real app, decode token and find user
    return True 

router = APIRouter()

class ProjectCreate(BaseModel):
    name: str
    repo_url: str # Docker Image for now
    domain: Optional[str] = None
    port: int = 80
    env_vars: Optional[dict] = {}
    provider: str = "image" # image, github

@router.post("/", response_model=dict)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db), authenticated: bool = Depends(get_current_user)):
    import secrets
    token = secrets.token_urlsafe(16)
    
    db_project = Project(
        name=project_in.name,
        repo_url=project_in.repo_url,
        domain=project_in.domain,
        port=project_in.port,
        status="stopped",
        provider=project_in.provider,
        env_vars=project_in.env_vars,
        webhook_token=token
    )
    db.add(db_project)
    db.commit()
    return {"status": "created", "id": db_project.id}

@router.post("/{project_id}/deploy")
def deploy_project(project_id: int, db: Session = Depends(get_db), authenticated: bool = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    result = DockerService.deploy_project(project)
    
    if result["status"] == "success":
        project.status = "running"
        project.last_deployed_at = datetime.utcnow()
        db.commit()
    
    return result

@router.get("/")
def list_projects(db: Session = Depends(get_db), authenticated: bool = Depends(get_current_user)):
    return db.query(Project).all()
