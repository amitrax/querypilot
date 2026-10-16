import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status


class InMemoryRateLimiter:
    def __init__(self, requests_per_minute: int = 15, window_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.history: Dict[str, List[float]] = defaultdict(list)
        self.last_cleanup = time.time()

    def _cleanup_old_records(self, now: float):
        # Run cleanup every 5 minutes
        if now - self.last_cleanup > 300:
            for ip in list(self.history.keys()):
                self.history[ip] = [t for t in self.history[ip] if now - t < self.window_seconds]
                if not self.history[ip]:
                    del self.history[ip]
            self.last_cleanup = now

    def check(self, request: Request):
        now = time.time()
        self._cleanup_old_records(now)

        client_ip = request.client.host if request.client else "unknown"
        timestamps = self.history[client_ip]

        # Filter out timestamps older than window
        valid_timestamps = [t for t in timestamps if now - t < self.window_seconds]
        self.history[client_ip] = valid_timestamps

        if len(valid_timestamps) >= self.requests_per_minute:
            retry_after = int(self.window_seconds - (now - valid_timestamps[0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Too many login/register attempts. Please retry in {max(1, retry_after)} seconds.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self.history[client_ip].append(now)


auth_rate_limiter = InMemoryRateLimiter(requests_per_minute=15, window_seconds=60)
