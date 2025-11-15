# Environment Management Guide

## Current Setup Overview

### **Local Development (Conda)**
- Environment Name: `pipecat-env`
- Python Version: 3.12
- Package Manager: Conda + Pip (mixed)
- Total Packages: ~218

### **Docker (Production/Testing)**
- Base Image: `python:3.12-slim`
- Package Manager: **pip only** (NO conda)
- Packages: Installed from `requirements.txt` files

---

## 🔑 **Key Insight: Different Approaches**

### Local (Conda)
```
conda env → pipecat-env → mixed conda + pip packages
```

### Docker (Production)
```
python:3.12-slim → pip only → requirements.txt
```

**This is intentional!** Docker doesn't need conda because:
- Containers are isolated (don't need conda's isolation)
- Smaller image size (conda adds ~1GB+)
- Faster builds (pip is faster than conda)

---

## 📦 **Question 1: Replicate Conda Env to Another Machine**

### **Option A: Export Full Conda Environment (Exact Replication)**

```bash
# On source machine (current)
cd /home/prashant/Playground/personal/consult/ai-interviewer

# Export complete environment with ALL packages
conda env export -n pipecat-env > environment.yml

# Export only pip packages from conda env
conda activate pipecat-env
pip list --format=freeze > conda-pip-requirements.txt
conda deactivate
```

```bash
# On target machine (new)
# 1. Create environment from file
conda env create -f environment.yml

# OR if you just want the essentials:
# 2. Create minimal env and install
conda create -n pipecat-env python=3.12 -y
conda activate pipecat-env
pip install -r server/requirements.txt
pip install -r web_server/requirements.txt
```

### **Option B: Minimal Reproducible Environment (Recommended)**

```bash
# On source machine
cd /home/prashant/Playground/personal/consult/ai-interviewer

# Export ONLY the packages you explicitly installed (not dependencies)
pip list --format=freeze | grep -E "pipecat-ai|cartesia|fastapi|uvicorn|rq|redis|pymongo|python-dotenv|openai|httpx|jinja2" > requirements-minimal.txt
```

Then on target machine:
```bash
conda create -n pipecat-env python=3.12 -y
conda activate pipecat-env
pip install -r requirements-minimal.txt
```

---

## 📦 **Question 2: Docker Package Management**

### **How Docker Manages Packages**

Looking at `Dockerfile.worker`:

```dockerfile
# 1. Starts with clean Python 3.12
FROM python:3.12-slim

# 2. Installs system dependencies (gcc, g++, curl)
RUN apt-get update && apt-get install -y gcc g++ curl

# 3. Installs Python packages via pip from requirements.txt
COPY server/requirements.txt /app/server/requirements.txt
RUN pip install -r server/requirements.txt

# NO CONDA! Pure pip installation
```

### **Current Requirements Files**

**server/requirements.txt:**
```
pipecat-ai[daily,elevenlabs,openai,silero,google,runner,tavus,simli,heygen]>=0.0.84
cartesia>=1.0.0
```

**web_server/requirements.txt:**
```
fastapi>=0.115.4
uvicorn[standard]>=0.32.0
python-dotenv>=1.0.0
pymongo>=4.10.1
redis>=5.2.0
rq>=2.0.0
httpx>=0.28.1
openai>=1.57.4
pydantic>=2.10.3
jinja2>=3.1.4
python-multipart>=0.0.19
tortoise-orm>=0.21.6
aerich>=0.7.2
```

---

## 🔄 **Synchronization Strategy**

### **Problem:**
- Local conda env has 218 packages
- Docker uses minimal requirements.txt
- **Risk:** Version mismatches between local and Docker

### **Solution: Keep Them Synced**

#### **Method 1: Lock File Approach (Recommended)**

```bash
# 1. Generate lock files from your working conda env
conda activate pipecat-env

# Server packages
cd server
pip freeze > requirements.lock
# Keep requirements.txt minimal for readability
echo "pipecat-ai[daily,elevenlabs,openai,silero,google,runner,tavus,simli,heygen]>=0.0.84" > requirements.txt
echo "cartesia>=1.0.0" >> requirements.txt

# Web server packages  
cd ../web_server
pip freeze | grep -E "fastapi|uvicorn|python-dotenv|pymongo|redis|rq|httpx|openai|pydantic|jinja2|python-multipart|tortoise-orm|aerich" > requirements.lock

cd ..
```

Then update Dockerfile to use `.lock` files:
```dockerfile
# Use lock files for exact versions
COPY server/requirements.lock /app/server/requirements.txt
COPY web_server/requirements.lock /app/web_server/requirements.txt
RUN pip install -r /app/server/requirements.txt
RUN pip install -r /app/web_server/requirements.txt
```

#### **Method 2: Single Source of Truth**

