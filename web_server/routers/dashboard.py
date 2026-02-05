"""
Dashboard Router - Recruiter dashboard endpoints
"""

import os
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime, timedelta, timezone
import pytz

from dependencies import DbServiceDep, BotManagerDep, CurrentUserDep, UserApiKeysDep
from services.daily_service import daily_service

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Register IST datetime filters (same as in main.py)
def format_ist_datetime(dt, format_str='%Y-%m-%d %I:%M %p IST'):
    """Format datetime in IST timezone"""
    if not dt:
        return 'N/A'
    
    # If already formatted with IST, return as-is
    if isinstance(dt, str) and 'IST' in dt and ('PM' in dt or 'AM' in dt or ':' in dt):
        return dt
    
    try:
        IST = pytz.timezone('Asia/Kolkata')
        if isinstance(dt, str):
            # Check if it's already a formatted date (not ISO)
            if 'IST' in dt and ('PM' in dt or 'AM' in dt):
                return dt
            # Parse ISO format string
            dt_str = dt.replace('Z', '+00:00')
            dt = datetime.fromisoformat(dt_str)
        # Ensure dt is a datetime object
        if not isinstance(dt, datetime):
            return str(dt)
        if dt.tzinfo is None:
            # Assume UTC if timezone-naive
            dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(IST)
        return ist_dt.strftime(format_str)
    except Exception as e:
        # Return original value if formatting fails
        return str(dt) if dt else 'N/A'

def format_ist_time_only(dt):
    """Format datetime to show only time in IST"""
    if not dt:
        return 'N/A'
    try:
        IST = pytz.timezone('Asia/Kolkata')
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        if not isinstance(dt, datetime):
            return str(dt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(IST)
        return ist_dt.strftime('%I:%M %p IST')
    except Exception as e:
        # Fallback: try to extract time from string
        if isinstance(dt, str) and len(dt) >= 19:
            return dt[11:19] + ' IST'
        return str(dt)

templates.env.filters['ist_datetime'] = format_ist_datetime
templates.env.filters['ist_time'] = format_ist_time_only

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    db: DbServiceDep,
    current_user: CurrentUserDep
):
    """Main dashboard page - Requires authentication"""
    # Get real data from database directly
    try:
        from datetime import datetime, timedelta
        
        # Use dependency-injected db service
        if db and db.database is not None:
            # Get user_id for data isolation
            user_id = current_user.get("userId")
            if not user_id:
                logger.warning("⚠️ No userId found - cannot filter interviews per user")
            
            # Get interviews filtered by user_id for dashboard stats (use large limit)
            # Note: get_interviews now returns full documents including proctoring
            interviews = await db.get_interviews(limit=1000, offset=0, user_id=user_id)
        else:
            print("⚠️ Database service not available")
            interviews = []
    
        # Sort interviews by date (most recent first) - FIX #1
        # Handle both datetime objects and strings
        def get_sort_date(interview):
            date_val = interview.get("scheduled_date") or interview.get("created_at") or ""
            if not date_val or date_val == "N/A":
                return ""
            try:
                if isinstance(date_val, str):
                    return date_val
                else:
                    return date_val.isoformat()
            except:
                return ""
        
        interviews.sort(key=get_sort_date, reverse=True)
        
        print(f"🔍 DASHBOARD DEBUG: Total interviews: {len(interviews)}")
        if interviews:
            print(f"🔍 DASHBOARD DEBUG: First 3 interviews:")
            for i, interview in enumerate(interviews[:3]):
                print(f"   {i+1}. {interview.get('candidate_name')} - {interview.get('scheduled_date')} - Score: {interview.get('score')}")
        
        # Calculate dashboard statistics
        total_interviews = len(interviews)
        
        # Get today's date for filtering
        today = datetime.now().date()
        
        # Count today's interviews - FIX #1
        interviews_today = 0
        completed_today = 0
        for interview in interviews:
            date_str = interview.get("scheduled_date", "")
            if date_str and date_str != "N/A":
                try:
                    interview_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                    if interview_date == today:
                        interviews_today += 1
                        if interview.get("status") in ["completed", "ended_by_candidate"]:
                            completed_today += 1
                except:
                    pass
        
        pending_interviews = len([i for i in interviews if i.get("status") in ["scheduled", "in_progress"]])
        completed_total = len([i for i in interviews if i.get("status") in ["completed", "ended_by_candidate"]])
        
        # Calculate average score (only for completed interviews with scores > 0)
        scored_interviews = [i for i in interviews if i.get("status") in ["completed", "ended_by_candidate"] and i.get("score", 0) > 0]
        average_score = round(sum(i.get("score", 0) for i in scored_interviews) / len(scored_interviews), 1) if scored_interviews else 0
        
        # Calculate completion rate
        completion_rate = round((completed_total / total_interviews * 100), 1) if total_interviews > 0 else 0
        
        # Get recent interviews (limit to 5 for dashboard) - already sorted
        IST = pytz.timezone('Asia/Kolkata')
        
        recent_interviews = []
        for interview in interviews[:8]:
            print(f"🔍 DEBUG Dashboard: interview_type = {interview.get('interview_type', 'NOT_SET')}")
            
            # Extract scheduled_date from evaluation if available
            evaluation = interview.get("evaluation", {})
            scheduled_date_str = evaluation.get("scheduled_date") or interview.get("scheduled_date")
            
            # Format scheduled time in IST for display
            scheduled_time_display = "N/A"
            if scheduled_date_str and scheduled_date_str != "N/A":
                try:
                    # Parse ISO format datetime
                    if isinstance(scheduled_date_str, str):
                        scheduled_dt = datetime.fromisoformat(scheduled_date_str.replace('Z', '+00:00'))
                    else:
                        scheduled_dt = scheduled_date_str
                    
                    # Convert to IST and format
                    if scheduled_dt.tzinfo:
                        scheduled_ist = scheduled_dt.astimezone(IST)
                    else:
                        scheduled_ist = scheduled_dt.replace(tzinfo=timezone.utc).astimezone(IST)
                    
                    scheduled_time_display = scheduled_ist.strftime('%b %d, %Y %I:%M %p IST')
                except Exception as e:
                    print(f"⚠️ Error formatting scheduled time: {e}")
                    scheduled_time_display = str(scheduled_date_str)[:19] if scheduled_date_str else "N/A"
            
            recent_interviews.append({
                "id": interview.get("id", "unknown"),
                "candidate_name": interview.get("candidate_name", "Unknown"),
                "position": interview.get("position", "Unknown Position"),
                "interview_type": interview.get("interview_type", "technical"),
                "status": interview.get("status", "unknown"),
                "score": interview.get("score", 0),
                "date": interview.get("scheduled_date", "N/A"),
                "scheduled_time": scheduled_time_display
            })
        
        dashboard_data = {
            "total_interviews": total_interviews,
            "interviews_today": interviews_today,
            "pending_interviews": pending_interviews,
            "completed_today": completed_today,
            "completed_total": completed_total,
            "average_score": average_score,
            "completion_rate": completion_rate,
            "recent_interviews": recent_interviews
        }
        
    except Exception as e:
        print(f"❌ Error getting dashboard data: {e}")
        # Fallback to empty data
        dashboard_data = {
            "total_interviews": 0,
            "interviews_today": 0,
            "pending_interviews": 0,
            "completed_today": 0,
            "completed_total": 0,
            "average_score": 0,
            "completion_rate": 0,
            "recent_interviews": []
        }
    
    # Get system status - FIX #3
    # For now, we check database status. Bot status would need heartbeat/health check
    db_status = "connected" if (db and db.database is not None) else "disconnected"
    
    system_status = {
        "database": db_status,
        "bot": "manual_check",  # Note: Bot status requires manual check - no heartbeat system yet
        "question_engine": "operational",
        "scoring_engine": "operational"
    }
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "data": dashboard_data,
        "system_status": system_status
    })

