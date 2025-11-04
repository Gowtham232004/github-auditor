"""
config.py
Configuration management using environment variables
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # API Configuration
    API_TITLE: str = os.getenv("API_TITLE", "GitHub Auditor API")
    API_VERSION: str = os.getenv("API_VERSION", "2.0.0")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8000))
    
    # Database
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "github_auditor.db")
    
    # GitHub API
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    GITHUB_API_BASE: str = "https://api.github.com"
    
    # Repository Analysis Limits
    MAX_REPO_SIZE_MB: int = int(os.getenv("MAX_REPO_SIZE_MB", 500))
    MAX_REPOS_PER_ANALYSIS: int = int(os.getenv("MAX_REPOS_PER_ANALYSIS", 10))
    CLONE_TIMEOUT_SECONDS: int = int(os.getenv("CLONE_TIMEOUT_SECONDS", 300))
    
    # Rate Limiting
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", 100))
    
    # Deployment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "true").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production"""
        return cls.ENVIRONMENT == "production"
    
    @classmethod
    def get_github_headers(cls) -> dict:
        """Get GitHub API headers with optional authentication"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Auditor-API"
        }
        
        if cls.GITHUB_TOKEN:
            # Support both classic tokens (token) and fine-grained tokens (Bearer)
            # GitHub API accepts both formats
            token = cls.GITHUB_TOKEN.strip()
            if token.startswith('ghp_'):
                # Classic Personal Access Token
                headers["Authorization"] = f"token {token}"
            elif token.startswith('github_pat_'):
                # Fine-grained Personal Access Token
                headers["Authorization"] = f"token {token}"
            else:
                # Default to token format
                headers["Authorization"] = f"token {token}"
        
        return headers
    
    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)"""
        print("="*50)
        print("⚙  CONFIGURATION")
        print("="*50)
        print(f"Environment: {cls.ENVIRONMENT}")
        print(f"Debug Mode: {cls.DEBUG_MODE}")
        print(f"API Version: {cls.API_VERSION}")
        print(f"Database: {cls.DATABASE_NAME}")
        print(f"GitHub Token: {'✅ Set' if cls.GITHUB_TOKEN else '❌ Not set'}")
        print(f"Max Repo Size: {cls.MAX_REPO_SIZE_MB}MB")
        print(f"Max Repos: {cls.MAX_REPOS_PER_ANALYSIS}")
        print(f"Rate Limit: {cls.RATE_LIMIT_PER_HOUR}/hour")
        print("="*50)


# Create singleton instance
config = Config()


if __name__ == "__main__":
    """Test configuration"""
    config.print_config()