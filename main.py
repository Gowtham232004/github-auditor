"""
main.py
GitHub Auditor API - Production Ready
Day 3: Polished with rate limiting, logging, monitoring, error handling
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Optional
from datetime import datetime
import time
import os
import re

# Import our modules
import github_api
import database
import git_analyzer
from config import config
from logger import logger, log_api_request, log_analysis_start, log_analysis_complete, log_error
from rate_limiter import check_rate_limit, rate_limiter
from health_monitor import health_monitor
# Add this import at the top of main.py
import ai_insights
import email_service

# ============================================
# CREATE FASTAPI APP
# ============================================

app = FastAPI(
    title=config.API_TITLE,
    description="Analyze GitHub profiles for authenticity and detect portfolio farming",
    version=config.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    debug=config.DEBUG_MODE
)

# Add CORS middleware - Allow all origins (public API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins - this is a public API
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# MIDDLEWARE
# ============================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and add rate limit headers"""
    start_time = time.time()
    
    # Increment request counter
    health_monitor.increment_requests()
    
    # Get client IP
    client_ip = request.client.host
    
    # Log request
    log_api_request(request.url.path, ip=client_ip)
    
    # Process request
    try:
        response = await call_next(request)
        
        # Add rate limit headers
        rate_info = rate_limiter.get_info(client_ip)
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset_in_seconds"])
        
        # Log response time
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(round(process_time, 3))
        
        return response
        
    except Exception as e:
        health_monitor.increment_errors()
        log_error(e, f"Request to {request.url.path}")
        raise

# ============================================
# STARTUP EVENT
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("="*50)
    logger.info("🚀 Starting GitHub Auditor API...")
    logger.info("="*50)
    
    # Print configuration
    config.print_config()
    
    # Initialize database
    database.initialize_database()
    
    logger.info("✅ API ready and listening for requests")
    logger.info("="*50)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Shutting down GitHub Auditor API...")

# ============================================
# ROOT ENDPOINT
# ============================================

@app.get("/")
def root():
    """API information and available endpoints"""
    return {
        "name": config.API_TITLE,
        "version": config.API_VERSION,
        "status": "running",
        "environment": config.ENVIRONMENT,
        "endpoints": {
            "/": "API information",
            "/health": "Basic health check",
            "/health/detailed": "Detailed system health",
            "/analyze/{username}": "Analyze GitHub profile",
            "/analyze-repo": "Analyze single repository",
            "/analyze-all/{username}": "Deep analysis (all repos)",
            "/analyze-ai/{username}": "AI-powered profile analysis",
            "/email-report": "Send analysis report via email",
            "/profile/{username}": "Get stored profile",
            "/repo-analyses/{username}": "Get stored repo analyses",
            "/history": "Get all analyzed profiles",
            "/stats": "Database statistics",
            "/docs": "Interactive API documentation"
        },
        "rate_limit": {
            "limit": config.RATE_LIMIT_PER_HOUR,
            "window": "1 hour"
        },
        "github": "https://github.com/yourusername/github-auditor",
        "documentation": "/docs"
    }

# ============================================
# HEALTH CHECK ENDPOINTS
# ============================================

@app.get("/health")
def health_check():
    """Basic health check"""
    is_healthy = health_monitor.is_healthy()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": config.API_VERSION
    }

@app.get("/health/detailed")
def detailed_health_check():
    """Detailed system health with metrics"""
    return health_monitor.get_complete_health()

# ============================================
# PROFILE ANALYSIS ENDPOINTS
# ============================================

@app.get("/analyze/{username}", dependencies=[Depends(check_rate_limit)])
async def analyze_profile(username: str):
    """
    Analyze a GitHub profile (basic analysis)
    
    Rate limited to prevent abuse
    """
    start_time = time.time()
    
    if not username or len(username) < 1:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    
    try:
        log_analysis_start(username, "profile")
        
        # Perform analysis
        analysis = github_api.analyze_github_user(username)
        
        # Save to database
        save_success = database.save_analysis(username, analysis)
        
        # Increment counter
        health_monitor.increment_analyses()
        
        # Log completion
        duration = time.time() - start_time
        log_analysis_complete(username, "profile", duration)
        
        return {
            "username": username,
            "analyzed_at": datetime.now().isoformat(),
            "saved_to_database": save_success,
            "analysis_time_seconds": round(duration, 2),
            "data": analysis
        }
        
    except github_api.GitHubAPIError as e:
        health_monitor.increment_errors()
        log_error(e, f"Profile analysis for {username}")
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 500,
            detail=str(e)
        )
    
    except Exception as e:
        health_monitor.increment_errors()
        log_error(e, f"Profile analysis for {username}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/profile/{username}")
