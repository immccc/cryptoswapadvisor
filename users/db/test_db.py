
from typing import Optional

from users.db.repository import UsersRepository
from users.model import User

class UsersTestRepository(UsersRepository):
    def __init__(self):
        self.users_in_system: dict[str, User] = {}

    def add_user(self, id: str, api_key: Optional[str]):
        self.users_in_system[id] = User(id=id, api_key=api_key)

    def remove_user(self, id: str):
        self.users_in_system.pop(id)

    def get_all_users(self) -> set[User]:
        return set(self.users_in_system.values())

    def get_by_api_key(self, api_key: str) -> Optional[User]:
        for user in self.users_in_system.values():
            if user.api_key == api_key:
                return user
