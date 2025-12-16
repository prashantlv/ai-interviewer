"""
Authentication Service - JWT Token Verification
Verifies tokens from human2intelligence.com
"""

import jwt
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from datetime import datetime

class AuthService:
    """Service for JWT token verification"""
    
    def __init__(self):
        # Load secrets from environment variables
        self.access_token_secret = os.getenv(
            "ACCESS_TOKEN_SECRET",
            "21b7643dbbc071e94875c707db9cddc23e41d1422d816e592140fa39a32627b5"
        )
        self.refresh_token_secret = os.getenv(
            "REFRESH_TOKEN_SECRET",
            "766ae15d98eba46726a0c5fbbf0fb54ad94e32543171419671c0f6ef6440b826"
        )
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """
        Verify access token from human2intelligence.com
        
        Args:
            token: JWT access token string
            
        Returns:
            Decoded token payload containing userId and dataModel
            
        Raises:
            HTTPException: If token is invalid, expired, or malformed
        """
        try:
            # Decode and verify token
            payload = jwt.decode(
                token,
                self.access_token_secret,
                algorithms=["HS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": False,  # Audience is optional in JWT spec
                }
            )
            
            # Extract userId and dataModel
            # The token structure is: { userId: '...', dataModel: '...' }
            # userId might be in 'userId', 'sub', or 'aud' fields
            user_id = payload.get("userId") or payload.get("sub") or payload.get("aud")
            data_model = payload.get("dataModel") or payload.get("data_model")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing userId"
                )
            
            return {
                "userId": user_id,
                "dataModel": data_model or "employers",  # Default to employers
                "payload": payload
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}"
            )
    
    def extract_token_from_request(self, request) -> Optional[str]:
        """
        Extract JWT token from request headers or cookies
        
        Checks:
        1. Authorization header: "Bearer <token>"
        2. Query parameter: "token"
        3. Cookie: "accessToken" or "access_token"
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Token string or None if not found
        """
        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        
        # Check query parameter (for direct links)
        token_param = request.query_params.get("token")
        if token_param:
            return token_param
        
        # Check cookies
        access_token = request.cookies.get("accessToken") or request.cookies.get("access_token")
        if access_token:
            return access_token
        
        return None

# Singleton instance
auth_service = AuthService()

