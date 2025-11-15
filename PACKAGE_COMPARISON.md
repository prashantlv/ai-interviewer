# Package Management Comparison

## 📊 Side-by-Side Comparison

| Aspect | Local Development (Conda) | Docker (Production) |
|--------|---------------------------|---------------------|
| **Environment Type** | Conda virtual environment | Container isolation |
| **Python Version** | 3.12.11 (conda) | 3.12.12 (official image) |
| **Package Manager** | conda + pip (mixed) | pip only |
| **Total Packages** | 161 Python packages | ~40-50 Python packages |
| **Base Size** | ~2-3 GB | ~500 MB |
| **Setup Time** | 5-10 minutes | 2-3 minutes (build) |
| **Portability** | Medium (conda required) | High (Docker only) |
| **Reproducibility** | High (with lock files) | Very High (image-based) |

---

## 📦 Package Source Files

### **Local Development**

```
environment.yml              ← Full conda export (all packages + dependencies)
requirements-all.lock        ← Exact pip package versions (161 packages)
server/requirements.txt      ← Minimal server deps (2 packages)
web_server/requirements.txt  ← Minimal web deps (13 packages)
```

### **Docker**

```
Dockerfile.web              ← Web server image definition
Dockerfile.worker           ← Worker image definition
server/requirements.txt     ← Installed in worker container
web_server/requirements.txt ← Installed in both containers
```

---

## 🔄 How They Work Together

### **Local Development Flow:**

```
┌─────────────────────────────────────┐
│   Conda Environment (pipecat-env)   │
│                                     │
│  1. conda create -n pipecat-env     │
│  2. pip install -r requirements.txt │
│                                     │
│  • All packages in same environment │
│  • Mixed conda + pip packages       │
│  • ~161 total packages              │
└─────────────────────────────────────┘
```

### **Docker Flow:**

```
┌─────────────────────────────────────┐
│   Docker Image (python:3.12-slim)   │
│                                     │
│  1. Start from clean Python 3.12    │
│  2. Install system deps (gcc, curl) │
│  3. pip install requirements.txt    │
│                                     │
│  • Only essential packages          │
│  • Pure pip installation            │
│  • ~40-50 packages                  │
└─────────────────────────────────────┘
```

---

## 🎯 Key Differences Explained

### 1. **Package Count: 161 vs 40-50**

**Why local has more packages?**
- Development tools (jupyter, ipython, etc.)
- Debugging tools
- Conda's own dependencies
- Transitive dependencies (pulled by conda)

**Why Docker has fewer?**
- Only runtime packages
- No dev tools
- Pip resolves minimal dependencies
- Clean slate (no legacy packages)

### 2. **Conda vs Pure Pip**

**Local (Conda + Pip):**
```bash
conda install python=3.12              # Python from conda
pip install pipecat-ai                 # Pipecat from PyPI
# Some packages from conda, some from pip
```

**Docker (Pure Pip):**
```bash
FROM python:3.12-slim                  # Python from Docker Hub
RUN pip install pipecat-ai             # Everything from PyPI
# All packages from pip only
```

### 3. **Dependencies**

**Local:**
```
pipecat-ai
├── Daily SDK (from pip)
├── OpenAI SDK (from pip)  
├── Cartesia (from pip)
└── 50+ other dependencies
```

**Docker:**
```
pipecat-ai[daily,openai,silero,tavus]
└── Only installs what's in brackets
    • Skips optional dependencies
    • Smaller footprint
```

---

## 🔍 Package Version Comparison

Let's compare key packages:

```bash
# Check versions in conda env
conda activate pipecat-env
pip show pipecat-ai cartesia fastapi openai

# Check versions in Docker
docker exec test-ai-worker pip show pipecat-ai cartesia fastapi openai
```

**Expected output (should match):**
```
pipecat-ai: 0.0.94
cartesia: 1.1.0
fastapi: 0.115.6
openai: 1.58.1
```

---

## ⚠️ Potential Issues & Solutions

### Issue 1: **Version Mismatch**

**Problem:**
```
Local: pipecat-ai==0.0.94
Docker: pipecat-ai==0.0.85
```

**Solution:**
```bash
# Update lock file from working environment
conda activate pipecat-env
pip freeze > requirements-all.lock

# Use in Docker
COPY requirements-all.lock /app/requirements.txt
RUN pip install -r /app/requirements.txt
```

