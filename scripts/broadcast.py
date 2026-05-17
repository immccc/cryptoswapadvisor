import asyncio
import os
import sys

from dotenv import load_dotenv
import httpx
from runner.dependencies import get_dependencies, register_dependencies
from users.db.repository import UsersRepository

load_dotenv(override=True)
token = os.getenv("TELEGRAM_BOT_TOKEN")


async def _send_message(user: int, msg: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": user, "text": msg},
        )


async def broadcast_message(msg: str):
    if not msg:
        print("No message provided. Skipping!")
        return

    users_repository: UsersRepository = get_dependencies().resolve(UsersRepository)
    users = users_repository.get_all_users()
    await asyncio.gather(*(_send_message(user, msg) for user in users))


if __name__ == "__main__":
    register_dependencies()
    asyncio.run(broadcast_message(sys.argv[1]))
