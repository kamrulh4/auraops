from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User, Permission
from app.api.auth import oauth2_scheme
from app.services.docker_service import DockerService
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt
from app.core.config import settings

router = APIRouter()

# Dependency to get current user from token
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# Permission checker
def require_permission(permission: str):
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not Permission.has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )
        return user
    return permission_checker

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    deployment_type: str = "docker_image"  # docker_image, dockerfile, docker_compose, static_build, service
    provider: str = "image"  # image, github, upload
    repo_url: Optional[str] = None
    branch: Optional[str] = "main"
    dockerfile_path: Optional[str] = "Dockerfile"
    build_context: Optional[str] = "/"
    compose_file: Optional[str] = None
    install_command: Optional[str] = None  # For static builds
    build_command: Optional[str] = None    # For static builds
    static_dir: Optional[str] = None       # For static builds
    port: int = 3000
    env_vars: Optional[dict] = {}

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    env_vars: Optional[dict] = None
    port: Optional[int] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    deployment_type: str
    provider: str
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    status: str
    last_deployed_at: Optional[datetime] = None
    port: int
    env_vars: dict
    webhook_token: Optional[str] = None
    internal_url: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True

@router.post("/", response_model=dict)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:create"))
):
    import secrets
    token = secrets.token_urlsafe(16)
    
    db_project = Project(
        name=project_in.name,
        description=project_in.description,
        owner_id=user.id,
        deployment_type=project_in.deployment_type,
        provider=project_in.provider,
        repo_url=project_in.repo_url,
        branch=project_in.branch,
        dockerfile_path=project_in.dockerfile_path,
        build_context=project_in.build_context,
        compose_file=project_in.compose_file,
        install_command=project_in.install_command,
        build_command=project_in.build_command,
        static_dir=project_in.static_dir,
        port=project_in.port,
        env_vars=project_in.env_vars or {},
        status="stopped",
        webhook_token=token
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    return {
        "id": db_project.id,
        "name": db_project.name,
        "deployment_type": db_project.deployment_type,
        "status": db_project.status,
        "webhook_token": db_project.webhook_token,
        "internal_url": db_project.internal_url
    }

@router.get("/", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:read"))
):
    # Admins see all projects, others see only their own
    if user.role == "admin":
        projects = db.query(Project).all()
    else:
        projects = db.query(Project).filter(Project.owner_id == user.id).all()
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:read"))
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:update"))
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    if project_in.name:
        project.name = project_in.name
    if project_in.description:
        project.description = project_in.description
    if project_in.env_vars is not None:
        project.env_vars = project_in.env_vars
    if project_in.port:
        project.port = project_in.port
    
    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:delete"))
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # TODO: Stop and remove containers
    db.delete(project)
    db.commit()
    return {"status": "deleted"}


@router.post("/{project_id}/deploy")
def deploy_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:deploy"))
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update deployment timestamp
    project.last_deployed_at = datetime.utcnow()
    project.status = "deploying"
    db.commit()
    
    # Trigger deployment
    result = DockerService.deploy_project(project)
    
    # Update status
    project.status = "running" if result.get("status") == "success" else "failed"
    db.commit()
    
    return {"status": "deployed", "result": result}

@router.post("/{project_id}/stop")
def stop_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:deploy"))
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = DockerService.stop_project(project)
    
    if result["status"] == "success":
        project.status = "stopped"
        db.commit()
    
    return result

@router.post("/{project_id}/rebuild")
def rebuild_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:deploy"))
):
    """Rebuild and redeploy a project"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Stop existing deployment
    DockerService.stop_project(project)
    
    # Redeploy
    project.status = "deploying"
    db.commit()
    
    result = DockerService.deploy_project(project)
    
    project.status = "running" if result.get("status") == "success" else "failed"
    db.commit()
    
    return {"status": "rebuilt", "result": result}

@router.get("/{project_id}/logs")
def get_project_logs(
    project_id: int,
    lines: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:read"))
):
    """Get container logs for a running project"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = DockerService.get_project_logs(project, lines)
    return result

@router.get("/{project_id}/build-logs")
def get_build_logs(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:read"))
):
    """Get build logs for static build projects"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "project_id": project.id,
        "build_logs": project.build_logs or "No build logs available"
    }

