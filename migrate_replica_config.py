#!/usr/bin/env python3
"""
Migration Script: Move replica and voice IDs from environment variables to database

This script:
1. Reads TAVUS_REPLICA_ID and CARTESIA_VOICE_ID from environment variables
2. Creates a default replica-voice mapping in the database
3. Sets it as the default configuration

Run this once after deploying the new database-backed replica config feature.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv()
server_env = Path(__file__).parent / "server" / ".env"
if server_env.exists():
    load_dotenv(server_env)

from web_server.services.database import DatabaseService
from web_server.services.tavus_service import tavus_service
from web_server.services.voice_cloning_service import voice_cloning_service
from loguru import logger

async def migrate_replica_config():
    """Migrate env vars to database"""
    db = DatabaseService()
    
    try:
        # Connect to database
        connected = await db.connect()
        if not connected:
            logger.error("❌ Failed to connect to database")
            return False
        
        # Check if default config already exists
        existing = await db.get_default_replica_config()
        if existing:
            logger.info(f"✅ Default replica config already exists: {existing.get('replica_id')}")
            logger.info("   Skipping migration (config already in database)")
            return True
        
        # Get values from environment
        replica_id = os.getenv("TAVUS_REPLICA_ID")
        voice_id = os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")
        
        if not replica_id:
            logger.warning("⚠️ TAVUS_REPLICA_ID not set in environment - cannot migrate")
            return False
        
        logger.info(f"🔄 Migrating replica config from environment variables...")
        logger.info(f"   Replica ID: {replica_id}")
        logger.info(f"   Voice ID: {voice_id}")
        
        # Validate replica exists in Tavus
        logger.info("🔍 Validating replica in Tavus...")
        replica = await tavus_service.get_replica(replica_id, verbose=False)
        if not replica:
            logger.error(f"❌ Replica not found in Tavus: {replica_id}")
            logger.error("   Please ensure the replica exists before migrating")
            return False
        logger.info(f"✅ Replica validated: {replica.get('replica_name', replica_id)}")
        
        # Validate voice exists in Cartesia
        logger.info("🔍 Validating voice in Cartesia...")
        voice = await voice_cloning_service.get_voice(voice_id)
        if not voice:
            # Try listing all voices
            all_voices = await voice_cloning_service.list_voices()
            voice_found = any(v.get("id") == voice_id for v in all_voices)
            if not voice_found:
                logger.warning(f"⚠️ Voice not found in Cartesia: {voice_id}")
                logger.warning("   Continuing anyway (may be a valid pre-built voice)")
            else:
                logger.info(f"✅ Voice validated: {voice_id}")
        else:
            logger.info(f"✅ Voice validated: {voice.get('name', voice_id)}")
        
        # Create default mapping
        logger.info("💾 Creating default replica-voice mapping in database...")
        success = await db.create_replica_mapping(
            replica_id=replica_id,
            voice_id=voice_id,
            name="Default Replica (Migrated)",
            description="Migrated from environment variables",
            is_default=True
        )
        
        if success:
            logger.info("✅ Migration completed successfully!")
            logger.info(f"   Default replica: {replica_id}")
            logger.info(f"   Mapped voice: {voice_id}")
            logger.info("")
            logger.info("📝 Next steps:")
            logger.info("   1. You can now manage replica-voice mappings via the dashboard")
            logger.info("   2. Environment variables will be used as fallback if database lookup fails")
            logger.info("   3. Consider removing TAVUS_REPLICA_ID and CARTESIA_VOICE_ID from .env files")
            return True
        else:
            logger.error("❌ Failed to create replica mapping")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await db.disconnect()

if __name__ == "__main__":
    logger.info("🚀 Starting replica config migration...")
    success = asyncio.run(migrate_replica_config())
    sys.exit(0 if success else 1)
