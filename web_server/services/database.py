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
        
        # MongoDB connection settings
        # ⚠️ SECURITY: Never hardcode credentials! Always use environment variables.
        self.mongodb_url = os.getenv("MONGODB_URL")
        self.database_name = os.getenv("DATABASE_NAME", "ai_interviewer")
        
        if not self.mongodb_url:
            raise ValueError(
                "MONGODB_URL environment variable is required. "
                "Please set it in your .env file or environment. "
                "Example: mongodb+srv://user:pass@cluster.mongodb.net/dbname?retryWrites=true&w=majority"
            )
        
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
        
        # replica_voice_mappings - stores replica to voice mappings
        if "replica_voice_mappings" not in collections:
            await self.database.create_collection("replica_voice_mappings")
            await self.database.replica_voice_mappings.create_index("replica_id", unique=True)
            await self.database.replica_voice_mappings.create_index("is_default")
            await self.database.replica_voice_mappings.create_index("is_active")
            print("✅ Created 'replica_voice_mappings' collection with indexes")
        
        # admin_users - stores admin login credentials
        if "admin_users" not in collections:
            await self.database.create_collection("admin_users")
            await self.database.admin_users.create_index("username", unique=True)
            await self.database.admin_users.create_index("is_active")
            print("✅ Created 'admin_users' collection with indexes")
        
        # replica_requests - stores replica creation requests (pending approval)
        if "replica_requests" not in collections:
            await self.database.create_collection("replica_requests")
            await self.database.replica_requests.create_index("request_id", unique=True)
            await self.database.replica_requests.create_index("status")
            await self.database.replica_requests.create_index("submitted_at")
            await self.database.replica_requests.create_index("submitted_by")
            print("✅ Created 'replica_requests' collection with indexes")
        
        # user_integrations - stores encrypted API keys per user
        if "user_integrations" not in collections:
            await self.database.create_collection("user_integrations")
            await self.database.user_integrations.create_index([("user_id", 1), ("provider", 1)], unique=True)
            await self.database.user_integrations.create_index("user_id")
            await self.database.user_integrations.create_index("provider")
            await self.database.user_integrations.create_index("is_active")
            print("✅ Created 'user_integrations' collection with indexes")
    
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
        recording: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Update interview with results"""
        if self.database is None:
            # Mock mode: pretend success
            return True

        now = datetime.now()

        # IMPORTANT: Do NOT replace the whole document.
        # We must preserve fields written by other parts of the system (e.g. `proctoring`).
        try:
            update_set: Dict[str, Any] = {
                "transcript": transcript,
                "evaluation": evaluation,
                "status": status,
            }

            # Store user_id if provided (for data isolation)
            if user_id:
                update_set["user_id"] = user_id
                print(f"🔍 DEBUG: Storing interview {interview_id} with user_id: {user_id}")

            # Only overwrite recording if explicitly provided (otherwise preserve existing).
            if recording is not None:
                update_set["recording"] = recording

            # Only set completed_at when we are marking completed (otherwise preserve).
            if status == "completed":
                update_set["completed_at"] = now

            result = await self.database.interview_results.update_one(
                {"interview_id": interview_id},
                {
                    "$set": update_set,
                    "$setOnInsert": {
                        "interview_id": interview_id,
                        "created_at": now,
                    },
                },
                upsert=True,
            )

            ok = (result.modified_count > 0) or (result.upserted_id is not None) or (result.matched_count > 0)
            if ok:
                print(f"✅ Stored interview result: {interview_id} (status: {status})")
            else:
                print(f"⚠️ Interview result not modified (but may already be up-to-date): {interview_id}")
            return True
        except Exception as e:
            print(f"❌ Error storing interview result: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of interviews with optional filtering by status and user_id"""
        if self.database is not None:
            try:
                # Query the interview_results collection for real data
                query = {}
                if status:
                    query["status"] = status
                
                # CRITICAL: Filter by user_id for data isolation
                # Only show interviews with matching user_id (strict isolation)
                if user_id:
                    query["user_id"] = user_id
                    print(f"🔍 DEBUG: Filtering interviews by user_id: {user_id} (strict isolation - old interviews without user_id will NOT be shown)")
                else:
                    # If no user_id provided, return empty (don't show interviews without user_id to everyone)
                    print(f"⚠️ WARNING: get_interviews called without user_id - returning EMPTY (strict isolation)")
                    return []
                
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
                    
                    # Include full document data (including proctoring) for duration calculation
                    results.append({
                        "id": doc.get("interview_id", "unknown"),
                        "interview_id": doc.get("interview_id", "unknown"),  # Add interview_id for consistency
                        "candidate_name": evaluation.get("candidate_name", "Unknown"),
                        "candidate_email": evaluation.get("candidate_email", "N/A"),
                        "position": evaluation.get("position", "Unknown Position"),
                        "status": doc.get("status", "unknown"),
                        "score": evaluation.get("overall_score", 0),
                        "created_at": date_value,
                        "scheduled_date": date_value,  # Alias for compatibility
                        "interview_type": evaluation.get("interview_type", "technical"),
                        "transcript_available": bool(doc.get("transcript") and doc.get("transcript") != "Interview scheduled - waiting for completion"),
                        # Include proctoring data for duration calculation
                        "proctoring": doc.get("proctoring"),
                        # Include evaluation for scheduled_date extraction
                        "evaluation": evaluation
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

    # ============================================================================
    # Replica-Voice Mapping Methods
    # ============================================================================
    
    async def get_default_replica_config(self) -> Optional[Dict[str, Any]]:
        """Get the default replica-voice mapping configuration"""
        if self.database is None:
            return None
        
        try:
            config = await self.database.replica_voice_mappings.find_one({
                "is_default": True,
                "is_active": True
            })
            if config:
                config.pop('_id', None)
            return config
        except Exception as e:
            print(f"❌ Error getting default replica config: {e}")
            return None
    
    async def get_replica_config(self, replica_id: str) -> Optional[Dict[str, Any]]:
        """Get replica-voice mapping for a specific replica"""
        if self.database is None:
            return None
        
        try:
            config = await self.database.replica_voice_mappings.find_one({
                "replica_id": replica_id,
                "is_active": True
            })
            if config:
                config.pop('_id', None)
            return config
        except Exception as e:
            print(f"❌ Error getting replica config: {e}")
            return None
    
    async def list_replica_configs(self) -> List[Dict[str, Any]]:
        """List all replica-voice mappings"""
        if self.database is None:
            return []
        
        try:
            configs = []
            cursor = self.database.replica_voice_mappings.find({"is_active": True}).sort("created_at", -1)
            async for config in cursor:
                config.pop('_id', None)
                configs.append(config)
            return configs
        except Exception as e:
            print(f"❌ Error listing replica configs: {e}")
            return []
    
    async def create_replica_mapping(
        self,
        replica_id: str,
        voice_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_default: bool = False
    ) -> bool:
        """Create or update a replica-voice mapping"""
        if self.database is None:
            return False
        
        try:
            # If setting as default, unset other defaults first
            if is_default:
                await self.database.replica_voice_mappings.update_many(
                    {"is_default": True},
                    {"$set": {"is_default": False}}
                )
            
            # Check if mapping already exists
            existing = await self.database.replica_voice_mappings.find_one({"replica_id": replica_id})
            
            mapping_data = {
                "replica_id": replica_id,
                "voice_id": voice_id,
                "name": name or f"Replica {replica_id[:8]}",
                "description": description or "",
                "is_default": is_default,
                "is_active": True,
                "updated_at": datetime.now()
            }
            
            if existing:
                # Update existing
                result = await self.database.replica_voice_mappings.update_one(
                    {"replica_id": replica_id},
                    {"$set": mapping_data}
                )
                return result.modified_count > 0
            else:
                # Create new
                mapping_data["created_at"] = datetime.now()
                await self.database.replica_voice_mappings.insert_one(mapping_data)
                return True
        except Exception as e:
            print(f"❌ Error creating replica mapping: {e}")
            return False
    
    async def set_default_replica(self, replica_id: str) -> bool:
        """Set a replica as the default (unset others)"""
        if self.database is None:
            return False
        
        try:
            # Unset all defaults
            await self.database.replica_voice_mappings.update_many(
                {"is_default": True},
                {"$set": {"is_default": False}}
            )
            
            # Set this one as default
            result = await self.database.replica_voice_mappings.update_one(
                {"replica_id": replica_id, "is_active": True},
                {"$set": {"is_default": True, "updated_at": datetime.now()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Error setting default replica: {e}")
            return False
    
    async def delete_replica_mapping(self, replica_id: str) -> bool:
        """Soft delete a replica mapping (set is_active=False)"""
        if self.database is None:
            return False
        
        try:
            result = await self.database.replica_voice_mappings.update_one(
                {"replica_id": replica_id},
                {"$set": {"is_active": False, "updated_at": datetime.now()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Error deleting replica mapping: {e}")
            return False

    # ============================================================================
    # Admin Users Methods (from hire2inspire_dev_db)
    # ============================================================================
    
    def _get_admin_database(self):
        """Get admin database connection (hire2inspire_dev_db)"""
        if self.client is None:
            return None
        # Use same MongoDB connection but different database
        return self.client["hire2inspire_dev_db"]
    
    async def get_admin_user(self, email: str) -> Optional[Dict[str, Any]]:
        """Get admin user by email from hire2inspire_dev_db.admins collection"""
        admin_db = self._get_admin_database()
        if admin_db is None:
            return None
        
        try:
            admin = await admin_db.admins.find_one({
                "email": email,
                "type": "1"  # Active admin
            })
            if admin:
                # Convert ObjectId to string for JSON serialization
                admin["_id"] = str(admin["_id"])
            return admin
        except Exception as e:
            print(f"❌ Error getting admin user: {e}")
            return None
    
    async def create_admin_user(self, username: str, password_hash: str) -> bool:
        """Create admin user - DEPRECATED: Admins are managed in hire2inspire_dev_db"""
        print("⚠️ create_admin_user is deprecated - admins are managed in hire2inspire_dev_db")
        return False
    
    async def update_admin_last_login(self, email: str) -> bool:
        """Update admin user's last login timestamp (updates updatedAt field)"""
        admin_db = self._get_admin_database()
        if admin_db is None:
            return False
        
        try:
            result = await admin_db.admins.update_one(
                {"email": email},
                {"$set": {"updatedAt": datetime.now()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Error updating admin last login: {e}")
            return False

    # ============================================================================
    # Replica Requests Methods
    # ============================================================================
    
    async def create_replica_request(
        self,
        replica_name: str,
        train_video_url: str,
        submitted_by: str,
        consent_video_url: Optional[str] = None,
        model_name: str = "phoenix-3"
    ) -> Optional[str]:
        """Create a new replica request (pending approval)"""
        if self.database is None:
            return None
        
        try:
            import uuid
            request_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            
            request_data = {
                "request_id": request_id,
                "replica_name": replica_name,
                "train_video_url": train_video_url,
                "consent_video_url": consent_video_url,
                "model_name": model_name,
                "status": "pending",
                "submitted_by": submitted_by,
                "submitted_at": datetime.now(),
                "reviewed_by": None,
                "reviewed_at": None,
                "rejection_reason": None,
                "tavus_replica_id": None,
                "trained_at": None,
                "notes": None
            }
            
            await self.database.replica_requests.insert_one(request_data)
            print(f"✅ Created replica request: {request_id}")
            return request_id
        except Exception as e:
            print(f"❌ Error creating replica request: {e}")
            return None
    
    async def get_replica_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get replica request by ID"""
        if self.database is None:
            return None
        
        try:
            request = await self.database.replica_requests.find_one({"request_id": request_id})
            if request:
                request.pop('_id', None)
            return request
        except Exception as e:
            print(f"❌ Error getting replica request: {e}")
            return None
    
    async def list_replica_requests(
        self,
        status: Optional[str] = None,
        submitted_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List replica requests with optional status and submitted_by filter"""
        if self.database is None:
            return []
        
        try:
            query = {}
            if status:
                query["status"] = status
            if submitted_by:
                query["submitted_by"] = submitted_by
            
            requests = []
            cursor = self.database.replica_requests.find(query).sort(
                "submitted_at", -1
            ).limit(limit).skip(offset)
            
            async for request in cursor:
                request.pop('_id', None)
                requests.append(request)
            
            return requests
        except Exception as e:
            print(f"❌ Error listing replica requests: {e}")
            return []
    
    async def approve_replica_request(
        self,
        request_id: str,
        admin_username: str
    ) -> bool:
        """Approve a replica request"""
        if self.database is None:
            return False
        
        try:
            result = await self.database.replica_requests.update_one(
                {"request_id": request_id},
                {
                    "$set": {
                        "status": "approved",
                        "reviewed_by": admin_username,
                        "reviewed_at": datetime.now()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Error approving replica request: {e}")
            return False
    
    async def reject_replica_request(
        self,
        request_id: str,
        admin_username: str,
        reason: Optional[str] = None
    ) -> bool:
        """Reject a replica request"""
        if self.database is None:
            return False
        
        try:
            result = await self.database.replica_requests.update_one(
                {"request_id": request_id},
                {
                    "$set": {
                        "status": "rejected",
                        "reviewed_by": admin_username,
                        "reviewed_at": datetime.now(),
                        "rejection_reason": reason or "Rejected by admin"
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Error rejecting replica request: {e}")
            return False
    
    async def start_replica_training(
        self,
        request_id: str,
        tavus_replica_id: str
    ) -> bool:
        """Mark replica request as training started"""
        if self.database is None:
            return False
        
        try:
            result = await self.database.replica_requests.update_one(
                {"request_id": request_id},
                {
                    "$set": {
                        "status": "training",
                        "tavus_replica_id": tavus_replica_id,
                        "trained_at": datetime.now()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Error starting replica training: {e}")
            return False



    async def update_replica_request_status(
        self,
        request_id: str,
        status: str,
        tavus_status: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update replica request status (used for syncing with Tavus)"""
        if self.database is None:
            return False
        
        try:
            update_data = {
                "status": status,
                "last_synced_at": datetime.now()
            }
            
            if tavus_status:
                update_data["tavus_status"] = tavus_status
            
            if error_message:
                update_data["error_message"] = error_message
            
            # Set completed_at if status is completed
            if status == "completed":
                update_data["completed_at"] = datetime.now()
            
            result = await self.database.replica_requests.update_one(
                {"request_id": request_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Error updating replica request status: {e}")
            return False
    
    # ============================================================================
    # User Integrations (API Keys) Management
    # ============================================================================
    
    async def set_user_api_key(
        self,
        user_id: str,
        provider: str,
        api_key: str,
        is_active: bool = True,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store encrypted API key for a user with optional configuration
        
        Args:
            user_id: User identifier
            provider: Provider name (e.g., "openai", "tavus", "cartesia")
            api_key: API key to encrypt and store
            is_active: Whether the key is active
            config: Optional provider-specific configuration (e.g., default_replica_id, default_voice_id)
        
        Returns:
            True if successful, False otherwise
        """
        if self.database is None:
            print("⚠️ Database not connected - cannot store API key")
            return False
        
        try:
            from services.encryption_service import encryption_service
            
            # Encrypt the API key
            encrypted_key = encryption_service.encrypt(api_key)
            
            # Build update document
            update_doc = {
                "api_key_encrypted": encrypted_key,
                "is_active": is_active,
                "updated_at": datetime.now()
            }
            
            # Add config if provided (merge with existing config if present)
            if config is not None:
                update_doc["config"] = config
            
            # Store in database
            await self.database.user_integrations.update_one(
                {
                    "user_id": user_id,
                    "provider": provider
                },
                {
                    "$set": update_doc,
                    "$setOnInsert": {
                        "user_id": user_id,
                        "provider": provider,
                        "created_at": datetime.now()
                    }
                },
                upsert=True
            )
            
            print(f"✅ Stored API key for user {user_id}, provider {provider}")
            if config:
                print(f"   Config: {config}")
            return True
        except Exception as e:
            print(f"❌ Error storing API key: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def update_user_integration_config(
        self,
        user_id: str,
        provider: str,
        config: Dict[str, Any]
    ) -> bool:
        """
        Update configuration for a user's integration (without changing API key)
        
        Args:
            user_id: User identifier
            provider: Provider name (e.g., "tavus", "cartesia")
            config: Configuration to update (will be merged with existing config)
        
        Returns:
            True if successful, False otherwise
        """
        if self.database is None:
            print("⚠️ Database not connected - cannot update config")
            return False
        
        try:
            # Get existing integration
            integration = await self.database.user_integrations.find_one(
                {
                    "user_id": user_id,
                    "provider": provider
                }
            )
            
            if not integration:
                print(f"⚠️ Integration not found for user {user_id}, provider {provider}")
                return False
            
            # Merge with existing config
            existing_config = integration.get("config", {})
            merged_config = {**existing_config, **config}
            
            # Update config
            await self.database.user_integrations.update_one(
                {
                    "user_id": user_id,
                    "provider": provider
                },
                {
                    "$set": {
                        "config": merged_config,
                        "updated_at": datetime.now()
                    }
                }
            )
            
            print(f"✅ Updated config for user {user_id}, provider {provider}")
            print(f"   Config: {merged_config}")
            return True
        except Exception as e:
            print(f"❌ Error updating config: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_user_integration_config(
        self,
        user_id: str,
        provider: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a user's integration
        
        Args:
            user_id: User identifier
            provider: Provider name
        
        Returns:
            Configuration dict or None if not found
        """
        if self.database is None:
            return None
        
        try:
            integration = await self.database.user_integrations.find_one(
                {
                    "user_id": user_id,
                    "provider": provider,
                    "is_active": True
                }
            )
            
            if not integration:
                return None
            
            return integration.get("config", {})
        except Exception as e:
            print(f"❌ Error getting config: {e}")
            return None
    
    async def get_user_api_key(
        self,
        user_id: str,
        provider: str
    ) -> Optional[str]:
        """
        Retrieve and decrypt API key for a user
        
        Args:
            user_id: User identifier
            provider: Provider name (e.g., "openai", "tavus", "cartesia")
        
        Returns:
            Decrypted API key or None if not found/inactive
        """
        if self.database is None:
            return None
        
        try:
            from services.encryption_service import encryption_service
            
            # Find the integration
            integration = await self.database.user_integrations.find_one(
                {
                    "user_id": user_id,
                    "provider": provider,
                    "is_active": True
                }
            )
            
            if not integration:
                return None
            
            # Decrypt the API key
            encrypted_key = integration.get("api_key_encrypted")
            if not encrypted_key:
                return None
            
            decrypted_key = encryption_service.decrypt(encrypted_key)
            return decrypted_key
        except Exception as e:
            print(f"❌ Error retrieving API key: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def delete_user_api_key(
        self,
        user_id: str,
        provider: str
    ) -> bool:
        """
        Delete (deactivate) API key for a user
        
        Args:
            user_id: User identifier
            provider: Provider name
        
        Returns:
            True if successful, False otherwise
        """
        if self.database is None:
            return False
        
        try:
            result = await self.database.user_integrations.update_one(
                {
                    "user_id": user_id,
                    "provider": provider
                },
                {
                    "$set": {
                        "is_active": False,
                        "deleted_at": datetime.now()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"❌ Error deleting API key: {e}")
            return False
    
    async def get_user_integrations(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all active integrations for a user
        
        Args:
            user_id: User identifier
        
        Returns:
            List of integration dictionaries (without decrypted keys, but includes config)
        """
        if self.database is None:
            return []
        
        try:
            integrations = await self.database.user_integrations.find(
                {
                    "user_id": user_id,
                    "is_active": True
                }
            ).to_list(length=100)
            
            # Remove encrypted keys and MongoDB _id from response, but keep config
            result = []
            for integration in integrations:
                integration.pop('_id', None)
                integration.pop('api_key_encrypted', None)  # Don't expose encrypted keys
                # Keep config field if present
                result.append(integration)
            
            return result
        except Exception as e:
            print(f"❌ Error retrieving integrations: {e}")
            return []

# Global database instance
db_service = DatabaseService()
