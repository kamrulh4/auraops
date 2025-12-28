import docker
import logging
from app.models.project import Project
from app.services.nginx_service import NginxService
from app.services.build_service import BuildService

logger = logging.getLogger(__name__)

class DockerService:
    """Enhanced Docker service for deploying projects"""
    
    @staticmethod
    def deploy_project(project: Project) -> dict:
        """
        Deploy a project based on its deployment type
        
        Deployment types:
        - docker_image: Pull and run image
        - dockerfile: Build from Dockerfile, then run
        - docker_compose: Deploy multi-service compose file
        - static_build: Build static site and serve with Nginx
        - service: Deploy managed service (DB, cache, etc.)
        """
        
        try:
            if project.deployment_type == "static_build":
                return DockerService._deploy_static_build(project)
            elif project.deployment_type == "docker_image":
                return DockerService._deploy_docker_image(project)
            elif project.deployment_type == "dockerfile":
                return DockerService._deploy_dockerfile(project)
            elif project.deployment_type == "docker_compose":
                return DockerService._deploy_compose(project)
            elif project.deployment_type == "service":
                return DockerService._deploy_service(project)
            else:
                raise ValueError(f"Unknown deployment type: {project.deployment_type}")
                
        except Exception as e:
            logger.error(f"Deployment failed for project {project.id}: {e}")
            return {
                "status": "failed",
                "message": str(e)
            }
    
    @staticmethod
    def _deploy_static_build(project: Project) -> dict:
        """Build and deploy static site"""
        
        logger.info(f"Building static site for project {project.id}")
        
        # Use BuildService to build the static site
        result = BuildService.build_static_site(project)
        
        if result["status"] == "success":
            logger.info(f"Static site deployed successfully: {project.id}")
        
        return result
    
    @staticmethod
    def _deploy_docker_image(project: Project) -> dict:
        """Pull and run Docker image"""
        
        client = docker.from_env()
        container_name = f"auraops-app-{project.id}"
        
        try:
            # Stop and remove existing container
            try:
                old_container = client.containers.get(container_name)
                old_container.stop()
                old_container.remove()
                logger.info(f"Removed old container: {container_name}")
            except docker.errors.NotFound:
                pass
            
            # Pull latest image
            logger.info(f"Pulling image: {project.repo_url}")
            client.images.pull(project.repo_url)
            
            # Run container
            logger.info(f"Starting container: {container_name}")
            container = client.containers.run(
                image=project.repo_url,
                name=container_name,
                detach=True,
                ports={f"{project.port}/tcp": project.port},
                environment=project.env_vars or {},
                restart_policy={"Name": "unless-stopped"},
                network="auraops-network"
            )
            
            # Generate Nginx config
            NginxService.write_config(project)
            
            logger.info(f"Container deployed successfully: {container.short_id}")
            
            return {
                "status": "success",
                "container_id": container.short_id,
                "message": "Container deployed successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy Docker image: {e}")
            return {
                "status": "failed",
                "message": str(e)
            }
    
    @staticmethod
    def _deploy_dockerfile(project: Project) -> dict:
        """Build from Dockerfile and run"""
        
        client = docker.from_env()
        container_name = f"auraops-app-{project.id}"
        
        try:
            # Clone repository to temp directory
            import tempfile
            import subprocess
            
            with tempfile.TemporaryDirectory() as tmpdir:
                # Clone repo
                logger.info(f"Cloning repository: {project.repo_url}")
                subprocess.run([
                    "git", "clone",
                    "--depth", "1",
                    "--branch", project.branch,
                    project.repo_url,
                    tmpdir
                ], check=True)
                
                # Build image
                build_path = f"{tmpdir}/{project.build_context}"
                dockerfile_path = f"{tmpdir}/{project.dockerfile_path}"
                
                logger.info(f"Building image from {dockerfile_path}")
                image, build_logs = client.images.build(
                    path=build_path,
                    dockerfile=dockerfile_path,
                    tag=f"auraops-{project.id}:latest",
                    rm=True
                )
                
                # Stop and remove old container
                try:
                    old_container = client.containers.get(container_name)
                    old_container.stop()
                    old_container.remove()
                except docker.errors.NotFound:
                    pass
                
                # Run container
                logger.info(f"Starting container: {container_name}")
                container = client.containers.run(
                    image=image.id,
                    name=container_name,
                    detach=True,
                    ports={f"{project.port}/tcp": project.port},
                    environment=project.env_vars or {},
                    restart_policy={"Name": "unless-stopped"},
                    network="auraops-network"
                )
                
                # Generate Nginx config
                NginxService.write_config(project)
                
                logger.info(f"Dockerfile deployment successful: {container.short_id}")
                
                return {
                    "status": "success",
                    "container_id": container.short_id,
                    "image_id": image.short_id,
                    "message": "Built and deployed successfully"
                }
                
        except Exception as e:
            logger.error(f"Dockerfile deployment failed: {e}")
            return {
                "status": "failed",
                "message": str(e)
            }
    
    @staticmethod
    def _deploy_compose(project: Project) -> dict:
        """Deploy Docker Compose project"""
        
        from app.services.compose_service import ComposeService
        
        logger.info(f"Deploying Docker Compose project: {project.id}")
        result = ComposeService.deploy_compose_project(project)
        
        return result
    
    @staticmethod
    def _deploy_service(project: Project) -> dict:
        """Deploy managed service (DB, cache, S3, etc.)"""
        
        from app.services.service_templates import ServiceDeployer
        
        # Extract service type from repo_url (e.g., "postgres", "minio", "redis")
        service_type = project.repo_url.lower() if project.repo_url else "postgres"
        
        logger.info(f"Deploying service: {service_type}")
        result = ServiceDeployer.deploy_service(project, service_type)
        
        return result
    
    @staticmethod
    def stop_project(project: Project) -> dict:
        """Stop a running project"""
        
        client = docker.from_env()
        container_name = f"auraops-app-{project.id}"
        
        try:
            container = client.containers.get(container_name)
            container.stop()
            logger.info(f"Stopped container: {container_name}")
            
            return {
                "status": "success",
                "message": "Project stopped"
            }
        except docker.errors.NotFound:
            return {
                "status": "success",
                "message": "Container not found (already stopped)"
            }
        except Exception as e:
            logger.error(f"Failed to stop project: {e}")
            return {
                "status": "failed",
                "message": str(e)
            }
    
    @staticmethod
    def remove_project(project: Project) -> dict:
        """Remove project containers and artifacts"""
        
        client = docker.from_env()
        container_name = f"auraops-app-{project.id}"
        
        try:
            # Stop and remove container
            try:
                container = client.containers.get(container_name)
                container.stop()
                container.remove()
                logger.info(f"Removed container: {container_name}")
            except docker.errors.NotFound:
                pass
            
            # Clean up static files if it's a static build
            if project.is_static:
                BuildService.clean_build_artifacts(project.id)
            
            # Remove Nginx config
            NginxService.delete_config(project.id)
            
            return {
                "status": "success",
                "message": "Project removed successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to remove project: {e}")
            return {
                "status": "failed",
                "message": str(e)
            }
    
    @staticmethod
    def get_project_logs(project: Project, lines: int = 100) -> dict:
        """Get container logs for a project"""
        
        client = docker.from_env()
        container_name = f"auraops-app-{project.id}"
        
        try:
            container = client.containers.get(container_name)
            logs = container.logs(tail=lines).decode('utf-8')
            
            return {
                "status": "success",
                "logs": logs
            }
        except docker.errors.NotFound:
            return {
                "status": "failed",
                "message": "Container not found"
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": str(e)
            }
