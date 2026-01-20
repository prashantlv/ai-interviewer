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
            self.token_expiry = datetime.now() + timedelta(hours=24)
            logger.info("✅ Using pre-configured access token")
        
    async def _ensure_token(self) -> str:
        """Ensure we have a valid token, refresh if needed"""
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.token
            
        # Login to get new token
        await self._login()
        return self.token
    
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
            token = await self._ensure_token()
            
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
                
                response.raise_for_status()
                data = response.json()
                
                logger.debug(f"📋 Parsed response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                
                # Extract agencies from response - check multiple possible structures
                agencies = []
                if isinstance(data, list):
                    # Response is directly a list
                    agencies = data
                elif isinstance(data, dict):
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
            logger.error(f"❌ HTTP error fetching agencies: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"❌ Failed to fetch agencies: {e}", exc_info=True)
            return []
    
    async def get_agency_details(self, agency_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific agency by ID"""
        try:
            token = await self._ensure_token()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/agency/{agency_id}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract agency details from response
                if "data" in data:
                    logger.info(f"✅ Fetched agency details for {agency_id}")
                    return data["data"]
                else:
                    logger.warning(f"⚠️ No agency data in response for {agency_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Failed to get agency details: {e}")
            return None


# Global instance
hire2inspire_service = Hire2InspireService()

