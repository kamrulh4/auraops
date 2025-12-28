import docker
import yaml
import logging
import tempfile
import subprocess
from typing import Dict, List, Optional
from app.models.project import Project

logger = logging.getLogger(__name__)

class ComposeService:
    """Service for deploying Docker Compose projects"""
    
    @staticmethod
    def parse_compose_file(compose_content: str) -> Dict:
        """
        Parse docker-compose.yml content
        
        Returns:
            Dict with services, networks, volumes
        """
        try:
            compose_data = yaml.safe_load(compose_content)
            
            # Validate required fields
            if 'services' not in compose_data:
                raise ValueError("Invalid docker-compose.yml: 'services' key not found")
            
            return {
                "services": compose_data.get('services', {}),
                "networks": compose_data.get('networks', {}),
                "volumes": compose_data.get('volumes', {}),
                "version": compose_data.get('version', '3')
            }
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse docker-compose.yml: {e}")
            raise ValueError(f"Invalid YAML: {e}")
    
    @staticmethod
    def get_service_dependencies(services: Dict) -> Dict[str, List[str]]:
        """
        Extract service dependencies from compose file
        
        Returns:
            Dict mapping service name to list of dependencies
        """
        dependencies = {}
        
        for service_name, service_config in services.items():
            deps = []
            
            # depends_on
            if 'depends_on' in service_config:
                if isinstance(service_config['depends_on'], list):
                    deps.extend(service_config['depends_on'])
                elif isinstance(service_config['depends_on'], dict):
                    deps.extend(service_config['depends_on'].keys())
            
            # links
            if 'links' in service_config:
                links = service_config['links']
                for link in links:
                    # Format: "service:alias" or just "service"
                    dep = link.split(':')[0]
                    deps.append(dep)
            
            dependencies[service_name] = deps
        
        return dependencies
    
    @staticmethod
    def topological_sort(dependencies: Dict[str, List[str]]) -> List[str]:
        """
        Sort services by dependencies (topological sort)
        
        Ensures services are started in correct order
        """
        # Build reverse dependency graph
        all_services = set(dependencies.keys())
        for deps in dependencies.values():
            all_services.update(deps)
        
        # Kahn's algorithm
        in_degree = {service: 0 for service in all_services}
        for deps in dependencies.values():
            for dep in deps:
                in_degree[dep] += 1
        
        queue = [s for s in all_services if in_degree[s] == 0]
        sorted_services = []
        
        while queue:
            service = queue.pop(0)
            sorted_services.append(service)
            
            for s, deps in dependencies.items():
                if service in deps:
                    in_degree[s] -= 1
                    if in_degree[s] == 0:
                        queue.append(s)
        
        if len(sorted_services) != len(all_services):
            raise ValueError("Circular dependency detected in docker-compose.yml")
        
        return sorted_services
    
    @staticmethod
    def deploy_compose_project(project: Project) -> dict:
        """
        Deploy a multi-service Docker Compose project
        
        Process:
        1. Parse compose file
        2. Create project network
        3. Create volumes
        4. Deploy services in dependency order
        5. Generate Nginx config for web services
        """
        
        client = docker.from_env()
        project_prefix = f"auraops-{project.id}"
        
        try:
            # 1. Parse compose file
            logger.info(f"Parsing docker-compose.yml for project {project.id}")
            compose_data = ComposeService.parse_compose_file(project.compose_file)
            services = compose_data['services']
            
            # 2. Create project network
            network_name = f"{project_prefix}-network"
            try:
                network = client.networks.create(
                    name=network_name,
                    driver="bridge",
                    labels={"auraops.project_id": str(project.id)}
                )
                logger.info(f"Created network: {network_name}")
            except docker.errors.APIError as e:
                if "already exists" in str(e):
                    network = client.networks.get(network_name)
                else:
                    raise
            
            # 3. Create named volumes
            created_volumes = []
            for volume_name, volume_config in compose_data.get('volumes', {}).items():
                full_volume_name = f"{project_prefix}-{volume_name}"
                try:
                    client.volumes.create(
                        name=full_volume_name,
                        labels={"auraops.project_id": str(project.id)}
                    )
                    created_volumes.append(full_volume_name)
                    logger.info(f"Created volume: {full_volume_name}")
                except docker.errors.APIError as e:
                    if "already exists" not in str(e):
                        raise
            
            # 4. Get deployment order
            dependencies = ComposeService.get_service_dependencies(services)
            deploy_order = ComposeService.topological_sort(dependencies)
            
            # 5. Deploy services
            deployed_containers = []
            
            for service_name in deploy_order:
                if service_name not in services:
                    continue
                
                service_config = services[service_name]
                container_name = f"{project_prefix}-{service_name}"
                
                logger.info(f"Deploying service: {service_name}")
                
                # Prepare container config
                run_config = {
                    "name": container_name,
                    "detach": True,
                    "network": network_name,
                    "labels": {
                        "auraops.project_id": str(project.id),
                        "auraops.service_name": service_name
                    }
                }
                
                # Image
                if 'image' in service_config:
                    run_config['image'] = service_config['image']
                elif 'build' in service_config:
                    # TODO: Handle build context
                    logger.warning(f"Build context not yet supported for {service_name}")
                    continue
                else:
                    logger.error(f"Service {service_name} has no image or build specified")
                    continue
                
                # Environment variables
                if 'environment' in service_config:
                    env = service_config['environment']
                    if isinstance(env, dict):
                        run_config['environment'] = env
                    elif isinstance(env, list):
                        run_config['environment'] = {
                            item.split('=')[0]: item.split('=')[1]
                            for item in env if '=' in item
                        }
                
                # Volumes
                if 'volumes' in service_config:
                    volumes = {}
                    for vol in service_config['volumes']:
                        if isinstance(vol, str):
                            parts = vol.split(':')
                            if len(parts) >= 2:
                                source = parts[0]
                                target = parts[1]
                                mode = parts[2] if len(parts) > 2 else 'rw'
                                
                                # Named volume
                                if not source.startswith('/') and not source.startswith('.'):
                                    source = f"{project_prefix}-{source}"
                                
                                volumes[source] = {"bind": target, "mode": mode}
                    
                    if volumes:
                        run_config['volumes'] = volumes
                
                # Ports
                if 'ports' in service_config:
                    ports = {}
                    for port_mapping in service_config['ports']:
                        if isinstance(port_mapping, str):
                            parts = port_mapping.split(':')
                            if len(parts) == 2:
                                host_port = parts[0]
                                container_port = parts[1]
                                ports[f"{container_port}/tcp"] = int(host_port)
                    
                    if ports:
                        run_config['ports'] = ports
                
                # Command
                if 'command' in service_config:
                    cmd = service_config['command']
                    if isinstance(cmd, list):
                        run_config['command'] = ' '.join(cmd)
                    else:
                        run_config['command'] = cmd
                
                # Restart policy
                restart = service_config.get('restart', 'no')
                if restart in ['always', 'unless-stopped', 'on-failure']:
                    run_config['restart_policy'] = {"Name": restart}
                
                # Stop and remove existing container
                try:
                    old_container = client.containers.get(container_name)
                    old_container.stop()
                    old_container.remove()
                    logger.info(f"Removed old container: {container_name}")
                except docker.errors.NotFound:
                    pass
                
                # Run container
                try:
                    container = client.containers.run(**run_config)
                    deployed_containers.append(container_name)
                    logger.info(f"Deployed container: {container.short_id}")
                except Exception as e:
                    logger.error(f"Failed to deploy {service_name}: {e}")
                    # Continue with other services
            
            logger.info(f"Compose project deployed: {len(deployed_containers)} services")
            
            return {
                "status": "success",
                "deployed_services": deployed_containers,
                "network": network_name,
                "volumes": created_volumes,
                "message": f"Deployed {len(deployed_containers)} services successfully"
            }
            
        except Exception as e:
            logger.error(f"Compose deployment failed: {e}")
            return {
                "status": "failed",
                "message": str(e)
            }
    
    @staticmethod
    def stop_compose_project(project: Project) -> dict:
        """Stop all services in a compose project"""
        
        client = docker.from_env()
        project_prefix = f"auraops-{project.id}"
        
        try:
            # Find all containers for this project
            containers = client.containers.list(
                filters={"label": f"auraops.project_id={project.id}"}
            )
            
            stopped = []
            for container in containers:
                container.stop()
                stopped.append(container.name)
                logger.info(f"Stopped: {container.name}")
            
            return {
                "status": "success",
                "stopped_services": stopped,
                "message": f"Stopped {len(stopped)} services"
            }
            
        except Exception as e:
            logger.error(f"Failed to stop compose project: {e}")
            return {
                "status": "failed",
                "message": str(e)
            }
    
    @staticmethod
    def remove_compose_project(project: Project) -> dict:
        """Remove all resources for a compose project"""
        
        client = docker.from_env()
        project_prefix = f"auraops-{project.id}"
        
        try:
            # Remove containers
            containers = client.containers.list(
                all=True,
                filters={"label": f"auraops.project_id={project.id}"}
            )
            
            for container in containers:
                try:
                    container.stop()
                    container.remove()
                    logger.info(f"Removed container: {container.name}")
                except:
                    pass
            
            # Remove network
            try:
                network = client.networks.get(f"{project_prefix}-network")
                network.remove()
                logger.info(f"Removed network: {network.name}")
            except:
                pass
            
            # Remove volumes (optional - data loss)
            # For now, keep volumes for data persistence
            
            return {
                "status": "success",
                "message": "Compose project removed successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to remove compose project: {e}")
            return {
                "status": "failed",
                "message": str(e)
            }
