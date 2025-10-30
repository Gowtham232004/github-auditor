"""
git_analyzer.py
Analyzes Git repositories and detects suspicious patterns
Day 2: Core fraud detection logic
"""

import os
import shutil
import tempfile
from git import Repo, GitCommandError
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional
import statistics

class GitAnalysisError(Exception):
    """Custom exception for Git analysis errors"""
    pass


def clone_repository(repo_url: str, max_size_mb: int = 500) -> Optional[Repo]:
    """
    Safely clone a repository to temporary directory
    
    Args:
        repo_url: GitHub repository URL
        max_size_mb: Maximum repo size to clone (safety limit)
        
    Returns:
        Git Repo object or None if failed
        
    Raises:
        GitAnalysisError: If clone fails or repo too large
    """
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="github_audit_")
    
    try:
        print(f"📥 Cloning repository to {temp_dir}...")
        
        # Clone with depth=100 (last 100 commits) for speed
        # Remove depth limit if you want full history
        repo = Repo.clone_from(
            repo_url,
            temp_dir,
            depth=100,  # Limit history for faster cloning
            single_branch=True  # Only main branch
        )
        
        # Check repository size (safety)
        repo_size = get_dir_size(temp_dir) / (1024 * 1024)  # Convert to MB
        
        if repo_size > max_size_mb:
            shutil.rmtree(temp_dir)
            raise GitAnalysisError(f"Repository too large: {repo_size:.1f}MB")
        
        print(f"✅ Repository cloned successfully ({repo_size:.1f}MB)")
        return repo
        
    except GitCommandError as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise GitAnalysisError(f"Failed to clone repository: {str(e)}")
    
    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise GitAnalysisError(f"Unexpected error during clone: {str(e)}")


def get_dir_size(path: str) -> int:
    """Calculate directory size in bytes"""
    total = 0
    for entry in os.scandir(path):
        if entry.is_file():
            total += entry.stat().st_size
        elif entry.is_dir():
            total += get_dir_size(entry.path)
    return total


def analyze_commits(repo: Repo) -> Dict:
    """
    Analyze commit history for patterns
    
    Args:
        repo: Git Repo object
        
    Returns:
        Dictionary with commit analysis
    """
    
    print("🔍 Analyzing commits...")
    
    try:
        commits = list(repo.iter_commits())
        total_commits = len(commits)
        
        if total_commits == 0:
            return {
                "total_commits": 0,
                "error": "No commits found"
            }
        
        # Data collection
        authors = defaultdict(int)
        commit_dates = []
        commit_hours = defaultdict(int)
        commit_days = defaultdict(int)
        commit_sizes = []
        commit_messages = []
        
        for commit in commits:
            # Author analysis
            author = commit.author.name
            authors[author] += 1
            
            # Time analysis
            commit_time = datetime.fromtimestamp(commit.committed_date)
            commit_dates.append(commit_time)
            commit_hours[commit_time.hour] += 1
            commit_days[commit_time.strftime("%A")] += 1
            
            # Size analysis (lines changed)
            try:
                stats = commit.stats.total
                lines_changed = stats.get('lines', 0)
                commit_sizes.append(lines_changed)
            except:
                pass
            
            # Message analysis
            message = commit.message.strip().split('\n')[0]  # First line only
            commit_messages.append(message)
        
        # Calculate statistics
        if commit_dates:
            first_commit = min(commit_dates)
            last_commit = max(commit_dates)
            days_active = (last_commit - first_commit).days
            
            # Time distribution analysis
            most_active_hour = max(commit_hours.items(), key=lambda x: x[1])[0]
            most_active_day = max(commit_days.items(), key=lambda x: x[1])[0]
            
            # Calculate hour concentration (how concentrated commits are in one hour)
            max_hour_commits = max(commit_hours.values())
            hour_concentration = max_hour_commits / total_commits
            
            # Commit size analysis
            if commit_sizes:
                avg_commit_size = statistics.mean(commit_sizes)
                max_commit_size = max(commit_sizes)
                median_commit_size = statistics.median(commit_sizes)
            else:
                avg_commit_size = 0
                max_commit_size = 0
                median_commit_size = 0
            
            # Message quality (simple check for generic messages)
            generic_messages = sum(
                1 for msg in commit_messages 
                if msg.lower() in ['initial commit', 'update', 'fix', 'commit', '.', 'first commit']
            )
            generic_message_ratio = generic_messages / total_commits
            
            return {
                "total_commits": total_commits,
                "unique_authors": len(authors),
                "top_author": max(authors.items(), key=lambda x: x[1])[0],
                "top_author_commits": max(authors.values()),
                "first_commit_date": first_commit.isoformat(),
                "last_commit_date": last_commit.isoformat(),
                "days_active": max(days_active, 1),
                "commits_per_day": round(total_commits / max(days_active, 1), 2),
                "most_active_hour": most_active_hour,
                "most_active_day": most_active_day,
                "hour_concentration": round(hour_concentration, 2),
                "avg_commit_size": round(avg_commit_size, 1),
                "max_commit_size": max_commit_size,
                "median_commit_size": round(median_commit_size, 1),
                "generic_message_ratio": round(generic_message_ratio, 2),
                "commit_hours_distribution": dict(commit_hours),
                "commit_days_distribution": dict(commit_days),
                "authors": dict(authors)
            }
        
        return {"error": "Could not analyze commits"}
        
    except Exception as e:
        return {"error": f"Commit analysis failed: {str(e)}"}


