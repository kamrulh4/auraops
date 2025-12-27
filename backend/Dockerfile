# Build stage
FROM python:3.13-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final stage
FROM python:3.13-alpine

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create non-root user for security (Commented out for MVP access to docker.sock)
# RUN adduser -D auraops
USER root

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
