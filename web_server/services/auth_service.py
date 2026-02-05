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
import re
import logging
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
            _log = logging.getLogger(__name__)
            
            # DEBUG: Log token info
            _log.info("=" * 60)
            _log.info("🔍 DEBUG: JWT Token Verification")
            _log.info("=" * 60)
            _log.info(f"Token length: {len(token)}")
            _log.info(f"Token preview: {token[:50]}...")
            
            payload = self._decode_and_verify_hs256_jwt(token, self.access_token_secret)
            
            # DEBUG: Log full payload
            _log.info("Full JWT Payload:")
            _log.info(json.dumps(payload, indent=2, default=str))
            _log.info("-" * 60)
            _log.info("All claims in payload:")
            for key, value in payload.items():
                _log.info(f"  {key}: {value} (type: {type(value).__name__})")
            _log.info("-" * 60)

            # Extract userId: check standard claims first, then fallback to "aud" ONLY if it looks like a user ID.
            # NOTE: "aud" is normally "audience" (who token is FOR), but in this system it appears to be the user ID.
            # We check standard claims first, then use "aud" as last resort if it looks like a MongoDB ObjectId (24 hex chars).
            _log.info("🔍 Extracting userId from claims...")
            
            user_id = None
            checked_claims = []
            
            # Check standard claims
            for claim_name in ["userId", "user_id", "sub", "id"]:
                value = payload.get(claim_name)
                checked_claims.append(f"{claim_name}={value}")
                if value:
                    user_id = value
                    _log.info(f"✅ Found userId in '{claim_name}': {value}")
                    break
            
            # Check nested data claims
            if not user_id and "data" in payload:
                data_obj = payload.get("data") or {}
                if isinstance(data_obj, dict):
                    for claim_name in ["userId", "user_id", "id"]:
                        value = data_obj.get(claim_name)
                        checked_claims.append(f"data.{claim_name}={value}")
                        if value:
                            user_id = value
                            _log.info(f"✅ Found userId in 'data.{claim_name}': {value}")
                            break
            
            # Fallback: If no standard user ID found, check if "aud" looks like a user ID (MongoDB ObjectId = 24 hex chars)
            if not user_id:
                aud_value = payload.get("aud")
                checked_claims.append(f"aud={aud_value}")
                if aud_value:
                    aud_str = str(aud_value).strip()
                    _log.info(f"🔍 Checking 'aud' claim: {aud_str}")
                    # MongoDB ObjectId is 24 hex characters - if aud matches this pattern, use it as user_id
                    if re.match(r'^[0-9a-fA-F]{24}$', aud_str):
                        user_id = aud_str
                        _log.warning("⚠️ Using 'aud' claim as userId (no standard user ID found)")
                        _log.warning(f"   aud value: {aud_str}")
                    else:
                        _log.warning(f"⚠️ 'aud' does not match MongoDB ObjectId pattern (24 hex chars)")
                        _log.warning(f"   aud value: {aud_str} (length: {len(aud_str)})")
            
            _log.info(f"Checked claims: {', '.join(checked_claims)}")
            
            data_model = payload.get("dataModel") or payload.get("data_model") or payload.get("model")

            if not user_id:
                _log.error("❌ No userId found in any checked claims")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing userId (expected claim: userId, user_id, sub, or id)",
                )

            # Normalize to string (e.g. if issuer sends id as number)
            user_id = str(user_id).strip()
            if not user_id:
                _log.error("❌ userId is empty after normalization")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token userId is empty",
                )

            # Log which userId we use (masked) so we can verify per-user isolation
            _mask = (user_id[:4] + "…") if len(user_id) > 4 else user_id
            _log.info(f"✅ Final userId: {_mask} (full length: {len(user_id)})")
            _log.info(f"   dataModel: {data_model}")
            _log.info("=" * 60)

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
