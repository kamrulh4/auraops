from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, projects, webhooks
from app.db.session import engine, Base

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AuraOps API",
    description="Peak Performance Deployment Engine",
    version="0.1.0"
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
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])

@app.get("/")
def read_root():
    return {"status": "AuraOps is running", "version": "0.1.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
