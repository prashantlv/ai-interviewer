#!/bin/bash
# 
# Cleanup Script for Duplicate AI Bots
# Run this on EC2 to kill all running bot processes and clear Redis locks
#

echo "🧹 Cleaning up duplicate AI bot processes..."

# 1. Kill all running ai-interviewer.py processes
echo ""
echo "1️⃣ Killing all ai-interviewer.py processes..."
pkill -f "ai-interviewer.py" || echo "No ai-interviewer.py processes found"
sleep 2

# 2. Double-check and force kill if needed
if pgrep -f "ai-interviewer.py" > /dev/null; then
    echo "⚠️ Some processes still running, force killing..."
    pkill -9 -f "ai-interviewer.py"
    sleep 1
fi

# 3. Clear all Redis bot locks
echo ""
echo "2️⃣ Clearing all Redis bot locks..."
redis-cli --scan --pattern "bot_lock:*" | xargs -r redis-cli DEL

# 4. Clear RQ job queue (optional - comment out if you want to keep jobs)
echo ""
echo "3️⃣ Clearing RQ job queue..."
# redis-cli FLUSHDB  # ⚠️ DANGER: This clears ALL Redis data
# Safer: Just clear the ai_bots queue
redis-cli DEL rq:queue:ai_bots
redis-cli DEL rq:queue:ai_bots:started
redis-cli DEL rq:queue:ai_bots:finished
redis-cli DEL rq:queue:ai_bots:failed

# 5. Show current status
echo ""
echo "4️⃣ Current status:"
echo "   Active bot processes: $(pgrep -f 'ai-interviewer.py' | wc -l)"
echo "   Redis bot locks: $(redis-cli --scan --pattern 'bot_lock:*' | wc -l)"
echo "   RQ jobs in queue: $(redis-cli LLEN rq:queue:ai_bots)"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📝 Next steps on EC2:"
echo "   1. git pull origin main"
echo "   2. docker compose down"
echo "   3. docker compose build"
echo "   4. docker compose up -d"

