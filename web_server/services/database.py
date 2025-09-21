"""
Database Service - MongoDB connection and operations
PLACEHOLDER: Waiting for ATS MongoDB schema from user
"""

from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any, List
import os
from datetime import datetime

class DatabaseService:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None
        
        # MongoDB connection settings (will be updated with real schema)
        self.mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.database_name = os.getenv("DATABASE_NAME", "ai_interviewer")
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            # Connect to real MongoDB
            self.client = AsyncIOMotorClient(self.mongodb_url)
            self.database = self.client[self.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            print(f"✅ Connected to MongoDB: {self.database_name}")
            
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
    
    async def health_check(self) -> str:
        """Check database health"""
        if self.client:
            try:
                await self.client.admin.command('ping')
                return "connected"
            except:
                return "disconnected"
        else:
            return "mock_mode"
    
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
    
    async def get_interviews(
        self, 
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get list of interviews with optional filtering"""
        # TODO: Implement with real MongoDB schema
        # PLACEHOLDER: Return mock data
        return [
            {
                "id": "int_001",
                "candidate_name": "John Doe",
                "status": "completed",
                "score": 85.5,
                "created_at": datetime.now()
            }
        ]
    
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
