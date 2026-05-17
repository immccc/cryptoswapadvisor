from abc import ABCMeta, abstractmethod
from typing import Optional

from users.model import User


class UsersRepository(metaclass=ABCMeta):
    @abstractmethod
    def add_user(self, id: str, api_key: Optional[str]):
        raise NotImplementedError

    @abstractmethod
    def remove_user(self, id: str):
        raise NotImplementedError

    @abstractmethod
    def get_all_users(self) -> set[User]:
        raise NotImplementedError

    @abstractmethod
    def get_by_api_key(self, api_key: str) -> Optional[User]:
        raise NotImplementedError