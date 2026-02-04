"""
Tavus API Service

Handles Tavus API interactions for replica management (phoenix-3 model).
API Documentation: https://docs.tavus.io/api-reference/phoenix-replica-model
"""

import os
import httpx
from typing import Dict, Any, Optional, List
from loguru import logger


class TavusService:
    """Service for interacting with Tavus API for replica management"""
    
    def __init__(self):
        # Default API key from environment (for backward compatibility)
        self.default_api_key = os.getenv("TAVUS_API_KEY")
        self.api_url = "https://tavusapi.com/v2"
        
        if not self.default_api_key:
            logger.warning("⚠️ TAVUS_API_KEY not set - replica operations will fail without per-user keys")
    
    def _get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        """Get standard headers for Tavus API requests
        
        Args:
            api_key: Optional API key to use. If not provided, uses default from env.
        """
        key = api_key or self.default_api_key
        if not key:
            raise ValueError("Tavus API key not provided and TAVUS_API_KEY env var not set")
        
        return {
            "x-api-key": key,
            "Content-Type": "application/json"
        }
    
    async def create_replica(
        self,
        train_video_url: str,
        replica_name: str,
        consent_video_url: Optional[str] = None,
        callback_url: Optional[str] = None,
        model_name: str = "phoenix-3",
        api_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new Tavus replica
        
        Args:
            train_video_url: Public URL to training video (required)
            replica_name: Name for the replica (required)
            consent_video_url: Public URL to consent video (required for personal replicas)
            callback_url: Webhook URL for training completion
            model_name: Phoenix model version (default: phoenix-3)
            api_key: Optional API key. If not provided, uses default from env.
        
        Returns:
            Dict with replica_id and status, or None on error
        
        API Doc: https://docs.tavus.io/api-reference/phoenix-replica-model/create-replica
        """
        try:
            headers = self._get_headers(api_key)
        except ValueError as e:
            logger.error(f"❌ Cannot create replica: {e}")
            return None
        
        try:
            payload = {
                "train_video_url": train_video_url,
                "replica_name": replica_name,
                "model_name": model_name
            }
            
            # Add optional parameters
            if consent_video_url:
                payload["consent_video_url"] = consent_video_url
            if callback_url:
                payload["callback_url"] = callback_url
            
            logger.info(f"🎬 Creating Tavus replica: {replica_name}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/replicas",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Replica created: {result.get('replica_id')} (status: {result.get('status')})")
                    return result
                else:
                    logger.error(f"❌ Failed to create replica: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error creating replica: {str(e)}")
            return None
    
    async def get_replica(
        self,
        replica_id: str,
        verbose: bool = True,
        api_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single replica by ID
        
        Args:
            replica_id: Unique identifier for the replica
            verbose: Include additional data like replica_type
            api_key: Optional API key. If not provided, uses default from env.
        
        Returns:
            Dict with replica details, or None on error
        
        API Doc: https://docs.tavus.io/api-reference/phoenix-replica-model/get-replica
        """
        try:
            headers = self._get_headers(api_key)
        except ValueError as e:
            logger.error(f"❌ Cannot get replica: {e}")
            return None
        
        try:
            params = {"verbose": str(verbose).lower()}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/replicas/{replica_id}",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Retrieved replica: {replica_id}")
                    return result
                elif response.status_code == 404:
                    logger.warning(f"⚠️ Replica not found: {replica_id}")
                    return None
                else:
                    logger.error(f"❌ Failed to get replica: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting replica: {str(e)}")
            return None
    
    async def list_replicas(
        self,
        limit: Optional[int] = None,
        page: Optional[int] = None,
        verbose: bool = True,
        replica_type: Optional[str] = None,
        replica_ids: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        List all replicas
        
        Args:
            limit: Number of replicas per page
            page: Page number
            verbose: Include additional data like replica_type
            replica_type: Filter by type ('user' or 'system')
            replica_ids: Comma-separated list of replica IDs to filter
            api_key: Optional API key. If not provided, uses default from env.
        
        Returns:
            Dict with 'data' (list of replicas) and 'total_count', or None on error
        
        API Doc: https://docs.tavus.io/api-reference/phoenix-replica-model/get-replicas
        """
        try:
            headers = self._get_headers(api_key)
        except ValueError as e:
            logger.error(f"❌ Cannot list replicas: {e}")
            return None
        
        try:
            params = {"verbose": str(verbose).lower()}
            
            # Add optional query parameters
            if limit is not None:
                params["limit"] = limit
            if page is not None:
                # Tavus API uses 0-based pagination, our UI uses 1-based
                params["page"] = page - 1 if page > 0 else 0
            if replica_type:
                params["replica_type"] = replica_type
            if replica_ids:
                params["replica_ids"] = replica_ids
            
            logger.info(f"📋 Listing Tavus replicas... API params: {params}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/replicas",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    count = result.get('total_count', 0)
                    data_len = len(result.get('data', []))
                    logger.info(f"📊 API returned total_count={count}, data length={data_len}, params={params}")
                    logger.info(f"✅ Retrieved {count} replicas")
                    # Log sample replica fields for debugging
                    if result.get("data") and len(result["data"]) > 0:
                        sample = result["data"][0]
                        logger.info(f"📋 Sample replica fields: {list(sample.keys())}")
                    return result
                else:
                    logger.error(f"❌ Failed to list replicas: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error listing replicas: {str(e)}")
            return None
    
    async def rename_replica(
        self,
        replica_id: str,
        new_name: str,
        api_key: Optional[str] = None
    ) -> bool:
        """
        Rename a replica
        
        Args:
            replica_id: Unique identifier for the replica
            new_name: New name for the replica
            api_key: Optional API key. If not provided, uses default from env.
        
        Returns:
            True if successful, False otherwise
        
        API Doc: https://docs.tavus.io/api-reference/phoenix-replica-model/patch-replica-name
        """
        try:
            headers = self._get_headers(api_key)
        except ValueError as e:
            logger.error(f"❌ Cannot rename replica: {e}")
            return False
        
        try:
            payload = {
                "replica_name": new_name
            }
            
            logger.info(f"✏️ Renaming replica {replica_id} to: {new_name}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(
                    f"{self.api_url}/replicas/{replica_id}",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Replica renamed successfully: {replica_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to rename replica: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error renaming replica: {str(e)}")
            return False
    
    async def delete_replica(
        self,
        replica_id: str,
        hard_delete: bool = False,
        api_key: Optional[str] = None
    ) -> bool:
        """
        Delete a replica
        
        Args:
            replica_id: Unique identifier for the replica
            hard_delete: If True, permanently delete replica and training footage.
                        CAUTION: This is irreversible!
            api_key: Optional API key. If not provided, uses default from env.
        
        Returns:
            True if successful, False otherwise
        
        API Doc: https://docs.tavus.io/api-reference/phoenix-replica-model/delete-replica
        """
        try:
            headers = self._get_headers(api_key)
        except ValueError as e:
            logger.error(f"❌ Cannot delete replica: {e}")
            return False
        
        try:
            params = {}
            if hard_delete:
                params["hard"] = "true"
                logger.warning(f"⚠️ HARD DELETE requested for replica: {replica_id}")
            
            logger.info(f"🗑️ Deleting replica: {replica_id}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.api_url}/replicas/{replica_id}",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Replica deleted successfully: {replica_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to delete replica: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error deleting replica: {str(e)}")
            return False
    
    async def health_check(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Check Tavus API health by attempting to list replicas
        
        Args:
            api_key: Optional API key. If not provided, uses default from env.
        
        Returns:
            Dict with health status information
        """
        key = api_key or self.default_api_key
        if not key:
            return {
                "status": "unhealthy",
                "error": "TAVUS_API_KEY not configured"
            }
        
        try:
            result = await self.list_replicas(limit=1, api_key=key)
            if result is not None:
                return {
                    "status": "healthy",
                    "api_key_valid": True,
                    "total_replicas": result.get('total_count', 0)
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Failed to connect to Tavus API"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
tavus_service = TavusService()

