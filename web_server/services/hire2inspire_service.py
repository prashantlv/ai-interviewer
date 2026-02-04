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
        self.base_url = "https://pro.hireinspire.com/api"
        self.email = os.getenv("H2I_EMAIL", "hire2inspireh2i@gmail.com")
        self.password = os.getenv("H2I_PASSWORD", "Sant@1506")
        # Token is always obtained from cookies (via request) or login
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        
    async def _ensure_token(self, token: Optional[str] = None) -> str:
        """Ensure we have a valid token, refresh if needed
        
        Args:
            token: Optional token from cookies. If provided, uses this token.
                   If not provided, falls back to cached token or login.
        """
        # If token is provided (from cookies), use it
        if token:
            logger.info("✅ Using token provided from cookies")
            return token
        
        # If we have a cached token and it's not expired, use it
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            logger.debug("✅ Using existing valid cached token")
            return self.token
        
        # If token exists but expired, try to login
        if self.token:
            logger.warning("⚠️ Cached token expired, attempting to login...")
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
    
    async def get_all_jobs(self, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all job descriptions for the agency
        
        Args:
            token: Optional access token from cookies. If provided, uses this token.
        """
        try:
            token = await self._ensure_token(token)
            
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
        limit: int = 100,
        token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get shortlisted candidates for a specific job
        
        Args:
            job_hash_id: The job hash ID
            page: Page number for pagination
            limit: Number of items per page
            token: Optional access token from cookies. If provided, uses this token.
        """
        try:
            token = await self._ensure_token(token)
            
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
    
    async def get_job_details(self, job_hash_id: str, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get details of a specific job by hash_id
        
        Args:
            job_hash_id: The job hash ID
            token: Optional access token from cookies. If provided, uses this token.
        """
        try:
            jobs = await self.get_all_jobs(token=token)
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
        candidate_id: str,
        token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get details of a specific candidate
        
        Args:
            job_hash_id: The job hash ID
            candidate_id: The candidate ID
            token: Optional access token from cookies. If provided, uses this token.
        """
        try:
            candidates = await self.get_shortlisted_candidates(job_hash_id, token=token)
            for candidate in candidates:
                if candidate.get("_id") == candidate_id or candidate.get("hash_id") == candidate_id:
                    return candidate
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get candidate details: {e}")
            return None
    
    async def get_agency_list(self, user_type: str = "agencies", token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of agencies or employers from Hire2Inspire API
        
        Args:
            user_type: Either "agencies" or "employers" (default: "agencies")
            token: Optional access token from cookies. If provided, uses this token.
        
        Returns:
            List of agency/employer dictionaries
        """
        try:
            token = await self._ensure_token(token)
            
            if not token:
                logger.error("❌ No token available for API call")
                return []
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/agency/h2i-list",
                    params={"user_type": user_type},
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
    
    async def get_agency_details(self, agency_id: str, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get details of a specific agency by ID
        
        Args:
            agency_id: The agency ID to fetch
            token: Optional access token from cookies. If provided, uses this for authenticated requests.
        """
        try:
            headers = {
                "Accept": "application/json"
            }
            
            # Add Authorization header if token is provided
            if token:
                headers["Authorization"] = f"Bearer {token}"
                logger.info("✅ Using token provided from cookies for agency details")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/agency/{agency_id}",
                    headers=headers
                )
                
                logger.info(f"📡 Agency details API response status: {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                # Log the FULL response structure for debugging
                import json
                logger.info(f"📋 Raw API response structure:")
                logger.info(f"📋 Response top-level keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                
                # Check if subscription exists in raw response at ANY level
                if isinstance(data, dict):
                    # Check top level
                    if "subscription" in data:
                        logger.info(f"✅ Found 'subscription' at top level of response")
                    
                    # Check data.data level
                    if "data" in data:
                        if isinstance(data["data"], dict):
                            logger.info(f"📋 data.data keys count: {len(data['data'])}")
                            logger.info(f"📋 data.data keys: {list(data['data'].keys())}")
                            if "subscription" in data["data"]:
                                logger.info(f"✅ Found 'subscription' in data.data - type: {type(data['data']['subscription'])}")
                                if isinstance(data["data"]["subscription"], list):
                                    logger.info(f"✅ Subscription is array with {len(data['data']['subscription'])} items")
                            else:
                                logger.warning(f"⚠️ 'subscription' NOT in data.data!")
                                # Check all keys for anything subscription-related
                                sub_keys = [k for k in data['data'].keys() if 'subscription' in k.lower()]
                                if sub_keys:
                                    logger.info(f"📋 Found subscription-related keys: {sub_keys}")
                                else:
                                    logger.warning(f"⚠️ No subscription-related keys found in data.data")
                        else:
                            logger.warning(f"⚠️ data.data is not a dict, it's: {type(data['data'])}")
                
                # Extract agency details from response
                # ROOT CAUSE: subscription and finalCredits are at TOP LEVEL of response, not inside data["data"]
                # Structure: { "data": {...agency...}, "subscription": [...], "finalCredits": {...} }
                agency_data = None
                if isinstance(data, dict):
                    if "data" in data:
                        # Extract agency data from data["data"]
                        agency_data = data["data"] if isinstance(data["data"], dict) else {}
                        
                        # CRITICAL: Merge subscription and finalCredits from TOP LEVEL into agency_data
                        if "subscription" in data:
                            agency_data["subscription"] = data["subscription"]
                            logger.info(f"✅ Added subscription from top level to agency_data")
                            if isinstance(data["subscription"], list):
                                logger.info(f"✅ Subscription is array with {len(data['subscription'])} items")
                        else:
                            logger.warning(f"⚠️ No subscription found at top level of response")
                        
                        if "finalCredits" in data:
                            agency_data["finalCredits"] = data["finalCredits"]
                            logger.info(f"✅ Added finalCredits from top level to agency_data")
                        
                        logger.info(f"📋 Extracted agency_data and merged top-level fields")
                        logger.info(f"📋 Agency data keys count: {len(agency_data)}")
                        logger.info(f"📋 Agency data ALL keys: {list(agency_data.keys())}")
                        
                        # Verify subscription is now in agency_data
                        if "subscription" in agency_data:
                            logger.info(f"✅ Subscription confirmed in agency_data after merge!")
                            if isinstance(agency_data['subscription'], list) and len(agency_data['subscription']) > 0:
                                logger.info(f"✅ First subscription status: {agency_data['subscription'][0].get('status')}")
                        else:
                            logger.error(f"❌ Subscription still missing after merge!")
                    else:
                        # Response might be the agency data directly
                        agency_data = data
                        logger.info(f"📋 Using response as agency data directly")
                elif isinstance(data, list) and len(data) > 0:
                    agency_data = data[0]
                    logger.info(f"📋 Using first item from list response")
                
                if agency_data:
                    logger.info(f"✅ Fetched agency details for {agency_id}")
                    # Log all keys to help debug
                    if isinstance(agency_data, dict):
                        all_keys = list(agency_data.keys())
                        logger.info(f"📋 Agency data has {len(agency_data)} keys")
                        logger.info(f"📋 All keys: {all_keys}")
                        # Check if subscription is in the keys (case-insensitive check)
                        subscription_keys = [k for k in all_keys if 'subscription' in k.lower()]
                        if subscription_keys:
                            logger.info(f"📋 Found keys containing 'subscription': {subscription_keys}")
                        else:
                            logger.warning(f"⚠️ No keys containing 'subscription' found!")
                        
                        # Check for subscription specifically - check all possible variations
                        subscription_field = None
                        for key in ['subscription', 'subscriptions', 'subscription_data', 'subscriptionInfo']:
                            if key in agency_data:
                                subscription_field = key
                                logger.info(f"✅ Found subscription field as '{key}'")
                                break
                        
                        if subscription_field:
                            subscription_data = agency_data[subscription_field]
                            if isinstance(subscription_data, list):
                                logger.info(f"📋 Subscription is an array with {len(subscription_data)} items")
                                if len(subscription_data) > 0:
                                    logger.info(f"📋 First subscription item keys: {list(subscription_data[0].keys()) if isinstance(subscription_data[0], dict) else 'not a dict'}")
                                    logger.info(f"📋 First subscription status: {subscription_data[0].get('status')}")
                                    logger.info(f"📋 First subscription type: {subscription_data[0].get('type')}")
                                    logger.info(f"📋 First subscription amount: {subscription_data[0].get('amount')}")
                            elif isinstance(subscription_data, dict):
                                logger.info(f"📋 Subscription is a dict with keys: {list(subscription_data.keys())}")
                        else:
                            logger.warning(f"⚠️ 'subscription' field NOT found in agency data!")
                            logger.warning(f"⚠️ Available keys: {all_keys}")
                            # Log full response to see what we actually got
                            import json
                            logger.warning(f"⚠️ Full response data (first 2000 chars): {json.dumps(data, default=str)[:2000]}")
                        
                        # Log sample fields to help debug
                        sample_fields = ['first_name', 'last_name', 'personal_email', 'agency_location', 'agency_account_info']
                        for field in sample_fields:
                            if field in agency_data:
                                logger.info(f"📋 Found field '{field}': {type(agency_data[field])}")
                        
                        # Log full structure (truncated) - but include subscription check
                        import json
                        if 'subscription' in agency_data:
                            logger.info(f"📋 Subscription data: {json.dumps(agency_data['subscription'], default=str)[:500]}")
                        
                        # Final verification before return - explicitly check subscription
                        if 'subscription' not in agency_data:
                            logger.error(f"❌ CRITICAL: Subscription field missing from agency_data before return!")
                            logger.error(f"❌ All keys that will be returned: {all_keys}")
                            # Try to get subscription from original response
                            if isinstance(data, dict) and "data" in data:
                                original_data = data["data"]
                                if isinstance(original_data, dict) and "subscription" in original_data:
                                    logger.warning(f"⚠️ Subscription exists in original data but not in agency_data - copying it!")
                                    agency_data["subscription"] = original_data["subscription"]
                                    logger.info(f"✅ Copied subscription to agency_data")
                        else:
                            logger.info(f"✅ Subscription field confirmed present before return")
                            logger.info(f"✅ Subscription type: {type(agency_data['subscription'])}, is array: {isinstance(agency_data['subscription'], list)}")
                    
                    # Ensure we return the full agency_data with all fields including subscription
                    # Final verification - double-check subscription is included
                    if isinstance(agency_data, dict):
                        if 'subscription' not in agency_data:
                            logger.error(f"❌ FINAL CHECK FAILED: Subscription still missing from agency_data!")
                            logger.error(f"❌ Final keys in agency_data: {list(agency_data.keys())}")
                            # Last resort: try to get it from original response
                            if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
                                if "subscription" in data["data"]:
                                    logger.warning(f"⚠️ LAST RESORT: Copying subscription from original data")
                                    agency_data["subscription"] = data["data"]["subscription"]
                                    logger.info(f"✅ Subscription copied in last resort attempt")
                        else:
                            logger.info(f"✅ FINAL CHECK PASSED: Subscription confirmed in agency_data")
                            logger.info(f"✅ Subscription value type: {type(agency_data['subscription'])}")
                            if isinstance(agency_data['subscription'], list):
                                logger.info(f"✅ Subscription array length: {len(agency_data['subscription'])}")
                    
                    # Log what we're actually returning
                    if isinstance(agency_data, dict):
                        return_keys = list(agency_data.keys())
                        logger.info(f"📤 Returning agency_data with {len(return_keys)} keys")
                        logger.info(f"📤 Keys being returned: {return_keys}")
                        if 'subscription' in return_keys:
                            logger.info(f"✅ Subscription WILL be returned to frontend")
                        else:
                            logger.error(f"❌ Subscription WILL NOT be returned to frontend!")
                    
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

