from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "changeme-super-secret-key-for-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = "sqlite:////app/data/auraops.db"
    
    # Docker
    DOCKER_SOCKET: str = "/var/run/docker.sock"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
