"""
Hire2Inspire API Integration Service

Handles authentication and data fetching from Hire2Inspire platform
"""

import httpx
import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class Hire2InspireService:
    """Service to interact with Hire2Inspire API"""
    
    def __init__(self):
        self.base_url = "https://api.hire2inspire.com/api"
        self.email = os.getenv("H2I_EMAIL", "hire2inspireh2i@gmail.com")
        self.password = os.getenv("H2I_PASSWORD", "Sant@1506")
        # Use pre-existing token if available (for testing/development)
        self.token: Optional[str] = os.getenv("H2I_ACCESS_TOKEN")
        self.token_expiry: Optional[datetime] = None
        if self.token:
            # Token valid for 24 hours from now if manually provided
            # Note: If token is provided via env var, we'll use it even if "expired"
            # The API will reject it if truly invalid
            self.token_expiry = datetime.now() + timedelta(hours=24)
            logger.info("✅ Using pre-configured access token from H2I_ACCESS_TOKEN")
        else:
            logger.warning("⚠️ H2I_ACCESS_TOKEN not set - will attempt login with credentials")
        
    async def _ensure_token(self) -> str:
        """Ensure we have a valid token, refresh if needed"""
        # If we have a pre-configured token from env var, prefer it (don't try to login)
        env_token = os.getenv("H2I_ACCESS_TOKEN")
        if env_token:
            logger.info("✅ Using token from H2I_ACCESS_TOKEN environment variable")
            self.token = env_token
            self.token_expiry = datetime.now() + timedelta(hours=24)  # Assume valid for 24h
            return self.token
        
        # If we have a token and it's not expired, use it
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            logger.debug("✅ Using existing valid token")
            return self.token
        
        # If token exists but expired, try to login
        if self.token:
            logger.warning("⚠️ Token expired, attempting to login...")
        else:
            logger.info("🔑 No token found, attempting to login...")
            
        # Login to get new token
        try:
            await self._login()
            return self.token
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            # If login fails but we have a token (even if expired), try using it anyway
            if self.token:
                logger.warning(f"⚠️ Login failed, but attempting to use existing token anyway")
                return self.token
            raise
    
    async def _login(self):
        """Login to Hire2Inspire and get access token"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/agency/login",
                    json={
                        "email": self.email,
                        "password": self.password,
                        "system": "Linux",
                        "browser_type": "Chrome",
                        "login_time": datetime.now().isoformat()
                    },
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    }
                )
                
                data = response.json()
                
                # Check if already logged in
                if data.get("error") and "already logged In" in data.get("message", ""):
                    logger.warning("⚠️ Already logged in - need to logout first")
                    # Try to logout and login again
                    await self._logout()
                    # Wait for logout to complete on server side
                    await asyncio.sleep(3)
                    logger.info("⏳ Waited 3s for logout to complete, retrying login...")
                    # Retry login
                    response = await client.post(
                        f"{self.base_url}/agency/login",
                        json={
                            "email": self.email,
                            "password": self.password,
                            "system": "Linux",
                            "browser_type": "Chrome",
                            "login_time": datetime.now().isoformat()
                        },
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json"
                        }
                    )
                    data = response.json()
                
                response.raise_for_status()
                
                # Extract token from response
                if "data" in data and "accessToken" in data["data"]:
                    self.token = data["data"]["accessToken"]
                    # Token typically expires in 24 hours
                    self.token_expiry = datetime.now() + timedelta(hours=23)
                    logger.info("✅ Logged in to Hire2Inspire successfully")
                else:
                    logger.error("❌ No token in response")
                    raise Exception("Failed to get access token")
                    
        except Exception as e:
            logger.error(f"❌ Hire2Inspire login failed: {e}")
            raise
    
    async def _logout(self):
        """Logout from Hire2Inspire - logs out from ALL sessions"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(
                    f"{self.base_url}/agency/update-logout",
                    json={"corporate_email": self.email},
                    headers={
                        "Accept": "application/json, text/plain, */*",
                        "Content-Type": "application/json",
                        "Referer": "https://app.hire2inspire.com/",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
                    }
                )
                if response.status_code < 400:
                    logger.info("✅ Logged out from all sessions successfully")
                else:
                    logger.warning(f"⚠️ Logout returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Logout failed: {e}")
    
    async def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all job descriptions for the agency"""
        try:
            token = await self._ensure_token()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/shortlist_candidate/get_jd_data_py",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract jobs from response
                if "data" in data:
                    jobs = data["data"]
                    logger.info(f"✅ Fetched {len(jobs)} jobs from Hire2Inspire")
                    return jobs
                else:
                    logger.warning("⚠️ No jobs data in response")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Failed to fetch jobs: {e}")
            return []
    
    async def get_shortlisted_candidates(
        self, 
        job_hash_id: str,
        page: int = 1,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get shortlisted candidates for a specific job"""
        try:
            token = await self._ensure_token()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/shortlist_candidate/",
                    params={
                        "page": page,
                        "limit": limit,
                        "candidatePage": 1,
                        "candidateLimit": limit,
                        "job_hash_id": job_hash_id  # API expects job_hash_id even though response has jd_hash_id
                    },
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract candidates from response
                # API returns: {"data": [{"shortlisted_candidates": [...]}]}
                if "data" in data and len(data["data"]) > 0:
                    job_data = data["data"][0]
                    if "shortlisted_candidates" in job_data:
                        candidates = job_data["shortlisted_candidates"]
                        logger.info(f"✅ Fetched {len(candidates)} candidates for job {job_hash_id}")
                        return candidates
                
                logger.warning(f"⚠️ No candidates found for job {job_hash_id}")
                return []
                    
        except Exception as e:
            logger.error(f"❌ Failed to fetch candidates: {e}")
            return []
    
    async def get_job_details(self, job_hash_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific job by hash_id"""
        try:
            jobs = await self.get_all_jobs()
            for job in jobs:
                if job.get("hash_id") == job_hash_id:
                    return job
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get job details: {e}")
            return None
    
    async def get_candidate_details(
        self, 
        job_hash_id: str, 
        candidate_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get details of a specific candidate"""
        try:
            candidates = await self.get_shortlisted_candidates(job_hash_id)
            for candidate in candidates:
                if candidate.get("_id") == candidate_id or candidate.get("hash_id") == candidate_id:
                    return candidate
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get candidate details: {e}")
            return None
    
    async def get_agency_list(self) -> List[Dict[str, Any]]:
        """Get list of all registered agencies"""
        try:
            # Try to get token, but if login fails, try with existing token anyway
            token = None
            try:
                token = await self._ensure_token()
            except Exception as login_error:
                logger.warning(f"⚠️ Token acquisition failed: {login_error}")
                # If we have a token set via env var, use it even if expired
                if self.token:
                    logger.info("🔄 Attempting to use token from environment variable")
                    token = self.token
                else:
                    raise
            
            if not token:
                logger.error("❌ No token available for API call")
                return []
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/agency/h2i-list",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json"
                    }
                )
                
                logger.info(f"📡 Agency list API response status: {response.status_code}")
                
                # Log response for debugging
                response_text = response.text
                logger.debug(f"📋 Agency list API response: {response_text[:500]}")
                
                # Check for authentication errors
                if response.status_code == 401:
                    logger.error("❌ Authentication failed - token may be invalid or expired")
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                logger.debug(f"📋 Parsed response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                
                # Extract agencies from response - check multiple possible structures
                agencies = []
                if isinstance(data, list):
                    # Response is directly a list
                    agencies = data
                elif isinstance(data, dict):
                    # Check for error first
                    if data.get("error"):
                        logger.error(f"❌ API returned error: {data.get('message', 'Unknown error')}")
                        return []
                    
                    # Check for data field
                    if "data" in data:
                        if isinstance(data["data"], list):
                            agencies = data["data"]
                        elif isinstance(data["data"], dict) and "agencies" in data["data"]:
                            agencies = data["data"]["agencies"]
                        else:
                            logger.warning(f"⚠️ Unexpected data structure: {type(data['data'])}")
                    elif "agencies" in data:
                        agencies = data["agencies"]
                    else:
                        logger.warning(f"⚠️ No agencies found in response. Keys: {list(data.keys())}")
                
                logger.info(f"✅ Fetched {len(agencies)} agencies from Hire2Inspire")
                return agencies
                    
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:200] if e.response.text else "No error message"
            logger.error(f"❌ HTTP error fetching agencies: {e.response.status_code} - {error_text}")
            return []
        except Exception as e:
            logger.error(f"❌ Failed to fetch agencies: {e}", exc_info=True)
            return []
    
    async def get_agency_details(self, agency_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific agency by ID - No token required"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/agency/{agency_id}",
                    headers={
                        "Accept": "application/json"
                    }
                )
                
                logger.info(f"📡 Agency details API response status: {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                # Log the response structure for debugging
                logger.debug(f"📋 Agency details response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                
                # Extract agency details from response
                agency_data = None
                if isinstance(data, dict):
                    if "data" in data:
                        agency_data = data["data"]
                        logger.debug(f"📋 Agency data keys: {list(agency_data.keys()) if isinstance(agency_data, dict) else 'not a dict'}")
                    else:
                        # Response might be the agency data directly
                        agency_data = data
                        logger.debug(f"📋 Using response as agency data directly")
                elif isinstance(data, list) and len(data) > 0:
                    agency_data = data[0]
                    logger.debug(f"📋 Using first item from list response")
                
                if agency_data:
                    logger.info(f"✅ Fetched agency details for {agency_id}")
                    # Log all keys to help debug
                    if isinstance(agency_data, dict):
                        logger.info(f"📋 Agency data has {len(agency_data)} keys: {list(agency_data.keys())[:20]}")  # First 20 keys
                        # Log sample fields to help debug
                        sample_fields = ['first_name', 'last_name', 'personal_email', 'agency_location', 'subscription', 'firstName', 'lastName']
                        for field in sample_fields:
                            if field in agency_data:
                                logger.info(f"📋 Found field '{field}': {agency_data[field]}")
                        # Check for subscription
                        if 'subscription' in agency_data:
                            logger.info(f"📋 Subscription keys: {list(agency_data['subscription'].keys()) if isinstance(agency_data['subscription'], dict) else 'not a dict'}")
                        # Log full structure (truncated)
                        import json
                        logger.debug(f"📋 Full agency data (first 1000 chars): {json.dumps(agency_data, default=str)[:1000]}")
                    return agency_data
                else:
                    logger.warning(f"⚠️ No agency data in response for {agency_id}")
                    return None
                    
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:200] if e.response.text else "No error message"
            logger.error(f"❌ HTTP error getting agency details: {e.response.status_code} - {error_text}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get agency details: {e}", exc_info=True)
            return None


# Global instance
hire2inspire_service = Hire2InspireService()

