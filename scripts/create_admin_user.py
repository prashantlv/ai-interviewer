#!/usr/bin/env python3
"""
Script to create an admin user for the admin panel
Usage: python scripts/create_admin_user.py --username admin --password your_password
"""

import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path to import web_server modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "web_server"))

# Try to load dotenv if available (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
    server_env = project_root / "server" / ".env"
    if server_env.exists():
        load_dotenv(server_env)
except ImportError:
    # dotenv not available - will use environment variables directly
    pass

# Check if dependencies are available
try:
    from web_server.services.admin_auth_service import admin_auth_service
    from web_server.services.database import db_service
except (ImportError, ModuleNotFoundError) as e:
    error_msg = str(e)
    print(f"❌ Import error: {error_msg}")
    print("")
    print("💡 This script needs to be run with the project dependencies installed.")
    print("")
    print("   Options:")
    print("   1. Activate virtual environment:")
    print("      source venv/bin/activate  # or your venv path")
    print("      pip install -r web_server/requirements.txt")
    print("")
    print("   2. Run from Docker container:")
    print("      docker-compose exec web-server python3 /app/scripts/create_admin_user.py --username admin --password your_password")
    print("")
    print("   3. Install dependencies directly:")
    print("      pip install -r web_server/requirements.txt")
    print("")
    if "motor" in error_msg.lower():
        print("   ⚠️  Missing 'motor' package (MongoDB driver)")
    elif "bcrypt" in error_msg.lower():
        print("   ⚠️  Missing 'bcrypt' package (password hashing)")
    sys.exit(1)


async def create_admin(username: str, password: str):
    """Create an admin user"""
    print(f"🔧 Creating admin user: {username}")
    
    # Connect to database
    connected = await db_service.connect()
    if not connected:
        print("❌ Failed to connect to database")
        return False
    
    try:
        # Create admin user
        success = await admin_auth_service.create_admin(username, password)
        if success:
            print(f"✅ Admin user '{username}' created successfully!")
            print(f"   You can now login at /admin/login")
            return True
        else:
            print(f"❌ Failed to create admin user. It may already exist.")
            return False
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False
    finally:
        await db_service.disconnect()


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create an admin user for the admin panel")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--password", required=True, help="Admin password")
    
    args = parser.parse_args()
    
    if len(args.password) < 6:
        print("❌ Password must be at least 6 characters long")
        sys.exit(1)
    
    # Run async function
    success = asyncio.run(create_admin(args.username, args.password))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
