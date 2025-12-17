"""
Authentication Service - JWT Token Verification
Verifies tokens from human2intelligence.com

NOTE:
- This service verifies HS256 JWTs using Python stdlib (no external PyJWT dependency).
- It validates token structure, algorithm, signature, and exp (if present).
"""

import os
import json
import time
import hmac
import hashlib
import base64
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class AuthService:
    """Service for JWT token verification"""

    def __init__(self):
        # Load secrets from environment variables
        self.access_token_secret = os.getenv(
            "ACCESS_TOKEN_SECRET",
            "21b7643dbbc071e94875c707db9cddc23e41d1422d816e592140fa39a32627b5",
        )
        self.refresh_token_secret = os.getenv(
            "REFRESH_TOKEN_SECRET",
            "766ae15d98eba46726a0c5fbbf0fb54ad94e32543171419671c0f6ef6440b826",
        )

    @staticmethod
    def _b64url_decode(data: str) -> bytes:
        padding = '=' * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)

    @staticmethod
    def _b64url_encode(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    def _decode_and_verify_hs256_jwt(self, token: str, secret: str) -> Dict[str, Any]:
        """Verify an HS256 JWT (compatible with jsonwebtoken HS256).

        Validates:
        - token structure header.payload.signature
        - header.alg == HS256
        - signature matches HMAC-SHA256(secret, header.payload)
        - exp (if present) is not expired
        """
        if not token or "." not in token:
            raise ValueError("Malformed token")

        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Malformed token")

        header_b64, payload_b64, signature_b64 = parts

        try:
            header = json.loads(self._b64url_decode(header_b64).decode("utf-8"))
        except Exception:
            raise ValueError("Invalid token header")

        if header.get("alg") != "HS256":
            raise ValueError("Unsupported token algorithm")

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(
            (secret or "").encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        expected_sig_b64 = self._b64url_encode(expected_sig)

        if not hmac.compare_digest(expected_sig_b64, signature_b64):
            raise ValueError("Invalid token signature")

        try:
            payload = json.loads(self._b64url_decode(payload_b64).decode("utf-8"))
        except Exception:
            raise ValueError("Invalid token payload")

        exp = payload.get("exp")
        if exp is not None:
            try:
                exp_int = int(exp)
            except Exception:
                raise ValueError("Invalid exp claim")
            if int(time.time()) >= exp_int:
                raise ValueError("Token has expired")

        return payload

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify access token from human2intelligence.com."""
        try:
            payload = self._decode_and_verify_hs256_jwt(token, self.access_token_secret)

            # Extract userId and dataModel
            user_id = payload.get("userId") or payload.get("sub") or payload.get("aud")
            data_model = payload.get("dataModel") or payload.get("data_model")

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing userId",
                )

            return {
                "userId": user_id,
                "dataModel": data_model or "employers",
                "payload": payload,
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}",
            )

    def extract_token_from_request(self, request) -> Optional[str]:
        """Extract JWT token from request headers/cookies/query param."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]

        token_param = request.query_params.get("token")
        if token_param:
            return token_param

        access_token = request.cookies.get("accessToken") or request.cookies.get("access_token")
        if access_token:
            return access_token

        return None


# Singleton instance
auth_service = AuthService()
