from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.project import Project
from app.services.docker_service import DockerService
from datetime import datetime

router = APIRouter()

@router.post("/deploy/{token}")
def trigger_deploy(token: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.webhook_token == token).first()
    if not project:
        raise HTTPException(status_code=404, detail="Invalid token")
    
    # Run deployment in background
    background_tasks.add_task(handle_deployment, project.id, db)
    
    return {"status": "deployment_queued", "project": project.name}

def handle_deployment(project_id: int, db: Session):
    # Re-fetch project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return

    # Update status
    project.status = "building"
    db.commit()

    # Deploy
    result = DockerService.deploy_project(project)

    # Update Final Status
    if result["status"] == "success":
        project.status = "running"
        project.last_deployed_at = datetime.utcnow()
    else:
        project.status = "failed"
    
    db.commit()
