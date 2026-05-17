from functools import partial

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware import Middleware

from api.model import VERSION_PATH_PART
from api.simulations import endpoints as simulations_endpoints
from api.users import endpoints as users_endpoints
from api.middlewares import ApiKeyMiddleware, HideUnknownRoutesMiddleware
from runner.dependencies import register_dependencies

import uvicorn

load_dotenv(override=True)

@asynccontextmanager
async def _lifespan(_: FastAPI):
    register_dependencies()
    yield

def _openapi_with_api_key(app: FastAPI) -> dict[str, any]:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema

    return app.openapi_schema

app = FastAPI(
    title="Crypto Simulation API",
    description=
        "API for managing cryptocurrency trading simulations for Premium users." \
        "\n\nIt allows creating, consulting, and deleting automated simulated portfolios." \
        "\n\nYou can connect signals with your script via webhooks." \
        "\n\n**Note**: Bot offers advice and may incur into losses, as crypto market is volatile. " \
        "You're accountable to what you do with received data." \
        "\n\n**Security**: Requires an API Key in a X-API-Key header",
    version="0.0.1",
    contact={
        "name": "Support",
        "email": "swapscr@proton.me",
    },
    lifespan=_lifespan,
    middleware=[Middleware(HideUnknownRoutesMiddleware), Middleware(ApiKeyMiddleware)],
    docs_url=f"{VERSION_PATH_PART}/docs",
    redoc_url=f"{VERSION_PATH_PART}/redoc",
    openapi_url=f"{VERSION_PATH_PART}/openapi.json",
)

app.openapi = partial(_openapi_with_api_key, app)
app.include_router(simulations_endpoints.router, prefix=VERSION_PATH_PART)
app.include_router(users_endpoints.router, prefix=VERSION_PATH_PART)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
