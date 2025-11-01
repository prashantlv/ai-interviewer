#!/bin/bash
# View Live Logs for AI Interviewer

echo "📝 AI Interviewer - Live Logs Viewer"
echo "====================================="
echo ""
echo "Choose what to view:"
echo "1) Web Server logs only"
echo "2) RQ Worker logs only (includes bot logs)"
echo "3) Both (combined)"
echo "4) All logs with colors"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo "📋 Viewing Web Server logs (Ctrl+C to stop)..."
        tail -f /tmp/web_server.log
        ;;
    2)
        echo "🤖 Viewing RQ Worker logs (Ctrl+C to stop)..."
        tail -f /tmp/rq_worker.log
        ;;
    3)
        echo "📋 Viewing combined logs (Ctrl+C to stop)..."
        tail -f /tmp/web_server.log /tmp/rq_worker.log
        ;;
    4)
        echo "🎨 Viewing all logs with colors (Ctrl+C to stop)..."
        tail -f /tmp/web_server.log /tmp/rq_worker.log | \
            sed 's/ERROR/\x1b[31mERROR\x1b[0m/g' | \
            sed 's/WARNING/\x1b[33mWARNING\x1b[0m/g' | \
            sed 's/INFO/\x1b[32mINFO\x1b[0m/g'
        ;;
    *)
        echo "Invalid choice. Viewing combined logs..."
        tail -f /tmp/web_server.log /tmp/rq_worker.log
        ;;
esac

