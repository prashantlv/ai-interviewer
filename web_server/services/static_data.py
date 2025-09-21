"""
Static Job Description and Resume data for Milestone 2 demo
"""

from typing import Dict, Any

def get_static_job_description() -> Dict[str, Any]:
    """Returns static JD for demo purposes"""
    return {
        "title": "Senior Software Engineer - Full Stack",
        "company": "Hire2Inspire Tech Solutions",
        "experience_level": "5-7 years",
        "job_type": "Full-time",
        "location": "Remote / Bangalore",
        "description": """
We are looking for a Senior Software Engineer to join our growing engineering team. 
You will be responsible for developing scalable web applications and working with 
modern technologies including React, Node.js, Python, and cloud platforms.
        """,
        "skills_required": [
            "JavaScript/TypeScript",
            "React.js",
            "Node.js", 
            "Python",
            "REST APIs",
            "Database Design (SQL/NoSQL)",
            "AWS/Azure",
            "Git/Version Control",
            "Agile/Scrum",
            "Problem Solving"
        ],
        "responsibilities": [
            "Design and develop scalable web applications",
            "Collaborate with cross-functional teams",
            "Implement REST APIs and microservices",
            "Optimize application performance",
            "Code review and mentoring junior developers",
            "Participate in architectural decisions"
        ],
        "requirements": [
            "5+ years of software development experience",
            "Strong proficiency in JavaScript and Python",
            "Experience with React.js and modern frontend frameworks",
            "Knowledge of backend technologies (Node.js, Express)",
            "Database experience (PostgreSQL, MongoDB)",
            "Cloud platform experience (AWS/Azure)",
            "Excellent problem-solving skills",
            "Strong communication skills"
        ]
    }

def get_static_resume_data() -> Dict[str, Any]:
    """Returns static resume for demo purposes"""
    return {
        "candidate_name": "Priya Sharma",
        "email": "priya.sharma@email.com",
        "phone": "+91-9876543210",
        "location": "Bangalore, India",
        "experience_years": 6,
        "current_role": "Software Engineer",
        "current_company": "TechCorp Solutions",
        "skills": [
            "JavaScript",
            "TypeScript", 
            "React.js",
            "Node.js",
            "Python",
            "Django",
            "PostgreSQL",
            "MongoDB",
            "AWS",
            "Docker",
            "Git"
        ],
        "previous_roles": [
            {
                "title": "Software Engineer",
                "company": "TechCorp Solutions",
                "duration": "2021-Present",
                "description": "Developed full-stack web applications using React and Node.js. Built microservices architecture on AWS."
            },
            {
                "title": "Frontend Developer",
                "company": "Digital Innovations",
                "duration": "2019-2021", 
                "description": "Created responsive web interfaces using React.js. Collaborated with UX team for optimal user experience."
            },
            {
                "title": "Junior Developer",
                "company": "StartupXYZ",
                "duration": "2018-2019",
                "description": "Built web applications using Python Django. Learned database design and REST API development."
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Technology in Computer Science",
                "institution": "Indian Institute of Technology",
                "year": "2018",
                "cgpa": "8.2/10"
            }
        ],
        "projects": [
            {
                "name": "E-commerce Platform",
                "technologies": ["React", "Node.js", "MongoDB", "AWS"],
                "description": "Built a scalable e-commerce platform handling 10K+ users with real-time inventory management."
            },
            {
                "name": "Task Management System", 
                "technologies": ["Python", "Django", "PostgreSQL"],
                "description": "Developed a collaborative task management system with real-time notifications."
            }
        ],
        "certifications": [
            "AWS Solutions Architect Associate",
            "MongoDB Certified Developer"
        ]
    }

def get_demo_interview_config() -> Dict[str, Any]:
    """Returns complete interview configuration for demo"""
    return {
        "interview_id": "demo_interview_001",
        "job_description": get_static_job_description(),
        "resume_data": get_static_resume_data(),
        "scoring_config": {
            "correctness": 0.25,
            "terminology": 0.20,
            "confidence": 0.15,
            "experience_relevance": 0.20,
            "problem_solving": 0.20
        },
        "interview_settings": {
            "difficulty_level": "medium",
            "focus_areas": {
                "technical_skills": 40,    # % allocation
                "experience": 30,
                "problem_solving": 20,
                "cultural_fit": 10
            },
            "duration_minutes": 30,
            "question_count": 8
        },
        "candidate_info": {
            "name": "Priya Sharma",
            "experience_years": 6,
            "current_role": "Software Engineer",
            "skills_match": 85  # % match with JD requirements
        }
    }
