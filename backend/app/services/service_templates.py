import docker
import logging
import secrets
from typing import Dict, Optional
from app.models.project import Project

logger = logging.getLogger(__name__)

class ServiceTemplates:
    """
    Pre-configured service templates for common infrastructure components
    
    Each template includes:
    - Docker image
    - Default ports
    - Environment variables
    - Volume mounts
    - Resource limits
    - Health checks
    """
    
    TEMPLATES = {
        "minio": {
            "name": "MinIO S3 Storage",
            "description": "S3-compatible object storage",
            "image": "minio/minio:latest",
            "ports": {
                "api": 9000,
                "console": 9001
            },
            "command": "server /data --console-address :9001",
            "env_vars": lambda: {
                "MINIO_ROOT_USER": "minioadmin",
                "MINIO_ROOT_PASSWORD": secrets.token_urlsafe(16)
            },
            "volumes": {
                "data": "/data"
            },
            "healthcheck": {
                "test": ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"],
                "interval": 30,
                "timeout": 10,
                "retries": 3
            },
            "category": "storage"
        },
        
        "postgres": {
            "name": "PostgreSQL Database",
            "description": "Relational database",
            "image": "postgres:16-alpine",
            "ports": {
                "db": 5432
            },
            "env_vars": lambda: {
                "POSTGRES_USER": "postgres",
                "POSTGRES_PASSWORD": secrets.token_urlsafe(16),
                "POSTGRES_DB": "app",
                "PGDATA": "/var/lib/postgresql/data/pgdata"
            },
            "volumes": {
                "data": "/var/lib/postgresql/data"
            },
            "healthcheck": {
                "test": ["CMD-SHELL", "pg_isready -U postgres"],
                "interval": 10,
                "timeout": 5,
                "retries": 5
            },
            "category": "database"
        },
        
        "mysql": {
            "name": "MySQL Database",
            "description": "Relational database",
            "image": "mysql:8.0",
            "ports": {
                "db": 3306
            },
            "env_vars": lambda: {
                "MYSQL_ROOT_PASSWORD": secrets.token_urlsafe(16),
                "MYSQL_DATABASE": "app",
                "MYSQL_USER": "app",
                "MYSQL_PASSWORD": secrets.token_urlsafe(16)
            },
            "volumes": {
                "data": "/var/lib/mysql"
            },
            "healthcheck": {
                "test": ["CMD", "mysqladmin", "ping", "-h", "localhost"],
                "interval": 10,
                "timeout": 5,
                "retries": 5
            },
            "category": "database"
        },
        
        "mongodb": {
            "name": "MongoDB Database",
            "description": "NoSQL document database",
            "image": "mongo:7",
            "ports": {
                "db": 27017
            },
            "env_vars": lambda: {
                "MONGO_INITDB_ROOT_USERNAME": "admin",
                "MONGO_INITDB_ROOT_PASSWORD": secrets.token_urlsafe(16),
                "MONGO_INITDB_DATABASE": "app"
            },
            "volumes": {
                "data": "/data/db",
                "config": "/data/configdb"
            },
            "healthcheck": {
                "test": ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"],
                "interval": 10,
                "timeout": 5,
                "retries": 5
            },
            "category": "database"
        },
        
        "redis": {
            "name": "Redis Cache",
            "description": "In-memory cache and message broker",
            "image": "redis:7-alpine",
            "ports": {
                "cache": 6379
            },
            "command": "redis-server --requirepass {password}",
            "env_vars": lambda: {
                "REDIS_PASSWORD": secrets.token_urlsafe(16)
            },
            "volumes": {
                "data": "/data"
            },
            "healthcheck": {
                "test": ["CMD", "redis-cli", "ping"],
                "interval": 10,
                "timeout": 5,
                "retries": 3
            },
            "category": "cache"
        },
        
        "rabbitmq": {
            "name": "RabbitMQ Message Queue",
            "description": "Message broker",
            "image": "rabbitmq:3-management-alpine",
            "ports": {
                "amqp": 5672,
                "management": 15672
            },
            "env_vars": lambda: {
                "RABBITMQ_DEFAULT_USER": "admin",
                "RABBITMQ_DEFAULT_PASSWORD": secrets.token_urlsafe(16)
            },
            "volumes": {
                "data": "/var/lib/rabbitmq"
            },
            "healthcheck": {
                "test": ["CMD", "rabbitmq-diagnostics", "ping"],
                "interval": 30,
                "timeout": 10,
                "retries": 3
            },
            "category": "queue"
        },
        
        "elasticsearch": {
            "name": "Elasticsearch Search Engine",
            "description": "Full-text search and analytics",
            "image": "elasticsearch:8.11.0",
            "ports": {
                "http": 9200,
                "transport": 9300
            },
            "env_vars": lambda: {
                "discovery.type": "single-node",
                "ELASTIC_PASSWORD": secrets.token_urlsafe(16),
                "xpack.security.enabled": "true"
            },
            "volumes": {
                "data": "/usr/share/elasticsearch/data"
            },
            "healthcheck": {
                "test": ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"],
                "interval": 30,
                "timeout": 10,
                "retries": 3
            },
            "category": "search"
        }
    }
    
    @classmethod
    def get_template(cls, service_type: str) -> Optional[Dict]:
        """Get service template by type"""
        return cls.TEMPLATES.get(service_type.lower())
    
    @classmethod
    def list_templates(cls, category: Optional[str] = None) -> Dict:
        """List all available service templates"""
        
        templates = {}
        for key, template in cls.TEMPLATES.items():
            if category and template["category"] != category:
                continue
            
            templates[key] = {
                "name": template["name"],
                "description": template["description"],
                "image": template["image"],
                "category": template["category"],
                "ports": template["ports"]
            }
        
        return templates
    
    @classmethod
    def get_categories(cls) -> list:
        """Get all service categories"""
        categories = set()
        for template in cls.TEMPLATES.values():
            categories.add(template["category"])
        return sorted(list(categories))


