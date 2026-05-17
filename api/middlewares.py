from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from api.model import VERSION_PATH_PART
from runner.dependencies import get_dependencies
from users.db.repository import UsersRepository
from users.model import User

_PATHS_WITHOUT_API_KEY = [
    f"{VERSION_PATH_PART}{path}" for path in ["/favicon.ico", "/docs", "/redoc", "/openapi.json"]
]

class HideUnknownRoutesMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Verify the route actually exists
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return await call_next(request)
            
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Not found"}
        )
    

class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(path) for path in _PATHS_WITHOUT_API_KEY):
            return await call_next(request)


        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "X-API-Key header missing"}
            )

        hashed_api_key = User.hash_api_key(api_key)
        users_repository: UsersRepository = get_dependencies().resolve(UsersRepository)
        user = users_repository.get_by_api_key(hashed_api_key)

        if not user:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API key"}
            )

        request.state.user = user

        return await call_next(request)