def detect_red_flags(commit_analysis: Dict) -> List[Dict]:
    """
    Detect suspicious patterns (red flags)
    
    Args:
        commit_analysis: Output from analyze_commits()
        
    Returns:
        List of red flag dictionaries
    """
    
    red_flags = []
    
    if "error" in commit_analysis:
        return red_flags
    
    # Red Flag 1: Very few commits
    if commit_analysis["total_commits"] < 5:
        red_flags.append({
            "type": "low_activity",
            "severity": "medium",
            "message": f"Only {commit_analysis['total_commits']} commits (expected 10+)",
            "score_impact": -15
        })
    
    # Red Flag 2: Single author (no collaboration)
    if commit_analysis["unique_authors"] == 1 and commit_analysis["total_commits"] > 5:
        red_flags.append({
            "type": "no_collaboration",
            "severity": "low",
            "message": "Single author with no collaboration",
            "score_impact": -5
        })
    
    # Red Flag 3: High hour concentration (bot behavior)
    if commit_analysis.get("hour_concentration", 0) > 0.8:
        red_flags.append({
            "type": "suspicious_timing",
            "severity": "high",
            "message": f"{int(commit_analysis['hour_concentration']*100)}% of commits at same hour",
            "score_impact": -25
        })
    
    # Red Flag 4: Very large commits (bulk upload)
    if commit_analysis.get("max_commit_size", 0) > 1000:
        red_flags.append({
            "type": "bulk_upload",
            "severity": "high",
            "message": f"Very large commit ({commit_analysis['max_commit_size']} lines)",
            "score_impact": -20
        })
    
    # Red Flag 5: Portfolio farming (many commits in few days)
    if commit_analysis["total_commits"] > 20 and commit_analysis["days_active"] < 7:
        red_flags.append({
            "type": "burst_activity",
            "severity": "high",
            "message": f"{commit_analysis['total_commits']} commits in {commit_analysis['days_active']} days",
            "score_impact": -25
        })
    
    # Red Flag 6: Generic commit messages
    if commit_analysis.get("generic_message_ratio", 0) > 0.5:
        red_flags.append({
            "type": "generic_messages",
            "severity": "medium",
            "message": f"{int(commit_analysis['generic_message_ratio']*100)}% generic commit messages",
            "score_impact": -10
        })
    
    # Red Flag 7: One author dominates completely
    if commit_analysis["unique_authors"] > 1:
        top_author_ratio = commit_analysis["top_author_commits"] / commit_analysis["total_commits"]
        if top_author_ratio > 0.95:
            red_flags.append({
                "type": "dominated_repo",
                "severity": "low",
                "message": f"One author made {int(top_author_ratio*100)}% of commits",
                "score_impact": -5
            })
    
    return red_flags


def calculate_repo_authenticity_score(commit_analysis: Dict, red_flags: List[Dict]) -> int:
    """
    Calculate authenticity score for repository (0-100)
    
    Args:
        commit_analysis: Commit analysis data
        red_flags: List of detected red flags
        
    Returns:
        Score from 0 (fake) to 100 (authentic)
    """
    
    if "error" in commit_analysis:
        return 0
    
    # Start with base score
    score = 50
    
    # Positive indicators
    if commit_analysis["total_commits"] >= 10:
        score += 10
    if commit_analysis["total_commits"] >= 50:
        score += 10
    
    if commit_analysis["unique_authors"] > 1:
        score += 10
    
    if commit_analysis["days_active"] > 30:
        score += 10
    
    if commit_analysis["days_active"] > 90:
        score += 5
    
    if commit_analysis.get("generic_message_ratio", 1) < 0.3:
        score += 5
    
    # Apply red flag penalties
    for flag in red_flags:
        score += flag["score_impact"]  # Already negative
    
    # Keep in valid range
    return max(0, min(100, score))


def analyze_repository(repo_url: str) -> Dict:
    """
    Complete repository analysis
    
    Args:
        repo_url: GitHub repository URL
        
    Returns:
        Complete analysis with commits, patterns, red flags, and score
    """
    
    repo = None
    temp_dir = None
    
    try:
        # Clone repository
        repo = clone_repository(repo_url)
        temp_dir = repo.working_dir
        
        # Analyze commits
        commit_analysis = analyze_commits(repo)
        
        # Detect red flags
        red_flags = detect_red_flags(commit_analysis)
        
        # Calculate score
        authenticity_score = calculate_repo_authenticity_score(commit_analysis, red_flags)
        
        return {
            "repository_url": repo_url,
            "commit_analysis": commit_analysis,
            "red_flags": red_flags,
            "authenticity_score": authenticity_score,
            "analyzed_at": datetime.now().isoformat()
        }
        
    except GitAnalysisError as e:
        return {
            "repository_url": repo_url,
            "error": str(e),
            "analyzed_at": datetime.now().isoformat()
        }
    
    finally:
        # Cleanup: Delete cloned repository
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print("🧹 Cleaned up temporary files")
            except:
                pass


# ============================================
# TEST FUNCTIONS
# ============================================

if __name__ == "__main__":
    """Test Git analysis functions"""
    
    print("🧪 Testing Git Analysis...")
    print("="*60)
    
    # Test with a small public repository
    test_repo = "https://github.com/octocat/Hello-World"
    
    print(f"\n📊 Analyzing: {test_repo}")
    print("-"*60)
    
    result = analyze_repository(test_repo)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"\n✅ Analysis Complete!")
        print(f"\n📈 Commit Analysis:")
        for key, value in result["commit_analysis"].items():
            if not isinstance(value, dict):
                print(f"  {key}: {value}")
        
        print(f"\n⚠  Red Flags ({len(result['red_flags'])}):")
        if result["red_flags"]:
            for flag in result["red_flags"]:
                print(f"  [{flag['severity'].upper()}] {flag['message']}")
        else:
            print("  None detected ✅")
        
        print(f"\n🎯 Authenticity Score: {result['authenticity_score']}/100")
    
    print("\n" + "="*60)
    print("✅ Test complete!")