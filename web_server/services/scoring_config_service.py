"""
Scoring Configuration Service

Manages scoring configurations in MongoDB with support for different difficulty levels.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class ScoringConfigService:
    """Service for managing scoring configurations in MongoDB"""
    
    def __init__(self, database=None):
        """Initialize scoring config service"""
        self.database = database
        self.collection_name = "scoring_configs"
        logger.info("ScoringConfigService initialized")
    
    async def initialize_default_configs(self):
        """Create default scoring configurations if they don't exist"""
        if self.database is None:
            logger.warning("Database not available - skipping default config initialization")
            return
        
        try:
            collection = self.database[self.collection_name]
            
            # Check if configs already exist
            existing_count = await collection.count_documents({})
            if existing_count > 0:
                logger.info(f"Found {existing_count} existing scoring configs")
                return
            
            # Create default configurations
            default_configs = self._get_default_configs()
            
            result = await collection.insert_many(default_configs)
            logger.info(f"✅ Created {len(result.inserted_ids)} default scoring configurations")
            
            # Create indexes
            await collection.create_index("config_id", unique=True)
            await collection.create_index("level")
            await collection.create_index("is_default")
            logger.info("✅ Created indexes for scoring_configs collection")
            
        except Exception as e:
            logger.error(f"Error initializing default configs: {e}")
    
    def _get_default_configs(self) -> List[Dict[str, Any]]:
        """Get the 3 default scoring configurations"""
        base_timestamp = datetime.now()
        
        return [
            # EASY Configuration - Lenient scoring
            {
                "config_id": "easy_001",
                "level": "easy",
                "name": "Easy - Lenient Scoring",
                "description": "Lenient scoring suitable for junior positions or entry-level interviews",
                "created_by": "system",
                "created_at": base_timestamp,
                "updated_at": base_timestamp,
                "is_active": True,
                "is_default": False,
                
                # Scoring parameters
                "strictness": "lenient",
                "strictness_multiplier": 1.2,  # 20% boost
                
                "weights": {
                    "correctness": 0.25,
                    "terminology": 0.15,
                    "confidence": 0.20,  # More weight on communication
                    "experience_relevance": 0.20,
                    "problem_solving": 0.20
                },
                
                "score_categories": {
                    "excellent": 80,  # Lower thresholds
                    "good": 65,
                    "average": 50,
                    "below_average": 35,
                    "poor": 0
                },
                
                "minimum_passing_score": 50,
                
                "recommendation_thresholds": {
                    "strong_yes": 75,
                    "yes": 60,
                    "maybe": 45,
                    "no": 30,
                    "strong_no": 0
                },
                
                "evaluation_focus": {
                    "technical_depth": "basic",
                    "experience_required": "0-2 years",
                    "communication_weight": "high",
                    "problem_solving_complexity": "simple"
                }
            },
            
            # INTERMEDIATE Configuration - Balanced scoring (DEFAULT)
            {
                "config_id": "intermediate_001",
                "level": "intermediate",
                "name": "Intermediate - Balanced Scoring",
                "description": "Balanced scoring for mid-level positions with moderate expectations",
                "created_by": "system",
                "created_at": base_timestamp,
                "updated_at": base_timestamp,
                "is_active": True,
                "is_default": True,  # This is the default
                
                # Scoring parameters
                "strictness": "moderate",
                "strictness_multiplier": 1.0,  # No adjustment
                
                "weights": {
                    "correctness": 0.30,
                    "terminology": 0.20,
                    "confidence": 0.15,
                    "experience_relevance": 0.20,
                    "problem_solving": 0.15
                },
                
                "score_categories": {
                    "excellent": 85,
                    "good": 70,
                    "average": 55,
                    "below_average": 40,
                    "poor": 0
                },
                
                "minimum_passing_score": 60,
                
                "recommendation_thresholds": {
                    "strong_yes": 80,
                    "yes": 65,
                    "maybe": 50,
                    "no": 35,
                    "strong_no": 0
                },
                
                "evaluation_focus": {
                    "technical_depth": "intermediate",
                    "experience_required": "2-5 years",
                    "communication_weight": "medium",
                    "problem_solving_complexity": "moderate"
                }
            },
            
            # STRICT Configuration - Rigorous scoring
            {
                "config_id": "strict_001",
                "level": "strict",
                "name": "Strict - Rigorous Scoring",
                "description": "Strict scoring for senior positions requiring high technical expertise",
                "created_by": "system",
                "created_at": base_timestamp,
                "updated_at": base_timestamp,
                "is_active": True,
                "is_default": False,
                
                # Scoring parameters
                "strictness": "very_strict",
                "strictness_multiplier": 0.75,  # 25% penalty
                
                "weights": {
                    "correctness": 0.35,  # Higher technical weight
                    "terminology": 0.25,
                    "confidence": 0.10,  # Less weight on communication
                    "experience_relevance": 0.15,
                    "problem_solving": 0.15
                },
                
                "score_categories": {
                    "excellent": 90,  # Higher thresholds
                    "good": 75,
                    "average": 60,
                    "below_average": 45,
                    "poor": 0
                },
                
                "minimum_passing_score": 70,
                
                "recommendation_thresholds": {
                    "strong_yes": 85,
                    "yes": 70,
                    "maybe": 55,
                    "no": 40,
                    "strong_no": 0
                },
                
                "evaluation_focus": {
                    "technical_depth": "advanced",
                    "experience_required": "5+ years",
                    "communication_weight": "low",
                    "problem_solving_complexity": "complex"
                }
            }
        ]
    
    async def get_config_by_level(self, level: str) -> Optional[Dict[str, Any]]:
        """Get scoring config by level (easy/intermediate/strict)"""
        if self.database is None:
            logger.warning("Database not available")
            return None
        
        try:
            collection = self.database[self.collection_name]
            config = await collection.find_one({"level": level, "is_active": True})
            
            if config:
                config.pop('_id', None)
                logger.info(f"Retrieved '{level}' scoring config")
                return config
            else:
                logger.warning(f"No config found for level: {level}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving config by level: {e}")
            return None
    
    async def get_config_by_id(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Get scoring config by ID"""
        if self.database is None:
            logger.warning("Database not available")
            return None
        
        try:
            collection = self.database[self.collection_name]
            config = await collection.find_one({"config_id": config_id})
            
            if config:
                config.pop('_id', None)
                return config
            return None
                
        except Exception as e:
            logger.error(f"Error retrieving config by ID: {e}")
            return None
    
    async def get_default_config(self) -> Optional[Dict[str, Any]]:
        """Get the default scoring configuration"""
        if self.database is None:
            logger.warning("Database not available")
            return None
        
        try:
            collection = self.database[self.collection_name]
            config = await collection.find_one({"is_default": True, "is_active": True})
            
            if config:
                config.pop('_id', None)
                logger.info(f"Retrieved default config: {config.get('level', 'unknown')}")
                return config
            else:
                # Fallback to intermediate if no default set
                logger.warning("No default config found, using intermediate")
                return await self.get_config_by_level("intermediate")
                
        except Exception as e:
            logger.error(f"Error retrieving default config: {e}")
            return None
    
    async def get_all_configs(self) -> List[Dict[str, Any]]:
        """Get all active scoring configurations"""
        if self.database is None:
            logger.warning("Database not available")
            return []
        
        try:
            collection = self.database[self.collection_name]
            cursor = collection.find({"is_active": True}).sort("level", 1)
            
            configs = []
            async for config in cursor:
                config.pop('_id', None)
                configs.append(config)
            
            logger.info(f"Retrieved {len(configs)} active configs")
            return configs
                
        except Exception as e:
            logger.error(f"Error retrieving all configs: {e}")
            return []
    
    async def reset_to_default(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Reset a scoring configuration to its factory default values"""
        if self.database is None:
            logger.warning("Database not available")
            return None
        
        try:
            # Get current config to determine level
            current_config = await self.get_config_by_id(config_id)
            if not current_config:
                logger.warning(f"Config not found: {config_id}")
                return None
            
            level = current_config.get("level")
            
            # Get the default config for this level from the factory defaults
            default_configs = self._get_default_configs()
            default_config = next((c for c in default_configs if c["level"] == level), None)
            
            if not default_config:
                logger.error(f"No factory default found for level: {level}")
                return None
            
            # Update the config in DB with default weights (preserve config_id and timestamps)
            collection = self.database[self.collection_name]
            result = await collection.update_one(
                {"config_id": config_id},
                {
                    "$set": {
                        "weights": default_config["weights"],
                        "updated_at": datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Reset config '{config_id}' to factory defaults")
                return await self.get_config_by_id(config_id)
            else:
                logger.warning(f"No changes made to config: {config_id}")
                return current_config
                
        except Exception as e:
            logger.error(f"Error resetting config to default: {e}")
            return None
    
    async def update_config(self, config_id: str, updates: Dict[str, Any]) -> bool:
        """Update a scoring configuration"""
        if self.database is None:
            logger.warning("Database not available")
            return False
        
        try:
            collection = self.database[self.collection_name]
            
            # Add updated_at timestamp
            updates["updated_at"] = datetime.now()
            
            result = await collection.update_one(
                {"config_id": config_id},
                {"$set": updates}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Updated config: {config_id}")
                return True
            else:
                logger.warning(f"No config updated for ID: {config_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return False
    
    async def create_custom_config(self, config_data: Dict[str, Any]) -> Optional[str]:
        """Create a new custom scoring configuration"""
        if self.database is None:
            logger.warning("Database not available")
            return None
        
        try:
            collection = self.database[self.collection_name]
            
            # Add timestamps
            config_data["created_at"] = datetime.now()
            config_data["updated_at"] = datetime.now()
            
            # Ensure required fields
            if "config_id" not in config_data:
                config_data["config_id"] = f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if "is_active" not in config_data:
                config_data["is_active"] = True
            
            if "is_default" not in config_data:
                config_data["is_default"] = False
            
            result = await collection.insert_one(config_data)
            logger.info(f"✅ Created custom config: {config_data['config_id']}")
            return config_data["config_id"]
                
        except Exception as e:
            logger.error(f"Error creating custom config: {e}")
            return None