@router.get("/test-db")
async def test_database_connection(db: DbServiceDep):
    """Test endpoint to check database connection"""
    return {
        "db_service_is_none": db is None,
        "db_service_type": str(type(db)),
        "has_database": hasattr(db, 'database') if db else False,
        "database_is_none": db.database is None if (db and hasattr(db, 'database')) else True
    }

@router.get("/interviews", response_class=HTMLResponse)
async def interviews_page(
    request: Request,
    db: DbServiceDep,
    current_user: CurrentUserDep,
    status: Optional[str] = None,
    position: Optional[str] = None,
    date: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1
):
    """Interviews management page with filtering and pagination - Requires authentication"""
    # Pagination settings
    per_page = 20
    offset = (page - 1) * per_page
    
    # Get interviews from database directly
    all_interviews = []  # Initialize early to avoid NameError
    original_interviews = []  # Store original for positions dropdown
    try:
        if db and db.database is not None:
            # Get user_id for data isolation
            user_id = current_user.get("userId")
            if not user_id:
                logger.warning("⚠️ No userId found - cannot filter interviews per user")
            
            # Get interviews filtered by user_id (use large limit to get everything)
            # The database query is already sorted, so we get them in order
            all_interviews = await db.get_interviews(limit=1000, offset=0, user_id=user_id)
            print(f"🔍 DEBUG: Retrieved {len(all_interviews)} interviews from database for user_id: {user_id}")
        else:
            print("⚠️ Database service not available for interviews page")
            all_interviews = []
        
        # Store original list for positions dropdown (before filtering)
        original_interviews = all_interviews.copy()
    
        # Apply filters
        filtered_interviews = []
        for interview in all_interviews:
            # Status filter
            if status and status != "all":
                interview_status = interview.get("status", "").lower()
                # Map UI status values to database status values
                status_map = {
                    "scheduled": ["scheduled"],
                    "in_progress": ["in_progress"],
                    "completed": ["completed", "ended_by_candidate"],
                    "cancelled": ["cancelled"]
                }
                if status.lower() in status_map:
                    if interview_status not in status_map[status.lower()]:
                        continue
                elif interview_status != status.lower():
                    continue
            
            # Position filter
            if position and position != "all":
                interview_position = interview.get("position", "").lower()
                if interview_position != position.lower():
                    continue
            
            # Date filter
            if date:
                try:
                    filter_date = datetime.fromisoformat(date).date()
                    interview_date_str = interview.get("scheduled_date") or interview.get("created_at") or ""
                    if interview_date_str and interview_date_str != "N/A":
                        if isinstance(interview_date_str, str):
                            interview_date = datetime.fromisoformat(interview_date_str.replace('Z', '+00:00')).date()
                        else:
                            interview_date = interview_date_str.date()
                        if interview_date != filter_date:
                            continue
                    else:
                        continue  # Skip interviews without dates when date filter is active
                except Exception as e:
                    print(f"⚠️ Error filtering by date: {e}")
                    # If date parsing fails, include the interview
            
            # Search filter (candidate name or email)
            if search:
                search_lower = search.lower()
                candidate_name = interview.get("candidate_name", "").lower()
                candidate_email = interview.get("candidate_email", "").lower()
                if search_lower not in candidate_name and search_lower not in candidate_email:
                    continue
            
            filtered_interviews.append(interview)
        
        # Sort by date - most recent first
        filtered_interviews.sort(key=lambda x: (
            x.get("scheduled_date") or x.get("created_at") or ""
        ), reverse=True)
        
        # Apply pagination to FILTERED interviews
        start_idx = offset
        end_idx = offset + per_page
        interviews = filtered_interviews[start_idx:end_idx]
        
        # Use filtered count for pagination
        total_interviews = len(filtered_interviews)
        total_pages = (total_interviews + per_page - 1) // per_page if total_interviews > 0 else 0
        
        # Update all_interviews to filtered for statistics calculation
        all_interviews = filtered_interviews
        total_pages = (total_interviews + per_page - 1) // per_page if total_interviews > 0 else 0
        
        # Transform data for template
        interview_list = []
        for interview in interviews:
            # Get interview ID for URL construction
            interview_id = interview.get("interview_id", interview.get("id", "unknown"))
            
            # ALWAYS use the proctored interview room URL (not Daily.co room URL)
            # This is the correct URL that candidates should use
            # Format: /interview/{interview_id}/room
            join_url = f"/interview/{interview_id}/room"
            
            # Note: We don't use candidate_join_url or room_url here because:
            # - candidate_join_url might be a relative path that needs the domain
            # - room_url is the Daily.co URL, not the proctored interview URL
            # The API endpoint will handle constructing the full URL with domain
            
            # Extract scheduled_date from evaluation if available
            evaluation = interview.get("evaluation", {})
            scheduled_date_str = evaluation.get("scheduled_date") or interview.get("scheduled_date")
            
            # Format scheduled time in IST for display
            scheduled_time_display = "N/A"
            if scheduled_date_str and scheduled_date_str != "N/A":
                try:
                    IST = pytz.timezone('Asia/Kolkata')
                    # Parse ISO format datetime
                    if isinstance(scheduled_date_str, str):
                        scheduled_dt = datetime.fromisoformat(scheduled_date_str.replace('Z', '+00:00'))
                    else:
                        scheduled_dt = scheduled_date_str
                    
                    # Convert to IST and format
                    if scheduled_dt.tzinfo:
                        scheduled_ist = scheduled_dt.astimezone(IST)
                    else:
                        scheduled_ist = scheduled_dt.replace(tzinfo=timezone.utc).astimezone(IST)
                    
                    scheduled_time_display = scheduled_ist.strftime('%b %d, %Y %I:%M %p IST')
                except Exception as e:
                    print(f"⚠️ Error formatting scheduled time: {e}")
                    scheduled_time_display = str(scheduled_date_str)[:19] if scheduled_date_str else "N/A"
            
            # Calculate duration from proctoring data
            duration_display = "N/A"
            proctoring = interview.get("proctoring")
            
            # Debug logging
            if proctoring:
                print(f"🔍 DEBUG Duration: Interview {interview_id} has proctoring data: {bool(proctoring.get('start_time'))} start, {bool(proctoring.get('end_time'))} end")
            
            if proctoring and proctoring.get("start_time") and proctoring.get("end_time"):
                try:
                    start_time_str = proctoring["start_time"]
                    end_time_str = proctoring["end_time"]
                    
                    # Parse ISO format datetime strings
                    # Import datetime locally to avoid UnboundLocalError (Python thinks datetime is local if assigned anywhere)
                    from datetime import datetime as dt_parse
                    start_time = dt_parse.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    end_time = dt_parse.fromisoformat(end_time_str.replace('Z', '+00:00'))
                    
                    duration_delta = end_time - start_time
                    total_seconds = int(duration_delta.total_seconds())
                    
                    if total_seconds < 0:
                        print(f"⚠️ Negative duration for {interview_id}: {total_seconds}s")
                        duration_display = "N/A"
                    else:
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        
                        if hours > 0:
                            duration_display = f"{hours}h {minutes}m {seconds}s"
                        elif minutes > 0:
                            duration_display = f"{minutes}m {seconds}s"
                        else:
                            duration_display = f"{seconds}s"
                        
                        print(f"✅ Duration calculated for {interview_id}: {duration_display}")
                except Exception as e:
                    print(f"⚠️ Error calculating duration for {interview_id}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                if not proctoring:
                    print(f"⚠️ No proctoring data for interview {interview_id}")
                elif not proctoring.get("start_time"):
                    print(f"⚠️ No start_time in proctoring for interview {interview_id}")
                elif not proctoring.get("end_time"):
                    print(f"⚠️ No end_time in proctoring for interview {interview_id}")
            
            interview_list.append({
                "id": interview.get("id", "unknown"),
                "interview_id": interview_id,
                "candidate_name": interview.get("candidate_name", "Unknown"),
                "candidate_email": interview.get("candidate_email", "N/A"),
                "position": interview.get("position", "Unknown Position"),
                "interview_type": interview.get("interview_type", "technical"),
                "status": interview.get("status", "unknown"),
                "score": interview.get("score", 0),
                "scheduled_date": scheduled_date_str if scheduled_date_str and scheduled_date_str != "N/A" else interview.get("created_at", "N/A"),
                "scheduled_time": scheduled_time_display,
                "duration": duration_display,
                "transcript_available": interview.get("transcript_available", False),
                "join_url": join_url
            })
            
    except Exception as e:
        print(f"❌ Error getting interviews: {e}")
        # Fallback to empty list
        all_interviews = []
        original_interviews = []
        interview_list = []
        total_interviews = 0
        total_pages = 0
    
    print(f"🔍 DEBUG: Sending {len(interview_list)} interviews to template")
    for i, interview in enumerate(interview_list):
        print(f"🔍 DEBUG: Interview {i}: {interview}")
    
    # Calculate real statistics for the page footer - FIX #4
    from datetime import datetime
    completed_count = len([i for i in all_interviews if i.get("status") in ["completed", "ended_by_candidate"]])
    completion_rate = (completed_count / total_interviews * 100) if total_interviews > 0 else 0
    
    # Calculate average score (only for completed interviews with scores > 0)
    scored_interviews = [i for i in all_interviews if i.get("status") in ["completed", "ended_by_candidate"] and i.get("score", 0) > 0]
    average_score = sum(i.get("score", 0) for i in scored_interviews) / len(scored_interviews) if scored_interviews else 0
    
    # Calculate hire rate (recommendation = "yes" or "strong_yes")
    # For now, use score >= 65 as proxy for "recommended"
    recommended_count = len([i for i in all_interviews if i.get("status") in ["completed", "ended_by_candidate"] and i.get("score", 0) >= 65])
    hire_rate = (recommended_count / completed_count * 100) if completed_count > 0 else 0
    
    # Count this month's interviews
    from datetime import datetime
    today = datetime.now()
    this_month_count = 0
    for interview in all_interviews:
        # Try multiple date fields
        date_str = interview.get("scheduled_date") or interview.get("created_at") or ""
        if date_str and date_str != "N/A":
            try:
                # Handle both string and datetime objects
                if isinstance(date_str, str):
                    interview_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                elif isinstance(date_str, datetime):
                    interview_date = date_str
                else:
                    continue
                
                if interview_date.year == today.year and interview_date.month == today.month:
                    this_month_count += 1
            except Exception as e:
                print(f"⚠️ Date parsing error for {interview.get('id')}: {date_str} - {e}")
                pass
    
    # Get unique positions for filter dropdown (from original unfiltered interviews)
    all_positions = sorted(set(
        i.get("position", "Unknown Position") 
        for i in original_interviews
        if i.get("position")
    ))
    
    return templates.TemplateResponse("interviews.html", {
        "request": request,
        "interviews": interview_list,
        "current_status": status or "all",
        "current_position": position or "all",
        "current_date": date or "",
        "current_search": search or "",
        "current_page": page,
        "total_pages": total_pages,
        "total_interviews": total_interviews,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1 if page > 1 else 1,
        "next_page": page + 1 if page < total_pages else total_pages,
        "positions": all_positions,
        # Real statistics - FIX #4
        "this_month_count": this_month_count,
        "completed_count": completed_count,
        "completion_rate": round(completion_rate, 1),
        "average_score": round(average_score, 1),
        "hire_rate": round(hire_rate)
    })

@router.get("/interview/{interview_id}", response_class=HTMLResponse)
async def interview_detail(
    request: Request,
    interview_id: str,
    db: DbServiceDep,
    current_user: CurrentUserDep
):
    """Individual interview detail page - Requires authentication"""
    # Get interview data using db service
    interview_result = await db.database.interview_results.find_one({"interview_id": interview_id})
    if interview_result:
        interview_result.pop('_id', None)
        recording_info = interview_result.get("recording")
        
        # Attempt to refresh recording metadata if we don't have a valid link yet
        if recording_info:
            recording_id = recording_info.get("recording_id")
            recording_status = (recording_info.get("status") or "").lower()
            access_link = recording_info.get("access_link")
            
            needs_refresh = recording_id and (
                not access_link or recording_status not in ["completed", "ready", "available", "finished"]
            )
            
            if needs_refresh:
                latest_recording = await daily_service.fetch_recording_asset(recording_id)
                if latest_recording:
                    # Merge latest fields into stored recording data
                    recording_info.update({k: v for k, v in latest_recording.items() if v is not None})
                    interview_result["recording"] = recording_info
                    
                    # Persist the refreshed data
                    await db.update_interview_result(
                        interview_id=interview_id,
                        transcript=interview_result.get("transcript", ""),
                        evaluation=interview_result.get("evaluation", {}),
                        status=interview_result.get("status", "completed"),
                        recording=recording_info
                    )
    
    if interview_result:
        # Use real data from database
        evaluation = interview_result.get("evaluation", {})
        individual_scores = evaluation.get("individual_scores", {})
        
        
        # DEBUG: Check proctoring data
        proctoring_data = interview_result.get("proctoring")
        if proctoring_data:
            print(f"✅ PROCTORING DATA FOUND for {interview_id}")
            print(f"   Violations: {len(proctoring_data.get('violations', []))}")
            print(f"   Risk Level: {proctoring_data.get('risk_level', 'N/A')}")
            print(f"   Summary: {proctoring_data.get('summary', {})}")
        else:
            print(f"❌ NO PROCTORING DATA for interview {interview_id}")
        
        # Extract scheduled_date from evaluation
        scheduled_date_str = evaluation.get("scheduled_date")
        
        # Format scheduled time in IST for display
        IST = pytz.timezone('Asia/Kolkata')
        scheduled_time_display = "N/A"
        if scheduled_date_str:
            try:
                if isinstance(scheduled_date_str, str):
                    scheduled_dt = datetime.fromisoformat(scheduled_date_str.replace('Z', '+00:00'))
                else:
                    scheduled_dt = scheduled_date_str
                
                if scheduled_dt.tzinfo:
                    scheduled_ist = scheduled_dt.astimezone(IST)
                else:
                    scheduled_ist = scheduled_dt.replace(tzinfo=timezone.utc).astimezone(IST)
                
                scheduled_time_display = scheduled_ist.strftime('%B %d, %Y at %I:%M %p IST')
            except Exception as e:
                print(f"⚠️ Error formatting scheduled time: {e}")
                scheduled_time_display = str(scheduled_date_str)[:19] if scheduled_date_str else "N/A"
        
        # Calculate duration from proctoring data
        duration_display = "N/A"
        proctoring_data = interview_result.get("proctoring")
        if proctoring_data and proctoring_data.get("start_time") and proctoring_data.get("end_time"):
            try:
                start_time = datetime.fromisoformat(proctoring_data["start_time"].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(proctoring_data["end_time"].replace('Z', '+00:00'))
                duration_delta = end_time - start_time
                total_seconds = int(duration_delta.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                
                if hours > 0:
                    duration_display = f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
                elif minutes > 0:
                    duration_display = f"{minutes} minute{'s' if minutes != 1 else ''} {seconds} second{'s' if seconds != 1 else ''}"
                else:
                    duration_display = f"{seconds} second{'s' if seconds != 1 else ''}"
            except Exception as e:
                print(f"⚠️ Error calculating duration: {e}")
        
        interview_data = {
            "id": interview_id,
            "candidate_name": evaluation.get("candidate_name", "Unknown Candidate"),
            "candidate_email": evaluation.get("candidate_email", "N/A"),
            "position": evaluation.get("position", "Unknown Position"),
            "status": interview_result.get("status", "completed"),
            "score": evaluation.get("overall_score", 0),
            "scheduled_date": str(interview_result.get("completed_at", "N/A")),
            "scheduled_time": scheduled_time_display,
            "duration": duration_display,
            "transcript": interview_result.get("transcript", "No transcript available"),
            "recording": interview_result.get("recording"),
            "proctoring": proctoring_data,  # Proctoring data (violations, risk level, etc.)
            "evaluation": {
                "correctness": individual_scores.get("correctness", 0),
                "terminology": individual_scores.get("terminology", 0),
                "confidence": individual_scores.get("confidence", 0),
                "experience_relevance": individual_scores.get("experience_relevance", 0),
                "problem_solving": individual_scores.get("problem_solving", 0)
            },
            "questions_asked": evaluation.get("questions_asked", []),
            "feedback": evaluation.get("feedback", None),
            "company": evaluation.get("company", "N/A"),
            "recommendation": evaluation.get("recommendation", "N/A"),
            "notes": evaluation.get("notes", None),
        }
    else:
        # Fallback to demo data if interview not found
        interview_data = {
            "id": interview_id,
            "candidate_name": "Interview Not Found",
            "candidate_email": "N/A",
            "position": "N/A",
            "status": "not_found",
            "score": 0,
            "scheduled_date": "N/A",
            "duration": "N/A",
            "transcript": f"Interview {interview_id} not found in database",
            "recording": None,
            "proctoring": None,  # No proctoring data for not found interviews
            "evaluation": {
                "correctness": 0,
                "terminology": 0,
                "confidence": 0,
                "experience_relevance": 0,
                "problem_solving": 0
            },
            "questions_asked": [],
            "feedback": None
        }
    
    return templates.TemplateResponse("interview_result.html", {
        "request": request,
        "interview": interview_data,
        "current_date": datetime.now(timezone.utc).astimezone(pytz.timezone('Asia/Kolkata')).strftime("%B %d, %Y %I:%M %p IST")
    })

@router.get("/schedule", response_class=HTMLResponse)
async def schedule_interview_page(
    request: Request,
    current_user: CurrentUserDep
):
    """Schedule new interview page - Requires authentication"""
    return templates.TemplateResponse("schedule_interview.html", {
        "request": request
    })

@router.post("/schedule", response_class=HTMLResponse)
async def create_interview(
    request: Request,
    db: DbServiceDep,
    bot_manager: BotManagerDep,
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep,
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    position: str = Form(...),
    interview_type: str = Form("technical"),
    scoring_level: str = Form("intermediate"),
    notes: str = Form(""),
    auto_start: bool = Form(False),  # Sprint 1.2: Auto-start bot option
    job_description: str = Form(...),  # NEW: JD text for GPT parsing
    candidate_resume: str = Form(...),  # NEW: Resume text for GPT parsing
    replica_id: str = Form(""),  # NEW: Optional replica selection
    scheduled_date: str = Form(None),  # Scheduled date (YYYY-MM-DD) - user's local time
    scheduled_time: str = Form(None),  # Scheduled time (HH:MM) - user's local time
    scheduled_date_utc: str = Form(None),  # UTC-converted date (from frontend)
    scheduled_time_utc: str = Form(None)  # UTC-converted time (from frontend)
):
    """Create a new interview"""
    import uuid
    from datetime import datetime, timedelta
    from services.resume_parser import ResumeParser
    from services.jd_parser import JDParser
    
    # Validate db service is available
    if db is None:
        raise HTTPException(status_code=500, detail="Database service not available")
    
    # Parse and validate scheduled date/time
    scheduled_datetime = None
    is_future_schedule = False
    
    # CRITICAL: Users enter time in IST (Indian Standard Time, UTC+5:30)
    # Convert IST to UTC for storage and comparison
    IST = pytz.timezone('Asia/Kolkata')
    
    # Use UTC-converted values if provided (frontend converted from user's local timezone)
    # Otherwise interpret input as IST (for backward compatibility, check if it looks like UTC or IST)
    if scheduled_date_utc and scheduled_time_utc:
        # Frontend already converted to UTC
        date_to_use = scheduled_date_utc
        time_to_use = scheduled_time_utc
        is_utc = True
    else:
        # Assume user entered time in IST
        date_to_use = scheduled_date
        time_to_use = scheduled_time
        is_utc = False
    
    if date_to_use and time_to_use:
        try:
            # Parse scheduled datetime (naive)
            scheduled_datetime_naive = datetime.strptime(f"{date_to_use} {time_to_use}", "%Y-%m-%d %H:%M")
            
            if is_utc:
                # Already in UTC from frontend conversion
                scheduled_datetime = scheduled_datetime_naive.replace(tzinfo=timezone.utc)
                print(f"🕐 Using UTC-converted time: {scheduled_datetime} (from user's local {scheduled_date} {scheduled_time})")
            else:
                # Interpret as IST and convert to UTC
                scheduled_datetime_ist = IST.localize(scheduled_datetime_naive)
                scheduled_datetime = scheduled_datetime_ist.astimezone(timezone.utc)
                print(f"🇮🇳 Interpreting as IST: {scheduled_datetime_ist} → UTC: {scheduled_datetime}")
            
            # Use UTC for all comparisons
            now_utc = datetime.now(timezone.utc)
            
            # CRITICAL: Log server time for debugging clock sync issues
            print(f"⏰ SERVER TIME CHECK: now_utc={now_utc} (If this seems wrong, check EC2 server clock sync!)")
            
            # Convert max_datetime to IST for user-friendly error message
            max_datetime_ist = (now_utc + timedelta(hours=72)).astimezone(IST)
            
            if scheduled_datetime < now_utc:
                scheduled_ist = scheduled_datetime.astimezone(IST)
                now_ist = now_utc.astimezone(IST)
                return templates.TemplateResponse("schedule_interview.html", {
                    "request": request,
                    "current_user": current_user,
                    "error": f"Scheduled time ({scheduled_ist.strftime('%Y-%m-%d %H:%M')} IST) cannot be in the past. Current time: {now_ist.strftime('%Y-%m-%d %H:%M')} IST"
                })
            
            # Validate 72-hour maximum
            max_datetime = now_utc + timedelta(hours=72)
            if scheduled_datetime > max_datetime:
                scheduled_ist = scheduled_datetime.astimezone(IST)
                return templates.TemplateResponse("schedule_interview.html", {
                    "request": request,
                    "current_user": current_user,
                    "error": f"Interviews can be scheduled up to 72 hours in advance. Latest available: {max_datetime_ist.strftime('%Y-%m-%d %H:%M')} IST (you entered: {scheduled_ist.strftime('%Y-%m-%d %H:%M')} IST)"
                })
            
            is_future_schedule = True
            print(f"📅 Future interview scheduled for: {scheduled_datetime} UTC (current: {now_utc} UTC)")
        except ValueError as e:
            return templates.TemplateResponse("schedule_interview.html", {
                "request": request,
                "current_user": current_user,
                "error": f"Invalid date/time format: {str(e)}"
            })
    
    # Generate unique interview ID
    interview_id = f"interview_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    # Get user API keys (with env fallback)
    openai_api_key = api_keys.get("openai")
    
    # Parse JD and Resume using GPT
    print(f"🤖 Parsing job description and resume with GPT...")
    jd_parser = JDParser()
    resume_parser = ResumeParser()
    
    # Parse in parallel for speed
    parsed_jd = await jd_parser.parse_job_description(job_description, position, api_key=openai_api_key)
    parsed_resume = await resume_parser.parse_resume(candidate_resume, api_key=openai_api_key)
    
    print(f"✅ JD parsed: {len(parsed_jd.get('skills_required', []))} skills required")
    print(f"✅ Resume parsed: {len(parsed_resume.get('skills', []))} skills found, {parsed_resume.get('experience_years', 0)} years exp")
    print(f"   Required skills: {', '.join(parsed_jd.get('skills_required', [])[:5])}")
    print(f"   Candidate skills: {', '.join(parsed_resume.get('skills', [])[:5])}")
    
    # Create unique Daily.co room for this interview
    # For future schedules, set nbf (not before) to scheduled time - 10 minutes (early join buffer)
    # Set exp (expires) to scheduled time + 1 hour (interview duration)
    room_nbf = None
    room_exp_minutes = None
    
    if is_future_schedule and scheduled_datetime:
        # Room opens 10 minutes before scheduled time (early join buffer)
        room_nbf = scheduled_datetime - timedelta(minutes=10)
        # Room expires 1 hour after scheduled time (allows interview to complete)
        room_exp_minutes = 60
        print(f"📅 Room will be available from: {room_nbf} (10 minutes before scheduled time)")
        print(f"📅 Room allows joining until: {scheduled_datetime + timedelta(minutes=10)} (10 minutes after scheduled time)")
    
    room_data = await daily_service.create_interview_room(
        interview_id=interview_id,
        candidate_name=candidate_name,
        scheduled_time=room_nbf,  # Pass nbf time (room opens 10 min before scheduled)
        expires_in_minutes=room_exp_minutes,
        scheduled_datetime=scheduled_datetime if is_future_schedule else None  # Pass actual scheduled time for exp calculation
    )
    
    if not room_data:
        raise HTTPException(
            status_code=500, 
            detail="Failed to create Daily.co room. Please check DAILY_API_KEY configuration."
        )
    
    # Generate candidate token (with their name)
    # For future schedules, token should be valid until room expires
    token_exp_minutes = room_exp_minutes if is_future_schedule else None
    candidate_token = await daily_service.create_candidate_token(
        room_name=room_data["room_name"],
        candidate_name=candidate_name,
        expires_in_minutes=token_exp_minutes,
        not_before=room_nbf,  # Token becomes valid when room opens (10 min before scheduled)
        scheduled_datetime=scheduled_datetime if is_future_schedule else None  # Pass actual scheduled time for exp calculation
    )
    
    # Store original Daily.co URL with token (for internal use)
    daily_room_url_with_token = f"{room_data['room_url']}?t={candidate_token}" if candidate_token else room_data['room_url']
    
    # Candidate join URL points to our proctored wrapper page
    # The wrapper will embed Daily.co and add proctoring
    candidate_join_url = f"/interview/{interview_id}/room"
    
    # Create interview record
    interview_data = {
        "interview_id": interview_id,
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "position": position,
        "interview_type": interview_type,
        "scoring_level": scoring_level,
        "status": "scheduled",
        "notes": notes,
        "created_at": datetime.now(),
        "room_url": room_data["room_url"],
        "daily_room_url_with_token": daily_room_url_with_token,  # Original Daily.co URL with token
        "room_name": room_data["room_name"],
        "candidate_join_url": candidate_join_url,
        # NEW: Store raw and parsed JD/Resume data
        "job_description_raw": job_description,
        "candidate_resume_raw": candidate_resume,
        "job_description_parsed": parsed_jd,
        "candidate_resume_parsed": parsed_resume
    }
    
    try:
        print(f"🔍 DEBUG: Attempting to save interview {interview_id}")
        print(f"   Candidate: {candidate_name}, Position: {position}")
        print(f"   Scoring Level: {scoring_level}")
        print(f"   db_service status: {db is not None}")
        
        # Extract user_id for data isolation
        user_id = current_user.get("userId")
        if not user_id:
            logger.warning("⚠️ No userId found in current_user - interview will not be isolated per user")
        
        # Store in database - create proper interview result entry
        success = await db.update_interview_result(
            interview_id=interview_id,
            transcript="Interview scheduled - waiting for completion",
            evaluation={
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
                "position": position,
                "company": "Hire2Inspire Tech Solutions",
                "interview_type": interview_type,
                "scoring_level": scoring_level,
                "status": "scheduled",
                "overall_score": 0,
                "individual_scores": {
                    "correctness": 0,
                    "terminology": 0,
                    "confidence": 0,
                    "experience_relevance": 0,
                    "problem_solving": 0
                },
                "questions_asked": [],
                "notes": notes,
                # Room URLs for proctoring
                "room_url": room_data["room_url"],
                "room_name": room_data["room_name"],
                "daily_room_url_with_token": daily_room_url_with_token,
                # NEW: Store parsed JD and Resume for question generation
                "job_description_parsed": parsed_jd,
                "candidate_resume_parsed": parsed_resume,
                "job_description_raw": job_description,
                "candidate_resume_raw": candidate_resume,
                # NEW: Store replica_id if specified (bot will read this from interview_config)
                "replica_id": replica_id if replica_id else None,
                # NEW: Store scheduled_date for future interviews (with timezone info)
                "scheduled_date": scheduled_datetime.isoformat() if scheduled_datetime else None
            },
            status="scheduled",
            user_id=user_id
        )
        
        print(f"🔍 DEBUG: Save result: {success}")
        
        if success:
            # Sprint 1.2: Auto-start bot if requested
            bot_job_id = None
            bot_status = "Not started (manual mode)"
            
            # Calculate delay for bot scheduling
            bot_delay_seconds = 0
            if is_future_schedule and scheduled_datetime:
                # Bot starts at scheduled time (room opens 10 minutes before, so bot can join early)
                # Use UTC to match scheduled_datetime's timezone
                now_utc = datetime.now(timezone.utc)
                delay_timedelta = scheduled_datetime - now_utc
                bot_delay_seconds = int(delay_timedelta.total_seconds())
                
                # Safety check: ensure delay is not negative (shouldn't happen due to validation, but safeguard)
                if bot_delay_seconds < 0:
                    print(f"⚠️ Bot delay is negative ({bot_delay_seconds}s) - scheduling immediately instead")
                    bot_delay_seconds = 0
                
                print(f"⏰ Bot will start in {bot_delay_seconds} seconds ({delay_timedelta})")
                print(f"⏰ Room will be available 10 minutes before bot starts")
            
            if auto_start:
                try:
                    # Use injected bot_manager (already available from DI)
                    
                    # Create bot token (owner privileges)
                    # For future schedules, token needs to be valid at scheduled time
                    bot_token = await daily_service.create_bot_token(
                        room_name=room_data["room_name"],
                        expires_in_minutes=room_exp_minutes if is_future_schedule else None,
                        not_before=room_nbf if is_future_schedule else None,
                        scheduled_datetime=scheduled_datetime if is_future_schedule else None  # Pass actual scheduled time for exp calculation
                    )
                    
                    # Bot joins with token for owner access
                    bot_room_url = f"{room_data['room_url']}?t={bot_token}" if bot_token else room_data['room_url']
                    
                    # Pass room URL with token in config
                    bot_config = {
                        "room_url": bot_room_url,
                        "room_name": room_data["room_name"]
                    }
                    # Schedule bot with delay for future interviews
                    bot_result = bot_manager.schedule_interview(
                        interview_id, 
                        config=bot_config,
                        delay=bot_delay_seconds  # 0 for immediate, >0 for future
                    )
                    if bot_result.get("success"):
                        bot_job_id = bot_result.get("job_id")
                        bot_status = f"Queued (Job: {bot_job_id[:16]}...)"
                        print(f"✅ Bot job enqueued: {bot_job_id}")
                        print(f"🔗 Bot Room URL: {bot_room_url}")
                        print(f"🔗 Candidate URL: {candidate_join_url}")
                    else:
                        bot_status = f"Failed: {bot_result.get('error', 'Unknown error')}"
                        print(f"❌ Bot job failed: {bot_status}")
                except Exception as e:
                    bot_status = f"Error: {str(e)}"
                    print(f"❌ Bot job error: {e}")
            
            # Add bot info to interview data for display
            interview_data["bot_job_id"] = bot_job_id
            interview_data["bot_status"] = bot_status
            interview_data["auto_start"] = auto_start
            # Add the actual join URL for the candidate (includes token)
            interview_data["join_url"] = candidate_join_url
            
            # Redirect to interview instructions
            return templates.TemplateResponse("interview_scheduled.html", {
                "request": request,
                "interview": interview_data
            })
        else:
            raise Exception("Failed to create interview")
            
    except Exception as e:
        return templates.TemplateResponse("schedule_interview.html", {
            "request": request,
            "error": f"Failed to schedule interview: {str(e)}"
        })

@router.post("/schedule")
async def schedule_interview(
    request: Request,
    current_user: CurrentUserDep,
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    position: str = Form(...),
    scheduled_date: str = Form(...),
    job_description_id: str = Form(...),
    resume_data_id: str = Form(...)
):
    """Handle interview scheduling form submission"""
    # TODO: Create interview in database
    # TODO: Generate interview questions
    # TODO: Send email to candidate
    
    interview_data = {
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "position": position,
        "scheduled_date": scheduled_date,
        "status": "scheduled",
        "created_at": datetime.now().isoformat()
    }
    
    # For now, just return success
    return {"success": True, "interview_id": "int_" + str(hash(candidate_email))[:6]}

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user: CurrentUserDep
):
    """Interview settings and configuration page - Requires authentication"""
    # TODO: Get current settings from database
    settings = {
        "default_duration": 45,
        "scoring_thresholds": {
            "excellent": 90,
            "good": 75,
            "average": 60,
            "poor": 40
        },
        "question_focus": {
            "technical_skills": 40,
            "experience": 30,
            "problem_solving": 20,
            "cultural_fit": 10
        },
        "difficulty_level": "medium"
    }
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": settings
    })

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    db: DbServiceDep,
    current_user: CurrentUserDep,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    position: Optional[str] = None
):
    """Analytics page with charts and insights - Requires authentication"""
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    # Set default date range (last 30 days)
    if not date_to:
        date_to = datetime.now().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Get all interviews from database directly (filtered by user_id)
    try:
        if db and db.database is not None:
            # Get user_id for data isolation
            user_id = current_user.get("userId")
            if not user_id:
                logger.warning("⚠️ No userId found - cannot filter interviews per user")
            
            all_interviews = await db.get_interviews(user_id=user_id)
        else:
            all_interviews = []
    except Exception as e:
        print(f"❌ Error getting interviews for analytics: {e}")
        all_interviews = []
    
    # Filter by date range and position
    filtered_interviews = []
    for interview in all_interviews:
        # Date filter
        date_str = interview.get("scheduled_date", "")
        if date_str and date_str != "N/A":
            try:
                if isinstance(date_str, str):
                    interview_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                else:
                    interview_date = date_str.date()
                
                if interview_date >= datetime.fromisoformat(date_from).date() and interview_date <= datetime.fromisoformat(date_to).date():
                    # Position filter
                    if not position or interview.get("position") == position:
                        filtered_interviews.append(interview)
            except:
                pass
    
    # Calculate metrics
    total_interviews = len(filtered_interviews)
    completed_interviews = [i for i in filtered_interviews if i.get("status") in ["completed", "ended_by_candidate"]]
    completed_count = len(completed_interviews)
    
    # Average score
    scored_interviews = [i for i in completed_interviews if i.get("score", 0) > 0]
    avg_score = round(sum(i.get("score", 0) for i in scored_interviews) / len(scored_interviews), 1) if scored_interviews else 0
    
    # Hire rate (score >= 65)
    recommended_count = len([i for i in completed_interviews if i.get("score", 0) >= 65])
    hire_rate = round((recommended_count / completed_count * 100), 1) if completed_count > 0 else 0
    
    # Completion rate
    completion_rate = round((completed_count / total_interviews * 100), 1) if total_interviews > 0 else 0
    
    # Growth rate (placeholder)
    growth_rate = 15.2
    
    metrics = {
        "total_interviews": total_interviews,
        "avg_score": avg_score,
        "hire_rate": hire_rate,
        "completion_rate": completion_rate,
        "recommended_count": recommended_count,
        "completed_count": completed_count,
        "growth_rate": growth_rate
    }
    
    # Trends data
    trends_by_date = defaultdict(int)
    for interview in filtered_interviews:
        date_str = interview.get("scheduled_date", "")
        if date_str and date_str != "N/A":
            try:
                if isinstance(date_str, str):
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime("%Y-%m-%d")
                else:
                    date = date_str.strftime("%Y-%m-%d")
                trends_by_date[date] += 1
            except:
                pass
    
    sorted_dates = sorted(trends_by_date.keys())
    trends_data = {
        "labels": sorted_dates,
        "values": [trends_by_date[d] for d in sorted_dates]
    }
    
    # Score distribution
    score_ranges = {"Poor (0-40)": 0, "Below Avg (41-60)": 0, "Average (61-75)": 0, "Good (76-85)": 0, "Excellent (86-100)": 0}
    for interview in scored_interviews:
        score = interview.get("score", 0)
        if score <= 40:
            score_ranges["Poor (0-40)"] += 1
        elif score <= 60:
            score_ranges["Below Avg (41-60)"] += 1
        elif score <= 75:
            score_ranges["Average (61-75)"] += 1
        elif score <= 85:
            score_ranges["Good (76-85)"] += 1
        else:
            score_ranges["Excellent (86-100)"] += 1
    
    score_dist_data = {
        "labels": list(score_ranges.keys()),
        "values": list(score_ranges.values())
    }
    
    # Scoring level data (placeholder)
    scoring_level_data = {
        "labels": ["Easy", "Intermediate", "Strict"],
        "values": [0, len(filtered_interviews), 0]
    }
    
    # Criteria performance
    criteria_data = {
        "labels": ["Correctness", "Terminology", "Confidence", "Experience", "Problem Solving"],
        "values": [avg_score * 0.9, avg_score * 0.85, avg_score * 1.1, avg_score * 0.95, avg_score * 1.05]
    }
    
    # Position stats
    position_groups = defaultdict(lambda: {"scores": [], "count": 0, "recommended": 0})
    for interview in completed_interviews:
        pos = interview.get("position", "Unknown")
        score = interview.get("score", 0)
        position_groups[pos]["scores"].append(score)
        position_groups[pos]["count"] += 1
        if score >= 65:
            position_groups[pos]["recommended"] += 1
    
    position_stats = []
    for pos, data in position_groups.items():
        if data["scores"]:
            position_stats.append({
                "position": pos,
                "count": data["count"],
                "avg_score": round(sum(data["scores"]) / len(data["scores"]), 1),
                "hire_rate": round((data["recommended"] / data["count"] * 100), 1),
                "top_score": max(data["scores"])
            })
    
    position_stats.sort(key=lambda x: x["count"], reverse=True)
    
    # Top candidates
    top_candidates_list = sorted(
        [i for i in completed_interviews if i.get("score", 0) > 0],
        key=lambda x: x.get("score", 0),
        reverse=True
    )[:10]
    
    top_candidates = []
    for i, candidate in enumerate(top_candidates_list):
        score = candidate.get("score", 0)
        if score >= 85:
            recommendation = "strong_yes"
        elif score >= 70:
            recommendation = "yes"
        elif score >= 55:
            recommendation = "maybe"
        else:
            recommendation = "no"
        
        date_str = candidate.get("scheduled_date", "N/A")
        if date_str != "N/A":
            try:
                if isinstance(date_str, str):
                    formatted_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime("%Y-%m-%d")
                else:
                    formatted_date = date_str.strftime("%Y-%m-%d")
            except:
                formatted_date = "N/A"
        else:
            formatted_date = "N/A"
        
        top_candidates.append((i, {
            "id": candidate.get("id", "unknown"),
            "name": candidate.get("candidate_name", "Unknown"),
            "position": candidate.get("position", "Unknown"),
            "score": score,
            "date": formatted_date,
            "recommendation": recommendation
        }))
    
    # Get unique positions for filter
    positions = sorted(set(i.get("position", "Unknown") for i in all_interviews))
    
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "date_from": date_from,
        "date_to": date_to,
        "selected_position": position or "",
        "positions": positions,
        "metrics": metrics,
        "trends_data": trends_data,
        "score_dist_data": score_dist_data,
        "scoring_level_data": scoring_level_data,
        "criteria_data": criteria_data,
        "position_stats": position_stats,
        "top_candidates": top_candidates
    })

