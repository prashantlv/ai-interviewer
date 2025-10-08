"""
Job Description Parser Service - GPT-based JD parsing
Extracts structured data from job description text
"""

import openai
import os
import json
import re
from typing import Dict, Any, Optional
from loguru import logger

class JDParser:
    def __init__(self):
        """Initialize JD Parser with OpenAI client"""
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
        else:
            self.openai_client = None
            logger.warning("⚠️ OPENAI_API_KEY not set. JD parser will use fallback mode.")
    
    def health_check(self) -> str:
        """Check if parser is operational"""
        return "operational" if self.openai_client else "operational_fallback_mode"
    
    async def parse_job_description(self, jd_text: str, position: str = None) -> Dict[str, Any]:
        """
        Parse job description text into structured data
        
        Args:
            jd_text: Raw job description text
            position: Job title (optional, used as fallback)
            
        Returns:
            Structured JD data with skills, requirements, responsibilities, etc.
        """
        if not jd_text or not jd_text.strip():
            logger.warning("⚠️ Empty JD text provided")
            return self._get_empty_jd_structure(position)
        
        # Try GPT-based parsing first
        if self.openai_client:
            try:
                parsed_data = await self._parse_with_gpt(jd_text, position)
                if parsed_data:
                    logger.info(f"✅ JD parsed successfully with GPT (found {len(parsed_data.get('skills_required', []))} required skills)")
                    return parsed_data
            except Exception as e:
                logger.error(f"❌ GPT parsing failed: {e}")
        
        # Fallback to regex-based parsing
        logger.info("📝 Using fallback regex-based parsing for JD")
        return self._parse_with_regex(jd_text, position)
    
    async def _parse_with_gpt(self, jd_text: str, position: str = None) -> Optional[Dict[str, Any]]:
        """Parse JD using GPT-4o-mini"""
        
        prompt = f"""
Extract structured information from this job description.

Job Description:
{jd_text[:3000]}

Extract and return as valid JSON with this exact structure:
{{
    "title": "job title",
    "company": "company name or null",
    "location": "location or null",
    "employment_type": "full-time/part-time/contract or null",
    "experience_level": "entry/mid/senior or X-Y years",
    "skills_required": ["skill1", "skill2", ...],
    "responsibilities": ["responsibility1", "responsibility2", ...],
    "qualifications": ["qualification1", "qualification2", ...],
    "nice_to_have": ["skill1", "skill2", ...],
    "salary_range": "salary range or null",
    "benefits": ["benefit1", "benefit2", ...],
    "summary": "brief 2-3 sentence summary of the role"
}}

Rules:
1. Extract ALL required technical skills (programming languages, frameworks, tools)
2. Separate "must have" skills into skills_required
3. Separate "nice to have" or "preferred" skills into nice_to_have
4. List key responsibilities and qualifications separately
5. Use null for missing fields, empty arrays for missing lists
6. Return ONLY valid JSON, no markdown formatting
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert job description parser. Extract structured data accurately. Return only valid JSON without markdown code blocks."
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
            
            # Use position as fallback for title
            if not parsed_data.get("title") and position:
                parsed_data["title"] = position
            
            # Validate structure
            required_fields = ["title", "skills_required", "responsibilities"]
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
    
    def _parse_with_regex(self, jd_text: str, position: str = None) -> Dict[str, Any]:
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
        
        text_lower = jd_text.lower()
        
        # Extract skills
        found_skills = []
        for skill in tech_skills:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill.title())
        
        # Extract experience level
        exp_match = re.search(r'(\d+)\+?\s*years?\s+(?:of\s+)?experience', text_lower)
        experience_level = f"{exp_match.group(1)}+ years" if exp_match else "mid-level"
        
        # Extract employment type
        employment_type = None
        if 'full-time' in text_lower or 'full time' in text_lower:
            employment_type = "full-time"
        elif 'part-time' in text_lower or 'part time' in text_lower:
            employment_type = "part-time"
        elif 'contract' in text_lower:
            employment_type = "contract"
        
        # Extract responsibilities (lines starting with bullet points or numbers)
        responsibilities = []
        resp_patterns = [r'^\s*[\-\*•]\s*(.+)$', r'^\s*\d+\.\s*(.+)$']
        for line in jd_text.split('\n'):
            for pattern in resp_patterns:
                match = re.match(pattern, line)
                if match:
                    responsibilities.append(match.group(1).strip())
        
        return {
            "title": position or "Software Developer",
            "company": None,
            "location": None,
            "employment_type": employment_type,
            "experience_level": experience_level,
            "skills_required": list(set(found_skills)) if found_skills else ["Programming"],
            "responsibilities": responsibilities[:5] if responsibilities else ["Develop software solutions"],
            "qualifications": [],
            "nice_to_have": [],
            "salary_range": None,
            "benefits": [],
            "summary": f"{position or 'Software Developer'} position requiring {experience_level} experience"
        }
    
    def _get_empty_jd_structure(self, position: str = None) -> Dict[str, Any]:
        """Return empty JD structure for missing data"""
        return {
            "title": position or "Software Developer",
            "company": None,
            "location": None,
            "employment_type": None,
            "experience_level": "mid-level",
            "skills_required": ["Programming"],
            "responsibilities": ["Develop software solutions"],
            "qualifications": [],
            "nice_to_have": [],
            "salary_range": None,
            "benefits": [],
            "summary": "No job description provided"
        }

