#!/bin/bash
# Generate EC2 setup commands with your actual .env values

echo "================================================"
echo "EC2 SETUP COMMANDS - Copy and paste on EC2"
echo "================================================"
echo ""
echo "# 1. Create server/.env"
echo "cat > ~/ai-interviewer/server/.env << 'ENVEOF'"
cat server/.env
echo "ENVEOF"
echo ""
echo "# 2. Create web_server/.env"
echo "cat > ~/ai-interviewer/web_server/.env << 'ENVEOF'"
cat web_server/.env
echo "ENVEOF"
echo ""
echo "# 3. Verify files created"
echo "ls -lh ~/ai-interviewer/server/.env ~/ai-interviewer/web_server/.env"
echo ""
echo "================================================"
echo "Copy the above commands and run on EC2!"
echo "================================================"

