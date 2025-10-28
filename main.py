"""
main.py
FastAPI application for GitHub Auditor
Day 1: Basic profile analysis and storage
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
from datetime import datetime

# Import our modules
import github_api
import database

# ============================================
# CREATE FASTAPI APP
# ============================================

app = FastAPI(
    title="GitHub Auditor API",
    description="Analyze GitHub profiles for authenticity",
    version="1.0.0 - Day 1",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware (allows frontend to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# STARTUP EVENT
# ============================================

@app.on_event("startup")
def startup_event():
    """Initialize database when app starts"""
    print("🚀 Starting GitHub Auditor API...")
    database.initialize_database()
    print("✅ API ready!")

# ============================================
# ROOT ENDPOINT
# ============================================

@app.get("/")
def root():
    """
    API information and available endpoints
    """
    return {
        "name": "GitHub Auditor API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/": "API information",
            "/health": "Health check",
            "/analyze/{username}": "Analyze GitHub profile",
            "/profile/{username}": "Get stored profile",
            "/history": "Get all analyzed profiles",
            "/stats": "Get database statistics",
            "/docs": "Interactive API documentation"
        },
        "github": "https://github.com/yourusername/github-auditor",
        "documentation": "/docs"
    }

# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
def health_check():
    """
    Health check endpoint
    Returns API status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "github-auditor-api"
    }

# ============================================
# MAIN ANALYSIS ENDPOINT
# ============================================

@app.get("/analyze/{username}")
def analyze_profile(username: str):
    """
    Analyze a GitHub profile
    
    This endpoint:
    1. Fetches profile from GitHub API
    2. Fetches repositories
    3. Calculates statistics
    4. Saves to database
    5. Returns analysis
    
    Args:
        username: GitHub username to analyze
        
    Returns:
        Complete analysis with profile and statistics
        
    Example:
        GET /analyze/torvalds
    """
    
    # Validate username
    if not username or len(username) < 1:
        raise HTTPException(
            status_code=400,
            detail="Username cannot be empty"
        )
    
    try:
        # Perform analysis
        print(f"🔍 Analyzing GitHub user: {username}")
        analysis = github_api.analyze_github_user(username)
        
        # Save to database
        save_success = database.save_analysis(username, analysis)
        
        if not save_success:
            print(f"⚠  Analysis completed but failed to save to database")
        
        # Add metadata
        result = {
            "username": username,
            "analyzed_at": datetime.now().isoformat(),
            "saved_to_database": save_success,
            "data": analysis
        }
        
        return result
        
    except github_api.GitHubAPIError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 500,
            detail=str(e)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

# ============================================
# GET STORED PROFILE
# ============================================

@app.get("/profile/{username}")
def get_stored_profile(username: str):
    """
    Get previously analyzed profile from database
    
    Returns the most recent analysis without making new GitHub API calls
    
    Args:
        username: GitHub username
        
    Returns:
        Stored profile and statistics
        
    Example:
        GET /profile/torvalds
    """
    
    # Get profile from database
    profile = database.get_profile(username)
    
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Profile '{username}' not found in database. Try /analyze/{username} first."
        )
    
    # Get latest statistics
    stats = database.get_latest_statistics(username)
    
    return {
        "username": username,
        "profile": profile,
        "statistics": stats,
        "source": "database"
    }

# ============================================
# GET ALL PROFILES
# ============================================

@app.get("/history")
def get_analysis_history():
    """
    Get all analyzed profiles from database
    
    Returns list of all profiles that have been analyzed,
    ordered by most recently analyzed first
    
    Returns:
        List of profiles with basic info
        
    Example:
        GET /history
    """
    
    profiles = database.get_all_profiles()
    
    return {
        "total_profiles": len(profiles),
        "profiles": profiles
    }

# ============================================
# DATABASE STATISTICS
# ============================================

@app.get("/stats")
def get_statistics():
    """
    Get overall database statistics
    
    Returns:
        - Total profiles analyzed
        - Total analyses performed
        - Most common languages
        
    Example:
        GET /stats
    """
    
    stats = database.get_database_stats()
    
    return {
        "database_statistics": stats,
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# DELETE PROFILE (BONUS)
# ============================================

@app.delete("/profile/{username}")
def delete_stored_profile(username: str):
    """
    Delete profile and all associated data from database
    
    Args:
        username: GitHub username to delete
        
    Returns:
        Success message
        
    Example:
        DELETE /profile/test_user
    """
    
    success = database.delete_profile(username)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Profile '{username}' not found in database"
        )
    
    return {
        "message": f"Profile '{username}' deleted successfully",
        "deleted": True
    }

# ============================================
# USER ANALYSIS HISTORY
# ============================================

@app.get("/history/{username}")
def get_user_history(username: str):
    """
    Get analysis history for specific user
    
    Shows how the user's stats have changed over time
    
    Args:
        username: GitHub username
        
    Returns:
        List of all analyses for this user
        
    Example:
        GET /history/torvalds
    """
    
    history = database.get_analysis_history(username)
    
    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis history found for '{username}'"
        )
    
    return {
        "username": username,
        "total_analyses": len(history),
        "history": history
    }

# ============================================
# ERROR HANDLERS
# ============================================

from fastapi.responses import JSONResponse

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "detail": str(exc.detail) if hasattr(exc, 'detail') else "The requested resource was not found",
            "status_code": 404
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "status_code": 500
        }
    )

# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    print("="*50)
    print("🚀 Starting GitHub Auditor API")
    print("="*50)
    print("📝 API Docs: http://localhost:8000/docs")
    print("🔄 Redoc: http://localhost:8000/redoc")
    print("💻 API: http://localhost:8000")
    print("="*50)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )