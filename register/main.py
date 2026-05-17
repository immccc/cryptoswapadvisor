import os
import re

from dotenv import load_dotenv
from fastapi import FastAPI, Request

import httpx
import structlog
import uvicorn

from register.middlewares import AlwaysOKMiddleware
from register.model import UserRegistrationRequest

_MAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

load_dotenv(override=True)

log = structlog.get_logger()

app = FastAPI(
    title="Internal API for registering users for API",
    version="0.0.1",
    openapi_tags=None,
    openapi_url=None,
)

app.add_middleware(AlwaysOKMiddleware)

load_dotenv(override=True)
token = os.getenv("TELEGRAM_BOT_TOKEN")
admin_user = os.getenv("ADMIN_TELEGRAM_ID")


# TODO Perhaps we can move this to a separated place to not repeat
async def _send_message(user: int, msg: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": user, "text": msg},
        )

@app.post("/register")
async def register_user(_: Request, registration_data: UserRegistrationRequest):

    if not re.match(_MAIL_REGEX, registration_data.email):
        log.error("Invalid email format", email=registration_data.email)
        return

    msg = f"🫅 Admin! There's an API request requested from {registration_data.email} !"

    await _send_message(admin_user, msg)



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
