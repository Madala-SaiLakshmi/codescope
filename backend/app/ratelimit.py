import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request


class RateLimiter:
    """Sliding-window limiter kept in process memory.

    Fine for one server process. Several workers or servers need a shared store (Redis).
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                retry = max(1, int(self.window - (now - q[0])) + 1)
                raise HTTPException(
                    status_code=429, detail="Too many requests, try again later",
                    headers={"Retry-After": str(retry)})
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


login_ip_limiter = RateLimiter(limit=20, window_seconds=60)
login_email_limiter = RateLimiter(limit=5, window_seconds=60)
register_limiter = RateLimiter(limit=10, window_seconds=3600)
heavy_limiter = RateLimiter(limit=10, window_seconds=3600)  # analyses and impact reports, per user
