"""
Resume Parser Service - GPT-based resume parsing
Extracts structured data from resume text
"""

import openai
import os
import json
import re
from typing import Dict, Any, Optional
from loguru import logger

class ResumeParser:
    def __init__(self):
        """Initialize Resume Parser with OpenAI client"""
        # Default API key from environment (for backward compatibility)
        self.default_api_key = os.getenv("OPENAI_API_KEY")
        if not self.default_api_key:
            logger.warning("⚠️ OPENAI_API_KEY not set. Resume parser will use fallback mode.")
    
    def _get_openai_client(self, api_key: Optional[str] = None):
        """Get OpenAI client with provided API key or default
        
        Args:
            api_key: Optional API key. If not provided, uses default from env.
        
        Returns:
            OpenAI client instance or None if no key available
        """
        key = api_key or self.default_api_key
        if not key:
            return None
        return openai.OpenAI(api_key=key)
    
    def health_check(self, api_key: Optional[str] = None) -> str:
        """Check if parser is operational
        
        Args:
            api_key: Optional API key. If not provided, uses default from env.
        """
        key = api_key or self.default_api_key
        return "operational" if key else "operational_fallback_mode"
    
    async def parse_resume(self, resume_text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse resume text into structured data
        
        Args:
            resume_text: Raw resume text (from textarea, PDF, etc.)
            api_key: Optional OpenAI API key. If not provided, uses default from env.
            
        Returns:
            Structured resume data with skills, experience, education, etc.
        """
        if not resume_text or not resume_text.strip():
            logger.warning("⚠️ Empty resume text provided")
            return self._get_empty_resume_structure()
        
        # Try GPT-based parsing first
        client = self._get_openai_client(api_key)
        if client:
            try:
                parsed_data = await self._parse_with_gpt(resume_text, api_key=api_key)
                if parsed_data:
                    logger.info(f"✅ Resume parsed successfully with GPT (found {len(parsed_data.get('skills', []))} skills)")
                    return parsed_data
            except Exception as e:
                logger.error(f"❌ GPT parsing failed: {e}")
        
        # Fallback to regex-based parsing
        logger.info("📝 Using fallback regex-based parsing")
        return self._parse_with_regex(resume_text)
    
    async def _parse_with_gpt(self, resume_text: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Parse resume using GPT-4o-mini"""
        
        prompt = f"""
Extract structured information from this resume/candidate profile.

Resume Text:
{resume_text[:3000]}  

Extract and return as valid JSON with this exact structure:
{{
    "name": "candidate name or null",
    "email": "email or null",
    "phone": "phone number or null",
    "skills": ["skill1", "skill2", ...],
    "experience_years": 0,
    "previous_roles": ["role1 at company1", "role2 at company2", ...],
    "education": ["degree1", "degree2", ...],
    "certifications": ["cert1", "cert2", ...],
    "summary": "brief 2-3 sentence summary of candidate background"
}}

Rules:
1. Extract ALL technical skills (programming languages, frameworks, tools, cloud platforms)
2. Calculate total years of experience (approximate if needed)
3. List previous job titles with company names
4. Include degrees and universities
5. Use null for missing fields, empty arrays for missing lists
6. Return ONLY valid JSON, no markdown formatting
"""
        
        client = self._get_openai_client(api_key)
        if not client:
            return None
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert resume parser. Extract structured data accurately. Return only valid JSON without markdown code blocks."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for consistent extraction
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'^```\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            
            parsed_data = json.loads(content)
            
            # Validate structure
            required_fields = ["skills", "experience_years", "previous_roles"]
            if all(field in parsed_data for field in required_fields):
                return parsed_data
            else:
                logger.warning(f"⚠️ GPT response missing required fields: {parsed_data}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error: {e}\nContent: {content[:200]}")
            return None
        except Exception as e:
            logger.error(f"❌ OpenAI API error: {e}")
            return None
    
    def _parse_with_regex(self, resume_text: str) -> Dict[str, Any]:
        """Fallback: Simple regex-based parsing"""
        
        # Common technical skills to look for
        tech_skills = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node', 'nodejs', 'express', 'django', 'flask', 'fastapi',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'k8s',
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis',
            'git', 'jenkins', 'ci/cd', 'terraform', 'ansible',
            'html', 'css', 'rest', 'api', 'graphql', 'microservices',
            'machine learning', 'ml', 'ai', 'data science', 'pandas', 'numpy'
        ]
        
        text_lower = resume_text.lower()
        
        # Extract skills
        found_skills = []
        for skill in tech_skills:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                # Capitalize properly
                found_skills.append(skill.title())
        
        # Extract years of experience
        exp_patterns = [
            r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
            r'experience[:\s]+(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?'
        ]
        experience_years = 0
        for pattern in exp_patterns:
            match = re.search(pattern, text_lower)
            if match:
                experience_years = int(match.group(1))
                break
        
        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
        email = email_match.group(0) if email_match else None
        
        # Extract phone
        phone_match = re.search(r'[\+\d][\d\s\-\(\)]{8,}', resume_text)
        phone = phone_match.group(0) if phone_match else None
        
        # Extract name (first line that looks like a name)
        name_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', resume_text.strip())
        name = name_match.group(1) if name_match else None
        
        return {
            "name": name,
            "email": email,
            "phone": phone,
            "skills": list(set(found_skills)) if found_skills else ["General"],
            "experience_years": experience_years,
            "previous_roles": [],
            "education": [],
            "certifications": [],
            "summary": f"Candidate with {experience_years} years of experience" if experience_years > 0 else "Entry-level candidate"
        }
    
    def _get_empty_resume_structure(self) -> Dict[str, Any]:
        """Return empty resume structure for missing data"""
        return {
            "name": None,
            "email": None,
            "phone": None,
            "skills": [],
            "experience_years": 0,
            "previous_roles": [],
            "education": [],
            "certifications": [],
            "summary": "No resume provided"
        }