def get_stored_profile(username: str):
    """Get previously analyzed profile from database"""
    profile = database.get_profile(username)
    
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Profile '{username}' not found. Try /analyze/{username} first."
        )
    
    stats = database.get_latest_statistics(username)
    
    return {
        "username": username,
        "profile": profile,
        "statistics": stats,
        "source": "database"
    }

# ============================================
# REPOSITORY ANALYSIS ENDPOINTS
# ============================================

@app.post("/analyze-repo", dependencies=[Depends(check_rate_limit)])
async def analyze_repository_endpoint(repo_url: str, username: Optional[str] = None):
    """
    Analyze a single repository's commits
    
    Rate limited - takes 10-30 seconds per repo
    """
    start_time = time.time()
    
    if not repo_url or "github.com" not in repo_url:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
    
    try:
        repo_name = repo_url.rstrip('/').split('/')[-1]
        
        logger.info(f"🔍 Analyzing repository: {repo_name}")
        
        # Perform Git analysis
        analysis = git_analyzer.analyze_repository(repo_url)
        
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {analysis['error']}")
        
        # Save to database if username provided
        saved = False
        if username:
            saved = database.save_repository_analysis(username, repo_name, repo_url, analysis)
        
        # Increment counter
        health_monitor.increment_analyses()
        
        duration = time.time() - start_time
        logger.info(f"✅ Repository analysis complete: {repo_name} (took {duration:.2f}s)")
        
        return {
            "repository": repo_name,
            "url": repo_url,
            "saved_to_database": saved,
            "analysis_time_seconds": round(duration, 2),
            "analysis": analysis
        }
        
    except git_analyzer.GitAnalysisError as e:
        health_monitor.increment_errors()
        log_error(e, f"Repository analysis for {repo_url}")
        raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        health_monitor.increment_errors()
        log_error(e, f"Repository analysis for {repo_url}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/analyze-all/{username}", dependencies=[Depends(check_rate_limit)])
async def analyze_all_repositories(username: str, max_repos: int = 3):
    """
    Deep analysis of all user repositories
    
    WARNING: SLOW! Analyzes commit history for multiple repos
    Limited to prevent timeouts
    """
    if max_repos > config.MAX_REPOS_PER_ANALYSIS:
        raise HTTPException(
            status_code=400,
            detail=f"max_repos cannot exceed {config.MAX_REPOS_PER_ANALYSIS}"
        )
    
    start_time = time.time()
    
    try:
        log_analysis_start(username, "deep")
        
        # Fetch profile
        analysis = github_api.analyze_github_user(username)
        database.save_analysis(username, analysis)
        
        # Get repositories
        repos = github_api.fetch_user_repositories(username, max_repos)
        
        # Analyze each repository
        repo_analyses = []
        logger.info(f"📊 Analyzing {len(repos[:max_repos])} repositories...")
        
        for repo in repos[:max_repos]:
            repo_url = repo['clone_url']
            repo_name = repo['name']
            repo_size_kb = repo.get('size', 0)  # Size in KB from GitHub API
            
            # Skip repos larger than 100MB (100,000 KB) to avoid timeouts
            if repo_size_kb > 100000:
                logger.warning(f"  ⏭️  Skipping {repo_name}: Too large ({repo_size_kb/1024:.1f}MB)")
                repo_analyses.append({
                    "repo_name": repo_name, 
                    "skipped": True,
                    "reason": f"Repository too large ({repo_size_kb/1024:.1f}MB), would cause timeout"
                })
                continue
            
            logger.info(f"  🔍 Analyzing: {repo_name} ({repo_size_kb/1024:.1f}MB)")
            
            try:
                repo_analysis = git_analyzer.analyze_repository(repo_url)
                
                if "error" not in repo_analysis:
                    database.save_repository_analysis(username, repo_name, repo_url, repo_analysis)
                    repo_analyses.append({"repo_name": repo_name, "analysis": repo_analysis})
                else:
                    repo_analyses.append({"repo_name": repo_name, "error": repo_analysis["error"]})
                    
            except Exception as e:
                logger.error(f"Failed to analyze {repo_name}: {e}")
                repo_analyses.append({"repo_name": repo_name, "error": str(e)})
        
        # Calculate overall score
        valid_scores = [
            r["analysis"]["authenticity_score"] 
            for r in repo_analyses 
            if "analysis" in r and "error" not in r["analysis"]
        ]
        
        overall_score = sum(valid_scores) // len(valid_scores) if valid_scores else 0
        
        # Increment counter
        health_monitor.increment_analyses()
        
        duration = time.time() - start_time
        log_analysis_complete(username, "deep", duration)
        
        # Generate AI insights if we have analysis data
        ai_analysis = None
        try:
            if repo_analyses and any("analysis" in r for r in repo_analyses):
                # Get data from first successful analysis
                first_analysis = next((r["analysis"] for r in repo_analyses if "analysis" in r), None)
                if first_analysis:
                    commit_data = first_analysis.get("commit_analysis", {})
                    all_red_flags = []
                    for r in repo_analyses:
                        if "analysis" in r:
                            all_red_flags.extend(r["analysis"].get("red_flags", []))
                    
                    logger.info("Generating AI insights...")
                    ai_summary = ai_insights.generate_profile_insights(
                        analysis["profile"],
                        commit_data,
                        all_red_flags
                    )
                    recommendation = ai_insights.generate_recommendation(overall_score, all_red_flags)
                    behavior_patterns = ai_insights.analyze_commit_behavior(commit_data)
                    
                    ai_analysis = {
                        "summary": ai_summary.get("summary", ""),
                        "generated_by": ai_summary.get("generated_by", "Analysis System"),
                        "confidence": ai_summary.get("confidence", "medium"),
                        "recommendation": recommendation,
                        "behavior_patterns": behavior_patterns
                    }
        except Exception as e:
            logger.error(f"AI insights generation failed: {e}")
            # Continue without AI insights

        result = {
            "username": username,
            "profile": analysis["profile"],
            "statistics": analysis["statistics"],
            "repositories_analyzed": len(repo_analyses),
            "repository_analyses": repo_analyses,
            "overall_authenticity_score": overall_score,
            "analysis_time_seconds": round(duration, 2),
            "analyzed_at": datetime.now().isoformat()
        }
        
        # Add AI insights if generated
        if ai_analysis:
            result["ai_insights"] = ai_analysis
            
        return result
        
    except github_api.GitHubAPIError as e:
        health_monitor.increment_errors()
        log_error(e, f"Deep analysis for {username}")
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 500,
            detail=str(e)
        )
    
    except Exception as e:
        health_monitor.increment_errors()
        log_error(e, f"Deep analysis for {username}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/repo-analyses/{username}")
