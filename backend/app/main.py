from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, projects, webhooks, domains, services, users, admin
from app.db.session import engine, Base

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AuraOps API",
    description="Lightweight PaaS for VPS Deployments",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(domains.router, prefix="/api/v1/domains", tags=["domains"])
app.include_router(services.router, prefix="/api/v1/services", tags=["services"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])

@app.get("/")
def read_root():
    return {"status": "AuraOps v2 is running", "version": "2.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
