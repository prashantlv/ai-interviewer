# 📦 For Deployment Team - Quick Reference

## 🎯 What You Need to Know

**Application**: AI Interviewer  
**Port**: `8009`  
**Endpoint**: `http://<host>:8009`  
**Health Check**: `http://<host>:8009/health`

## 🐳 Docker Images to Build

```bash
# Build web server
docker build -f Dockerfile.web -t ai-interviewer-web:latest .

# Build worker
docker build -f Dockerfile.worker -t ai-interviewer-worker:latest .
```

## ⚙️ Required Environment Variables

```bash
MONGODB_URL=<mongodb-connection-string>
DATABASE_NAME=ai_interviewer
REDIS_URL=<redis-connection-string>
OPENAI_API_KEY=<openai-key>
DAILY_API_KEY=<daily-key>
```

## 🚀 Run Containers

### Web Server (1 instance)
```bash
docker run -d \
  --name ai-interviewer-web \
  -p 8009:8009 \
  -e MONGODB_URL="..." \
  -e DATABASE_NAME="ai_interviewer" \
  -e REDIS_URL="..." \
  -e OPENAI_API_KEY="..." \
  -e DAILY_API_KEY="..." \
  ai-interviewer-web:latest
```

### Workers (2-3 instances recommended)
```bash
docker run -d \
  --name ai-interviewer-worker-1 \
  -e MONGODB_URL="..." \
  -e REDIS_URL="..." \
  -e WEB_SERVER_URL="http://ai-interviewer-web:8009" \
  -e OPENAI_API_KEY="..." \
  -e DAILY_API_KEY="..." \
  ai-interviewer-worker:latest
```

## ✅ Verify Deployment

```bash
# Check health
curl http://<host>:8009/health

# Should return:
# {"status":"healthy","database":"connected","bot_queue":"healthy"}
```

## 📋 Dependencies

- **MongoDB**: Database (provide connection string)
- **Redis**: Job queue (provide connection string)

## 📚 Full Documentation

See `DEPLOYMENT_GUIDE.md` for complete details.

