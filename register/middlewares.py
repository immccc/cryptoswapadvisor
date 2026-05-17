from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware


# Useful to cheat attackers, making them thing the endpoint just works and does not have any security measures.
class AlwaysOKMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        await call_next(request)
        return Response(status_code=200)
