# Daily.co Integration Guide

## Overview

The AI Interviewer system uses Daily.co's API to create unique, private video rooms for each interview. This document explains how the integration works.

**Reference:** [Daily.co Room Access Control](https://www.daily.co/blog/intro-to-room-access-control/)

## Architecture

### Components

1. **DailyService** (`web_server/services/daily_service.py`)
   - Handles all Daily.co API interactions
   - Creates rooms, generates tokens, manages lifecycle

2. **Dashboard Route** (`web_server/routers/dashboard.py`)
   - Creates room when interview is scheduled
   - Generates tokens for bot and candidate
   - Stores room info in database

3. **Bot Worker** (`web_server/workers/ai_bot_worker.py`)
   - Receives room URL with bot token
   - Starts ai-interviewer.py with `--room-url` argument

## How It Works

### 1. Interview Scheduling Flow

```
User Schedules Interview
    ↓
DailyService.create_interview_room()
    ↓
Daily.co API creates private room
    ↓
DailyService.create_bot_token()
    ↓
DailyService.create_candidate_token()
    ↓
Tokens embedded in URLs
    ↓
Bot joins with owner token
Candidate joins with participant token
```

### 2. Room Configuration

```json
{
  "name": "interview-{interview_id}",
  "privacy": "private",
  "properties": {
    "enable_chat": true,
    "enable_screenshare": true,
    "enable_recording": "cloud",
    "exp": 1699999999,
    "eject_at_room_exp": true,
    "owner_only_broadcast": false,
    "enable_prejoin_ui": true
  }
}
```

### 3. Token Types

#### Bot Token (Owner)
```json
{
  "properties": {
    "room_name": "interview-...",
    "is_owner": true,
    "user_name": "AI Interviewer Bot",
    "exp": 1699999999,
    "enable_recording": "cloud"
  }
}
```

**Privileges:**
- Can start/stop recording
- Can remove participants
- Full room control

#### Candidate Token (Participant)
```json
{
  "properties": {
    "room_name": "interview-...",
    "is_owner": false,
    "user_name": "John Doe",
    "exp": 1699999999
  }
}
```

**Privileges:**
- Can join room
- Can speak and share video
- Cannot control room settings

## Configuration

### Environment Variables

Required in `web_server/.env`:

```bash
DAILY_API_KEY=your_daily_api_key_here
DAILY_API_URL=https://api.daily.co/v1  # Optional, defaults to this
DAILY_DOMAIN=hi2inspire.daily.co        # Optional, your Daily.co domain
```

### Getting DAILY_API_KEY

1. Sign up at [Daily.co](https://www.daily.co)
2. Go to **Developers** tab
3. Copy your API key
4. Add to `.env` file

## API Endpoints Used

### Create Room

```bash
POST https://api.daily.co/v1/rooms
Authorization: Bearer {DAILY_API_KEY}
Content-Type: application/json

{
  "name": "interview-...",
  "privacy": "private",
  "properties": {...}
}
```

### Create Meeting Token

```bash
POST https://api.daily.co/v1/meeting-tokens
Authorization: Bearer {DAILY_API_KEY}
Content-Type: application/json

{
  "properties": {
    "room_name": "interview-...",
    "is_owner": true,
    "user_name": "..."
  }
}
```

### Delete Room

```bash
DELETE https://api.daily.co/v1/rooms/{room_name}
Authorization: Bearer {DAILY_API_KEY}
```

## Usage Examples

### Creating an Interview Room

```python
from services.daily_service import daily_service

# Create room
room_data = await daily_service.create_interview_room(
    interview_id="interview_20251006_172000_abc123",
    candidate_name="John Doe",
    expires_in_minutes=90
)

# Returns:
# {
#   "room_url": "https://hi2inspire.daily.co/interview-...",
#   "room_name": "interview-...",
#   "room_id": "...",
#   "created_at": "2025-10-06T17:20:00Z",
#   "expires": 1699999999
# }
```

### Generating Tokens

```python
# Bot token (owner)
bot_token = await daily_service.create_bot_token(
    room_name="interview-...",
    expires_in_minutes=90
)

# Candidate token (participant)
candidate_token = await daily_service.create_candidate_token(
    room_name="interview-...",
    candidate_name="John Doe",
    expires_in_minutes=90
)

# Build URLs
bot_url = f"{room_url}?t={bot_token}"
candidate_url = f"{room_url}?t={candidate_token}"
```

### Deleting a Room

```python
success = await daily_service.delete_room("interview-...")
```

## Database Schema

### Interview Document

```json
{
  "interview_id": "interview_20251006_172000_abc123",
  "candidate_name": "John Doe",
  "candidate_email": "john@example.com",
  "room_url": "https://hi2inspire.daily.co/interview-...",
  "room_name": "interview-...",
  "candidate_join_url": "https://...?t=CANDIDATE_TOKEN",
  "status": "scheduled",
  "created_at": "2025-10-06T17:20:00Z"
}
```

## Security Considerations

### Token Security

- ✅ Tokens expire after 90 minutes
- ✅ Tokens are room-specific
- ✅ Tokens are embedded in URLs (one-time use URLs)
- ⚠️ URLs contain sensitive tokens - don't log in production

### Room Privacy

- ✅ Rooms are private (require tokens)
- ✅ Bot has owner privileges
- ✅ Candidates have limited access
- ✅ Rooms auto-expire and eject participants

### Best Practices

1. **Never log full URLs** with tokens in production
2. **Use short expiration times** (90 minutes default)
3. **Delete rooms** after interviews complete
4. **Validate tokens** server-side before generating
5. **Rate limit** room creation to prevent abuse

## Troubleshooting

### Common Issues

#### 1. Room Creation Fails

**Error:** `Failed to create Daily.co room`

**Solutions:**
- Check DAILY_API_KEY is set correctly
- Verify API key permissions
- Check Daily.co account status
- Verify domain (hi2inspire.daily.co) exists

#### 2. Token Generation Fails

**Error:** `Failed to create bot/candidate token`

**Solutions:**
- Ensure room was created first
- Check room_name matches exactly
- Verify API key has token creation permissions

#### 3. Bot Doesn't Join Room

**Possible Causes:**
- Token expired
- Room doesn't exist
- Bot URL malformed
- Network issues

**Debug:**
```bash
# Check bot logs for actual URL being used
# Should see: 📝 Command: python ai-interviewer.py --room-url https://...?t=...
```

#### 4. Candidate Can't Join

**Possible Causes:**
- Token expired
- Wrong URL
- Room expired
- Browser security settings

**Debug:**
- Check URL has `?t=` parameter with token
- Verify room hasn't expired
- Try in incognito mode

### Logs to Check

**Web Server:**
```
✅ Created Daily.co room: https://...
✅ Created bot token for room: interview-...
✅ Created candidate token for: John Doe
```

**RQ Worker:**
```
📍 Using room URL from config: https://...?t=...
📝 Command: python ai-interviewer.py --room-url https://...
✅ Bot started successfully! PID: ...
```

## Testing

### Manual Test

1. Schedule interview with auto-start enabled
2. Check web server logs for room creation
3. Check worker logs for bot joining
4. Open candidate URL in browser
5. Verify bot is visible and speaking

### API Test

```bash
# Test room creation
curl -X POST https://api.daily.co/v1/rooms \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"test-room","privacy":"private"}'

# Test token creation
curl -X POST https://api.daily.co/v1/meeting-tokens \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"properties":{"room_name":"test-room","is_owner":true}}'
```

## Future Improvements

### Potential Enhancements

1. **Room Cleanup**
   - Background job to delete expired rooms
   - Scheduled cleanup of old interviews

2. **Recording Management**
   - Auto-start recording when bot joins
   - Download recordings after interview
   - Store recordings in cloud storage

3. **Advanced Access Control**
   - Time-based access windows
   - Multi-participant interviews
   - Observer/admin tokens

4. **Monitoring**
   - Track room usage
   - Monitor token generation
   - Alert on API failures

5. **Webhooks**
   - Listen for room events
   - Track participant join/leave
   - Update interview status automatically

## References

- [Daily.co Room Access Control](https://www.daily.co/blog/intro-to-room-access-control/)
- [Daily.co API Docs](https://docs.daily.co/reference/rest-api)
- [Daily.co Meeting Tokens](https://docs.daily.co/reference/rest-api/meeting-tokens)
- [Daily.co Rooms API](https://docs.daily.co/reference/rest-api/rooms)

