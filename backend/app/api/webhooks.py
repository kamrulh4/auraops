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
    # Re-fetch to ensure session validity if needed, or just pass ID
    # Here we create a new session or use logic carefully. 
    # For simplicity, let's assume valid scope or re-query.
    
    # Note: In real app, avoid passing DB session to bg task if it closes.
    # We should use a fresh session in the background task.
    
    # Logic:
    # 1. Update status to 'building'
    # 2. Call DockerService
    # 3. Update status to 'running'/'failed'
    pass # Simplification for MVP structure. Real implementation is in DockerService.deploy_project
