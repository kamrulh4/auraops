import docker
import logging
import shutil
import os
import tempfile
from typing import Optional
from app.models.project import Project
from app.services.nginx_service import NginxService

logger = logging.getLogger(__name__)

class BuildService:
    """Service for building static sites (Next.js, React, Vue, etc.)"""
    
    STATIC_OUTPUT_DIR = "/var/www"  # Shared with Nginx
    
    # Framework detection based on package.json
    FRAMEWORK_CONFIGS = {
        "nextjs": {
            "detection": ["next"],
            "default_install": "npm install",
            "default_build": "npm run build",
            "default_output": "out",  # or .next/standalone
            "build_env": {"NODE_ENV": "production"}
        },
        "react": {
            "detection": ["react", "react-scripts"],
            "default_install": "npm install",
            "default_build": "npm run build",
            "default_output": "build",
            "build_env": {"NODE_ENV": "production"}
        },
        "vue": {
            "detection": ["vue", "@vue/cli"],
            "default_install": "npm install",
            "default_build": "npm run build",
            "default_output": "dist",
            "build_env": {"NODE_ENV": "production"}
        },
        "vite": {
            "detection": ["vite"],
            "default_install": "npm install",
            "default_build": "npm run build",
            "default_output": "dist",
            "build_env": {"NODE_ENV": "production"}
        },
        "angular": {
            "detection": ["@angular/core"],
            "default_install": "npm install",
            "default_build": "npm run build",
            "default_output": "dist",
            "build_env": {"NODE_ENV": "production"}
        }
    }
    
    @staticmethod
    def build_static_site(project: Project) -> dict:
        """
        Build a static site using a temporary Docker container
        
        Process:
        1. Create temp build container (node:20-alpine)
        2. Clone repository
        3. Install dependencies
        4. Run build command
        5. Copy output to Nginx volume
        6. Clean up temp container
        7. Generate Nginx config
        """
        
        client = docker.from_env()
        build_logs = []
        
        try:
            # Update project status
            project.status = "building"
            
            logger.info(f"Starting build for project {project.id}: {project.name}")
            build_logs.append(f"[INFO] Starting build for {project.name}")
            
            # 1. Create build container
            build_logs.append("[INFO] Creating build container...")
            
            container = client.containers.run(
                "node:20-alpine",
                command="/bin/sh -c 'tail -f /dev/null'",  # Keep container running
                detach=True,
                name=f"auraops-build-{project.id}",
                working_dir="/app",
                environment=project.env_vars or {},
                remove=False  # We'll remove it manually after copying files
            )
            
            build_logs.append(f"[INFO] Build container created: {container.short_id}")
            
            # 2. Clone repository
            build_logs.append(f"[INFO] Cloning repository: {project.repo_url}")
            
            clone_cmd = f"apk add --no-cache git && git clone --depth 1 --branch {project.branch} {project.repo_url} /app"
            result = container.exec_run(f"/bin/sh -c '{clone_cmd}'")
            
            if result.exit_code != 0:
                error_msg = result.output.decode()
                build_logs.append(f"[ERROR] Git clone failed: {error_msg}")
                raise Exception(f"Git clone failed: {error_msg}")
            
            build_logs.append("[SUCCESS] Repository cloned")
            
            # 3. Install dependencies
            install_cmd = project.install_command or "npm install"
            build_logs.append(f"[INFO] Installing dependencies: {install_cmd}")
            
            result = container.exec_run(
                f"/bin/sh -c 'cd /app && {install_cmd}'",
                stream=True
            )
            
            for line in result.output:
                log_line = line.decode().strip()
                if log_line:
                    build_logs.append(log_line)
            
            build_logs.append("[SUCCESS] Dependencies installed")
            
            # 4. Run build command
            build_cmd = project.build_command or "npm run build"
            build_logs.append(f"[INFO] Running build: {build_cmd}")
            
            # Set build environment variables
            env_str = " ".join([f"{k}={v}" for k, v in (project.env_vars or {}).items()])
            full_build_cmd = f"cd /app && {env_str} {build_cmd}"
            
            result = container.exec_run(
                f"/bin/sh -c '{full_build_cmd}'",
                stream=True
            )
            
            for line in result.output:
                log_line = line.decode().strip()
                if log_line:
                    build_logs.append(log_line)
            
            build_logs.append("[SUCCESS] Build completed")
            
            # 5. Copy built files to Nginx volume
            build_logs.append("[INFO] Copying built files to Nginx volume...")
            
            output_dir = project.static_dir or "dist"
            destination = f"{BuildService.STATIC_OUTPUT_DIR}/project-{project.id}"
            
            # Create destination directory
            os.makedirs(destination, exist_ok=True)
            
            # Copy files from container to host
            # We'll use docker cp command
            copy_cmd = f"docker cp auraops-build-{project.id}:/app/{output_dir}/. {destination}/"
            os.system(copy_cmd)
            
            build_logs.append(f"[SUCCESS] Files copied to {destination}")
            
            # 6. Clean up container
            build_logs.append("[INFO] Cleaning up build container...")
            container.stop()
            container.remove()
            build_logs.append("[SUCCESS] Build container removed")
            
            # 7. Generate Nginx config for static site
            build_logs.append("[INFO] Generating Nginx configuration...")
            NginxService.write_config(project)
            build_logs.append("[SUCCESS] Nginx configured")
            
            # Save build logs
            project.build_logs = "\n".join(build_logs)
            project.status = "running"
            
            logger.info(f"Build completed successfully for project {project.id}")
            
            return {
                "status": "success",
                "message": "Build completed successfully",
                "output_dir": destination,
                "logs": build_logs
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Build failed for project {project.id}: {error_msg}")
            
            build_logs.append(f"[ERROR] Build failed: {error_msg}")
            project.build_logs = "\n".join(build_logs)
            project.status = "failed"
            
            # Clean up container if it exists
            try:
                container = client.containers.get(f"auraops-build-{project.id}")
                container.stop()
                container.remove()
            except:
                pass
            
            return {
                "status": "failed",
                "message": error_msg,
                "logs": build_logs
            }
    
    @staticmethod
    def detect_framework(project: Project) -> Optional[str]:
        """
        Detect framework from package.json in repository
        
        This is useful for auto-configuring build settings
        """
        # TODO: Implement package.json parsing from repo
        # For now, rely on user-provided config
        return None
    
    @staticmethod
    def get_build_suggestions(framework: str) -> dict:
        """Get suggested build configuration for a framework"""
        
        config = BuildService.FRAMEWORK_CONFIGS.get(framework.lower())
        if not config:
            return {
                "install_command": "npm install",
                "build_command": "npm run build",
                "static_dir": "dist"
            }
        
        return {
            "install_command": config["default_install"],
            "build_command": config["default_build"],
            "static_dir": config["default_output"]
        }
    
    @staticmethod
    def clean_build_artifacts(project_id: int):
        """Remove built files for a project"""
        
        try:
            destination = f"{BuildService.STATIC_OUTPUT_DIR}/project-{project_id}"
            if os.path.exists(destination):
                shutil.rmtree(destination)
                logger.info(f"Cleaned build artifacts for project {project_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to clean artifacts: {e}")
            return False
