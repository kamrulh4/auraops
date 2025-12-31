from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.domain import Domain
from app.models.project import Project
from app.models.user import User
from app.api.projects import get_current_user, require_permission
from app.services.nginx_service import NginxService
from app.services.ssl_service import SSLService
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class DomainCreate(BaseModel):
    domain: str
    project_id: int
    ssl_enabled: bool = False

class DomainUpdate(BaseModel):
    ssl_enabled: Optional[bool] = None
    is_active: Optional[bool] = None

class DomainResponse(BaseModel):
    id: int
    domain: str
    project_id: int
    ssl_enabled: bool
    ssl_valid: bool
    is_active: bool
    dns_verified: bool
    
    class Config:
        from_attributes = True

@router.post("/", response_model=DomainResponse)
def create_domain(
    domain_in: DomainCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("domains:create"))
):
    """Add a custom domain to a project"""
    
    # Check if domain already exists
    existing = db.query(Domain).filter(Domain.domain == domain_in.domain).first()
    if existing:
        raise HTTPException(status_code=400, detail="Domain already registered")
    
    # Check if project exists and user has access
    project = db.query(Project).filter(Project.id == domain_in.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create domain
    domain = Domain(
        domain=domain_in.domain,
        project_id=domain_in.project_id,
        ssl_enabled=False,  # Initially disabled
        dns_verified=False
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    
    # Generate Nginx config with new domain
    NginxService.write_config(project, domain)
    
    # Issue SSL certificate if requested
    if domain_in.ssl_enabled:
        success = SSLService.issue_certificate(domain)
        if success:
            db.commit()
            # Regenerate Nginx config with SSL
            NginxService.write_config(project, domain)
    
    return {
        "id": domain.id,
        "domain": domain.domain,
        "project_id": domain.project_id,
        "ssl_enabled": domain.ssl_enabled,
        "ssl_valid": domain.ssl_valid
    }

@router.get("/{domain_id}", response_model=DomainResponse)
def get_domain(
    domain_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("domains:read"))
):
    """Get domain details"""
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Check access
    project = db.query(Project).filter(Project.id == domain.project_id).first()
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return domain

@router.get("/project/{project_id}", response_model=list[DomainResponse])
def list_project_domains(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("domains:read"))
):
    """List all domains for a project"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    domains = db.query(Domain).filter(Domain.project_id == project_id).all()
    return domains

@router.post("/{domain_id}/ssl/issue")
def issue_ssl(
    domain_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("domains:create"))
):
    """Issue or renew SSL certificate for domain"""
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Check access
    project = db.query(Project).filter(Project.id == domain.project_id).first()
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Issue certificate
    success = SSLService.issue_certificate(domain)
    
    if success:
        db.commit()
        # Regenerate Nginx config with SSL
        NginxService.write_config(project, domain)
        return {"status": "success", "message": "SSL certificate issued"}
    else:
        raise HTTPException(status_code=500, detail="Failed to issue SSL certificate")

@router.post("/{domain_id}/ssl/renew")
def renew_ssl(
    domain_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("domains:create"))
):
    """Renew SSL certificate"""
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    project = db.query(Project).filter(Project.id == domain.project_id).first()
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = SSLService.renew_certificate(domain)
    
    if success:
        db.commit()
        return {"status": "success", "message": "SSL certificate renewed"}
    else:
        raise HTTPException(status_code=500, detail="Failed to renew SSL certificate")

@router.delete("/{domain_id}")
def delete_domain(
    domain_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("domains:delete"))
):
    """Remove domain from project"""
    
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    project = db.query(Project).filter(Project.id == domain.project_id).first()
    if user.role != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Revoke SSL if enabled
    if domain.ssl_enabled:
        SSLService.revoke_certificate(domain)
    
    # Delete domain
    db.delete(domain)
    db.commit()
    
    # Regenerate Nginx config without this domain
    NginxService.write_config(project)
    
    return {"status": "deleted"}

@router.get("/wildcard/guide/{base_domain}")
def get_wildcard_guide(
    base_domain: str,
    user: User = Depends(require_permission("domains:read"))
):
    """Get setup instructions for wildcard SSL"""
    
    return SSLService.setup_wildcard_ssl(base_domain)
