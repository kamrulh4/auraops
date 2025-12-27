# AuraOps

AuraOps is a modern web application with a Python FastAPI backend and a Next.js frontend.

## Project Structure

- `backend/`: FastAPI application
- `frontend/`: Next.js application
- `docker-compose.yml`: Docker configuration for orchestration

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js (for local development)
- Python 3.x (for local development)

### Running with Docker

1.  Make sure Docker is running.
2.  Start the application:

    ```bash
    docker-compose up --build
    ```

3.  Access the applications:
    - Frontend: http://localhost:3000
    - Backend API: http://localhost:8000 (approx, check docker-compose port mapping)

### Local Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```
