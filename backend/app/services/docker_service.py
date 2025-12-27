import docker
from app.models.project import Project
from app.services.nginx_service import NginxService
import logging

logger = logging.getLogger(__name__)

client = docker.from_env()

class DockerService:
    @staticmethod
    def deploy_project(project: Project):
        """
        Deploys a project.
        Simple strategy:
        1. Pull image (if no build needed) OR Build image.
        2. Stop old container.
        3. Run new container.
        """
        image_tag = f"auraops-{project.name.lower()}:latest"
        container_name = f"auraops-app-{project.id}"

        try:
            # 1. Build Image (Assumes repo is cloned locally for now, or just pulls if it's an image)
            # For this MVP, let's assume 'repo_url' is actually a Docker Image Name for simplicity
            # OR we implement git clone later.
            # Let's support just running a standard image for now (e.g. nginx, postgres)
            
            logger.info(f"Deploying {project.name} using image {project.repo_url}")
            
            # 2. Stop/Remove Old
            try:
                old = client.containers.get(container_name)
                old.stop()
                old.remove()
            except docker.errors.NotFound:
                pass

            # 3. Network
            # Connect to 'auraops-network' so Nginx can reach it by container_name
            
            # 4. Run
            container = client.containers.run(
                project.repo_url,
                detach=True,
                name=container_name,
                network="auraops-network",
                restart_policy={"Name": "unless-stopped"},
                # Environment variables would go here
            )
            
            # 5. Generate Nginx Config
            NginxService.generate_config(project, container_name)
            
            return {"status": "success", "container_id": container.id}

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return {"status": "failed", "error": str(e)}

    @staticmethod
    def get_container_status(project_id: int):
        container_name = f"auraops-app-{project_id}"
        try:
            container = client.containers.get(container_name)
            return container.status
        except docker.errors.NotFound:
            return "stopped"
