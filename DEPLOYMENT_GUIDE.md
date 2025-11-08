# 🚀 AI Interviewer - Deployment Guide

This document provides deployment instructions for the AI Interviewer application.

## 📋 Application Overview

**Application Name**: AI Interviewer  
**Type**: Python FastAPI Web Application + Background Workers  
**Port**: `8009` (Web Server)  
**Health Check Endpoint**: `http://<host>:8009/health`

## 🐳 Docker Setup

### Docker Images

The application consists of 2 Docker images:

1. **Web Server** (`Dockerfile.web`)
   - FastAPI web application
   - Port: `8009`
   - Health check: `GET /health`

2. **RQ Worker** (`Dockerfile.worker`)
   - Background job processor for bot management
   - No exposed ports (internal only)

### Building Docker Images

```bash
# Build web server image
docker build -f Dockerfile.web -t ai-interviewer-web:latest .

# Build worker image
docker build -f Dockerfile.worker -t ai-interviewer-worker:latest .
```

## 🌐 Endpoints

### Web Server Endpoints

- **Main Dashboard**: `http://<host>:8009/dashboard`
- **API Documentation**: `http://<host>:8009/docs`
- **Health Check**: `http://<host>:8009/health`
- **API Base**: `http://<host>:8009/api/v1/`

### Health Check Response

```json
{
  "status": "healthy",
  "timestamp": "2025-10-23T...",
  "database": "connected",
  "bot_queue": "healthy"
}
```

## ⚙️ Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URL` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `DATABASE_NAME` | Database name | `ai_interviewer` |
| `REDIS_URL` | Redis connection string | `redis://redis-host:6379/0` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-proj-...` |
| `DAILY_API_KEY` | Daily.co API key | `3c9c92366e...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VIDEO_SERVICE` | Video service: `tavus`, `heygen`, or `none` | `none` |
| `BOT_IMPLEMENTATION` | Bot backend: `openai` or `gemini` | `openai` |
| `TAVUS_API_KEY` | Tavus API key (if using Tavus) | - |
| `TAVUS_REPLICA_ID` | Tavus replica ID (if using Tavus) | - |
| `HEYGEN_API_KEY` | HeyGen API key (if using HeyGen) | - |
| `HEYGEN_AVATAR_ID` | HeyGen avatar ID (if using HeyGen) | - |

## 🚀 Deployment Instructions

### 1. Web Server Container

```bash
docker run -d \
  --name ai-interviewer-web \
  -p 8009:8009 \
  -e MONGODB_URL="<mongodb-connection-string>" \
  -e DATABASE_NAME="ai_interviewer" \
  -e REDIS_URL="<redis-connection-string>" \
  -e OPENAI_API_KEY="<openai-key>" \
  -e DAILY_API_KEY="<daily-key>" \
  -e VIDEO_SERVICE="tavus" \
  -e TAVUS_API_KEY="<tavus-key>" \
  -e TAVUS_REPLICA_ID="<tavus-replica-id>" \
  ai-interviewer-web:latest
```

### 2. Worker Container (Background Jobs)

```bash
docker run -d \
  --name ai-interviewer-worker \
  -e MONGODB_URL="<mongodb-connection-string>" \
  -e DATABASE_NAME="ai_interviewer" \
  -e REDIS_URL="<redis-connection-string>" \
  -e WEB_SERVER_URL="http://ai-interviewer-web:8009" \
  -e OPENAI_API_KEY="<openai-key>" \
  -e DAILY_API_KEY="<daily-key>" \
  -e VIDEO_SERVICE="tavus" \
  -e TAVUS_API_KEY="<tavus-key>" \
  -e TAVUS_REPLICA_ID="<tavus-replica-id>" \
  ai-interviewer-worker:latest
```

**Note**: Run multiple worker containers for better throughput (recommended: 2-3 workers).

## 📦 Dependencies

### External Services Required

1. **MongoDB** - Database for storing interviews and results
   - Can use MongoDB Atlas (cloud) or self-hosted
   - Connection string format: `mongodb://host:port/` or `mongodb+srv://...`

2. **Redis** - Job queue for background bot processing
   - Required for RQ workers
   - Connection string format: `redis://host:6379/0`

### Network Requirements

- Web server must be accessible on port `8009`
- Worker containers need access to:
  - MongoDB (default port 27017)
  - Redis (default port 6379)
  - Web server (for API calls)

## 🔍 Health Checks

### Web Server Health Check

```bash
curl http://<host>:8009/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "bot_queue": "healthy"
}
```

### Container Health Check

The web server container includes a built-in health check:
- Command: `curl -f http://localhost:8009/health || exit 1`
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3

## 📊 Resource Requirements

### Web Server Container
- **CPU**: 1-2 cores
- **Memory**: 1-2 GB
- **Port**: 8009 (HTTP)

### Worker Container
- **CPU**: 1-2 cores per worker
- **Memory**: 1-2 GB per worker
- **Ports**: None (internal only)

## 🔄 Scaling

### Web Server
- Run 1-2 instances behind a load balancer
- Use sticky sessions if needed (not required)

### Workers
- Run 2-3 worker instances for better throughput
- Workers automatically process jobs from Redis queue
- Scale up workers if job queue grows

## 📝 Logs

### View Logs

```bash
# Web server logs
docker logs -f ai-interviewer-web

# Worker logs
docker logs -f ai-interviewer-worker
```

### Log Locations (inside container)
- Application logs: stdout/stderr
- No file-based logging (all to stdout)

## 🛠️ Troubleshooting

### Container won't start
- Check environment variables are set correctly
- Verify MongoDB and Redis are accessible
- Check container logs: `docker logs ai-interviewer-web`

### Health check fails
- Verify MongoDB connection string is correct
- Check Redis is accessible
- Ensure port 8009 is not blocked

### Workers not processing jobs
- Verify Redis connection
- Check `WEB_SERVER_URL` points to web server
- Ensure worker has same API keys as web server

## 📞 Support

For deployment issues, check:
1. Container logs
2. Health check endpoint
3. MongoDB and Redis connectivity
4. Environment variables

---

**Deployment Team Notes:**
- Application runs on port **8009**
- Health check: `GET /health`
- Requires MongoDB and Redis
- Run 1 web server + 2-3 workers
- All configuration via environment variables

