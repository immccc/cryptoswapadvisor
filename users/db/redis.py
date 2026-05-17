import os
from typing import Optional
from redis import Redis

from users.db.repository import UsersRepository
from users.model import User

_USERS_DB = 1


class UsersRedisRepository(UsersRepository):
    _redis_client_users: Redis

    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))

        self._redis_client_users = Redis(
            redis_host, redis_port, db=_USERS_DB, decode_responses=True
        )

    def add_user(self, id: str, api_key: Optional[str]):
        self._redis_client_users.hset(id, mapping={
            "id": 1,
            "api_key": api_key
        }
    )

    def remove_user(self, id: str):
        self._redis_client_users.delete(id)

    def get_all_users(self) -> set[User]:
        all_keys = self._redis_client_users.keys("*") # Ultraslow, but this is not gonna be used so...
        
        raw_users = self._redis_client_users.transaction(
            lambda pipeline: [pipeline.hgetall(key) for key in all_keys]
        )

        return {
            User(
                id=int(user["id"]),
                api_key=user["api_key"]
            ) for user in raw_users # pyright: ignore[reportOptionalIterable]
        }

    
    def get_by_api_key(self, api_key: str) -> Optional[User]:
        users = self.get_all_users() # TODO Why not just deprecating this Redis implementation? It's not neede whatsoever!
        for user in users:
            if user.api_key == api_key:
                return user
