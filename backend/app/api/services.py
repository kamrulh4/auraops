from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.api.projects import get_current_user, require_permission
from app.services.service_templates import ServiceTemplates, ServiceDeployer
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()

class ServiceCreate(BaseModel):
    name: str
    service_type: str  # postgres, mysql, mongodb, redis, minio, etc.
    description: Optional[str] = None
    env_vars: Optional[dict] = {}

@router.get("/templates")
def list_service_templates(
    category: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """List all available service templates"""
    
    return {
        "templates": ServiceTemplates.list_templates(category),
        "categories": ServiceTemplates.get_categories()
    }

@router.get("/templates/{service_type}")
def get_service_template(
    service_type: str,
    user: User = Depends(get_current_user)
):
    """Get details of a specific service template"""
    
    template = ServiceTemplates.get_template(service_type)
    if not template:
        raise HTTPException(status_code=404, detail="Service template not found")
    
    return {
        "service_type": service_type,
        "template": template
    }

@router.post("/deploy", response_model=dict)
def deploy_service(
    service_in: ServiceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:create"))
):
    """
    Deploy a managed service from template
    
    This creates a new project with deployment_type="service"
    """
    
    import secrets
    
    # Validate service type
    template = ServiceTemplates.get_template(service_in.service_type)
    if not template:
        raise HTTPException(status_code=400, detail=f"Unknown service type: {service_in.service_type}")
    
    # Create project for the service
    db_project = Project(
        name=service_in.name,
        description=service_in.description or template["description"],
        owner_id=user.id,
        deployment_type="service",
        provider="template",
        repo_url=service_in.service_type,  # Store service type here
        port=list(template["ports"].values())[0],  # Primary port
        env_vars=service_in.env_vars or {},
        status="deploying",
        webhook_token=secrets.token_urlsafe(16)
    )
    
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # Deploy the service
    result = ServiceDeployer.deploy_service(db_project, service_in.service_type)
    
    # Update status
    db_project.status = "running" if result.get("status") == "success" else "failed"
    db_project.last_deployed_at = datetime.utcnow()
    
    # Store credentials in build_logs for now (we could add a credentials field)
    if result.get("status") == "success":
        import json
        db_project.build_logs = json.dumps(result.get("connection_info"), indent=2)
    
    db.commit()
    db.refresh(db_project)
    
    return {
        "project_id": db_project.id,
        "service_type": service_in.service_type,
        "status": result.get("status"),
        "connection_info": result.get("connection_info"),
        "message": result.get("message")
    }

@router.get("/{project_id}/credentials")
def get_service_credentials(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:read"))
):
    """Get connection credentials for a deployed service"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if project.deployment_type != "service":
        raise HTTPException(status_code=400, detail="Project is not a service")
    
    # Parse connection info from build_logs
    import json
    try:
        connection_info = json.loads(project.build_logs or "{}")
    except:
        connection_info = {}
    
    return {
        "project_id": project.id,
        "project_name": project.name,
        "service_type": project.repo_url,
        "status": project.status,
        "connection_info": connection_info
    }

@router.post("/{project_id}/restart")
def restart_service(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects:deploy"))
):
    """Restart a service container"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if project.deployment_type != "service":
        raise HTTPException(status_code=400, detail="Project is not a service")
    
    # Stop and redeploy
    from app.services.docker_service import DockerService
    
    DockerService.stop_project(project)
    result = ServiceDeployer.deploy_service(project, project.repo_url)
    
    project.status = "running" if result.get("status") == "success" else "failed"
    db.commit()
    
    return {
        "status": result.get("status"),
        "message": "Service restarted successfully" if result.get("status") == "success" else result.get("message")
    }
