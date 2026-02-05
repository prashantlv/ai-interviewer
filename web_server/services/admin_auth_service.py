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
    
    async def authenticate_admin(self, email: str, password: str, db_service_instance=None) -> Optional[Dict[str, Any]]:
        """Authenticate admin user with email and password from hire2inspire_dev_db.admins"""
        try:
            # Use provided db_service or fall back to global one
            db = db_service_instance or db_service
            
            admin = await db.get_admin_user(email)
            if not admin:
                print(f"❌ Admin user '{email}' not found in database")
                return None
            
            password_hash = admin.get("password", "")
            if not password_hash:
                print(f"❌ Admin user '{email}' has no password field")
                return None
            
            print(f"🔍 Verifying password for admin '{email}'...")
            is_valid = self.verify_password(password, password_hash)
            if not is_valid:
                print(f"❌ Password verification failed for admin '{email}'")
                print(f"   Password hash in DB: {password_hash[:20]}...")
                return None
            
            print(f"✅ Password verified successfully for admin '{email}'")
            
            # Update last login (updates updatedAt field)
            await db.update_admin_last_login(email)
            
            return {
                "email": admin.get("email"),
                "name": admin.get("name"),
                "created_at": admin.get("createdAt"),
                "updated_at": admin.get("updatedAt")
            }
        except Exception as e:
            print(f"❌ Error authenticating admin: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def create_admin(self, email: str, password: str) -> bool:
        """Create a new admin user - DEPRECATED: Admins are managed in hire2inspire_dev_db"""
        print("⚠️ create_admin is deprecated - admins are managed in hire2inspire_dev_db")
        return False


# Singleton instance
admin_auth_service = AdminAuthService()