@router.get("/system-health", response_class=HTMLResponse)
async def system_health_page(
    request: Request,
    db: DbServiceDep,
    bot_manager: BotManagerDep,
    current_user: CurrentUserDep
):
    """System health monitoring page - Requires authentication"""
    import sys
    import os
    from datetime import datetime
    
    # Check database status
    db_status = "connected" if (db and db.database is not None) else "disconnected"
    
    # Get database info
    if db and db.database is not None:
        try:
            db_name = db.database.name
            collection_names = await db.database.list_collection_names()
            db_collections = len(collection_names)
            
            # Get interview stats
            total_interviews = await db.database.interview_results.count_documents({})
            completed = await db.database.interview_results.count_documents({"status": {"$in": ["completed", "ended_by_candidate"]}})
            pending = await db.database.interview_results.count_documents({"status": {"$nin": ["completed", "ended_by_candidate"]}})
            scoring_configs = await db.database.scoring_configs.count_documents({})
        except:
            db_name = "Unknown"
            db_collections = 0
            total_interviews = 0
            completed = 0
            pending = 0
            scoring_configs = 0
    else:
        db_name = "Not connected"
        db_collections = 0
        total_interviews = 0
        completed = 0
        pending = 0
        scoring_configs = 0
    
    db_info = {
        "connection": db_name,
        "collections": db_collections
    }
    
    db_stats = {
        "total_interviews": total_interviews,
        "completed": completed,
        "pending": pending,
        "scoring_configs": scoring_configs,
        "size": "~2.5 MB"  # Placeholder
    }
    
    # Calculate overall health
    active_services = 0
    total_services = 5
    
    if db_status == "connected":
        active_services += 1
    active_services += 3  # Question Engine, Scoring Engine, Web Server (always on)
    
    health_score = round((active_services / total_services) * 100)
    
    if health_score >= 80:
        overall_status = "healthy"
    elif health_score >= 50:
        overall_status = "degraded"
    else:
        overall_status = "critical"
    
    system_status = {
        "overall": overall_status,
        "database": db_status,
        "bot": "manual_check",
        "question_engine": "operational",
        "scoring_engine": "operational",
        "web_server": "running"
    }
    
    # Environment info
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    environment = "Development"
    debug_mode = "Enabled"
    # Check if user has API keys configured (no env fallback)
    has_openai_key = False  # Will be checked per-user if needed
    has_daily_room = bool(os.getenv("DAILY_ROOM_URL"))  # Infrastructure config, not user-specific
    
    return templates.TemplateResponse("system_health.html", {
        "request": request,
        "system_status": system_status,
        "uptime": "Running",
        "last_check": datetime.now(timezone.utc).astimezone(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %I:%M:%S %p IST"),
        "active_services": active_services,
        "total_services": total_services,
        "health_score": health_score,
        "db_info": db_info,
        "db_stats": db_stats,
        "port": 8009,
        "python_version": python_version,
        "environment": environment,
        "debug_mode": debug_mode,
        "has_openai_key": has_openai_key,
        "has_daily_room": has_daily_room
    })


@router.post("/api/v1/interviews/{interview_id}/generate-link")
async def generate_interview_link(
    interview_id: str,
    db: DbServiceDep,
    current_user: CurrentUserDep
):
    """Generate a fresh join link with token for an interview - Requires authentication"""
    print(f"🔍 API called: generate_interview_link for {interview_id}")
    try:
        # Get interview from database
        if db is None or db.database is None:
            print(f"❌ Database not available")
            raise HTTPException(status_code=500, detail="Database not available")
        
        # Find interview by interview_id
        interview = await db.database.interview_results.find_one({"interview_id": interview_id})
        print(f"📊 Interview found: {interview is not None}")
        
        if not interview:
            print(f"❌ Interview not found: {interview_id}")
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Check if interview has room_url and room_name
        room_url = interview.get("room_url")
        room_name = interview.get("room_name")
        candidate_name = interview.get("candidate_name", "Candidate")
        print(f"📋 Interview data: room_url={room_url}, room_name={room_name}, candidate={candidate_name}")
        
        if not room_url:
            # Construct room URL if missing
            daily_domain = os.getenv("DAILY_DOMAIN", "human2intelligence.daily.co")
            if room_name:
                room_url = f"https://{daily_domain}/{room_name}"
            else:
                room_url = f"https://{daily_domain}/interview-{interview_id}"
                room_name = f"interview-{interview_id}"
        
        # Extract room_name from room_url if not stored
        if not room_name and room_url:
            room_name = room_url.split("/")[-1]
        
        # Return the proctored interview room URL (not the Daily.co room URL)
        # This is the URL that candidates should use to join the interview
        join_url = f"/interview/{interview_id}/room"
        
        # Construct full URL from request
        base_url = str(request.base_url).rstrip('/')
        full_join_url = f"{base_url}{join_url}"
        
        print(f"✅ Returning proctored interview URL: {full_join_url}")
        return JSONResponse({
            "success": True,
            "join_url": full_join_url,
            "interview_id": interview_id
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error generating interview link: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/replica-requests", response_class=HTMLResponse)
async def replica_requests_page(
    request: Request,
    db: DbServiceDep,
    current_user: CurrentUserDep
):
    """Display user's replica requests status"""
    try:
        # Get user identifier from JWT token
        user_id = current_user.get("userId", "unknown")
        payload = current_user.get("payload", {})
        user_email = payload.get("email") or payload.get("userEmail") or None
        
        # Use email if available, otherwise user_id (matches how requests are stored)
        submitted_by = user_email if user_email else user_id
        
        # Get all replica requests for this user
        all_requests = await db.list_replica_requests(
            submitted_by=submitted_by,
            limit=1000
        )
        
        # Group by status
        pending_requests = [r for r in all_requests if r.get("status") == "pending"]
        approved_requests = [r for r in all_requests if r.get("status") == "approved"]
        rejected_requests = [r for r in all_requests if r.get("status") == "rejected"]
        training_requests = [r for r in all_requests if r.get("status") == "training"]
        completed_requests = [r for r in all_requests if r.get("status") == "completed"]
        
        stats = {
            "total": len(all_requests),
            "pending": len(pending_requests),
            "approved": len(approved_requests),
            "rejected": len(rejected_requests),
            "training": len(training_requests),
            "completed": len(completed_requests)
        }
        
        return templates.TemplateResponse("replica_requests.html", {
            "request": request,
            "pending_requests": pending_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "training_requests": training_requests,
            "completed_requests": completed_requests,
            "stats": stats
        })
    except Exception as e:
        print(f"❌ Error loading replica requests: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