class ServiceDeployer:
    """Deploy and manage service templates"""
    
    @staticmethod
    def deploy_service(project: Project, service_type: str) -> dict:
        """
        Deploy a managed service from template
        
        Args:
            project: Project model instance
            service_type: Type of service (minio, postgres, redis, etc.)
        
        Returns:
            Dict with deployment status and credentials
        """
        
        template = ServiceTemplates.get_template(service_type)
        if not template:
            raise ValueError(f"Unknown service type: {service_type}")
        
        client = docker.from_env()
        container_name = f"auraops-service-{project.id}"
        
        try:
            # Generate environment variables (with random passwords)
            env_vars = template["env_vars"]()
            
            # Override with user-provided env vars
            if project.env_vars:
                env_vars.update(project.env_vars)
            
            # Handle command template (e.g., Redis password)
            command = template.get("command")
            if command and "{password}" in command:
                password = env_vars.get("REDIS_PASSWORD", "")
                command = command.format(password=password)
            
            # Create volumes
            volumes = {}
            for vol_name, mount_point in template.get("volumes", {}).items():
                volume_name = f"auraops-{project.id}-{vol_name}"
                # Create volume if it doesn't exist
                try:
                    client.volumes.get(volume_name)
                except docker.errors.NotFound:
                    client.volumes.create(name=volume_name)
                
                volumes[volume_name] = {"bind": mount_point, "mode": "rw"}
            
            # Stop and remove old container if exists
            try:
                old_container = client.containers.get(container_name)
                old_container.stop()
                old_container.remove()
                logger.info(f"Removed old service container: {container_name}")
            except docker.errors.NotFound:
                pass
            
            # Get primary port
            primary_port = list(template["ports"].values())[0]
            
            # Create port mapping
            ports = {}
            for port in template["ports"].values():
                ports[f"{port}/tcp"] = port
            
            # Run service container
            logger.info(f"Deploying {template['name']} as {container_name}")
            
            container = client.containers.run(
                image=template["image"],
                name=container_name,
                command=command if command else None,
                detach=True,
                environment=env_vars,
                volumes=volumes,
                ports=ports,
                restart_policy={"Name": "unless-stopped"},
                network="auraops-network"
                # Note: healthcheck not supported in python-docker run() - use compose for healthchecks
            )
            
            logger.info(f"Service deployed successfully: {container.short_id}")
            
            # Prepare connection info for user
            connection_info = {
                "internal_url": f"http://{container_name}:{primary_port}",
                "container_name": container_name,
                "ports": template["ports"],
                "credentials": {}
            }
            
            # Extract relevant credentials (hide full env vars)
            if service_type == "postgres":
                connection_info["credentials"] = {
                    "username": env_vars.get("POSTGRES_USER"),
                    "password": env_vars.get("POSTGRES_PASSWORD"),
                    "database": env_vars.get("POSTGRES_DB"),
                    "connection_string": f"postgresql://{env_vars['POSTGRES_USER']}:{env_vars['POSTGRES_PASSWORD']}@{container_name}:5432/{env_vars['POSTGRES_DB']}"
                }
            elif service_type == "mysql":
                connection_info["credentials"] = {
                    "username": env_vars.get("MYSQL_USER"),
                    "password": env_vars.get("MYSQL_PASSWORD"),
                    "root_password": env_vars.get("MYSQL_ROOT_PASSWORD"),
                    "database": env_vars.get("MYSQL_DATABASE"),
                    "connection_string": f"mysql://{env_vars['MYSQL_USER']}:{env_vars['MYSQL_PASSWORD']}@{container_name}:3306/{env_vars['MYSQL_DATABASE']}"
                }
            elif service_type == "mongodb":
                connection_info["credentials"] = {
                    "username": env_vars.get("MONGO_INITDB_ROOT_USERNAME"),
                    "password": env_vars.get("MONGO_INITDB_ROOT_PASSWORD"),
                    "database": env_vars.get("MONGO_INITDB_DATABASE"),
                    "connection_string": f"mongodb://{env_vars['MONGO_INITDB_ROOT_USERNAME']}:{env_vars['MONGO_INITDB_ROOT_PASSWORD']}@{container_name}:27017/{env_vars['MONGO_INITDB_DATABASE']}?authSource=admin"
                }
            elif service_type == "redis":
                connection_info["credentials"] = {
                    "password": env_vars.get("REDIS_PASSWORD"),
                    "connection_string": f"redis://:{env_vars['REDIS_PASSWORD']}@{container_name}:6379"
                }
            elif service_type == "minio":
                connection_info["credentials"] = {
                    "access_key": env_vars.get("MINIO_ROOT_USER"),
                    "secret_key": env_vars.get("MINIO_ROOT_PASSWORD"),
                    "endpoint": f"http://{container_name}:9000",
                    "console_url": f"http://{container_name}:9001"
                }
            
            # Save credentials to project env_vars for future reference
            project.env_vars = env_vars
            
            return {
                "status": "success",
                "service_type": service_type,
                "service_name": template["name"],
                "container_id": container.short_id,
                "connection_info": connection_info,
                "message": f"{template['name']} deployed successfully"
            }
            
        except Exception as e:
            logger.error(f"Service deployment failed: {e}")
            return {
                "status": "failed",
                "message": str(e)
            }
