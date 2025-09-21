#!/usr/bin/env python3
"""Debug question engine issues"""

import sys
import asyncio
sys.path.append('/home/prashant/Playground/personal/consult/ai-interviewer/web_server')

from services.static_data import get_demo_interview_config
from services.question_engine import QuestionEngine

async def debug_question_generation():
    print("🔍 Debugging Question Engine")
    print("=" * 50)
    
    # Get static data
    config = get_demo_interview_config()
    print(f"✅ Static config loaded")
    print(f"📝 JD Title: {config['job_description']['title']}")
    print(f"👤 Candidate: {config['candidate_info']['name']}")
    
    # Initialize question engine
    question_engine = QuestionEngine()
    print(f"✅ Question engine initialized")
    
    try:
        # Try to generate questions
        questions = await question_engine.generate_questions(
            job_description=config["job_description"],
            resume_data=config["resume_data"],
            interview_config=config.get("interview_settings", {})
        )
        
        print(f"✅ Questions generated: {len(questions)}")
        for i, q in enumerate(questions, 1):
            print(f"   {i}. [{q.get('category', 'unknown')}] {q.get('question', '')[:60]}...")
            
    except Exception as e:
        print(f"❌ Error generating questions: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_question_generation())
