"""
ai_insights.py
AI-powered insights generation using OpenAI
"""

import os
from typing import Dict, List
from config import config

# Try to import OpenAI (optional dependency)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    # Initialize OpenAI client if API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key) if api_key else None
except ImportError:
    OPENAI_AVAILABLE = False
    client = None

def generate_profile_insights(profile_data: Dict, commit_analysis: Dict, red_flags: List[Dict]) -> Dict:
    """
    Generate AI-powered insights about a GitHub profile
    
    Args:
        profile_data: GitHub profile information
        commit_analysis: Commit pattern analysis
        red_flags: List of detected red flags
        
    Returns:
        Dictionary with AI-generated insights
    """
    
    # Prepare context for AI
    context = f"""
    Analyze this GitHub profile and provide insights:
    
    Profile:
    - Username: {profile_data.get('username')}
    - Public Repos: {profile_data.get('public_repos')}
    - Followers: {profile_data.get('followers')}
    - Account Age: {profile_data.get('created_at')}
    
    Commit Patterns:
    - Total Commits: {commit_analysis.get('total_commits', 0)}
    - Unique Authors: {commit_analysis.get('unique_authors', 0)}
    - Days Active: {commit_analysis.get('days_active', 0)}
    - Commits per Day: {commit_analysis.get('commits_per_day', 0)}
    - Most Active Hour: {commit_analysis.get('most_active_hour', 'N/A')}
    
    Red Flags Detected: {len(red_flags)}
    {', '.join([f['type'] for f in red_flags]) if red_flags else 'None'}
    
    Based on this data, provide:
    1. A brief assessment (2-3 sentences) of the developer's authenticity
    2. Their likely experience level (Junior/Mid/Senior)
    3. Development patterns observed
    4. Recommendations for improvement
    """
    
    # Use fallback if OpenAI is not available
    if not OPENAI_AVAILABLE or not client:
        return {
            "summary": generate_fallback_insights(profile_data, commit_analysis, red_flags),
            "generated_by": "rule-based (OpenAI not configured)",
            "confidence": "medium"
        }
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or gpt-4 for better results
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert code reviewer and developer analyst. Provide concise, professional insights about GitHub profiles based on their activity patterns."
                },
                {
                    "role": "user",
                    "content": context
                }
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        insights_text = response.choices[0].message.content
        
        # Parse the response (simple version)
        return {
            "summary": insights_text,
            "generated_by": "GPT-3.5",
            "confidence": "high" if len(red_flags) < 2 else "medium" if len(red_flags) < 4 else "low"
        }
        
    except Exception as e:
        print(f"AI insight generation failed: {e}")
        return {
            "summary": generate_fallback_insights(profile_data, commit_analysis, red_flags),
            "generated_by": "rule-based",
            "confidence": "medium"
        }


def generate_fallback_insights(profile_data: Dict, commit_analysis: Dict, red_flags: List[Dict]) -> str:
    """
    Generate insights using rules when AI is unavailable
    """
    
    total_commits = commit_analysis.get('total_commits', 0)
    days_active = commit_analysis.get('days_active', 1)
    commits_per_day = total_commits / days_active if days_active > 0 else 0
    
    # Experience level assessment
    if total_commits > 500 and days_active > 365:
        experience = "Senior Developer"
    elif total_commits > 100 and days_active > 180:
        experience = "Mid-Level Developer"
    else:
        experience = "Junior Developer"
    
    # Authenticity assessment
    if len(red_flags) == 0:
        authenticity = "This profile shows healthy, authentic development patterns."
    elif len(red_flags) <= 2:
        authenticity = "This profile shows mostly authentic patterns with minor concerns."
    else:
        authenticity = "This profile shows several suspicious patterns that warrant careful review."
    
    # Activity pattern
    if commits_per_day < 1:
        activity = "Shows moderate, sustainable development activity."
    elif commits_per_day < 5:
        activity = "Demonstrates consistent, regular development habits."
    else:
        activity = "Shows very high commit frequency - verify if this is normal workflow or bulk uploads."
    
    return f"{authenticity} {activity} Profile characteristics suggest a {experience} with {days_active} days of tracked activity."


def generate_recommendation(authenticity_score: int, red_flags: List[Dict]) -> str:
    """
    Generate hiring recommendation based on score and red flags
    """
    
    if authenticity_score >= 80 and len(red_flags) == 0:
        return "✅ RECOMMENDED: Profile shows authentic development patterns. Safe to proceed with interview process."
    
    elif authenticity_score >= 60 and len(red_flags) <= 2:
        return "⚠️ PROCEED WITH CAUTION: Profile is mostly authentic but has minor concerns. Recommend technical interview to verify skills."
    
    elif authenticity_score >= 40:
        return "⚠️ CAREFUL REVIEW NEEDED: Profile shows several red flags. Strongly recommend in-depth technical assessment and code review."
    
    else:
        return "🚫 NOT RECOMMENDED: Profile shows significant suspicious patterns. High risk of portfolio farming or fake contributions."


def analyze_commit_behavior(commit_analysis: Dict) -> str:
    """
    Analyze commit behavior patterns
    """
    
    hour_concentration = commit_analysis.get('hour_concentration', 0)
    commits_per_day = commit_analysis.get('commits_per_day', 0)
    
    patterns = []
    
    if hour_concentration > 0.7:
        patterns.append("⚠️ High concentration of commits at same hour (possible automation)")
    
    if commits_per_day > 10:
        patterns.append("⚠️ Very high commit frequency (verify if normal workflow)")
    
    if commit_analysis.get('generic_message_ratio', 0) > 0.5:
        patterns.append("⚠️ Many generic commit messages (indicates low effort)")
    
    if commit_analysis.get('unique_authors', 1) == 1:
        patterns.append("ℹ️ Single contributor (no collaborative work)")
    
    if not patterns:
        patterns.append("✅ Normal commit patterns observed")
    
    return " | ".join(patterns)


# ============================================
# TEST FUNCTION
# ============================================

if __name__ == "__main__":
    """Test AI insights generation"""
    
    print("🧪 Testing AI Insights...")
    
    # Mock data
    profile_data = {
        'username': 'test_user',
        'public_repos': 25,
        'followers': 150,
        'created_at': '2020-01-01'
    }
    
    commit_analysis = {
        'total_commits': 250,
        'unique_authors': 1,
        'days_active': 365,
        'commits_per_day': 0.68,
        'most_active_hour': 14
    }
    
    red_flags = [
        {'type': 'low_activity', 'severity': 'medium'}
    ]
    
    # Generate insights
    insights = generate_profile_insights(profile_data, commit_analysis, red_flags)
    recommendation = generate_recommendation(75, red_flags)
    behavior = analyze_commit_behavior(commit_analysis)
    
    print("\n📊 Results:")
    print(f"Summary: {insights['summary']}")
    print(f"Generated by: {insights['generated_by']}")
    print(f"Recommendation: {recommendation}")
    print(f"Behavior: {behavior}")
    
    print("\n✅ Test complete!")