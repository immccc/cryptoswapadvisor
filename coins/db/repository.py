from abc import ABCMeta, abstractmethod
from typing import Iterable

from coins.model import Coin


class CoinsRepository(metaclass=ABCMeta):
    @abstractmethod
    async def get_exchanges_from_range(
        self, coin: str, start_timestamp: int, end_timestamp: int
    ) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    async def get_exchanges_from_range_multi(
        self, coins: Iterable[str], start_timestamp: int, end_timestamp: int
    ) -> dict[str, list[float]]:
        raise NotImplementedError


    @abstractmethod
    async def save_exchange(self, coin: str, timestamp: int, value: float) -> None:
        raise NotImplementedError

    @abstractmethod
    async def compact_exchanges(self, coin: str, until_timestamp: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_coins_registered(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    async def get_coins(self, *coin_names: str) -> list[Coin]:
        raise NotImplementedError

    @abstractmethod
    async def save_coins(self, *coins: Coin):
        raise NotImplementedError