def get_user_repo_analyses(username: str):
    """Get all stored repository analyses"""
    analyses = database.get_repository_analyses(username)
    
    if not analyses:
        raise HTTPException(
            status_code=404,
            detail=f"No repository analyses found for '{username}'"
        )
    
    return {
        "username": username,
        "total_repositories_analyzed": len(analyses),
        "repositories": analyses
    }

# ============================================
# HISTORY & STATS ENDPOINTS
# ============================================

@app.get("/history")
def get_analysis_history():
    """Get all analyzed profiles"""
    profiles = database.get_all_profiles()
    
    return {
        "total_profiles": len(profiles),
        "profiles": profiles
    }

@app.get("/history/{username}")
def get_user_history(username: str):
    """Get analysis history for specific user"""
    history = database.get_analysis_history(username)
    
    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for '{username}'"
        )
    
    return {
        "username": username,
        "total_analyses": len(history),
        "history": history
    }

@app.get("/stats")
def get_statistics():
    """Get database statistics"""
    stats = database.get_database_stats()
    
    return {
        "database_statistics": stats,
        "api_statistics": health_monitor.get_api_stats(),
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# AI-POWERED ANALYSIS ENDPOINT
# ============================================

@app.get("/analyze-ai/{username}", dependencies=[Depends(check_rate_limit)])
async def analyze_with_ai_insights(username: str):
    """
    Analyze GitHub profile with AI-powered insights
    
    Returns profile analysis + GPT-generated assessment
    Includes hiring recommendation and behavior patterns
    """
    
    start_time = time.time()
    
    try:
        log_analysis_start(username, "ai-powered")
        
        # Get basic profile analysis
        analysis = github_api.analyze_github_user(username)
        profile = analysis['profile']
        stats = analysis['statistics']
        
        # Get commit analysis from first repository
        repos = github_api.fetch_user_repositories(username, 1)
        
        if repos and len(repos) > 0:
            repo_url = repos[0]['clone_url']
            logger.info(f"Analyzing repository: {repos[0]['name']}")
            
            try:
                repo_analysis = git_analyzer.analyze_repository(repo_url)
                
                if "error" not in repo_analysis:
                    commit_data = repo_analysis['commit_analysis']
                    red_flags = repo_analysis['red_flags']
                    auth_score = repo_analysis['authenticity_score']
                else:
                    commit_data = {}
                    red_flags = []
                    auth_score = 50
                    
            except Exception as e:
                logger.error(f"Repository analysis failed: {e}")
                commit_data = {}
                red_flags = []
                auth_score = 50
        else:
            commit_data = {}
            red_flags = []
            auth_score = 50
        
        # Generate AI insights
        logger.info("Generating AI insights...")
        ai_analysis = ai_insights.generate_profile_insights(
            profile,
            commit_data,
            red_flags
        )
        
        # Generate recommendation
        recommendation = ai_insights.generate_recommendation(auth_score, red_flags)
        
        # Analyze behavior patterns
        behavior_patterns = ai_insights.analyze_commit_behavior(commit_data)
        
        # Save to database
        database.save_analysis(username, analysis)
        
        health_monitor.increment_analyses()
        
        duration = time.time() - start_time
        log_analysis_complete(username, "ai-powered", duration)
        
        return {
            "username": username,
            "profile": profile,
            "statistics": stats,
            "authenticity_score": auth_score,
            "red_flags": red_flags,
            "commit_analysis": commit_data,
            "ai_insights": ai_analysis,
            "recommendation": recommendation,
            "behavior_patterns": behavior_patterns,
            "analysis_time_seconds": round(duration, 2),
            "analyzed_at": datetime.now().isoformat()
        }
        
    except github_api.GitHubAPIError as e:
        health_monitor.increment_errors()
        log_error(e, f"AI analysis for {username}")
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 500,
            detail=str(e)
        )
    
    except Exception as e:
        health_monitor.increment_errors()
        log_error(e, f"AI analysis for {username}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

# ============================================
# DELETE ENDPOINT
# ============================================

@app.delete("/profile/{username}")
def delete_stored_profile(username: str):
    """Delete profile from database"""
    success = database.delete_profile(username)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Profile '{username}' not found"
        )
    
    return {
        "message": f"Profile '{username}' deleted successfully",
        "deleted": True
    }

