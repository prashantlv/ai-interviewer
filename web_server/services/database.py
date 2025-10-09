"""
Database Service - MongoDB connection and operations
PLACEHOLDER: Waiting for ATS MongoDB schema from user
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
        
        if "interviews" not in collections:
            await self.database.create_collection("interviews")
            # Create indexes for interviews
            await self.database.interviews.create_index("interview_id", unique=True)
            await self.database.interviews.create_index("candidate_id")
            await self.database.interviews.create_index("status")
            await self.database.interviews.create_index("created_at")
            print("✅ Created 'interviews' collection with indexes")
        
        if "candidates" not in collections:
            await self.database.create_collection("candidates")
            await self.database.candidates.create_index("candidate_id", unique=True)
            await self.database.candidates.create_index("email", unique=True)
            print("✅ Created 'candidates' collection with indexes")
        
        if "job_descriptions" not in collections:
            await self.database.create_collection("job_descriptions")
            await self.database.job_descriptions.create_index("job_id", unique=True)
            print("✅ Created 'job_descriptions' collection with indexes")
        
        if "interview_results" not in collections:
            await self.database.create_collection("interview_results")
            await self.database.interview_results.create_index("interview_id", unique=True)
            print("✅ Created 'interview_results' collection with indexes")
    
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
        status: str
    ) -> bool:
        """Update interview with results"""
        result_data = {
            "interview_id": interview_id,
            "transcript": transcript,
            "evaluation": evaluation,
            "status": status,
            "completed_at": datetime.now(),
            "created_at": datetime.now()
        }
        
        if self.database is not None:
            try:
                # Store in MongoDB
                await self.database.interview_results.replace_one(
                    {"interview_id": interview_id},
                    result_data,
                    upsert=True
                )
                print(f"✅ Stored interview result: {interview_id}")
                return True
            except Exception as e:
                print(f"❌ Error storing interview result: {e}")
        
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
                
                cursor = self.database.interview_results.find(query).limit(limit).skip(offset)
                results = []
                
                async for doc in cursor:
                    # Remove MongoDB's _id field
                    doc.pop('_id', None)
                    
                    # Extract candidate info from evaluation
                    evaluation = doc.get("evaluation", {})
                    
                    date_value = doc.get("completed_at", doc.get("created_at"))
                    results.append({
                        "id": doc.get("interview_id", "unknown"),
                        "candidate_name": evaluation.get("candidate_name", "Unknown"),
                        "position": evaluation.get("position", "Unknown Position"),
                        "status": doc.get("status", "unknown"),
                        "score": evaluation.get("overall_score", 0),
                        "created_at": date_value,
                        "scheduled_date": date_value,  # Alias for compatibility
                        "transcript_available": bool(doc.get("transcript"))
                    })
                
                return results
            except Exception as e:
                print(f"❌ Error retrieving interviews: {e}")
        
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

# Global database instance
db_service = DatabaseService()
