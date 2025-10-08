"""
Question Engine - Dynamic question generation based on JD and Resume
"""

import openai
import os
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from loguru import logger

class QuestionEngine:
    def __init__(self):
        # Initialize OpenAI client only if API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
        else:
            self.openai_client = None
        
        self.default_config = {
            "difficulty_level": "medium",  # easy, medium, hard
            "question_count": 8,
            "focus_areas": {
                "technical_skills": 40,    # % allocation
                "experience": 30,
                "problem_solving": 20,
                "cultural_fit": 10
            },
            "strictness": 0.7,  # 0.1 to 1.0
        }
    
    def health_check(self) -> str:
        """Check if question engine is working"""
        return "operational" if self.openai_client else "operational_fallback_mode"
    
    async def generate_questions(
        self,
        job_description: Dict[str, Any],
        resume_data: Dict[str, Any],
        interview_config: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Generate interview questions based on JD and resume"""
        
        config = {**self.default_config, **(interview_config or {})}
        
        # Analyze skill gaps and matches
        skill_analysis = self._analyze_skills(job_description, resume_data)
        
        # Generate questions for each focus area
        questions = []
        
        # Technical skills questions
        tech_questions = await self._generate_technical_questions(
            skill_analysis, 
            config["focus_areas"]["technical_skills"],
            config["difficulty_level"]
        )
        questions.extend(tech_questions)
        
        # Experience-based questions
        exp_questions = await self._generate_experience_questions(
            resume_data,
            job_description,
            config["focus_areas"]["experience"]
        )
        questions.extend(exp_questions)
        
        # Problem-solving questions
        problem_questions = await self._generate_problem_solving_questions(
            job_description,
            config["focus_areas"]["problem_solving"],
            config["difficulty_level"]
        )
        questions.extend(problem_questions)
        
        # Cultural fit questions
        culture_questions = await self._generate_cultural_fit_questions(
            job_description,
            config["focus_areas"]["cultural_fit"]
        )
        questions.extend(culture_questions)
        
        # Prioritize and limit questions
        final_questions = self._prioritize_questions(questions, config["question_count"])
        
        return final_questions
    
    def _analyze_skills(self, job_description: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze skill gaps and matches between JD and resume"""
        jd_skills = set(job_description.get("skills_required", []))
        resume_skills = set(resume_data.get("skills", []))
        
        return {
            "matching_skills": list(jd_skills & resume_skills),
            "missing_skills": list(jd_skills - resume_skills),
            "additional_skills": list(resume_skills - jd_skills),
            "skill_match_percentage": len(jd_skills & resume_skills) / len(jd_skills) * 100 if jd_skills else 0
        }
    
    async def _generate_technical_questions(
        self, 
        skill_analysis: Dict[str, Any], 
        allocation: int,
        difficulty: str
    ) -> List[Dict[str, Any]]:
        """Generate technical skill questions"""
        
        question_count = max(1, allocation // 12)  # Rough allocation
        
        prompt = f"""
        Generate {question_count} technical interview questions based on:
        
        Required Skills: {skill_analysis['missing_skills'] + skill_analysis['matching_skills']}
        Candidate Has: {skill_analysis['matching_skills']}
        Missing Skills: {skill_analysis['missing_skills']}
        Difficulty: {difficulty}
        
        Focus on:
        1. Testing depth in matching skills
        2. Exploring missing skills (if any)
        3. Practical application scenarios
        
        Return as JSON array with structure:
        [{{"question": "...", "category": "technical", "skill": "...", "difficulty": "...", "follow_up": "..."}}]
        """
        
        try:
            response = await self._call_openai(prompt)
            if response.strip():  # Only parse if we got a response
                questions = json.loads(response)
                return questions[:question_count]
            else:
                # No API response - use fallback silently
                return self._get_fallback_technical_questions(skill_analysis, question_count)
        except json.JSONDecodeError:
            # JSON parsing failed - use fallback silently
            return self._get_fallback_technical_questions(skill_analysis, question_count)
        except Exception as e:
            print(f"Error generating technical questions: {e}")
            return self._get_fallback_technical_questions(skill_analysis, question_count)
    
    async def _generate_experience_questions(
        self,
        resume_data: Dict[str, Any],
        job_description: Dict[str, Any],
        allocation: int
    ) -> List[Dict[str, Any]]:
        """Generate experience-based questions"""
        
        question_count = max(1, allocation // 15)
        
        prompt = f"""
        Generate {question_count} experience-based interview questions:
        
        Candidate Experience: {resume_data.get('experience_years', 0)} years
        Previous Roles: {resume_data.get('previous_roles', [])}
        Target Role: {job_description.get('title', '')}
        Required Experience: {job_description.get('experience_level', '')}
        
        Focus on:
        1. Relevance of past experience
        2. Career progression
        3. Specific project challenges
        4. Leadership and teamwork
        
        Return as JSON array with structure:
        [{{"question": "...", "category": "experience", "focus": "...", "follow_up": "..."}}]
        """
        
        try:
            response = await self._call_openai(prompt)
            if response.strip():  # Only parse if we got a response
                questions = json.loads(response)
                return questions[:question_count]
            else:
                # No API response - use fallback silently
                return self._get_fallback_experience_questions(question_count)
        except json.JSONDecodeError:
            # JSON parsing failed - use fallback silently
            return self._get_fallback_experience_questions(question_count)
        except Exception as e:
            print(f"Error generating experience questions: {e}")
            return self._get_fallback_experience_questions(question_count)
    
    async def _generate_problem_solving_questions(
        self,
        job_description: Dict[str, Any],
        allocation: int,
        difficulty: str
    ) -> List[Dict[str, Any]]:
        """Generate problem-solving questions"""
        
        question_count = max(1, allocation // 20)
        
        # Problem-solving questions are more generic but role-specific
        fallback_questions = [
            {
                "question": "Describe a challenging technical problem you solved recently. What was your approach?",
                "category": "problem_solving",
                "focus": "analytical_thinking",
                "follow_up": "What would you do differently if you faced a similar problem again?"
            },
            {
                "question": "How do you approach debugging a complex issue when you have limited information?",
                "category": "problem_solving", 
                "focus": "systematic_thinking",
                "follow_up": "Can you walk me through a specific example?"
            }
        ]
        
        return fallback_questions[:question_count]
    
    async def _generate_cultural_fit_questions(
        self,
        job_description: Dict[str, Any],
        allocation: int
    ) -> List[Dict[str, Any]]:
        """Generate cultural fit questions"""
        
        question_count = max(1, allocation // 10)
        
        fallback_questions = [
            {
                "question": "What type of work environment helps you be most productive?",
                "category": "cultural_fit",
                "focus": "work_style",
                "follow_up": "How do you handle feedback and criticism?"
            },
            {
                "question": "Describe a time when you had to work with a difficult team member. How did you handle it?",
                "category": "cultural_fit",
                "focus": "teamwork",
                "follow_up": "What did you learn from that experience?"
            }
        ]
        
        return fallback_questions[:question_count]
    
    def _prioritize_questions(self, questions: List[Dict[str, Any]], max_count: int) -> List[Dict[str, Any]]:
        """Prioritize and limit questions based on importance"""
        
        def get_priority(question):
            category = question.get("category", "cultural_fit")
            # Map categories to priority order
            if "technical" in category:
                return 0
            elif "experience" in category:
                return 1
            elif "problem" in category:
                return 2
            else:
                return 3
        
        sorted_questions = sorted(questions, key=get_priority)
        return sorted_questions[:max_count]
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API for question generation"""
        if not self.openai_client:
            # Return empty string to trigger fallback questions
            return ""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert interview question generator. Generate relevant, insightful questions that help evaluate candidates effectively."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI: {e}")
            return ""  # Trigger fallback
    
    def _get_fallback_technical_questions(self, skill_analysis: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """Fallback technical questions when API fails"""
        fallback = [
            {
                "question": f"Can you explain your experience with {skill}?",
                "category": "technical",
                "skill": skill,
                "difficulty": "medium",
                "follow_up": "How would you solve a performance issue related to this?"
            } for skill in skill_analysis.get("matching_skills", ["programming"])[:count]
        ]
        return fallback
    
    def _get_fallback_experience_questions(self, count: int) -> List[Dict[str, Any]]:
        """Fallback experience questions when API fails"""
        fallback = [
            {
                "question": "Tell me about your most challenging project and how you handled it.",
                "category": "experience",
                "focus": "project_management",
                "follow_up": "What would you do differently if you had to do it again?"
            },
            {
                "question": "Describe a time when you had to learn a new technology quickly.",
                "category": "experience",
                "focus": "adaptability",
                "follow_up": "How do you typically approach learning new skills?"
            }
        ]
        return fallback[:count]
