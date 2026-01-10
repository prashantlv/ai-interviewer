"""
AI Interview Scoring Engine

Uses LLM to analyze interview transcripts and generate detailed scores
based on multiple evaluation criteria.
"""

import os
import json
from typing import Dict, Any, List, Optional
from loguru import logger
from openai import AsyncOpenAI

# Import scoring configuration
from scoring_config import (
    SCORING_STRICTNESS,
    STRICTNESS_MULTIPLIERS,
    MINIMUM_PASSING_SCORE,
    SCORE_CATEGORIES,
    SCORING_WEIGHTS,
    SCORING_LLM_MODEL,
    SCORING_LLM_TEMPERATURE,
    EVALUATION_CRITERIA,
    POSITIVE_INDICATORS,
    NEGATIVE_INDICATORS,
    MIN_TRANSCRIPT_EXCHANGES,
    PROVIDE_DETAILED_FEEDBACK,
    INCLUDE_IMPROVEMENT_SUGGESTIONS,
    RECOMMENDATION_THRESHOLDS,
)


class ScoringEngine:
    """LLM-based scoring engine for interview evaluation"""
    
    def __init__(self, api_key: Optional[str] = None, scoring_config: Optional[Dict[str, Any]] = None):
        """Initialize scoring engine with OpenAI client and optional DB config"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("No OpenAI API key provided - scoring will fail")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)
        
        # Use provided config or fall back to defaults from config file
        if scoring_config:
            logger.info(f"Using DB-based scoring config: {scoring_config.get('name', 'Unknown')}")
            self.config = scoring_config
            self.strictness = scoring_config.get("strictness", SCORING_STRICTNESS)
            self.strictness_multiplier = scoring_config.get("strictness_multiplier", 1.0)
            self.weights = scoring_config.get("weights", SCORING_WEIGHTS)
            self.score_categories = scoring_config.get("score_categories", SCORE_CATEGORIES)
            self.recommendation_thresholds = scoring_config.get("recommendation_thresholds", RECOMMENDATION_THRESHOLDS)
            self.config_source = "database"
            self.config_id = scoring_config.get("config_id", "unknown")
            self.config_level = scoring_config.get("level", "unknown")
        else:
            logger.info("Using file-based scoring config (fallback)")
            self.config = None
            self.strictness = SCORING_STRICTNESS
            self.strictness_multiplier = STRICTNESS_MULTIPLIERS.get(self.strictness, 1.0)
            self.weights = SCORING_WEIGHTS
            self.score_categories = SCORE_CATEGORIES
            self.recommendation_thresholds = RECOMMENDATION_THRESHOLDS
            self.config_source = "file"
            self.config_id = "file_based"
            self.config_level = self.strictness
        
        logger.info(f"Scoring Engine initialized - Source: {self.config_source}, Level: {self.config_level}, Multiplier: {self.strictness_multiplier}")
    
    def _build_scoring_prompt(
        self,
        transcript: List[Dict[str, str]],
        job_description: Dict[str, Any],
        questions_asked: List[str]
    ) -> str:
        """Build the scoring prompt with all configuration parameters"""
        
        # Format transcript for readability
        transcript_text = "\n".join([
            f"{entry['role'].upper()}: {entry['content']}"
            for entry in transcript
        ])
        
        # Format questions
        questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions_asked)])
        
        # Format evaluation criteria (use instance weights)
        criteria_details = "\n".join([
            f"- **{criterion.upper()}** (Weight: {self.weights[criterion]*100:.0f}%):\n"
            f"  {EVALUATION_CRITERIA[criterion]['description']}\n"
            f"  Excellent: {EVALUATION_CRITERIA[criterion]['excellent']}\n"
            f"  Good: {EVALUATION_CRITERIA[criterion]['good']}\n"
            f"  Average: {EVALUATION_CRITERIA[criterion]['average']}\n"
            f"  Poor: {EVALUATION_CRITERIA[criterion]['poor']}\n"
            for criterion in self.weights.keys()
        ])
        
        # Format positive/negative indicators
        positive_text = "\n".join([f"  ✓ {ind}" for ind in POSITIVE_INDICATORS])
        negative_text = "\n".join([f"  ✗ {ind}" for ind in NEGATIVE_INDICATORS])
        
        prompt = f"""You are an expert technical interviewer and talent evaluator. Your task is to analyze this interview transcript and provide a detailed, objective scoring.

**JOB DETAILS:**
- Position: {job_description.get('title', 'Not specified')}
- Company: {job_description.get('company', 'Not specified')}
- Required Skills: {', '.join(job_description.get('required_skills', ['Not specified']))}

**QUESTIONS ASKED:**
{questions_text}

**INTERVIEW TRANSCRIPT:**
{transcript_text}

**SCORING STRICTNESS:** {self.strictness.upper()}
- You should evaluate this interview with a **{self.strictness}** level of strictness.
- Be fair but maintain {self.strictness} standards throughout your evaluation.

**EVALUATION CRITERIA:**
{criteria_details}

**POSITIVE INDICATORS TO LOOK FOR:**
{positive_text}

**NEGATIVE INDICATORS TO WATCH FOR:**
{negative_text}

