"""
Hire2Inspire API Integration Service

Handles authentication and data fetching from Hire2Inspire platform
"""

import httpx
import os
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
        """Logout from Hire2Inspire"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/agency/logout",
                    json={
                        "email": self.email
                    },
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    }
                )
                logger.info("✅ Logged out successfully")
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
                if "data" in data and "shortlist_candidate" in data["data"]:
                    candidates = data["data"]["shortlist_candidate"]
                    logger.info(f"✅ Fetched {len(candidates)} candidates for job {job_hash_id}")
                    return candidates
                else:
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


# Global instance
hire2inspire_service = Hire2InspireService()

