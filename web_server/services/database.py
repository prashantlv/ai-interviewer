"""
Database Service - MongoDB connection and operations
Manages interview_results and cloned_voices collections
"""

from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any, List
import os
import json
from datetime import datetime

class DatabaseService:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None
        
        # MongoDB connection settings (will be updated with real schema)
        self.mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.database_name = os.getenv("DATABASE_NAME", "ai_interviewer")
        
        # Connection pool settings
        self.max_pool_size = int(os.getenv("MONGODB_MAX_POOL_SIZE", "100"))
        self.min_pool_size = int(os.getenv("MONGODB_MIN_POOL_SIZE", "10"))
        self.max_idle_time_ms = int(os.getenv("MONGODB_MAX_IDLE_TIME_MS", "45000"))
        
    async def connect(self):
        """Connect to MongoDB with connection pooling"""
        try:
            # Connect to real MongoDB with connection pooling
            self.client = AsyncIOMotorClient(
                self.mongodb_url,
                maxPoolSize=self.max_pool_size,
                minPoolSize=self.min_pool_size,
                maxIdleTimeMS=self.max_idle_time_ms,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=10000,  # 10 second connection timeout
                socketTimeoutMS=20000,   # 20 second socket timeout
            )
            self.database = self.client[self.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            print(f"✅ Connected to MongoDB: {self.database_name}")
            print(f"   Pool size: {self.min_pool_size}-{self.max_pool_size} connections")
            
            # Initialize collections and indexes
            await self._initialize_collections()
            return True
            
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            print("🔄 Falling back to mock mode")
            self.client = None
            self.database = None
            return False
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            print("🔌 MongoDB connection closed")
        else:
            print("🔌 Mock mode shutdown complete")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health with detailed statistics"""
        if self.client:
            try:
                # Ping database
                await self.client.admin.command('ping')
                
                # Get server info
                server_info = await self.client.server_info()
                
                # Get database stats
                db_stats = await self.database.command("dbStats")
                
                return {
                    "status": "connected",
                    "database": self.database_name,
                    "server_version": server_info.get("version", "unknown"),
                    "connection_pool": {
                        "max_pool_size": self.max_pool_size,
                        "min_pool_size": self.min_pool_size,
                        "max_idle_time_ms": self.max_idle_time_ms
                    },
                    "database_stats": {
                        "collections": db_stats.get("collections", 0),
                        "data_size": db_stats.get("dataSize", 0),
                        "storage_size": db_stats.get("storageSize", 0),
                        "indexes": db_stats.get("indexes", 0)
                    }
                }
            except Exception as e:
                return {
                    "status": "disconnected",
                    "error": str(e)
                }
        else:
            return {
                "status": "mock_mode",
                "message": "Running without database connection"
            }
    
    async def _initialize_collections(self):
        """Initialize MongoDB collections and indexes"""
        if self.database is None:
            return
        
        # Create collections if they don't exist
        collections = await self.database.list_collection_names()
        
        # interview_results - stores ALL interview data (scheduled + completed)
        if "interview_results" not in collections:
            await self.database.create_collection("interview_results")
            await self.database.interview_results.create_index("interview_id", unique=True)
            await self.database.interview_results.create_index("status")
            await self.database.interview_results.create_index("created_at")
            print("✅ Created 'interview_results' collection with indexes")
        
        # cloned_voices - stores voice cloning data
        if "cloned_voices" not in collections:
            await self.database.create_collection("cloned_voices")
            await self.database.cloned_voices.create_index("voice_id", unique=True)
            await self.database.cloned_voices.create_index("owner_id")
            await self.database.cloned_voices.create_index("created_at")
            print("✅ Created 'cloned_voices' collection with indexes")
    
    def _load_json_data(self, filename: str) -> Dict[str, Any]:
        """Load data from JSON file"""
        try:
            file_path = os.path.join(os.path.dirname(__file__), "..", "data", filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
            return {}
    
    # Database Methods - Use JSON files for JD and Resume, store results in MongoDB
    
    async def create_interview(self, interview_data: Dict[str, Any]) -> str:
        """Create a new interview record"""
        # TODO: Implement with real MongoDB schema
        # PLACEHOLDER: Return mock interview ID
        return f"int_{hash(str(interview_data)) % 100000:05d}"
    
    async def get_interview(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """Get interview by ID"""
        # TODO: Implement with real MongoDB schema
        # PLACEHOLDER: Return mock data
        return {
            "id": interview_id,
            "status": "scheduled",
            "job_description": {"title": "Developer", "skills": ["Python"]},
            "resume_data": {"skills": ["Python", "JavaScript"], "experience": 3},
            "config": {"difficulty": "medium"}
        }
    
    async def update_interview_result(
        self, 
        interview_id: str,
        transcript: str,
        evaluation: Dict[str, Any],
        status: str,
        recording: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update interview with results"""
        # Check if this interview already exists
        existing_interview = None
        if self.database is not None:
            try:
                existing_interview = await self.database.interview_results.find_one(
                    {"interview_id": interview_id}
                )
            except Exception as e:
                print(f"⚠️ Error checking existing interview: {e}")
        
        # Build result data
        result_data = {
            "interview_id": interview_id,
            "transcript": transcript,
            "evaluation": evaluation,
            "status": status,
        }
        
        # Set created_at only if this is a new interview
        if existing_interview:
            # Preserve existing created_at
            result_data["created_at"] = existing_interview.get("created_at", datetime.now())
        else:
            # New interview - set created_at
            result_data["created_at"] = datetime.now()
        
        # Persist recording information
        if recording:
            result_data["recording"] = recording
        elif existing_interview and existing_interview.get("recording"):
            result_data["recording"] = existing_interview.get("recording")
        
        # Set completed_at only if status is "completed"
        if status == "completed":
            result_data["completed_at"] = datetime.now()
        elif existing_interview:
            # Preserve existing completed_at if interview isn't being marked as completed
            if "completed_at" in existing_interview:
                result_data["completed_at"] = existing_interview["completed_at"]
        
        if self.database is not None:
            try:
                # Store in MongoDB using upsert
                await self.database.interview_results.replace_one(
                    {"interview_id": interview_id},
                    result_data,
                    upsert=True
                )
                print(f"✅ Stored interview result: {interview_id} (status: {status})")
                return True
            except Exception as e:
                print(f"❌ Error storing interview result: {e}")
                import traceback
                traceback.print_exc()
        
        # Fallback: return success even in mock mode
        return True
    
    async def get_interview_result(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """Get interview result by ID"""
        if self.database is not None:
            try:
                result = await self.database.interview_results.find_one(
                    {"interview_id": interview_id}
                )
                if result:
                    # Remove MongoDB's _id field for cleaner data
                    result.pop('_id', None)
                    return result
            except Exception as e:
                print(f"❌ Error retrieving interview result: {e}")
        
        # Return None if not found
        return None
    
    async def get_interviews(
        self, 
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get list of interviews with optional filtering"""
        if self.database is not None:
            try:
                # Query the interview_results collection for real data
                query = {}
                if status:
                    query["status"] = status
                
                # Sort by date (most recent first) BEFORE pagination
                # Use completed_at if available, otherwise created_at
                cursor = self.database.interview_results.find(query).sort(
                    [("completed_at", -1), ("created_at", -1)]
                ).limit(limit).skip(offset)
                
                results = []
                
                async for doc in cursor:
                    # Remove MongoDB's _id field
                    doc.pop('_id', None)
                    
                    # Extract candidate info from evaluation
                    evaluation = doc.get("evaluation", {})
                    
                    # Get date value - prefer completed_at, fallback to created_at
                    date_value = doc.get("completed_at") or doc.get("created_at")
                    
                    # Handle datetime objects
                    if date_value and hasattr(date_value, 'isoformat'):
                        date_value = date_value.isoformat()
                    
                    results.append({
                        "id": doc.get("interview_id", "unknown"),
                        "candidate_name": evaluation.get("candidate_name", "Unknown"),
                        "candidate_email": evaluation.get("candidate_email", "N/A"),
                        "position": evaluation.get("position", "Unknown Position"),
                        "status": doc.get("status", "unknown"),
                        "score": evaluation.get("overall_score", 0),
                        "created_at": date_value,
                        "scheduled_date": date_value,  # Alias for compatibility
                        "interview_type": evaluation.get("interview_type", "technical"),
                        "transcript_available": bool(doc.get("transcript") and doc.get("transcript") != "Interview scheduled - waiting for completion")
                    })
                
                return results
            except Exception as e:
                print(f"❌ Error retrieving interviews: {e}")
                import traceback
                traceback.print_exc()
        
        # Fallback: Return empty list if database unavailable
        return []
    
    async def store_feedback(self, feedback_data: Dict[str, Any]) -> str:
        """Store recruiter feedback"""
        # TODO: Implement with real MongoDB schema
        return f"fb_{hash(str(feedback_data)) % 100000:05d}"
    
    async def get_job_description(self, jd_id: str) -> Optional[Dict[str, Any]]:
        """Get job description from ATS"""
        # TODO: Implement with ATS integration
        return {
            "id": jd_id,
            "title": "Software Developer",
            "skills_required": ["Python", "React", "MongoDB"],
            "experience_level": "Mid-level",
            "department": "Engineering"
        }
    
    async def get_resume_data(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """Get resume data from ATS"""
        # TODO: Implement with ATS integration
        return {
            "id": resume_id,
            "skills": ["Python", "JavaScript", "React"],
            "experience_years": 3,
            "education": "Computer Science",
            "previous_roles": ["Junior Developer", "Frontend Developer"]
        }


    async def update_interview(
        self,
        interview_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update interview record with arbitrary data (e.g., proctoring)"""
        if self.database is not None:
            try:
                result = await self.database.interview_results.update_one(
                    {"interview_id": interview_id},
                    {"$set": update_data}
                )
                return result.modified_count > 0 or result.matched_count > 0
            except Exception as e:
                print(f"❌ Error updating interview: {e}")
                return False
        return False


# Global database instance
db_service = DatabaseService()
