# 🧪 Testing Docker Images Locally

Quick guide to test Docker images before handoff.

## 🚀 Quick Test (Automated)

```bash
# Run automated test script
./test-docker.sh
```

This will:
- Build both images
- Test web server container
- Test worker container
- Verify images work correctly

## 📋 Manual Testing Steps

### 1. Build Images

```bash
# Build web server
docker build -f Dockerfile.web -t ai-interviewer-web:test .

# Build worker
docker build -f Dockerfile.worker -t ai-interviewer-worker:test .
```

### 2. Test Web Server (Basic)

```bash
# Start Redis (required)
docker run -d --name test-redis -p 6379:6379 redis:7-alpine

# Start web server (will show connection errors but image works)
docker run --rm -p 8009:8009 \
  -e MONGODB_URL="mongodb://test:test@test:27017/test" \
  -e DATABASE_NAME="test" \
  -e REDIS_URL="redis://host.docker.internal:6379/0" \
  -e OPENAI_API_KEY="test" \
  -e DAILY_API_KEY="test" \
  ai-interviewer-web:test

# In another terminal, test health endpoint
curl http://localhost:8009/health
```

### 3. Test with Docker Compose (Full Test)

```bash
# Start all services (requires .env file with real credentials)
docker-compose up -d

# Check logs
docker-compose logs -f web-server

# Test health
curl http://localhost:8009/health

# Stop
docker-compose down
```

### 4. Verify Images

```bash
# List images
docker images | grep ai-interviewer

# Check image size (should be reasonable)
docker images ai-interviewer-web:test
docker images ai-interviewer-worker:test

# Inspect image
docker inspect ai-interviewer-web:test
```

## ✅ Success Criteria

- [ ] Both images build without errors
- [ ] Web server container starts
- [ ] Health endpoint responds (even if unhealthy due to missing services)
- [ ] Worker image builds and can run
- [ ] No obvious errors in container logs

## 🔍 Common Issues

### Image too large
- Check `.dockerignore` is working
- Remove unnecessary files

### Build fails
- Check Dockerfile syntax
- Verify requirements.txt exists
- Check Python version compatibility

### Container exits immediately
- Check environment variables
- Review container logs: `docker logs <container-name>`

## 📦 Tag for Production

After testing, tag images for deployment:

```bash
docker tag ai-interviewer-web:test ai-interviewer-web:latest
docker tag ai-interviewer-worker:test ai-interviewer-worker:latest
```

