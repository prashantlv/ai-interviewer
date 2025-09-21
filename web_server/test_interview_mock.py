#!/usr/bin/env python3
"""
Test Interview Flow - Mock Version (No API Keys Required)
Demonstrates the complete interview system with fallback data
"""

import asyncio
import json
from datetime import datetime

# Mock Question Engine (No OpenAI required)
class MockQuestionEngine:
    def __init__(self):
        self.default_config = {
            "difficulty_level": "medium",
            "question_count": 5,
            "strictness": 0.7
        }
    
    def health_check(self):
        return "operational"
    
    async def generate_questions(self, job_description, resume_data, interview_config=None):
        """Generate mock questions based on job description and resume"""
        config = {**self.default_config, **(interview_config or {})}
        
        # Analyze skills for targeted questions
        jd_skills = job_description.get("skills_required", [])
        resume_skills = resume_data.get("skills", [])
        missing_skills = [skill for skill in jd_skills if skill not in resume_skills]
        
        # Generate questions based on the role and skills
        questions = []
        
        # Technical questions based on required skills
        for skill in jd_skills[:2]:
            questions.append({
                "question": f"Can you explain your experience with {skill} and how you've used it in recent projects?",
                "category": "technical",
                "skill": skill,
                "difficulty": config["difficulty_level"],
                "follow_up": f"What challenges have you faced when working with {skill}?"
            })
        
        # Experience-based question
        questions.append({
            "question": f"Tell me about a challenging {job_description.get('title', 'development')} project you worked on recently.",
            "category": "experience", 
            "focus": "project_management",
            "follow_up": "What would you do differently if you had to do it again?"
        })
        
        # Problem-solving question
        questions.append({
            "question": "How do you approach debugging a complex issue when you have limited information?",
            "category": "problem_solving",
            "focus": "analytical_thinking", 
            "follow_up": "Can you walk me through a specific example?"
        })
        
        # Cultural fit question
        questions.append({
            "question": "What type of work environment helps you be most productive?",
            "category": "cultural_fit",
            "focus": "work_style",
            "follow_up": "How do you handle feedback and criticism?"
        })
        
        return questions[:config["question_count"]]

