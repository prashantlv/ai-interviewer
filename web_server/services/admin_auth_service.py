"""
Admin Authentication Service
Handles admin login with username/password (separate from JWT auth)
"""

import bcrypt
from typing import Optional, Dict, Any

# Import database service - handle both relative and absolute imports
# When imported from script (web_server in path): use services
# When imported from main.py (web_server in path): use services
# When imported with project root in path: use web_server.services
try:
    from services.database import db_service
except ImportError:
    try:
        from web_server.services.database import db_service
    except ImportError:
        raise ImportError(
            "Could not import database service. "
            "Make sure you're running with the correct Python path setup."
        )


class AdminAuthService:
    """Service for admin authentication (username/password)"""
    
    def __init__(self):
        pass
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against a hash"""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception as e:
            print(f"❌ Error verifying password: {e}")
            return False
    
    async def authenticate_admin(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate admin user with username and password"""
        try:
            admin = await db_service.get_admin_user(username)
            if not admin:
                return None
            
            if not self.verify_password(password, admin.get("password_hash", "")):
                return None
            
            # Update last login
            await db_service.update_admin_last_login(username)
            
            return {
                "username": admin.get("username"),
                "created_at": admin.get("created_at"),
                "last_login": admin.get("last_login")
            }
        except Exception as e:
            print(f"❌ Error authenticating admin: {e}")
            return None
    
    async def create_admin(self, username: str, password: str) -> bool:
        """Create a new admin user"""
        try:
            password_hash = self.hash_password(password)
            return await db_service.create_admin_user(username, password_hash)
        except Exception as e:
            print(f"❌ Error creating admin: {e}")
            return False


# Singleton instance
admin_auth_service = AdminAuthService()
