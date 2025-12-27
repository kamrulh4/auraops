import os
import subprocess
from app.models.project import Project
import logging

logger = logging.getLogger(__name__)

NGINX_CONF_DIR = "/etc/nginx/conf.d"

class NginxService:
    @staticmethod
    def generate_config(project: Project, container_name: str):
        """
        Generates an Nginx config file for the project.
        """
        if not project.domain:
            return # No domain, no proxy (or we could use a subdomain strategy later)

        config_content = f"""
server {{
    listen 80;
    server_name {project.domain};

    location / {{
        proxy_pass http://{container_name}:{project.port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
        config_path = os.path.join(NGINX_CONF_DIR, f"app-{project.id}.conf")
        
        try:
            with open(config_path, "w") as f:
                f.write(config_content)
            
            # Reload Nginx
            # Since we are in the 'backend' container, we can't directly reload 'proxy' container nginx easily 
            # UNLESS we share a way to signal it.
            # OR we execute a docker command to reload it if we have access to docker socket.
            
            # Strategy: Docker Exec
            import docker
            client = docker.from_env()
            proxy_container = client.containers.get("auraops-proxy")
            proxy_container.exec_run("nginx -s reload")
            
            logger.info(f"Generated Nginx config for {project.domain}")
            
        except Exception as e:
            logger.error(f"Failed to generate Nginx config: {e}")

    @staticmethod
    def remove_config(project: Project):
        config_path = os.path.join(NGINX_CONF_DIR, f"app-{project.id}.conf")
        if os.path.exists(config_path):
            os.remove(config_path)
            # Reload
            import docker
            client = docker.from_env()
            try:
                proxy_container = client.containers.get("auraops-proxy")
                proxy_container.exec_run("nginx -s reload")
            except:
                pass
