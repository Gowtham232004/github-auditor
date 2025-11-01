"""
health_monitor.py
System health monitoring and statistics
UNIQUE FEATURE: Real-time system insights
"""

import psutil
import os
from datetime import datetime, timedelta
from typing import Dict
import database
from config import config

class HealthMonitor:
    """Monitor system health and statistics"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        self.analysis_count = 0
    
    def increment_requests(self):
        """Increment request counter"""
        self.request_count += 1
    
    def increment_errors(self):
        """Increment error counter"""
        self.error_count += 1
    
    def increment_analyses(self):
        """Increment analysis counter"""
        self.analysis_count += 1
    
    def get_uptime(self) -> Dict:
        """Get application uptime"""
        uptime = datetime.now() - self.start_time
        
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return {
            "started_at": self.start_time.isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_formatted": f"{days}d {hours}h {minutes}m {seconds}s"
        }
    
    def get_system_metrics(self) -> Dict:
        """Get system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": psutil.virtual_memory().used / (1024 * 1024),
            "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
            "disk_percent": psutil.disk_usage('/').percent,
            "disk_used_gb": psutil.disk_usage('/').used / (1024 * 1024 * 1024),
            "disk_free_gb": psutil.disk_usage('/').free / (1024 * 1024 * 1024)
        }
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            db_stats = database.get_database_stats()
            
            # Add database file size
            db_path = config.DATABASE_NAME
            if os.path.exists(db_path):
                db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            else:
                db_size_mb = 0
            
            return {
                **db_stats,
                "database_size_mb": round(db_size_mb, 2)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_api_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "total_analyses": self.analysis_count,
            "error_rate": round(self.error_count / max(self.request_count, 1) * 100, 2)
        }
    
    def get_complete_health(self) -> Dict:
        """Get complete health report"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "environment": config.ENVIRONMENT,
            "version": config.API_VERSION,
            "uptime": self.get_uptime(),
            "system": self.get_system_metrics(),
            "database": self.get_database_stats(),
            "api": self.get_api_stats()
        }
    
    def is_healthy(self) -> bool:
        """Check if system is healthy"""
        try:
            metrics = self.get_system_metrics()
            
            # Check critical thresholds
            if metrics["memory_percent"] > 90:
                return False
            if metrics["cpu_percent"] > 95:
                return False
            if metrics["disk_percent"] > 95:
                return False
            
            return True
        except:
            return False


# Create global monitor instance
health_monitor = HealthMonitor()


if __name__ == "__main__":
    """Test health monitor"""
    print("🧪 Testing Health Monitor...")
    
    # Simulate some activity
    health_monitor.increment_requests()
    health_monitor.increment_requests()
    health_monitor.increment_analyses()
    
    # Get complete health report
    health = health_monitor.get_complete_health()
    
    print("\n📊 System Health Report:")
    print(f"Status: {health['status']}")
    print(f"Uptime: {health['uptime']['uptime_formatted']}")
    print(f"CPU: {health['system']['cpu_percent']}%")
    print(f"Memory: {health['system']['memory_percent']}%")
    print(f"Requests: {health['api']['total_requests']}")
    print(f"Analyses: {health['api']['total_analyses']}")
    
    print("\n✅ Health monitor test complete!")