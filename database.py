"""
database.py
Handles all database operations
"""

import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import json

DATABASE_NAME = "github_auditor.db"

def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


def initialize_database():
    """
    Create database tables if they don't exist
    Run this once when app starts
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create profiles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            username TEXT PRIMARY KEY,
            name TEXT,
            bio TEXT,
            location TEXT,
            email TEXT,
            company TEXT,
            blog TEXT,
            public_repos INTEGER,
            followers INTEGER,
            following INTEGER,
            created_at TEXT,
            profile_url TEXT,
            avatar_url TEXT,
            analyzed_at TEXT NOT NULL
        )
    ''')
    
    # Create statistics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            total_repos INTEGER,
            total_stars INTEGER,
            total_forks INTEGER,
            most_used_language TEXT,
            average_stars INTEGER,
            forked_repos INTEGER,
            original_repos INTEGER,
            fork_ratio REAL,
            languages_json TEXT,
            analyzed_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES profiles(username)
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print("✅ Database initialized successfully")


def save_analysis(username: str, analysis_data: Dict) -> bool:
    """
    Save complete analysis to database
    
    Args:
        username: GitHub username
        analysis_data: Complete analysis dictionary from github_api.analyze_github_user()
        
    Returns:
        True if successful, False otherwise
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        profile = analysis_data['profile']
        stats = analysis_data['statistics']
        timestamp = datetime.now().isoformat()
        
        # Insert or replace profile
        cursor.execute('''
            INSERT OR REPLACE INTO profiles 
            (username, name, bio, location, email, company, blog, 
             public_repos, followers, following, created_at, 
             profile_url, avatar_url, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile['username'],
            profile.get('name'),
            profile.get('bio'),
            profile.get('location'),
            profile.get('email'),
            profile.get('company'),
            profile.get('blog'),
            profile['public_repos'],
            profile['followers'],
            profile['following'],
            profile['created_at'],
            profile['profile_url'],
            profile.get('avatar_url'),
            timestamp
        ))
        
        # Insert statistics (new record each time for history)
        cursor.execute('''
            INSERT INTO statistics 
            (username, total_repos, total_stars, total_forks, 
             most_used_language, average_stars, forked_repos, 
             original_repos, fork_ratio, languages_json, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            username,
            stats['total_repos'],
            stats['total_stars'],
            stats['total_forks'],
            stats['most_used_language'],
            stats['average_stars'],
            stats['forked_repos'],
            stats['original_repos'],
            stats['fork_ratio'],
            json.dumps(stats['languages']),
            timestamp
        ))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Error saving to database: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


def get_profile(username: str) -> Optional[Dict]:
    """
    Get profile from database
    
    Args:
        username: GitHub username
        
    Returns:
        Profile dictionary or None if not found
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM profiles WHERE username = ?', (username,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_latest_statistics(username: str) -> Optional[Dict]:
    """
    Get latest statistics for user
    
    Args:
        username: GitHub username
        
    Returns:
        Statistics dictionary or None if not found
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM statistics 
        WHERE username = ?
        ORDER BY analyzed_at DESC
        LIMIT 1
    ''', (username,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        stats = dict(row)
        # Parse JSON languages
        if stats.get('languages_json'):
            stats['languages'] = json.loads(stats['languages_json'])
        return stats
    
    return None


def get_all_profiles() -> List[Dict]:
    """
    Get all analyzed profiles from database
    
    Returns:
        List of profile dictionaries
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, name, followers, public_repos, analyzed_at
        FROM profiles
        ORDER BY analyzed_at DESC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_analysis_history(username: str) -> List[Dict]:
    """
    Get analysis history for a user (all past analyses)
    
    Args:
        username: GitHub username
        
    Returns:
        List of statistics dictionaries ordered by date
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM statistics
        WHERE username = ?
        ORDER BY analyzed_at DESC
    ''', (username,))
    
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        stats = dict(row)
        if stats.get('languages_json'):
            stats['languages'] = json.loads(stats['languages_json'])
        results.append(stats)
    
    return results


def delete_profile(username: str) -> bool:
    """
    Delete profile and all associated statistics
    
    Args:
        username: GitHub username
        
    Returns:
        True if successful, False otherwise
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM statistics WHERE username = ?', (username,))
        cursor.execute('DELETE FROM profiles WHERE username = ?', (username,))
        conn.commit()
        return True
    
    except Exception as e:
        print(f"❌ Error deleting profile: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()


def get_database_stats() -> Dict:
    """
    Get overall database statistics
    
    Returns:
        Dictionary with database stats
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Count profiles
    cursor.execute('SELECT COUNT(*) as count FROM profiles')
    profile_count = cursor.fetchone()['count']
    
    # Count analyses
    cursor.execute('SELECT COUNT(*) as count FROM statistics')
    analysis_count = cursor.fetchone()['count']
    
    # Get top languages
    cursor.execute('''
        SELECT most_used_language, COUNT(*) as count
        FROM statistics
        WHERE most_used_language IS NOT NULL
        GROUP BY most_used_language
        ORDER BY count DESC
        LIMIT 5
    ''')
    
    top_languages = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total_profiles": profile_count,
        "total_analyses": analysis_count,
        "top_languages": top_languages
    }


# ============================================
# TEST FUNCTIONS
# ============================================

if __name__ == "__main__":
    """Test database functions"""
    
    print("🧪 Testing database functions...")
    
    # Test 1: Initialize database
    print("\nTest 1: Initialize database")
    initialize_database()
    
    # Test 2: Save dummy data
    print("\nTest 2: Save analysis")
    dummy_analysis = {
        "profile": {
            "username": "test_user",
            "name": "Test User",
            "bio": "Test bio",
            "location": "Test City",
            "email": None,
            "company": "Test Co",
            "blog": None,
            "public_repos": 10,
            "followers": 100,
            "following": 50,
            "created_at": "2020-01-01T00:00:00Z",
            "profile_url": "https://github.com/test_user",
            "avatar_url": None
        },
        "statistics": {
            "total_repos": 10,
            "total_stars": 500,
            "total_forks": 50,
            "most_used_language": "Python",
            "average_stars": 50,
            "forked_repos": 2,
            "original_repos": 8,
            "fork_ratio": 0.2,
            "languages": {"Python": 6, "JavaScript": 4}
        }
    }
    
    success = save_analysis("test_user", dummy_analysis)
    print(f"{'✅' if success else '❌'} Save analysis: {success}")
    
    # Test 3: Retrieve profile
    print("\nTest 3: Retrieve profile")
    profile = get_profile("test_user")
    if profile:
        print(f"✅ Retrieved profile: {profile['username']}")
    else:
        print("❌ Failed to retrieve profile")
    
    # Test 4: Get statistics
    print("\nTest 4: Get statistics")
    stats = get_latest_statistics("test_user")
    if stats:
        print(f"✅ Retrieved stats: {stats['total_stars']} stars")
    else:
        print("❌ Failed to retrieve stats")
    
    # Test 5: Get all profiles
    print("\nTest 5: Get all profiles")
    all_profiles = get_all_profiles()
    print(f"✅ Found {len(all_profiles)} profiles in database")
    
    # Test 6: Database stats
    print("\nTest 6: Database statistics")
    db_stats = get_database_stats()
    print(f"✅ Total profiles: {db_stats['total_profiles']}")
    print(f"✅ Total analyses: {db_stats['total_analyses']}")
    
    print("\n✅ All database tests completed!")