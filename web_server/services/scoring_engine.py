"""
Scoring Engine - Multi-attribute real-time evaluation system
"""

import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import openai
import os

class ScoringEngine:
    def __init__(self):
        # No default API key - must be provided per-request from user's database
        self.default_api_key = None  # Removed env fallback for security
        
        # Default scoring weights and thresholds
        self.default_weights = {
            "correctness": 0.25,        # Factual accuracy of answers
            "terminology": 0.20,        # Use of correct technical terms
            "confidence": 0.15,         # Speaking confidence and clarity
            "experience_relevance": 0.20, # Relevance to past experience
            "problem_solving": 0.20     # Analytical thinking approach
        }
        
        self.scoring_thresholds = {
            "excellent": 90,
            "good": 75,
            "average": 60,
            "poor": 40
        }
    
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
        """Check if scoring engine is working
        
        Args:
            api_key: Optional API key. If not provided, uses default from env.
        """
        key = api_key or self.default_api_key
        return "operational" if key else "missing_api_key"
    
    async def evaluate_response(
        self,
        question: Dict[str, Any],
        candidate_response: str,
        context: Dict[str, Any] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate a single candidate response
        
        Args:
            question: Question dictionary
            candidate_response: Candidate's response text
            context: Optional context with job_description, resume_data, scoring_config
            api_key: Optional OpenAI API key. If not provided, uses default from env.
        """
        # Extract scoring context
        job_description = context.get("job_description", {}) if context else {}
        resume_data = context.get("resume_data", {}) if context else {}
        scoring_config = context.get("scoring_config", self.default_weights) if context else self.default_weights
        
        # Generate detailed evaluation
        evaluation = await self._comprehensive_evaluation(
            question, candidate_response, job_description, resume_data, scoring_config, api_key=api_key
        )
        
        # Calculate weighted overall score
        overall_score = self._calculate_overall_score(evaluation, scoring_config)
        
        return {
            "question_id": question.get("id", "unknown"),
            "individual_scores": evaluation,
            "overall_score": overall_score,
            "score_category": self._get_score_category(overall_score),
            "feedback": evaluation.get("feedback", ""),
            "strengths": evaluation.get("strengths", []),
            "areas_for_improvement": evaluation.get("improvements", []),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _comprehensive_evaluation(
        self,
        question: Dict[str, Any],
        response: str,
        job_description: Dict[str, Any],
        resume_data: Dict[str, Any],
        scoring_config: Dict[str, float],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform comprehensive AI-powered evaluation
        
        Args:
            question: Question dictionary
            response: Candidate response
            job_description: Job description data
            resume_data: Resume data
            scoring_config: Scoring weights configuration
            api_key: Optional OpenAI API key. If not provided, uses default from env.
        """
        evaluation_prompt = f"""
        Evaluate this interview response across multiple dimensions:
        
        QUESTION: {question.get('question', '')}
        QUESTION CATEGORY: {question.get('category', 'general')}
        EXPECTED SKILL: {question.get('skill', 'general')}
        
        CANDIDATE RESPONSE: {response}
        
        CANDIDATE BACKGROUND:
        - Skills: {resume_data.get('skills', [])}
        - Experience: {resume_data.get('experience_years', 0)} years
        - Previous Roles: {resume_data.get('previous_roles', [])}
        
        JOB REQUIREMENTS:
        - Required Skills: {job_description.get('skills_required', [])}
        - Experience Level: {job_description.get('experience_level', '')}
        - Position: {job_description.get('title', '')}
        
        Evaluate on these dimensions (0-100 scale):
        1. CORRECTNESS: Factual accuracy and completeness of the answer
        2. TERMINOLOGY: Proper use of technical/industry terms
        3. CONFIDENCE: Speaking clarity, hesitation, confidence level
        4. EXPERIENCE_RELEVANCE: How well the answer relates to their background
        5. PROBLEM_SOLVING: Analytical thinking and approach demonstrated
        
        Also provide:
        - Brief feedback (2-3 sentences)
        - 2-3 key strengths shown in the response
        - 2-3 areas for improvement
        
        Return as JSON:
        {{
            "correctness": 85,
            "terminology": 78,
            "confidence": 82,
            "experience_relevance": 90,
            "problem_solving": 75,
            "feedback": "Strong technical knowledge demonstrated...",
            "strengths": ["Clear explanation", "Good examples"],
            "improvements": ["More specific examples", "Deeper technical detail"]
        }}
        """
        
        try:
            response_text = await self._call_openai_evaluation(evaluation_prompt, api_key=api_key)
            evaluation = json.loads(response_text)
            return evaluation
        except Exception as e:
            print(f"Error in AI evaluation: {e}")
            return self._fallback_evaluation(response, question)
    
    def _calculate_overall_score(self, evaluation: Dict[str, Any], weights: Dict[str, float]) -> float:
        """Calculate weighted overall score"""
        total_score = 0
        total_weight = 0
        
        for dimension, weight in weights.items():
            if dimension in evaluation:
                total_score += evaluation[dimension] * weight
                total_weight += weight
        
        return round(total_score / total_weight if total_weight > 0 else 0, 1)
    
    def _get_score_category(self, score: float) -> str:
        """Get score category based on thresholds"""
        if score >= self.scoring_thresholds["excellent"]:
            return "excellent"
        elif score >= self.scoring_thresholds["good"]:
            return "good"
        elif score >= self.scoring_thresholds["average"]:
            return "average"
        else:
            return "poor"
    
    async def _call_openai_evaluation(self, prompt: str, api_key: Optional[str] = None) -> str:
        """Call OpenAI for detailed evaluation
        
        Args:
            prompt: Evaluation prompt
            api_key: Optional OpenAI API key. If not provided, uses default from env.
        
        Returns:
            Response text
        
        Raises:
            Exception if API call fails
        """
        client = self._get_openai_client(api_key)
        if not client:
            raise ValueError("OpenAI API key not available")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert interview evaluator. Provide objective, constructive assessments of candidate responses. Be fair but thorough in your evaluation."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for consistent scoring
            max_tokens=800
        )
        return response.choices[0].message.content
    
    def _fallback_evaluation(self, response: str, question: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback evaluation when AI fails"""
        # Simple heuristic-based evaluation
        response_length = len(response.split())
        
        # Basic scoring based on response length and keywords
        base_score = min(80, max(40, response_length * 2))  # 40-80 based on length
        
        return {
            "correctness": base_score,
            "terminology": base_score - 5,
            "confidence": base_score + 5,
            "experience_relevance": base_score,
            "problem_solving": base_score - 10,
            "feedback": "Technical evaluation temporarily unavailable. Score based on response completeness.",
            "strengths": ["Provided a response", "Engaged with the question"],
            "improvements": ["More detailed analysis needed", "Consider specific examples"]
        }
    
    async def calculate_interview_summary(self, all_evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate final interview summary and recommendation"""
        if not all_evaluations:
            return {"overall_score": 0, "recommendation": "insufficient_data"}
        
        # Calculate average scores across all dimensions
        dimension_averages = {}
        dimensions = ["correctness", "terminology", "confidence", "experience_relevance", "problem_solving"]
        
        for dimension in dimensions:
            scores = [eval_data["individual_scores"].get(dimension, 0) for eval_data in all_evaluations]
            dimension_averages[dimension] = round(sum(scores) / len(scores), 1) if scores else 0
        
        # Calculate overall interview score
        overall_score = sum(dimension_averages.values()) / len(dimension_averages)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(overall_score, dimension_averages)
        
        # Identify top strengths and areas for improvement
        strengths = self._extract_common_themes([eval_data["strengths"] for eval_data in all_evaluations])
        improvements = self._extract_common_themes([eval_data["areas_for_improvement"] for eval_data in all_evaluations])
        
        return {
            "overall_score": round(overall_score, 1),
            "dimension_scores": dimension_averages,
            "score_category": self._get_score_category(overall_score),
            "recommendation": recommendation,
            "top_strengths": strengths[:3],
            "key_improvements": improvements[:3],
            "total_questions": len(all_evaluations),
            "evaluation_date": datetime.now().isoformat()
        }
    
    def _generate_recommendation(self, overall_score: float, dimensions: Dict[str, float]) -> str:
        """Generate hiring recommendation based on scores"""
        if overall_score >= 85:
            return "strong_hire"
        elif overall_score >= 75:
            return "hire"
        elif overall_score >= 60:
            return "maybe"
        else:
            return "no_hire"
    
    def _extract_common_themes(self, theme_lists: List[List[str]]) -> List[str]:
        """Extract common themes from multiple lists"""
        all_themes = [theme for themes in theme_lists for theme in themes]
        # Simple frequency-based extraction (in real implementation, use NLP)
        theme_counts = {}
        for theme in all_themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
        
        return sorted(theme_counts.keys(), key=lambda x: theme_counts[x], reverse=True)
    
    def update_scoring_weights(self, new_weights: Dict[str, float]):
        """Update scoring weights based on feedback"""
        # Normalize weights to sum to 1.0
        total_weight = sum(new_weights.values())
        if total_weight > 0:
            self.default_weights = {k: v/total_weight for k, v in new_weights.items()}
    
    def get_scoring_config(self) -> Dict[str, Any]:
        """Get current scoring configuration"""
        return {
            "weights": self.default_weights,
            "thresholds": self.scoring_thresholds,
            "dimensions": list(self.default_weights.keys())
        }