### Issue 2: **Missing System Dependencies**

**Problem:**
```
Error: gcc not found (needed by some Python packages)
```

**Solution (already in Dockerfile):**
```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

### Issue 3: **Conda-Specific Packages**

**Problem:**
Some packages work in conda but fail in pure pip.

**Solution:**
Test with pure pip locally before Docker:
```bash
# Create test venv
python3.12 -m venv test-pip-env
source test-pip-env/bin/activate
pip install -r requirements-all.lock
# Test if everything works
```

---

## 📋 Verification Checklist

After setting up on a new machine, verify:

### **Conda Environment:**
```bash
conda activate pipecat-env

# 1. Check Python version
python --version  # Should be 3.12.x

# 2. Check key packages
pip show pipecat-ai cartesia fastapi

# 3. Test imports
python -c "import pipecat, cartesia, fastapi; print('✅ OK')"

# 4. Run test server
cd web_server
uvicorn main:app --host 0.0.0.0 --port 8009
# Visit http://localhost:8009/health
```

### **Docker Environment:**
```bash
# 1. Build images
docker build -f Dockerfile.web -t ai-interviewer-web:test .
docker build -f Dockerfile.worker -t ai-interviewer-worker:test .

# 2. Check package versions
docker run --rm ai-interviewer-web:test pip show pipecat-ai

# 3. Run containers
docker run -d --name test-web --network host ai-interviewer-web:test
docker run -d --name test-worker --network host ai-interviewer-worker:test

# 4. Test health endpoint
curl http://localhost:8009/health

# 5. Check logs
docker logs test-web
docker logs test-worker
```

---

## 🎓 Best Practices

### **For Development:**
1. ✅ Use conda environment for isolation
2. ✅ Keep `requirements.txt` minimal (high-level deps only)
3. ✅ Generate `requirements.lock` for exact versions
4. ✅ Test regularly in Docker to catch differences early

### **For Production/Deployment:**
1. ✅ Use Docker for consistency
2. ✅ Use lock files for reproducibility
3. ✅ Multi-stage builds to reduce image size
4. ✅ Pin versions in production

### **For Team Collaboration:**
1. ✅ Commit `environment.yml` (conda backup)
2. ✅ Commit `requirements.lock` (exact versions)
3. ✅ Commit minimal `requirements.txt` (readability)
4. ✅ Document system dependencies

---

## 🚀 Quick Commands

### **Setup on New Machine:**
```bash
# Option 1: Full replication
conda env create -f environment.yml

# Option 2: Minimal setup
./setup-environment.sh

# Option 3: Manual
conda create -n pipecat-env python=3.12
conda activate pipecat-env
pip install -r requirements-all.lock
```

### **Update Lock Files:**
```bash
# After installing new packages locally
conda activate pipecat-env
pip freeze > requirements-all.lock
conda env export > environment.yml
```

### **Compare Environments:**
```bash
# Local packages
conda activate pipecat-env
pip list > local-packages.txt

# Docker packages
docker exec test-ai-worker pip list > docker-packages.txt

# Compare
diff local-packages.txt docker-packages.txt
```

---

## 📊 Summary

### **You asked:**
1. ✅ How to replicate conda env to another machine?
   → Use `environment.yml` or `requirements-all.lock`

2. ✅ Does Docker use conda or pip?
   → **Pure pip** (no conda in Docker)

### **Key Takeaways:**

- **Local:** Conda + pip (161 packages, dev + runtime)
- **Docker:** Pure pip (40-50 packages, runtime only)
- **Sync:** Use lock files to keep them aligned
- **Portable:** Both approaches are now fully documented

### **Files Created:**
- ✅ `environment.yml` - Full conda export
- ✅ `requirements-all.lock` - All package versions
- ✅ `setup-environment.sh` - Automated setup script
- ✅ `ENVIRONMENT_MANAGEMENT_GUIDE.md` - Detailed guide
- ✅ `PACKAGE_COMPARISON.md` - This file

---

**Need help setting up? Run:**
```bash
./setup-environment.sh
```

**Questions? Check:**
- `ENVIRONMENT_MANAGEMENT_GUIDE.md` for detailed explanations
- This file for comparisons
- Docker logs for troubleshooting

