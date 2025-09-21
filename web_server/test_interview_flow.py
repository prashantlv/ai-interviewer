#!/usr/bin/env python3
"""
Test Interview Flow - Simulates complete interview process
"""

import asyncio
import json
from services.question_engine import QuestionEngine
from services.scoring_engine import ScoringEngine

async def test_complete_interview():
    print("🎯 Testing Complete Interview Flow")
    print("=" * 50)
    
    # Initialize engines
    question_engine = QuestionEngine()
    scoring_engine = ScoringEngine()
    
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
        "I have 4 years of experience with Python, mainly using Django for web development. I've worked on several e-commerce projects.",
        "I use PostgreSQL primarily, but I'm familiar with MongoDB concepts. I'd need some time to get up to speed with MongoDB specifics.",
        "In my last project, I optimized database queries which reduced response time by 40%. I used indexing and query optimization techniques.",
        "I prefer agile methodology with daily standups. I work well in collaborative environments and enjoy pair programming.",
        "My biggest challenge was implementing a real-time notification system. I solved it using WebSockets and Redis for message queuing."
    ]
    
    evaluations = []
    print("📊 Evaluating Responses...")
    
    for i, (question, response) in enumerate(zip(questions, mock_responses), 1):
        print(f"\n   Question {i}: {question.get('question', '')}")
        print(f"   Response: {response}")
        
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
    print("=" * 50)
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

if __name__ == "__main__":
    asyncio.run(test_complete_interview())
