from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.user import User
from app.models.project import Project
from app.models.domain import Domain
from app.api.projects import get_current_user
from app.api.users import require_admin
import docker
import psutil
from datetime import datetime
from typing import Dict

router = APIRouter()

@router.get("/health")
def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

@router.get("/stats")
def get_system_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get system statistics"""
    
    # Database stats
    total_users = db.query(func.count(User.id)).scalar()
    total_projects = db.query(func.count(Project.id)).scalar()
    total_domains = db.query(func.count(Domain.id)).scalar()
    
    running_projects = db.query(func.count(Project.id)).filter(
        Project.status == "running"
    ).scalar()
    
    # Docker stats
    try:
        client = docker.from_env()
        containers = client.containers.list()
        auraops_containers = [c for c in containers if "auraops" in c.name.lower()]
        
        docker_stats = {
            "total_containers": len(containers),
            "auraops_containers": len(auraops_containers),
            "running": len([c for c in containers if c.status == "running"])
        }
    except:
        docker_stats = {"error": "Could not connect to Docker"}
    
    # System resources
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_stats = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2)
        }
    except:
        system_stats = {"error": "Could not get system stats"}
    
    return {
        "database": {
            "users": total_users,
            "projects": total_projects,
            "domains": total_domains,
            "running_projects": running_projects
        },
        "docker": docker_stats,
        "system": system_stats,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/stats/projects")
def get_project_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get project statistics by deployment type"""
    
    # Query projects
    if user.role == "admin":
        projects = db.query(Project).all()
    else:
        projects = db.query(Project).filter(Project.owner_id == user.id).all()
    
    # Group by deployment type
    by_type = {}
    by_status = {}
    
    for project in projects:
        # By type
        dep_type = project.deployment_type or "unknown"
        by_type[dep_type] = by_type.get(dep_type, 0) + 1
        
        # By status
        status = project.status or "unknown"
        by_status[status] = by_status.get(status, 0) + 1
    
    return {
        "total_projects": len(projects),
        "by_deployment_type": by_type,
        "by_status": by_status,
        "user_id": user.id if user.role != "admin" else "all"
    }

@router.get("/stats/users")
def get_user_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Get user statistics (admin only)"""
    
    users = db.query(User).all()
    
    by_role = {}
    active_count = 0
    
    for user in users:
        role = user.role or "unknown"
        by_role[role] = by_role.get(role, 0) + 1
        
        if user.is_active:
            active_count += 1
    
    return {
        "total_users": len(users),
        "active_users": active_count,
        "inactive_users": len(users) - active_count,
        "by_role": by_role,
        "superusers": len([u for u in users if u.is_superuser])
    }

@router.get("/containers")
def list_containers(
    admin: User = Depends(require_admin)
):
    """List all Docker containers (admin only)"""
    
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
        
        container_list = []
        for container in containers:
            container_list.append({
                "id": container.short_id,
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "status": container.status,
                "created": container.attrs['Created'],
                "ports": container.ports
            })
        
        return {
            "total": len(container_list),
            "containers": container_list
        }
        
    except Exception as e:
        return {
            "error": str(e)
        }

@router.get("/volumes")
def list_volumes(
    admin: User = Depends(require_admin)
):
    """List all Docker volumes (admin only)"""
    
    try:
        client = docker.from_env()
        volumes = client.volumes.list()
        
        volume_list = []
        for volume in volumes:
            volume_list.append({
                "name": volume.name,
                "driver": volume.attrs.get('Driver'),
                "mountpoint": volume.attrs.get('Mountpoint'),
                "created": volume.attrs.get('CreatedAt')
            })
        
        return {
            "total": len(volume_list),
            "volumes": volume_list
        }
        
    except Exception as e:
        return {
            "error": str(e)
        }

@router.get("/networks")
def list_networks(
    admin: User = Depends(require_admin)
):
    """List all Docker networks (admin only)"""
    
    try:
        client = docker.from_env()
        networks = client.networks.list()
        
        network_list = []
        for network in networks:
            network_list.append({
                "id": network.short_id,
                "name": network.name,
                "driver": network.attrs.get('Driver'),
                "scope": network.attrs.get('Scope'),
                "created": network.attrs.get('Created')
            })
        
        return {
            "total": len(network_list),
            "networks": network_list
        }
        
    except Exception as e:
        return {
            "error": str(e)
        }
