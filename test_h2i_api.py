#!/usr/bin/env python3
"""Test Hire2Inspire API to debug candidates endpoint"""

import asyncio
import httpx
import json
from datetime import datetime

EMAIL = "hire2inspireh2i@gmail.com"
PASSWORD = "Sant@1506"
BASE_URL = "https://api.hire2inspire.com/api"

async def test_api():
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Step 1: Logout first (from ALL sessions)
        print("1️⃣ Logging out from all sessions...")
        try:
            logout_response = await client.patch(
                f"{BASE_URL}/agency/update-logout",
                json={"email": EMAIL},
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json",
                    "Referer": "https://app.hire2inspire.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
                }
            )
            print(f"   Logout status: {logout_response.status_code}")
            if logout_response.status_code < 400:
                print("   ✅ Logged out from all sessions")
        except Exception as e:
            print(f"   ⚠️ Logout failed: {e}")
        
        # Step 2: Login
        print("\n2️⃣ Logging in...")
        login_response = await client.post(
            f"{BASE_URL}/agency/login",
            json={
                "email": EMAIL,
                "password": PASSWORD,
                "system": "Linux",
                "browser_type": "Chrome",
                "login_time": datetime.now().isoformat()
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )
        print(f"   Login status: {login_response.status_code}")
        
        login_data = login_response.json()
        if "data" in login_data and "accessToken" in login_data["data"]:
            token = login_data["data"]["accessToken"]
            print(f"   ✅ Token: {token[:30]}...")
        else:
            print(f"   ❌ Login failed: {login_data}")
            return
        
        # Step 3: Get jobs
        print("\n3️⃣ Getting jobs...")
        jobs_response = await client.get(
            f"{BASE_URL}/shortlist_candidate/get_jd_data_py",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
        )
        print(f"   Jobs status: {jobs_response.status_code}")
        
        jobs_data = jobs_response.json()
        if "data" in jobs_data:
            jobs = jobs_data["data"]
            print(f"   ✅ Found {len(jobs)} jobs")
            
            # Find job with jd_hash_id
            job_with_hash = None
            for job in jobs:
                if job.get("jd_hash_id"):
                    job_with_hash = job
                    print(f"\n   Job: {job.get('job_title')}")
                    print(f"   jd_hash_id: {job.get('jd_hash_id')}")
                    break
            
            if not job_with_hash:
                print("   ❌ No job with jd_hash_id found")
                return
            
            job_hash_id = job_with_hash.get("jd_hash_id")
            
            # Step 4: Get candidates - TEST BOTH PARAMETERS
            print(f"\n4️⃣ Testing candidates endpoint...")
            
            # Test A: job_hash_id parameter
            print(f"\n   A) Using job_hash_id={job_hash_id}")
            cand_response_a = await client.get(
                f"{BASE_URL}/shortlist_candidate/",
                params={
                    "page": 1,
                    "limit": 5,
                    "candidatePage": 1,
                    "candidateLimit": 5,
                    "job_hash_id": job_hash_id
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                }
            )
            print(f"   Status: {cand_response_a.status_code}")
            cand_data_a = cand_response_a.json()
            print(f"   Response keys: {list(cand_data_a.keys())}")
            print(f"   Full response:\n{json.dumps(cand_data_a, indent=2, default=str)[:1500]}")
            
            # Test B: jd_hash_id parameter
            print(f"\n   B) Using jd_hash_id={job_hash_id}")
            cand_response_b = await client.get(
                f"{BASE_URL}/shortlist_candidate/",
                params={
                    "page": 1,
                    "limit": 5,
                    "candidatePage": 1,
                    "candidateLimit": 5,
                    "jd_hash_id": job_hash_id
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                }
            )
            print(f"   Status: {cand_response_b.status_code}")
            cand_data_b = cand_response_b.json()
            print(f"   Response keys: {list(cand_data_b.keys())}")
            print(f"   Full response:\n{json.dumps(cand_data_b, indent=2, default=str)[:1500]}")

if __name__ == "__main__":
    asyncio.run(test_api())

