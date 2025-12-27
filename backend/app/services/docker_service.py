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
        Deploys a project based on its provider (image or github).
        """
        container_name = f"auraops-app-{project.id}"
        image_tag = f"auraops-{project.name.lower()}:latest"

        try:
            # 1. Prepare Image
            if project.provider == "github":
                # Clone and Build
                import git
                import os
                import shutil
                
                # Temp dir for cloning
                build_dir = f"/tmp/build/{project.id}"
                if os.path.exists(build_dir):
                    shutil.rmtree(build_dir)
                os.makedirs(build_dir)
                
                logger.info(f"Cloning {project.repo_url} to {build_dir}")
                git.Repo.clone_from(project.repo_url, build_dir)
                
                # Build Context inside repo
                context_path = os.path.join(build_dir, project.build_context.lstrip("/"))
                
                logger.info(f"Building image {image_tag} from {context_path}")
                client.images.build(
                    path=context_path,
                    tag=image_tag,
                    dockerfile=project.dockerfile_path,
                    rm=True
                )
                
                # Cleanup
                shutil.rmtree(build_dir)
                project_image = image_tag
                
            else:
                # Standard Image
                logger.info(f"Using image {project.repo_url}")
                # Pull if needed (client.images.pull(project.repo_url)) - optional for local
                project_image = project.repo_url

            # 2. Stop/Remove Old
            try:
                old = client.containers.get(container_name)
                old.stop()
                old.remove()
            except docker.errors.NotFound:
                pass

            # 3. Run
            logger.info(f"Starting container {container_name}")
            container = client.containers.run(
                project_image,
                detach=True,
                name=container_name,
                network="auraops-network",
                restart_policy={"Name": "unless-stopped"},
                ports={f"{project.port}/tcp": None}, # Let Nginx handle routing
                environment=project.env_vars or {}
            )
            
            # 4. Generate Nginx Config (Only if domain is set)
            if project.domain:
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
