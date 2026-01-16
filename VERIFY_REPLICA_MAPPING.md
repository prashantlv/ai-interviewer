# 🔍 How to Verify Replica-Voice Mapping System

## ✅ Verification Steps

### 1. Check Database Migration
```bash
# On EC2, verify migration ran successfully
docker-compose exec web-server python3 migrate_replica_config.py
```

**Expected Output:**
```
✅ Migration completed successfully!
   Default replica: r0518ad3a314
   Mapped voice: c252b73c-8627-4b1d-b9e1-9e03e8550d47
```

### 2. Verify Database Has Mapping
```bash
# Connect to MongoDB and check
docker-compose exec web-server python3 -c "
from services.database import DatabaseService
import asyncio

async def check():
    db = DatabaseService()
    await db.connect()
    config = await db.get_default_replica_config()
    print('Default config:', config)
    await db.disconnect()

asyncio.run(check())
"
```

**Expected Output:**
```
Default config: {
    'replica_id': 'r0518ad3a314',
    'voice_id': 'c252b73c-8627-4b1d-b9e1-9e03e8550d47',
    'is_default': True,
    ...
}
```

### 3. Check API Endpoint
```bash
# Test the bot API endpoint
curl http://localhost:8009/api/v1/bot/replica-config
```

**Expected Output:**
```json
{
  "replica_id": "r0518ad3a314",
  "voice_id": "c252b73c-8627-4b1d-b9e1-9e03e8550d47",
  "is_default": true,
  "source": "database"
}
```

### 4. Check Bot Logs
```bash
# Watch bot logs when starting an interview
docker-compose logs -f rq-worker | grep -i "replica\|voice"
```

**Expected Output:**
```
📋 Using replica config from database: replica=r0518ad3a314, voice=c252b73c-8627-4b1d-b9e1-9e03e8550d47
✅ Initialized Cartesia TTS (WebSocket) with voice: c252b73c-8627-4b1d-b9e1-9e03e8550d47
Initialized Tavus with replica: r0518ad3a314
```

### 5. Verify UI Features

#### A. Replicas Dashboard
1. Go to: `https://api.human2intelligence.com/dashboard/replicas`
2. You should see:
   - Voice column showing mapped voice for each replica
   - "Configure Voice" button (mic icon) on each replica
   - Default replica marked with ⭐

#### B. Schedule Interview Form
1. Go to: `https://api.human2intelligence.com/dashboard/schedule`
2. You should see:
   - "Avatar Replica" dropdown field
   - Options: "Use Default Replica" + list of all replicas
   - Default replica pre-selected

### 6. Test Per-Interview Replica Selection

1. **Schedule interview with default replica:**
   - Leave "Avatar Replica" as "Use Default Replica"
   - Schedule interview
   - Check bot logs - should use default replica

2. **Schedule interview with specific replica:**
   - Select a different replica from dropdown
   - Schedule interview
   - Check bot logs - should use selected replica

### 7. Verify Bot Uses Database Config

**Check bot startup logs:**
```bash
docker-compose logs rq-worker | grep -A 5 "Starting AI Interviewer"
```

**Look for:**
- `📋 Using replica config from database: replica=..., voice=...`
- NOT `📋 Using replica config from environment: ...`

## 🐛 Troubleshooting

### Issue: Bot still using env vars
**Solution:** Check if bot code has `fetch_replica_config()` function. If not, pull latest code:
```bash
git pull origin main
docker-compose restart rq-worker
```

### Issue: No replicas in schedule form dropdown
**Solution:** Check API endpoint:
```bash
curl http://localhost:8009/api/v1/tavus/replicas?limit=100
```

### Issue: Migration says "already exists"
**Solution:** That's fine! It means migration already ran. Check database to verify.

### Issue: Can't configure voice in replicas dashboard
**Solution:** Check browser console for errors. Verify API endpoint:
```bash
curl http://localhost:8009/api/v1/tavus/replica-mappings
```

## 📊 Expected Behavior

### ✅ Working Correctly:
- Bot logs show: `📋 Using replica config from database`
- Replicas dashboard shows voice mappings
- Schedule form has replica dropdown
- Bot uses correct voice for each replica

### ❌ Not Working:
- Bot logs show: `📋 Using replica config from environment`
- Replicas dashboard shows "Voice not configured"
- Schedule form missing replica dropdown
- Bot uses wrong voice or env var voice

## 🎯 Quick Verification Command

Run this on EC2 to verify everything:
```bash
echo "=== Checking Replica Config ===" && \
docker-compose exec web-server python3 -c "
from services.database import DatabaseService
import asyncio

async def verify():
    db = DatabaseService()
    await db.connect()
    config = await db.get_default_replica_config()
    if config:
        print('✅ Default replica:', config.get('replica_id'))
        print('✅ Mapped voice:', config.get('voice_id'))
    else:
        print('❌ No default config found')
    await db.disconnect()

asyncio.run(verify())
" && \
echo "" && \
echo "=== Checking API ===" && \
curl -s http://localhost:8009/api/v1/bot/replica-config | python3 -m json.tool
```