# ============================================
# EMAIL SERVICE ENDPOINT
# ============================================

@app.post("/email-report", dependencies=[Depends(check_rate_limit)])
async def send_email_report(username: str, email: str):
    """
    Send analysis report via email
    
    Args:
        username: GitHub username to analyze
        email: Recipient email address
    """
    
    # Validate email format
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    try:
        # Get analysis (use cached if available)
        try:
            profile_data = database.get_profile(username)
            stats = database.get_latest_statistics(username)
            repo_analyses = database.get_repository_analyses(username)
            
            if not profile_data:
                # Analyze if not in database
                analysis = github_api.analyze_github_user(username)
                database.save_analysis(username, analysis)
                profile_data = analysis['profile']
                stats = analysis['statistics']
                repo_analyses = []
            
        except Exception as e:
            # Fresh analysis if database fails
            analysis = github_api.analyze_github_user(username)
            database.save_analysis(username, analysis)
            profile_data = analysis['profile']
            stats = analysis['statistics']
            repo_analyses = []
        
        # Prepare data for email
        email_data = {
            'profile': profile_data,
            'statistics': stats,
            'authenticity_score': 75,  # Calculate properly based on your logic
            'red_flags': []  # Get from repo_analyses
        }
        
        # Send email
        success = email_service.send_analysis_email(email, username, email_data)
        
        if success:
            return {
                "message": f"Analysis report sent to {email}",
                "username": username,
                "sent_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send email. Check SendGrid configuration."
            )
            
    except Exception as e:
        log_error(e, f"Email report for {username}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send report: {str(e)}"
        )

# ============================================
# GLOBAL ERROR HANDLERS
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    health_monitor.increment_errors()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler"""
    health_monitor.increment_errors()
    log_error(exc, f"Unhandled exception at {request.url.path}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if config.DEBUG_MODE else "An unexpected error occurred",
            "status_code": 500,
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat()
        }
    )
    
@app.post("/email-report")
async def email_report(username: str, email: str):
    '''Send analysis report via email'''
    try:
        # Get analysis
        analysis = await analyze_profile(username)
        
        # Send email
        success = email_service.send_analysis_email(email, username, analysis)
        
        if success:
            return {"message": f"Report sent to {email}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("="*50)
    logger.info("🚀 Starting GitHub Auditor API")
    logger.info("="*50)
    logger.info(f"📝 API Docs: http://localhost:{config.API_PORT}/docs")
    logger.info(f"🔄 Redoc: http://localhost:{config.API_PORT}/redoc")
    logger.info(f"💻 API: http://localhost:{config.API_PORT}")
    logger.info("="*50)
    
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=int(os.getenv("PORT", config.API_PORT)),
        reload=config.DEBUG_MODE,
        log_level=config.LOG_LEVEL.lower()
    )