# AuraOps v2 - Lightweight PaaS for VPS

**AuraOps** is a production-ready, lightweight Platform-as-a-Service (PaaS) designed for single VPS deployments. Deploy Docker apps, static sites, and managed services with automatic SSL, multi-user RBAC, and zero configuration.

## 🚀 Features

### Deployment Types
- **Docker Images** - Pull and run any Docker image
- **Dockerfiles** - Build from source (GitHub repos)
- **Docker Compose** - Multi-service YAML deployments
- **Static Sites** - Next.js, React, Vue, Vite, Angular
- **Service Templates** - One-click PostgreSQL, Redis, MinIO, MySQL, MongoDB, RabbitMQ, Elasticsearch

### Core Features
- ✅ **Automated SSL/TLS** - Let's Encrypt with auto-renewal
- ✅ **Wildcard Domains** - `*.yourdomain.com` support
- ✅ **Multi-User RBAC** - Admin/Developer/Viewer roles
- ✅ **Service Discovery** - Internal DNS routing
- ✅ **Monitoring** - System metrics, container stats, logs
- ✅ **Zero Configuration** - Auto-generated Nginx configs

---

## 📋 Prerequisites

### VPS Requirements
- **OS**: Ubuntu 20.04+ or Debian 11+
- **RAM**: Minimum 2GB (4GB recommended)
- **Storage**: 20GB+ SSD
- **CPU**: 2+ cores recommended

### Software Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Git
- Domain name (optional, for SSL)

---

## 🛠️ VPS Setup Guide

### Step 1: Initial VPS Setup

```bash
# SSH into your VPS
ssh root@your-vps-ip

# Update system packages
apt update && apt upgrade -y

# Install required packages
apt install -y curl git nano ufw

# Configure firewall
ufw allow OpenSSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 3000/tcp  # Frontend (optional, can be closed later)
ufw enable
```

### Step 2: Install Docker & Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Start Docker service
systemctl start docker
systemctl enable docker

# Verify installation
docker --version
docker compose version
```

### Step 3: Clone AuraOps Repository

```bash
# Create app directory
mkdir -p /opt/auraops
cd /opt/auraops

# Clone repository (replace with your repo URL)
git clone https://github.com/yourusername/AuraOps.git .

# Or download as zip and extract
wget https://github.com/yourusername/AuraOps/archive/main.zip
unzip main.zip
mv AuraOps-main/* .
```

### Step 4: Configure Environment Variables

```bash
# Create environment file
nano /opt/auraops/backend/.env
```

Add the following (customize values):

```env
# Database
DATABASE_URL=sqlite:///./auraops.db

# JWT Secret (generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here-change-this-in-production

# API Settings
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# Docker Network (optional)
DOCKER_NETWORK=auraops-network
```

### Step 5: Configure DNS (Optional but Recommended)

If you have a domain, point it to your VPS:

```
A Record:  @              → your-vps-ip
A Record:  *              → your-vps-ip  (for wildcard subdomains)
A Record:  api            → your-vps-ip
A Record:  dashboard      → your-vps-ip
```

**DNS Propagation**: Wait 5-15 minutes for DNS changes to propagate.

### Step 6: Deploy AuraOps

```bash
cd /opt/auraops

# Pull required images
docker compose pull

# Build and start services
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f
```

Expected output:
```
NAME               STATUS
auraops-backend    Up
auraops-frontend   Up
auraops-proxy      Up
```

### Step 7: Verify Deployment

```bash
# Check if API is responding
curl http://localhost:8000/api/v1/admin/health

# Expected response:
# {"status":"healthy","timestamp":"...","version":"2.0.0"}
```

---

## 🔐 Initial Setup

### 1. Register First Admin User

The first registered user automatically becomes an admin.

```bash
curl -X POST http://your-vps-ip:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourdomain.com",
    "username": "admin",
    "password": "YourSecurePassword123!"
  }'
```

### 2. Get Access Token

```bash
curl -X POST http://your-vps-ip:8000/api/v1/auth/token \
  -d "username=admin@yourdomain.com&password=YourSecurePassword123!"

# Save the access_token from the response
export TOKEN="your_access_token_here"
```

### 3. Access Web Dashboard

Open your browser:
- **Frontend**: `http://your-vps-ip:3000`
- **API Docs**: `http://your-vps-ip:8000/docs`

---

## 📚 Usage Examples

### Deploy PostgreSQL Database

```bash
curl -X POST http://your-vps-ip:8000/api/v1/services/deploy \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production-db",
    "service_type": "postgres"
  }'
```

### Get Database Credentials

```bash
# Replace {id} with the project_id from previous response
curl http://your-vps-ip:8000/api/v1/services/{id}/credentials \
  -H "Authorization: Bearer $TOKEN"
```

### Deploy Static Next.js Site

```bash
curl -X POST http://your-vps-ip:8000/api/v1/projects/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-blog",
    "deployment_type": "static_build",
    "provider": "github",
    "repo_url": "https://github.com/username/nextjs-blog",
    "branch": "main",
    "install_command": "npm install",
    "build_command": "npm run build",
    "static_dir": "out"
  }'

# Deploy the project
curl -X POST http://your-vps-ip:8000/api/v1/projects/{id}/deploy \
  -H "Authorization: Bearer $TOKEN"
```

### Add Custom Domain with SSL

```bash
curl -X POST http://your-vps-ip:8000/api/v1/domains/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "blog.yourdomain.com",
    "project_id": 1,
    "ssl_enabled": true
  }'
```

---

## 🔧 Management & Maintenance

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f proxy
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart backend
```

### Update AuraOps

```bash
cd /opt/auraops

# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose down
docker compose up -d --build
```

### Backup Database

```bash
# Backup SQLite database
docker compose exec backend cp /app/auraops.db /app/backup.db
docker cp auraops-backend:/app/backup.db ./auraops-backup-$(date +%Y%m%d).db
```

### Monitor System Resources

```bash
# System stats via API
curl http://your-vps-ip:8000/api/v1/admin/stats \
  -H "Authorization: Bearer $TOKEN" | jq .

# Docker stats
docker stats

# Disk usage
df -h

# Container list
docker ps -a
```

---

## 🌐 Production Hardening

### 1. Enable HTTPS Only

Once SSL is configured, redirect HTTP to HTTPS by updating Nginx config.

### 2. Secure Environment Variables

```bash
# Move .env to secure location
chmod 600 /opt/auraops/backend/.env
chown root:root /opt/auraops/backend/.env
```

### 3. Configure Firewall

```bash
# Close frontend port (access via proxy only)
ufw delete allow 3000/tcp

# Only allow 80, 443, and SSH
ufw status
```

### 4. Set Up Automated Backups

```bash
# Create backup script
nano /opt/auraops/scripts/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/auraops/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
docker compose exec -T backend cp /app/auraops.db /app/backup.db
docker cp auraops-backend:/app/backup.db $BACKUP_DIR/auraops-$DATE.db

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: auraops-$DATE.db"
```

```bash
chmod +x /opt/auraops/scripts/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /opt/auraops/scripts/backup.sh >> /var/log/auraops-backup.log 2>&1
```

### 5. Configure Log Rotation

```bash
nano /etc/logrotate.d/auraops
```

```
/opt/auraops/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## 🐛 Troubleshooting

### Backend Not Starting

```bash
# Check logs
docker compose logs backend

# Common issues:
# 1. Port conflicts - Check if port 8000 is in use
netstat -tuln | grep 8000

# 2. Permission issues
chmod -R 755 /opt/auraops
```

### SSL Certificate Issues

```bash
# Check Certbot logs
docker compose exec proxy cat /var/log/letsencrypt/letsencrypt.log

# Manually issue certificate
docker compose exec backend certbot certonly \
  --webroot -w /var/www/certbot \
  -d yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos
```

### Container Deployment Fails

```bash
# Check Docker network
docker network ls | grep auraops

# Recreate network if missing
docker network create auraops-network

# Check Docker socket permissions
ls -la /var/run/docker.sock
```

### Out of Disk Space

```bash
# Clean up Docker
docker system prune -a --volumes

# Remove old images
docker image prune -a

# Check volumes
docker volume ls
docker volume rm <unused_volume>
```

---

## 📖 API Documentation

Visit `http://your-vps-ip:8000/docs` for interactive API documentation (Swagger UI).

**Key Endpoints**:
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/token` - Login
- `GET /api/v1/services/templates` - List service templates
- `POST /api/v1/services/deploy` - Deploy service
- `POST /api/v1/projects/` - Create project
- `POST /api/v1/domains/` - Add custom domain
- `GET /api/v1/admin/stats` - System statistics

---

## 🤝 Support & Contributing

- **Documentation**: See `/docs` folder for detailed guides
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join GitHub Discussions for help

---

## 📄 License

This project is licensed under the MIT License.

---

## 🎉 You're All Set!

AuraOps is now running on your VPS! You can:

1. Deploy applications via API or frontend
2. Add custom domains with automatic SSL
3. Deploy one-click databases and services
4. Monitor system health and resources

**Next Steps**:
- Configure wildcard SSL for `*.yourdomain.com`
- Set up automated backups
- Invite team members with different roles
- Deploy your first application!

**Need Help?** Check the `/docs` folder or open an issue on GitHub.

---

**Built with ❤️ by the AuraOps Team**
