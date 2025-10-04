"""
Scoring Engine Configuration

This file contains all tunable parameters for the interview scoring system.
Adjust these values to control scoring strictness, weights, and evaluation criteria.
"""

# Scoring Strictness Level
# Options: "lenient" (1-5), "moderate" (3-7), "strict" (5-9), "very_strict" (7-10)
SCORING_STRICTNESS = "moderate"

# Strictness Multipliers
STRICTNESS_MULTIPLIERS = {
    "lenient": 1.2,      # Boost scores by 20%
    "moderate": 1.0,     # No adjustment
    "strict": 0.85,      # Reduce scores by 15%
    "very_strict": 0.70  # Reduce scores by 30%
}

# Minimum passing score (out of 100)
MINIMUM_PASSING_SCORE = 60

# Score Category Thresholds
SCORE_CATEGORIES = {
    "excellent": 85,
    "good": 70,
    "average": 55,
    "below_average": 40,
    "poor": 0
}

# Individual Scoring Criteria Weights (must sum to 1.0)
SCORING_WEIGHTS = {
    "correctness": 0.30,           # Technical accuracy and correctness
    "terminology": 0.20,           # Use of industry-specific terms
    "confidence": 0.15,            # Communication clarity and confidence
    "experience_relevance": 0.20,  # Relevance to job requirements
    "problem_solving": 0.15        # Problem-solving approach
}

# LLM Model Configuration for Scoring
SCORING_LLM_MODEL = "gpt-4o-mini"  # Cost-effective model for analysis
SCORING_LLM_TEMPERATURE = 0.3      # Low temperature for consistent scoring

# Scoring Evaluation Criteria Descriptions
EVALUATION_CRITERIA = {
    "correctness": {
        "description": "Accuracy of technical answers and factual correctness",
        "excellent": "All answers are technically accurate with no errors",
        "good": "Most answers are correct with minor inaccuracies",
        "average": "Some correct answers but with notable gaps",
        "poor": "Significant errors or fundamental misunderstandings"
    },
    "terminology": {
        "description": "Use of appropriate industry terminology and technical vocabulary",
        "excellent": "Consistently uses correct technical terms and industry jargon",
        "good": "Uses technical terms appropriately most of the time",
        "average": "Limited use of technical vocabulary",
        "poor": "Lacks technical terminology or uses terms incorrectly"
    },
    "confidence": {
        "description": "Communication clarity, articulation, and confidence level",
        "excellent": "Clear, confident responses with good articulation",
        "good": "Generally clear with minor hesitations",
        "average": "Some clarity issues or noticeable hesitation",
        "poor": "Unclear communication or very hesitant responses"
    },
    "experience_relevance": {
        "description": "Relevance of past experience to the role requirements",
        "excellent": "Experience directly aligns with job requirements",
        "good": "Experience is mostly relevant with some transferable skills",
        "average": "Some relevant experience but significant gaps",
        "poor": "Limited relevant experience for the role"
    },
    "problem_solving": {
        "description": "Approach to solving problems and analytical thinking",
        "excellent": "Demonstrates structured problem-solving with clear methodology",
        "good": "Shows good problem-solving approach with minor gaps",
        "average": "Basic problem-solving ability with some guidance needed",
        "poor": "Struggles with problem-solving or lacks clear approach"
    }
}

# Response Quality Indicators (for LLM to look for)
POSITIVE_INDICATORS = [
    "Clear and structured responses",
    "Specific examples from past experience",
    "Technical depth and understanding",
    "Proactive questions and engagement",
    "Problem-solving methodology",
    "Industry best practices mentioned",
    "Quantifiable achievements discussed"
]

NEGATIVE_INDICATORS = [
    "Vague or generic answers",
    "Lack of specific examples",
    "Technical inaccuracies",
    "Excessive hesitation or uncertainty",
    "Off-topic responses",
    "Unable to explain concepts clearly",
    "No questions or engagement"
]

# Minimum transcript length for valid scoring
MIN_TRANSCRIPT_EXCHANGES = 5  # Need at least 5 exchanges for meaningful scoring

# LLM Timeout Configuration
SCORING_TIMEOUT_SECONDS = 30

# Detailed Feedback Requirements
PROVIDE_DETAILED_FEEDBACK = True
INCLUDE_IMPROVEMENT_SUGGESTIONS = True
MAX_FEEDBACK_LENGTH = 500  # characters

# Recommendation Thresholds
RECOMMENDATION_THRESHOLDS = {
    "strong_yes": 80,      # Highly recommend for next round
    "yes": 65,             # Recommend with minor reservations
    "maybe": 50,           # On the fence, needs discussion
    "no": 35,              # Do not recommend
    "strong_no": 0         # Strongly do not recommend
}

