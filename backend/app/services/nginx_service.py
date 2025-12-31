import subprocess
import logging
import docker
from typing import Optional
from app.models.project import Project
from app.models.domain import Domain

logger = logging.getLogger(__name__)

class NginxService:
    """Enhanced Nginx service with SSL, wildcards, and static file support"""
    
    NGINX_CONF_DIR = "/etc/nginx/conf.d"
    STATIC_FILES_DIR = "/var/www"
    
    @staticmethod
    def generate_config(project: Project, domain: Optional[Domain] = None):
        """Generate Nginx configuration based on project type"""
        
        if project.is_static:
            return NginxService._generate_static_config(project, domain)
        else:
            return NginxService._generate_proxy_config(project, domain)
    
    @staticmethod
    def _generate_proxy_config(project: Project, domain: Optional[Domain] = None):
        """Generate reverse proxy configuration for dynamic apps"""
        
        domain_name = domain.domain if domain else f"app-{project.id}.localhost"
        ssl_config = ""
        
        if domain and domain.ssl_enabled:
            ssl_config = f"""
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/{domain_name}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain_name}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
"""
        
        config = f"""
# AuraOps Project: {project.name} (ID: {project.id})
# Type: Dynamic App (Reverse Proxy)

server {{
    listen 80;
    server_name {domain_name};
    {ssl_config}
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/{project.id}-access.log;
    error_log /var/log/nginx/{project.id}-error.log;
    
    location / {{
        proxy_pass http://auraops-app-{project.id}:{project.port};
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}
}}
"""
        
        if domain and domain.ssl_enabled:
            # Add HTTP to HTTPS redirect
            config += f"""
# HTTP to HTTPS redirect
server {{
    listen 80;
    server_name {domain_name};
    return 301 https://$server_name$request_uri;
}}
"""
        
        return config
    
    @staticmethod
    def _generate_static_config(project: Project, domain: Optional[Domain] = None):
        """Generate configuration for static file serving"""
        
        domain_name = domain.domain if domain else f"app-{project.id}.localhost"
        ssl_config = ""
        
        if domain and domain.ssl_enabled:
            ssl_config = f"""
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/{domain_name}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain_name}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
"""
        
        config = f"""
# AuraOps Project: {project.name} (ID: {project.id})
# Type: Static Site

server {{
    listen 80;
    server_name {domain_name};
    {ssl_config}
    
    root {NginxService.STATIC_FILES_DIR}/project-{project.id};
    index index.html index.htm;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/{project.id}-access.log;
    error_log /var/log/nginx/{project.id}-error.log;
    
    # SPA routing (try files, fallback to index.html)
    location / {{
        try_files $uri $uri/ /index.html;
    }}
    
    # Static asset caching
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {{
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }}
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript;
}}
"""
        
        if domain and domain.ssl_enabled:
            config += f"""
# HTTP to HTTPS redirect
server {{
    listen 80;
    server_name {domain_name};
    return 301 https://$server_name$request_uri;
}}
"""
        
        return config
    
    @staticmethod
    def write_config(project: Project, domain: Optional[Domain] = None):
        """Write configuration file to Nginx conf directory"""
        
        config_content = NginxService.generate_config(project, domain)
        config_path = f"{NginxService.NGINX_CONF_DIR}/project-{project.id}.conf"
        
        try:
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            logger.info(f"Generated Nginx config for project {project.id} at {config_path}")
            
            # Reload Nginx
            NginxService.reload()
            return True
            
        except Exception as e:
            logger.error(f"Failed to write Nginx config: {e}")
            return False
    
    @staticmethod
    def delete_config(project_id: int):
        """Delete Nginx configuration for a project"""
        
        config_path = f"{NginxService.NGINX_CONF_DIR}/project-{project_id}.conf"
        
        try:
            subprocess.run(["rm", "-f", config_path], check=True)
            logger.info(f"Deleted Nginx config for project {project_id}")
            
            # Reload Nginx
            NginxService.reload()
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Nginx config: {e}")
            return False
    
    @staticmethod
    def write_base_config():
        """Write base routing configuration for AuraOps"""
        
        config = """
server {
    listen 80;
    server_name localhost;

    # Backend API
    location /api/ {
        proxy_pass http://auraops-backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend
    location / {
        proxy_pass http://auraops-frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SPA support
        proxy_intercept_errors on;
        error_page 404 = /index.html;
    }
}
"""
        config_path = f"{NginxService.NGINX_CONF_DIR}/auraops-base.conf"
        
        try:
            import os
            os.makedirs(NginxService.NGINX_CONF_DIR, exist_ok=True)
            with open(config_path, 'w') as f:
                f.write(config)
            
            logger.info(f"Generated base Nginx config at {config_path}")
            NginxService.reload()
            return True
        except Exception as e:
            logger.error(f"Failed to write base Nginx config: {e}")
            return False

    @staticmethod
    def reload():
        """Reload Nginx configuration without downtime"""
        
        try:
            client = docker.from_env()
            try:
                proxy_container = client.containers.get("auraops-proxy")
            except docker.errors.NotFound:
                logger.warning("auraops-proxy container not found, skip reload")
                return False
            
            # First test the configuration
            test_result = proxy_container.exec_run("nginx -t")
            
            if test_result.exit_code != 0:
                logger.error(f"Nginx config test failed: {test_result.output.decode()}")
                return False
            
            # Reload Nginx
            reload_result = proxy_container.exec_run("nginx -s reload")
            
            if reload_result.exit_code == 0:
                logger.info("Nginx reloaded successfully")
                return True
            else:
                logger.error(f"Nginx reload failed: {reload_result.output.decode()}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to reload Nginx: {e}")
            return False
    
    @staticmethod
    def generate_wildcard_config(base_domain: str):
        """Generate wildcard subdomain configuration
        
        Example: *.yourdomain.com routes to auraops-app-{subdomain}
        """
        
        config = f"""
# AuraOps Wildcard Configuration
# Base Domain: {base_domain}
# Catches: *.{base_domain}

server {{
    listen 80;
    server_name ~^(?<subdomain>.+)\\.{base_domain.replace('.', '\\.')}$;
    
    # Access log with subdomain
    access_log /var/log/nginx/wildcard-access.log;
    error_log /var/log/nginx/wildcard-error.log;
    
    location / {{
        # Proxy to container named after subdomain
        proxy_pass http://auraops-app-$subdomain;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
}}
"""
        return config