**SCORING INSTRUCTIONS:**
1. Analyze each response carefully against the job requirements
2. Score each criterion from 0-100 based on the strictness level ({self.strictness})
3. Consider the overall quality of responses, not just quantity
4. Look for specific examples, technical depth, and clarity
5. Factor in communication skills and problem-solving approach

**OUTPUT FORMAT (MUST BE VALID JSON):**
{{
    "individual_scores": {{
        "correctness": <score 0-100>,
        "terminology": <score 0-100>,
        "confidence": <score 0-100>,
        "experience_relevance": <score 0-100>,
        "problem_solving": <score 0-100>
    }},
    "overall_score": <weighted average 0-100>,
    "score_category": "<excellent|good|average|below_average|poor>",
    "recommendation": "<strong_yes|yes|maybe|no|strong_no>",
    "feedback": "<detailed feedback about candidate's performance>",
    "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
    "improvement_suggestions": ["<suggestion 1>", "<suggestion 2>", "<suggestion 3>"]
}}

Provide your evaluation now as valid JSON only (no other text):"""
        
        return prompt
    
    async def score_interview(
        self,
        transcript: List[Dict[str, str]],
        job_description: Dict[str, Any],
        questions_asked: List[str]
    ) -> Dict[str, Any]:
        """Score an interview using LLM analysis"""
        
        # Validate inputs
        if not transcript:
            logger.warning("Empty transcript - returning default scores")
            return self._get_default_scores("Insufficient transcript for scoring")

        # Require at least some candidate content. If we only have AI messages
        # (e.g. candidate left immediately or STT failed), scoring would be meaningless.
        candidate_entries = [
            e for e in transcript
            if (e.get("role") == "candidate") and (e.get("content") or "").strip()
        ]
        candidate_word_count = sum(len((e.get("content") or "").strip().split()) for e in candidate_entries)

        if len(candidate_entries) == 0 or candidate_word_count < 3:
            logger.warning(
                "No/insufficient candidate responses in transcript "
                f"(candidate_entries={len(candidate_entries)}, candidate_words={candidate_word_count}) - returning default scores"
            )
            return self._get_default_scores("Insufficient candidate responses for scoring")

        if len(transcript) < MIN_TRANSCRIPT_EXCHANGES:
            logger.warning(f"Transcript too short ({len(transcript)} exchanges) - returning default scores")
            return self._get_default_scores("Insufficient transcript for scoring")
        
        if not self.client:
            logger.error("OpenAI client not initialized - cannot score interview")
            return self._get_default_scores("Scoring service unavailable")
        
        try:
            # Build the scoring prompt
            prompt = self._build_scoring_prompt(transcript, job_description, questions_asked)
            
            logger.info(f"Sending transcript to LLM for scoring (strictness: {self.strictness})...")
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=SCORING_LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical interviewer. Analyze transcripts and provide objective, detailed scores in JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=SCORING_LLM_TEMPERATURE,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Apply strictness multiplier to scores
            for criterion in result.get("individual_scores", {}).keys():
                original_score = result["individual_scores"][criterion]
                adjusted_score = min(100, original_score * self.strictness_multiplier)
                result["individual_scores"][criterion] = round(adjusted_score, 1)
            
            # Recalculate overall score with weights and strictness (use instance weights)
            overall_score = sum(
                result["individual_scores"].get(criterion, 0) * weight
                for criterion, weight in self.weights.items()
            )
            result["overall_score"] = round(overall_score, 1)
            
            # Add config metadata to result
            result["config_used"] = {
                "config_id": self.config_id,
                "config_level": self.config_level,
                "config_source": self.config_source,
                "strictness_multiplier": self.strictness_multiplier
            }
            
            # Determine score category
            result["score_category"] = self._get_score_category(result["overall_score"])
            
            # Determine recommendation
            result["recommendation"] = self._get_recommendation(result["overall_score"])
            
            logger.info(f"✅ Scoring complete - Overall: {result['overall_score']}/100 ({result['score_category']})")
            logger.info(f"   Recommendation: {result['recommendation']}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return self._get_default_scores("JSON parsing error")
        except Exception as e:
            logger.error(f"Error during scoring: {e}")
            return self._get_default_scores(f"Scoring error: {str(e)}")
    
    def _get_score_category(self, overall_score: float) -> str:
        """Determine score category based on thresholds (use instance thresholds)"""
        for category, threshold in sorted(self.score_categories.items(), key=lambda x: x[1], reverse=True):
            if overall_score >= threshold:
                return category
        return "poor"
    
    def _get_recommendation(self, overall_score: float) -> str:
        """Determine recommendation based on thresholds (use instance thresholds)"""
        for recommendation, threshold in sorted(self.recommendation_thresholds.items(), key=lambda x: x[1], reverse=True):
            if overall_score >= threshold:
                return recommendation
        return "strong_no"
    
    def _get_default_scores(self, reason: str) -> Dict[str, Any]:
        """Return default scores when scoring fails"""
        return {
            "individual_scores": {
                "correctness": 0,
                "terminology": 0,
                "confidence": 0,
                "experience_relevance": 0,
                "problem_solving": 0
            },
            "overall_score": 0,
            "score_category": "pending",
            "recommendation": "pending",
            "feedback": f"Unable to score interview: {reason}",
            "strengths": [],
            "weaknesses": [],
            "improvement_suggestions": []
        }

