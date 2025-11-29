"""
Scoring Settings Router - UI and API for managing scoring configurations
"""

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, Optional
from dependencies import ScoringConfigDep, DbServiceDep
from loguru import logger

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Criteria descriptions for UI
CRITERIA_DESCRIPTIONS = {
    "correctness": {
        "name": "Technical Correctness",
        "description": "Accuracy of technical answers and factual correctness. Evaluates how well the candidate understands and explains technical concepts.",
        "icon": "✓"
    },
    "terminology": {
        "name": "Technical Terminology",
        "description": "Use of appropriate industry terminology and technical vocabulary. Assesses familiarity with domain-specific language and jargon.",
        "icon": "📚"
    },
    "confidence": {
        "name": "Communication & Confidence",
        "description": "Speaking clarity, articulation, and confidence level. Measures how effectively the candidate communicates their thoughts.",
        "icon": "💬"
    },
    "experience_relevance": {
        "name": "Experience Relevance",
        "description": "Relevance of past experience to the role requirements. Evaluates how well the candidate's background aligns with the job needs.",
        "icon": "🎯"
    },
    "problem_solving": {
        "name": "Problem Solving",
        "description": "Approach to solving problems and analytical thinking. Assesses structured problem-solving methodology and analytical skills.",
        "icon": "🧩"
    }
}

@router.get("/", response_class=HTMLResponse)
async def scoring_settings_page(
    request: Request,
    scoring_config: ScoringConfigDep
):
    """Main scoring settings page"""
    try:
        # Get all scoring configurations
        configs = await scoring_config.get_all_configs()
        
        # Organize by level
        configs_by_level = {}
        for config in configs:
            level = config.get("level", "unknown")
            configs_by_level[level] = config
        
        # Ensure we have all three levels
        levels = ["easy", "intermediate", "strict"]
        for level in levels:
            if level not in configs_by_level:
                # Fallback to default if missing
                config = await scoring_config.get_config_by_level(level)
                if config:
                    configs_by_level[level] = config
        
        return templates.TemplateResponse("scoring_settings.html", {
            "request": request,
            "configs": configs_by_level,
            "criteria_descriptions": CRITERIA_DESCRIPTIONS,
            "levels": levels
        })
    except Exception as e:
        logger.error(f"Error loading scoring settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/configs", response_class=JSONResponse)
async def get_all_configs_api(scoring_config: ScoringConfigDep):
    """API endpoint to get all scoring configurations"""
    try:
        configs = await scoring_config.get_all_configs()
        return {
            "success": True,
            "configs": configs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/configs/{level}", response_class=JSONResponse)
async def get_config_by_level_api(level: str, scoring_config: ScoringConfigDep):
    """API endpoint to get config by level"""
    try:
        config = await scoring_config.get_config_by_level(level)
        if not config:
            raise HTTPException(status_code=404, detail=f"Config not found for level: {level}")
        return {
            "success": True,
            "config": config
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/configs/{config_id}/update", response_class=JSONResponse)
async def update_config_api(
    config_id: str,
    request: Request,
    scoring_config: ScoringConfigDep
):
    """API endpoint to update scoring configuration"""
    try:
        data = await request.json()
        
        # Validate weights sum to 1.0
        if "weights" in data:
            weights = data["weights"]
            total = sum(float(v) for v in weights.values())
            if abs(total - 1.0) > 0.01:  # Allow small floating point errors
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": f"Weights must sum to 1.0 (current: {total:.2f})",
                        "total": round(total, 2)
                    }
                )
        
        # Update the config
        success = await scoring_config.update_config(config_id, data)
        if success:
            # Return updated config
            updated_config = await scoring_config.get_config_by_id(config_id)
            return {
                "success": True,
                "config": updated_config,
                "message": "Configuration updated successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Config not found or no changes made")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/configs/{config_id}/weights", response_class=JSONResponse)
async def update_weights_api(
    config_id: str,
    request: Request,
    scoring_config: ScoringConfigDep
):
    """API endpoint to update only weights (simplified)"""
    try:
        data = await request.json()
        weights = data.get("weights", {})
        
        # Validate weights sum to 1.0
        total = sum(float(v) for v in weights.values())
        if abs(total - 1.0) > 0.01:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"Weights must sum to 1.0 (current: {total:.2f})",
                    "total": round(total, 2)
                }
            )
        
        # Update only weights
        success = await scoring_config.update_config(config_id, {"weights": weights})
        if success:
            updated_config = await scoring_config.get_config_by_id(config_id)
            return {
                "success": True,
                "config": updated_config,
                "message": "Weights updated successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Config not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating weights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/configs/by-level/{level}/weights", response_class=JSONResponse)
async def update_weights_by_level_api(
    level: str,
    request: Request,
    scoring_config: ScoringConfigDep
):
    """API endpoint to update weights by level (fallback if config_id is missing)"""
    try:
        # Get config by level first
        config = await scoring_config.get_config_by_level(level)
        if not config:
            raise HTTPException(status_code=404, detail=f"Config not found for level: {level}")
        
        config_id = config.get("config_id")
        if not config_id:
            raise HTTPException(status_code=404, detail=f"Config ID not found for level: {level}")
        
        data = await request.json()
        weights = data.get("weights", {})
        
        # Validate weights sum to 1.0
        total = sum(float(v) for v in weights.values())
        if abs(total - 1.0) > 0.01:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"Weights must sum to 1.0 (current: {total:.2f})",
                    "total": round(total, 2)
                }
            )
        
        # Update only weights
        success = await scoring_config.update_config(config_id, {"weights": weights})
        if success:
            updated_config = await scoring_config.get_config_by_id(config_id)
            return {
                "success": True,
                "config": updated_config,
                "message": "Weights updated successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Config not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating weights by level: {e}")
        raise HTTPException(status_code=500, detail=str(e))

