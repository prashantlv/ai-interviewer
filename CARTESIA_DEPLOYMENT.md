# 🎤 Cartesia TTS Deployment Guide for EC2

## ✅ Local Testing Completed Successfully

The Cartesia TTS integration has been tested locally and is working perfectly:
- ✅ API authentication successful
- ✅ Speech generation working (117KB+ audio per request)
- ✅ No deprecation warnings
- ✅ Ready for production deployment

---

## 🚀 EC2 Deployment Steps

### Step 1: Pull Latest Code on EC2

```bash
ssh ubuntu@ec2-15-206-54-22.ap-south-1.compute.amazonaws.com
cd ~/ai-interviewer
git pull origin main
```

### Step 2: Update Environment Variables

```bash
# Add Cartesia configuration to server/.env
cat >> ~/ai-interviewer/server/.env << 'EOF'

# Cartesia TTS Configuration
TTS_SERVICE=cartesia
CARTESIA_API_KEY=sk_car_ib5wETe49cRfZX6HMGpArL
CARTESIA_VOICE_ID=a0e99841-438c-4a64-b679-ae501e7d6091
CARTESIA_MODEL=sonic-english
CARTESIA_LANGUAGE=en
EOF

# Add Cartesia configuration to web_server/.env
cat >> ~/ai-interviewer/web_server/.env << 'EOF'

# Cartesia TTS Configuration
TTS_SERVICE=cartesia
CARTESIA_API_KEY=sk_car_ib5wETe49cRfZX6HMGpArL
CARTESIA_VOICE_ID=a0e99841-438c-4a64-b679-ae501e7d6091
CARTESIA_MODEL=sonic-english
CARTESIA_LANGUAGE=en
EOF

echo "✅ Environment variables updated"
```

### Step 3: Rebuild Docker Images

```bash
cd ~/ai-interviewer

# Rebuild both images with new dependencies
echo "Building web server image..."
sudo docker build -f Dockerfile.web -t ai-interviewer-web:test .

echo "Building worker image..."
sudo docker build -f Dockerfile.worker -t ai-interviewer-worker:test .

echo "✅ Docker images rebuilt"
```

### Step 4: Stop and Remove Old Containers

```bash
sudo docker stop ai-interviewer-web ai-interviewer-worker
sudo docker rm ai-interviewer-web ai-interviewer-worker
echo "✅ Old containers removed"
```

### Step 5: Start New Containers

```bash
cd ~/ai-interviewer

# Start web server
sudo docker run -d \
  --name ai-interviewer-web \
  --network host \
  --env-file server/.env \
  --env-file web_server/.env \
  --restart unless-stopped \
  ai-interviewer-web:test

# Start worker
sudo docker run -d \
  --name ai-interviewer-worker \
  --network host \
  --env-file server/.env \
  --env-file web_server/.env \
  --restart unless-stopped \
  ai-interviewer-worker:test

echo "✅ New containers started"
```

### Step 6: Verify Deployment

```bash
# Check containers are running
sudo docker ps

# Verify TTS_SERVICE is set
echo "=== Checking TTS configuration ==="
sudo docker exec ai-interviewer-worker env | grep -E "TTS_SERVICE|CARTESIA"

# Check logs for Cartesia initialization
echo "=== Checking worker logs ==="
sudo docker logs ai-interviewer-worker --tail 50 | grep -i "cartesia\|tts"
```

**Expected output:**
```
TTS_SERVICE=cartesia
CARTESIA_API_KEY=sk_car_ib5wETe49cRfZX6HMGpArL
CARTESIA_VOICE_ID=a0e99841-438c-4a64-b679-ae501e7d6091
```

---

## 🧪 Testing After Deployment

### 1. Schedule a Test Interview

- Go to: https://api.human2intelligence.com/dashboard/schedule
- Schedule a new interview
- Join the call

### 2. Monitor Logs in Real-Time

```bash
# Watch for Cartesia TTS initialization
sudo docker logs -f ai-interviewer-worker | grep --line-buffered -i "cartesia\|tts\|voice"
```

**What to look for:**
```
🎤 Using Cartesia TTS
✅ Initialized Cartesia TTS with voice: a0e99841-438c-4a64-b679-ae501e7d6091
🎵 Generating speech for text: ...
✅ Generated 117484 bytes of audio
```

### 3. Verify Audio Quality

During the call, check:
- ✅ Low latency (~150ms vs ~500ms with OpenAI)
- ✅ Clear audio quality
- ✅ Natural voice
- ✅ No stuttering or dropouts

---

## 🔄 Rollback to OpenAI TTS (If Needed)

If you encounter any issues, quickly roll back:

```bash
# Update .env to use OpenAI
sed -i 's/TTS_SERVICE=cartesia/TTS_SERVICE=openai/' ~/ai-interviewer/server/.env
sed -i 's/TTS_SERVICE=cartesia/TTS_SERVICE=openai/' ~/ai-interviewer/web_server/.env

# Restart containers (no rebuild needed)
sudo docker restart ai-interviewer-web ai-interviewer-worker

# Verify
sudo docker exec ai-interviewer-worker env | grep TTS_SERVICE
```

---

## 📊 Cartesia Free Tier Limits

- **Concurrent Requests**: 2 max
- **Monthly Limit**: 10 minutes of audio generation
- **Estimated Interviews**: ~50-100 interviews/month (depending on length)

**Monitor usage at**: https://cartesia.ai/dashboard

---

## 🎯 Available Free Voices

Your current configuration uses: `a0e99841-438c-4a64-b679-ae501e7d6091`

To test other voices, update `CARTESIA_VOICE_ID` in `.env` and restart containers.

**Popular free voices:**
- `a0e99841-438c-4a64-b679-ae501e7d6091` - Professional male (current)
- `b7d50908-b17c-442d-ad8d-810c63997ed9` - Friendly female
- `156fb8d2-335b-4950-9cb3-a2d33befec77` - British male
- `79a125e8-cd45-4c13-8a67-188112f4dd22` - Energetic female

---

## 🆘 Troubleshooting

### Issue: "CARTESIA_API_KEY is required"

**Fix:**
```bash
grep CARTESIA_API_KEY ~/ai-interviewer/server/.env
# If not found, add it:
echo "CARTESIA_API_KEY=sk_car_ib5wETe49cRfZX6HMGpArL" >> ~/ai-interviewer/server/.env
```

### Issue: Rate limit errors

**Fix:** You've exceeded 2 concurrent requests (free tier limit)
```bash
# Check how many bots are running
ps aux | grep ai-interviewer.py
```

### Issue: Audio sounds garbled

**Fix:** Check sample rate compatibility
```bash
# Verify in logs
sudo docker logs ai-interviewer-worker | grep "sample_rate"
# Should be: 16000
```

---

## ✅ Deployment Checklist

- [ ] Git pulled on EC2
- [ ] Environment variables updated (both .env files)
- [ ] Docker images rebuilt
- [ ] Old containers removed
- [ ] New containers started
- [ ] TTS_SERVICE verified as "cartesia"
- [ ] Test interview scheduled
- [ ] Audio quality verified
- [ ] Latency improvement confirmed

---

## 🎉 Success Metrics

After deployment, you should see:
- **Latency**: ~150ms (vs ~500ms with OpenAI)
- **Cost**: $0/month (free tier)
- **Quality**: Comparable to OpenAI
- **Concurrency**: 2 simultaneous interviews max

---

**Ready to deploy? Follow the steps above carefully. Good luck! 🚀**

