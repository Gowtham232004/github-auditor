"""
github_api.py
Handles all GitHub API interactions
"""

import requests
from typing import Optional, Dict, List
from config import config

# GitHub API base URL
GITHUB_API_BASE = config.GITHUB_API_BASE

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors"""
    pass

def fetch_user_profile(username: str) -> Optional[Dict]:
    """
    Fetch GitHub user profile
    
    Args:
        username: GitHub username
        
    Returns:
        Dictionary with user data or None if error
        
    Raises:
        GitHubAPIError: If user not found or API error
    """
    
    url = f"{GITHUB_API_BASE}/users/{username}"
    headers = config.get_github_headers()
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            raise GitHubAPIError(f"User '{username}' not found on GitHub")
        
        if response.status_code == 401:
            raise GitHubAPIError("GitHub API authentication failed - Invalid or missing token")
        
        if response.status_code == 403:
            # Check if it's rate limit or token permission issue
            if 'X-RateLimit-Remaining' in response.headers and response.headers['X-RateLimit-Remaining'] == '0':
                raise GitHubAPIError("GitHub API rate limit exceeded")
            else:
                raise GitHubAPIError("GitHub API access forbidden - Check token permissions")
        
        if response.status_code != 200:
            raise GitHubAPIError(f"GitHub API error: {response.status_code}")
        
        return response.json()
        
    except requests.exceptions.Timeout:
        raise GitHubAPIError("Request timed out")
    
    except requests.exceptions.ConnectionError:
        raise GitHubAPIError("Network connection error")
    
    except requests.exceptions.RequestException as e:
        raise GitHubAPIError(f"Request failed: {str(e)}")


def fetch_user_repositories(username: str, max_repos: int = 100) -> List[Dict]:
    """
    Fetch user's public repositories
    
    Args:
        username: GitHub username
        max_repos: Maximum number of repos to fetch (default 100)
        
    Returns:
        List of repository dictionaries
    """
    
    url = f"{GITHUB_API_BASE}/users/{username}/repos"
    headers = config.get_github_headers()
    params = {
        "per_page": min(max_repos, 100),  # GitHub max is 100 per page
        "sort": "updated",
        "direction": "desc"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            raise GitHubAPIError(f"Failed to fetch repositories: {response.status_code}")
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        raise GitHubAPIError(f"Failed to fetch repositories: {str(e)}")


def extract_profile_data(raw_data: Dict) -> Dict:
    """
    Extract and clean relevant profile data
    
    Args:
        raw_data: Raw GitHub API response
        
    Returns:
        Cleaned profile dictionary
    """
    
    return {
        "username": raw_data.get("login"),
        "name": raw_data.get("name"),
        "bio": raw_data.get("bio"),
        "location": raw_data.get("location"),
        "email": raw_data.get("email"),
        "blog": raw_data.get("blog"),
        "company": raw_data.get("company"),
        "public_repos": raw_data.get("public_repos", 0),
        "public_gists": raw_data.get("public_gists", 0),
        "followers": raw_data.get("followers", 0),
        "following": raw_data.get("following", 0),
        "created_at": raw_data.get("created_at"),
        "updated_at": raw_data.get("updated_at"),
        "profile_url": raw_data.get("html_url"),
        "avatar_url": raw_data.get("avatar_url"),
    }


def calculate_basic_stats(repos: List[Dict]) -> Dict:
    """
    Calculate basic statistics from repositories
    
    Args:
        repos: List of repository dictionaries
        
    Returns:
        Dictionary with calculated statistics
    """
    
    if not repos:
        return {
            "total_repos": 0,
            "total_stars": 0,
            "total_forks": 0,
            "languages": {},
            "most_used_language": None,
            "average_stars": 0,
            "forked_repos": 0,
            "original_repos": 0
        }
    
    # Initialize counters
    total_stars = 0
    total_forks = 0
    languages = {}
    forked_count = 0
    original_count = 0
    
    # Process each repository
    for repo in repos:
        total_stars += repo.get("stargazers_count", 0)
        total_forks += repo.get("forks_count", 0)
        
        # Count languages
        lang = repo.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
        
        # Count forked vs original
        if repo.get("fork", False):
            forked_count += 1
        else:
            original_count += 1
    
    # Find most used language
    most_used_lang = None
    if languages:
        most_used_lang = max(languages.items(), key=lambda x: x[1])[0]
    
    return {
        "total_repos": len(repos),
        "total_stars": total_stars,
        "total_forks": total_forks,
        "languages": languages,
        "most_used_language": most_used_lang,
        "average_stars": total_stars // len(repos) if repos else 0,
        "forked_repos": forked_count,
        "original_repos": original_count,
        "fork_ratio": round(forked_count / len(repos), 2) if repos and len(repos) > 0 else 0
    }


def analyze_github_user(username: str) -> Dict:
    """
    Complete analysis of GitHub user
    Combines profile and repository data
    
    Args:
        username: GitHub username
        
    Returns:
        Complete analysis dictionary
    """
    
    # Fetch profile
    raw_profile = fetch_user_profile(username)
    profile = extract_profile_data(raw_profile)
    
    # Fetch repositories
    repos = fetch_user_repositories(username)
    
    # Calculate statistics
    stats = calculate_basic_stats(repos)
    
    # Combine everything
    return {
        "profile": profile,
        "statistics": stats,
        "repositories_analyzed": len(repos)
    }


# ============================================
# TEST FUNCTIONS (for debugging)
# ============================================

if __name__ == "__main__":
    """Test the GitHub API functions"""
    
    print("🧪 Testing GitHub API functions...")
    
    # Test 1: Fetch profile
    print("\nTest 1: Fetch user profile")
    try:
        profile = fetch_user_profile("torvalds")
        print(f"✅ Fetched profile for: {profile['login']}")
        print(f"   Name: {profile.get('name')}")
        print(f"   Followers: {profile.get('followers')}")
    except GitHubAPIError as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Fetch repositories
    print("\nTest 2: Fetch repositories")
    try:
        repos = fetch_user_repositories("torvalds")
        print(f"✅ Fetched {len(repos)} repositories")
        if repos:
            print(f"   Latest repo: {repos[0]['name']}")
    except GitHubAPIError as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Complete analysis
    print("\nTest 3: Complete analysis")
    try:
        analysis = analyze_github_user("torvalds")
        print(f"✅ Complete analysis done")
        print(f"   Total stars: {analysis['statistics']['total_stars']}")
        print(f"   Most used language: {analysis['statistics']['most_used_language']}")
    except GitHubAPIError as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Error handling (user not found)
    print("\nTest 4: Error handling")
    try:
        profile = fetch_user_profile("thisuserdoesnotexist123456789")
        print("❌ Should have raised error!")
    except GitHubAPIError as e:
        print(f"✅ Correctly caught error: {e}")
    
    print("\n✅ All tests completed!")