import threading
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    @staticmethod
    def _client_ip(request: Request) -> str:
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip
        fwd = request.headers.get("X-Forwarded-For")
        if fwd:
            return fwd.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next):
        now = time.time()
        window_start = now - 60
        ip = self._client_ip(request)

        with self._lock:
            active_hits = [ts for ts in self._hits[ip] if ts >= window_start]
            if len(active_hits) >= self.requests_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": "60"},
                )
            active_hits.append(now)
            self._hits[ip] = active_hits

        return await call_next(request)