Create one master requirements file:

```bash
# Create master requirements
cat > requirements-all.txt << 'EOF'
# AI/Bot Dependencies
pipecat-ai[daily,elevenlabs,openai,silero,google,runner,tavus,simli,heygen]>=0.0.84
cartesia>=1.0.0

# Web Server Dependencies
fastapi>=0.115.4
uvicorn[standard]>=0.32.0
python-dotenv>=1.0.0
pymongo>=4.10.1
redis>=5.2.0
rq>=2.0.0
httpx>=0.28.1
openai>=1.57.4
pydantic>=2.10.3
jinja2>=3.1.4
python-multipart>=0.0.19
tortoise-orm>=0.21.6
aerich>=0.7.2
EOF

# Use in conda
conda activate pipecat-env
pip install -r requirements-all.txt

# Use in Docker
# Update Dockerfile.worker to use this single file
```

---

## 🎯 **Recommended Workflow**

### **For New Machine Setup:**

```bash
# 1. Clone repo
git clone <repo-url>
cd ai-interviewer

# 2. Create conda environment
conda create -n pipecat-env python=3.12 -y
conda activate pipecat-env

# 3. Install all dependencies
pip install -r server/requirements.txt
pip install -r web_server/requirements.txt

# 4. Setup .env files
cp server/env.example server/.env
cp web_server/env.example web_server/.env
# Edit .env files with your API keys

# 5. Test locally
cd web_server
uvicorn main:app --reload --port 8009
```

### **For Docker Deployment:**

```bash
# 1. Build images (uses requirements.txt automatically)
docker build -f Dockerfile.web -t ai-interviewer-web:latest .
docker build -f Dockerfile.worker -t ai-interviewer-worker:latest .

# 2. Run containers
docker-compose up -d
# OR use docker run commands
```

---

## 📋 **Quick Commands Reference**

### Export Current Conda Environment:
```bash
# Full export (all packages with versions)
conda env export -n pipecat-env > environment.yml

# Minimal export (only top-level packages)
conda env export -n pipecat-env --from-history > environment-minimal.yml

# Pip packages only
conda activate pipecat-env
pip list --format=freeze > pip-requirements.txt
```

### Create Environment on New Machine:
```bash
# From full export
conda env create -f environment.yml

# From minimal export
conda env create -f environment-minimal.yml

# From pip requirements
conda create -n pipecat-env python=3.12 -y
conda activate pipecat-env
pip install -r pip-requirements.txt
```

### Verify Package Versions Match:
```bash
# In conda env
conda activate pipecat-env
pip show pipecat-ai cartesia fastapi

# In Docker container
docker exec test-ai-worker pip show pipecat-ai cartesia fastapi
```

---

## 🚨 **Common Issues & Solutions**

### Issue 1: "Package versions differ between local and Docker"
**Solution:** Generate lock files from working environment:
```bash
pip freeze > requirements.lock
```

### Issue 2: "Conda environment too large (GB+)"
**Solution:** Create minimal environment with only project dependencies:
```bash
conda create -n pipecat-env-minimal python=3.12
pip install -r server/requirements.txt -r web_server/requirements.txt
```

### Issue 3: "Docker build fails but local works"
**Solution:** Test locally with pip-only (no conda):
```bash
python3.12 -m venv test-venv
source test-venv/bin/activate
pip install -r server/requirements.txt -r web_server/requirements.txt
# Test if it works
```

---

## 🎓 **Best Practices**

1. **Use `requirements.txt` for dependencies** (high-level packages)
2. **Use `requirements.lock` for deployment** (exact versions)
3. **Keep Docker and local in sync** by testing both regularly
4. **Document system dependencies** (gcc, ffmpeg, etc.)
5. **Version pin critical packages** (pipecat-ai, openai, etc.)

---

## 📦 **Example: Complete Portable Setup**

Create this structure:
```
ai-interviewer/
├── environment.yml          # Full conda export (backup)
├── requirements.txt         # Minimal high-level deps
├── requirements.lock        # Exact versions for production
├── server/
│   ├── requirements.txt     # Server-specific deps
│   └── requirements.lock
└── web_server/
    ├── requirements.txt     # Web-specific deps
    └── requirements.lock
```

Then anyone can replicate with:
```bash
# Quick start (latest versions)
conda env create -f environment.yml

# OR production-exact (locked versions)
conda create -n pipecat-env python=3.12
pip install -r requirements.lock
```

---

## 🔧 **Action Items for Your Project**

I can help you:

1. ✅ **Export current conda environment to portable files**
2. ✅ **Create lock files for exact version replication**
3. ✅ **Update Dockerfiles to use lock files**
4. ✅ **Create setup script for new machines**
5. ✅ **Document all system dependencies**

**Would you like me to generate these files now?**

