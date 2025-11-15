# Migration Guide: Conda to Pure Pip

## 🎯 What Changed?

We've moved from **conda** to **pure pip** for local development. This makes the project:
- ✅ Simpler to set up
- ✅ Consistent with Docker (both use pip)
- ✅ Easier for contributors (no conda required)
- ✅ Lighter weight (no 2GB+ conda installation)

---

## 📦 Old vs New Approach

### **Before (Conda):**
```bash
conda create -n pipecat-env python=3.12
conda activate pipecat-env
pip install -r server/requirements.txt
pip install -r web_server/requirements.txt
```

### **After (Pure Pip):**
```bash
./setup-venv.sh
source venv/bin/activate
# Packages already installed!
```

---

## 🔄 Migration Steps

### **If you have existing conda environment:**

**Option 1: Fresh Start (Recommended)**
```bash
# 1. Backup your .env files (if any custom changes)
cp server/.env server/.env.backup
cp web_server/.env web_server/.env.backup

# 2. Setup new venv
./setup-venv.sh

# 3. Restore .env files if needed
# (setup script will create them from examples)

# 4. Start using venv
./start.sh
```

**Option 2: Side-by-side (Keep both)**
```bash
# 1. Setup venv (conda stays untouched)
./setup-venv.sh

# 2. You can still use conda if needed
conda activate pipecat-env

# 3. Or use venv (recommended)
source venv/bin/activate
```

**Option 3: Remove conda completely**
```bash
# 1. Setup venv first
./setup-venv.sh

# 2. Remove conda environment
conda deactivate
conda env remove -n pipecat-env

# 3. Optional: Uninstall conda
# (if you don't use it for other projects)
```

---

## 🚀 New Workflow

### **Setup (First Time):**
```bash
./setup-venv.sh
```

### **Daily Work:**
```bash
./start.sh
# That's it! The script activates venv automatically
```

### **Manual Commands:**
```bash
# Activate venv
source venv/bin/activate

# Run commands
python main.py
pip install some-package
python -c "import pipecat; print(pipecat.__version__)"

# Deactivate when done
deactivate
```

---

## 📁 What's Different?

### **Files Changed:**

| File | Old | New |
|------|-----|-----|
| Setup Script | `setup-environment.sh` | `setup-venv.sh` |
| Environment | `conda env` | `venv/` directory |
| Activation | `conda activate pipecat-env` | `source venv/bin/activate` |
| Start Script | Uses conda | Uses venv |
| Worker Script | Checks for conda | Uses sys.executable |

### **Files Archived:**

Moved to `archive/conda/`:
- `environment.yml` - Conda environment export
- `setup-environment.sh` - Conda setup script

These are kept for reference but not used anymore.

---

## 🔍 Key Differences

### **Activation:**

**Old (Conda):**
```bash
conda activate pipecat-env
```

**New (Venv):**
```bash
source venv/bin/activate
```

### **Package Management:**

**Old:**
```bash
conda activate pipecat-env
pip install package-name
```

**New:**
```bash
source venv/bin/activate
pip install package-name
```

### **Checking Environment:**

**Old:**
```bash
conda info --envs
conda list
```

**New:**
```bash
which python  # Should show /path/to/ai-interviewer/venv/bin/python
pip list
```

---

## ✅ Verification

After migration, verify everything works:

### **1. Check Python:**
```bash
source venv/bin/activate
which python
# Should output: /path/to/ai-interviewer/venv/bin/python

python --version
# Should be: Python 3.12.x or 3.11.x or 3.10.x
```

### **2. Check Packages:**
```bash
pip show pipecat-ai cartesia fastapi
# Should show package info
```

### **3. Test Import:**
```bash
python -c "import pipecat, cartesia, fastapi; print('✅ All imports OK')"
```

### **4. Start Application:**
```bash
./start.sh
# Should start without errors
```

### **5. Access Dashboard:**
```bash
open http://localhost:8009/dashboard
# Should load successfully
```

---

## 🐛 Troubleshooting

### **Issue: Command not found: python3.12**

Your system doesn't have Python 3.12. Options:

**Option A: Install Python 3.12**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3.12-venv

# macOS (with Homebrew)
brew install python@3.12
```

**Option B: Use Python 3.11 or 3.10**
```bash
# Setup script will detect and use available version
./setup-venv.sh
```

### **Issue: venv creation fails**

```bash
# Install venv module
sudo apt install python3-venv  # Ubuntu/Debian
# or
sudo yum install python3-venv  # RHEL/CentOS
```

### **Issue: Packages won't install**

```bash
# Upgrade pip first
source venv/bin/activate
pip install --upgrade pip

# Then install packages
pip install -r server/requirements.txt
pip install -r web_server/requirements.txt
```

### **Issue: start.sh says "venv not found"**

```bash
# Run setup first
./setup-venv.sh

# Then start
./start.sh
```

### **Issue: Want to go back to conda**

```bash
# Conda files are archived, you can restore them:
cp archive/conda/environment.yml .
cp archive/conda/setup-environment.sh .

# Run conda setup
./setup-environment.sh
```

---

## 📊 Comparison

| Aspect | Conda | Pure Pip (venv) |
|--------|-------|-----------------|
| **Setup Time** | 5-10 min | 2-3 min |
| **Disk Space** | ~2-3 GB | ~500 MB |
| **Dependencies** | Conda required | Python only |
| **Consistency** | Different from Docker | Same as Docker |
| **Portability** | Conda-specific | Standard Python |
| **Speed** | Slower (conda solver) | Faster (pip) |
| **Learning Curve** | Higher | Lower |

---

## 🎯 Why This Change?

### **1. Consistency**
- Docker uses pip → Local uses pip
- Same package versions everywhere
- No more "works in Docker but not locally"

### **2. Simplicity**
- No conda installation needed
- Standard Python tools only
- Easier for new contributors

### **3. Performance**
- Faster package installation
- Smaller disk footprint
- Quicker environment setup

### **4. Industry Standard**
- Most Python projects use venv
- Better CI/CD integration
- Widely documented

---

## 📚 Resources

### **Python venv Documentation:**
- https://docs.python.org/3/library/venv.html

### **pip Documentation:**
- https://pip.pypa.io/en/stable/

### **Virtual Environments Guide:**
- https://realpython.com/python-virtual-environments-a-primer/

---

## 🎓 Quick Reference

### **Common Commands:**

```bash
# Setup
./setup-venv.sh

# Start
./start.sh

# Manual activation
source venv/bin/activate

# Deactivate
deactivate

# Install package
source venv/bin/activate
pip install package-name

# Update requirements
pip freeze > requirements-all.lock

# Check environment
which python
pip list
```

---

## ✅ Summary

**What you need to do:**
1. Run `./setup-venv.sh` once
2. Use `./start.sh` for daily work
3. That's it!

**What changed:**
- ❌ No more conda
- ✅ Standard Python venv
- ✅ Simpler, faster, lighter
- ✅ Consistent with Docker

**Benefits:**
- Faster setup
- Smaller footprint
- Easier for contributors
- Same as Docker (no version mismatches)

---

**Questions?** Check `README.md` or other documentation files.

**Ready to migrate?**

```bash
./setup-venv.sh
```

🎉 **You're all set!**

