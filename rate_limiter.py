"""
rate_limiter.py
Simple in-memory rate limiting
For production, use Redis-based rate limiting
"""

from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import HTTPException, Request
from config import config

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 100, window_hours: int = 1):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed per window
            window_hours: Time window in hours
        """
        self.max_requests = max_requests
        self.window_hours = window_hours
        self.requests: Dict[str, list] = defaultdict(list)
    
    def _clean_old_requests(self, ip: str):
        """Remove requests older than time window"""
        cutoff_time = datetime.now() - timedelta(hours=self.window_hours)
        self.requests[ip] = [
            req_time for req_time in self.requests[ip]
            if req_time > cutoff_time
        ]
    
    def is_allowed(self, ip: str) -> Tuple[bool, int, int]:
        """
        Check if request is allowed
        
        Args:
            ip: Client IP address
            
        Returns:
            Tuple of (allowed, remaining_requests, reset_seconds)
        """
        # Clean old requests
        self._clean_old_requests(ip)
        
        # Count current requests
        current_count = len(self.requests[ip])
        
        if current_count >= self.max_requests:
            # Calculate reset time
            oldest_request = min(self.requests[ip])
            reset_time = oldest_request + timedelta(hours=self.window_hours)
            reset_seconds = int((reset_time - datetime.now()).total_seconds())
            
            return False, 0, reset_seconds
        
        # Allow request
        self.requests[ip].append(datetime.now())
        remaining = self.max_requests - current_count - 1
        
        return True, remaining, self.window_hours * 3600
    
    def get_info(self, ip: str) -> Dict:
        """Get rate limit info for IP"""
        self._clean_old_requests(ip)
        current_count = len(self.requests[ip])
        
        return {
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - current_count),
            "used": current_count,
            "reset_in_seconds": self.window_hours * 3600
        }


# Create global rate limiter instance
rate_limiter = RateLimiter(
    max_requests=config.RATE_LIMIT_PER_HOUR,
    window_hours=1
)


async def check_rate_limit(request: Request):
    """
    FastAPI dependency for rate limiting
    
    Usage:
        @app.get("/endpoint", dependencies=[Depends(check_rate_limit)])
    """
    # Get client IP
    client_ip = request.client.host
    
    # Check rate limit
    allowed, remaining, reset_seconds = rate_limiter.is_allowed(client_ip)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {reset_seconds} seconds.",
            headers={
                "X-RateLimit-Limit": str(config.RATE_LIMIT_PER_HOUR),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_seconds),
                "Retry-After": str(reset_seconds)
            }
        )
    
    # Add rate limit headers to response (done in middleware)
    return {
        "remaining": remaining,
        "reset": reset_seconds
    }


if __name__ == "__main__":
    """Test rate limiter"""
    print("🧪 Testing Rate Limiter...")
    
    test_limiter = RateLimiter(max_requests=5, window_hours=1)
    test_ip = "192.168.1.1"
    
    # Make 5 requests (should all succeed)
    for i in range(5):
        allowed, remaining, _ = test_limiter.is_allowed(test_ip)
        print(f"Request {i+1}: {'✅ Allowed' if allowed else '❌ Blocked'} (Remaining: {remaining})")
    
    # 6th request should fail
    allowed, remaining, reset = test_limiter.is_allowed(test_ip)
    print(f"Request 6: {'✅ Allowed' if allowed else '❌ Blocked'} (Reset in: {reset}s)")
    
    print("\n✅ Rate limiter test complete!")