# Mock Scoring Engine (No OpenAI required)
class MockScoringEngine:
    def __init__(self):
        self.default_weights = {
            "correctness": 0.25,
            "terminology": 0.20,
            "confidence": 0.15,
            "experience_relevance": 0.20,
            "problem_solving": 0.20
        }
        
        self.scoring_thresholds = {
            "excellent": 90,
            "good": 75,
            "average": 60,
            "poor": 40
        }
    
    def health_check(self):
        return "operational"
    
    async def evaluate_response(self, question, candidate_response, context=None):
        """Mock evaluation based on response length and keywords"""
        response_length = len(candidate_response.split())
        
        # Simple scoring based on response quality indicators
        base_score = min(85, max(45, response_length * 2))  # 45-85 based on length
        
        # Adjust based on question category
        category = question.get("category", "general")
        if category == "technical":
            # Look for technical terms
            tech_terms = ["API", "database", "framework", "algorithm", "optimization", "implementation"]
            tech_score = sum(1 for term in tech_terms if term.lower() in candidate_response.lower()) * 5
            base_score += tech_score
        elif category == "experience":
            # Look for experience indicators
            exp_terms = ["project", "team", "challenge", "solution", "result", "learned"]
            exp_score = sum(1 for term in exp_terms if term.lower() in candidate_response.lower()) * 3
            base_score += exp_score
        
        # Ensure score is within bounds
        base_score = min(95, max(40, base_score))
        
        # Generate individual dimension scores
        evaluation = {
            "correctness": min(100, base_score + (hash(candidate_response) % 10 - 5)),
            "terminology": min(100, base_score + (hash(candidate_response) % 8 - 4)),
            "confidence": min(100, base_score + (hash(candidate_response) % 12 - 6)),
            "experience_relevance": min(100, base_score + (hash(candidate_response) % 6 - 3)),
            "problem_solving": min(100, base_score + (hash(candidate_response) % 14 - 7))
        }
        
        # Calculate overall score
        overall_score = sum(evaluation.values()) / len(evaluation)
        
        return {
            "question_id": question.get("id", "unknown"),
            "individual_scores": evaluation,
            "overall_score": round(overall_score, 1),
            "score_category": self._get_score_category(overall_score),
            "feedback": f"Response demonstrates {self._get_score_category(overall_score)} understanding of the topic.",
            "strengths": ["Clear communication", "Relevant examples", "Good technical understanding"][:2],
            "areas_for_improvement": ["More specific examples", "Deeper technical detail", "Quantitative results"][:2],
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_score_category(self, score):
        if score >= self.scoring_thresholds["excellent"]:
            return "excellent"
        elif score >= self.scoring_thresholds["good"]:
            return "good"
        elif score >= self.scoring_thresholds["average"]:
            return "average"
        else:
            return "poor"
    
    async def calculate_interview_summary(self, all_evaluations):
        """Calculate final interview summary"""
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
        if overall_score >= 85:
            recommendation = "strong_hire"
        elif overall_score >= 75:
            recommendation = "hire"
        elif overall_score >= 60:
            recommendation = "maybe"
        else:
            recommendation = "no_hire"
        
        # Extract strengths and improvements
        all_strengths = []
        all_improvements = []
        for eval_data in all_evaluations:
            all_strengths.extend(eval_data.get("strengths", []))
            all_improvements.extend(eval_data.get("areas_for_improvement", []))
        
        return {
            "overall_score": round(overall_score, 1),
            "dimension_scores": dimension_averages,
            "score_category": self._get_score_category(overall_score),
            "recommendation": recommendation,
            "top_strengths": list(set(all_strengths))[:3],
            "key_improvements": list(set(all_improvements))[:3],
            "total_questions": len(all_evaluations),
            "evaluation_date": datetime.now().isoformat()
        }

async def test_complete_interview():
    print("🎯 Testing Complete Interview Flow (Mock Mode)")
    print("=" * 60)
    
    # Initialize mock engines
    question_engine = MockQuestionEngine()
    scoring_engine = MockScoringEngine()
    
    # 1. Mock job description and resume data
    job_description = {
        "title": "Senior Python Developer",
        "skills_required": ["Python", "FastAPI", "MongoDB", "React"],
        "experience_level": "Senior",
        "department": "Engineering"
    }
    
    resume_data = {
        "skills": ["Python", "Django", "JavaScript", "PostgreSQL"],
        "experience_years": 4,
        "previous_roles": ["Junior Developer", "Python Developer"],
        "education": "Computer Science"
    }
    
    interview_config = {
        "difficulty_level": "medium",
        "question_count": 5,
        "strictness": 0.7
    }
    
    print("📝 Job Description:")
    print(f"   Position: {job_description['title']}")
    print(f"   Required Skills: {job_description['skills_required']}")
    print()
    
    print("👤 Candidate Profile:")
    print(f"   Experience: {resume_data['experience_years']} years")
    print(f"   Skills: {resume_data['skills']}")
    print()
    
    # 2. Generate interview questions
    print("🤖 Generating Interview Questions...")
    questions = await question_engine.generate_questions(
        job_description=job_description,
        resume_data=resume_data,
        interview_config=interview_config
    )
    
    print(f"✅ Generated {len(questions)} questions:")
    for i, q in enumerate(questions, 1):
        print(f"   {i}. [{q.get('category', 'general')}] {q.get('question', '')}")
    print()
    
    # 3. Simulate candidate responses and scoring
    mock_responses = [
        "I have 4 years of experience with Python, mainly using Django for web development. I've worked on several e-commerce projects where I implemented RESTful APIs and optimized database queries for better performance.",
        
        "I'm very familiar with FastAPI - I've used it in my recent projects to build high-performance APIs. I love its automatic documentation generation and type hints. For MongoDB, I have some experience but primarily work with PostgreSQL.",
        
        "In my last project, I had to optimize a slow-performing e-commerce platform. The challenge was identifying bottlenecks in the order processing system. I used profiling tools, implemented caching strategies, and redesigned some database queries. The result was a 60% improvement in response time.",
        
        "I prefer collaborative environments with clear communication. I work well in agile teams with regular standups and code reviews. I believe in continuous learning and enjoy mentoring junior developers when possible.",
        
        "When debugging complex issues, I start by reproducing the problem consistently. Then I use logging and debugging tools to trace the execution flow. I break down the problem into smaller components and test each part systematically. Documentation and version control history often provide valuable clues."
    ]
    
    evaluations = []
    print("📊 Evaluating Responses...")
    
    for i, (question, response) in enumerate(zip(questions, mock_responses), 1):
        print(f"\n   Question {i}: {question.get('question', '')}")
        print(f"   Response: {response[:100]}..." if len(response) > 100 else f"   Response: {response}")
        
        # Score the response
        evaluation = await scoring_engine.evaluate_response(
            question=question,
            candidate_response=response,
            context={
                "job_description": job_description,
                "resume_data": resume_data,
                "scoring_config": scoring_engine.default_weights
            }
        )
        
        evaluations.append(evaluation)
        print(f"   ✅ Score: {evaluation['overall_score']}/100 ({evaluation['score_category']})")
    
    # 4. Generate final interview summary
    print("\n📋 Generating Final Interview Report...")
    final_summary = await scoring_engine.calculate_interview_summary(evaluations)
    
    print("\n🎯 FINAL INTERVIEW RESULTS:")
    print("=" * 60)
    print(f"Overall Score: {final_summary['overall_score']}/100")
    print(f"Recommendation: {final_summary['recommendation'].upper()}")
    print(f"Score Category: {final_summary['score_category'].upper()}")
    
    print("\n📊 Dimension Breakdown:")
    for dimension, score in final_summary['dimension_scores'].items():
        print(f"   {dimension.replace('_', ' ').title()}: {score}/100")
    
    print(f"\n✨ Top Strengths:")
    for strength in final_summary.get('top_strengths', [])[:3]:
        print(f"   • {strength}")
    
    print(f"\n🎯 Areas for Improvement:")
    for improvement in final_summary.get('key_improvements', [])[:3]:
        print(f"   • {improvement}")
    
    print("\n🎉 Interview Flow Test Complete!")
    print("\nℹ️  This is a mock demonstration. In production:")
    print("   • Questions would be generated by OpenAI based on JD+Resume")
    print("   • Scoring would use AI analysis for more accurate evaluation")
    print("   • Real-time integration with Pipecat bot for live interviews")

if __name__ == "__main__":
    asyncio.run(test_complete_interview())
