import asyncio
from typing import Iterable
from coins.db.repository import CoinsRepository
from coins.model import Coin


class CoinsTestRepository(CoinsRepository):
    def __init__(self):
        self.exchanges_db: dict[str, list[tuple[int, float]]] = {}
        self.coins_db: dict[str, Coin] = {}

    async def get_exchanges_from_range(
        self, coin: str, start_timestamp: int, end_timestamp: int
    ) -> list[float]:
        if coin not in self.exchanges_db:
            return []
        return [
            value
            for timestamp, value in self.exchanges_db[coin]
            if start_timestamp <= timestamp <= end_timestamp
        ]

    async def get_exchanges_from_range_multi(
        self, coins: Iterable[str], start_timestamp: int, end_timestamp: int
    ) -> dict[str, list[float]]:
        exchanges = await asyncio.gather(
            *(
                self.get_exchanges_from_range(coin, start_timestamp, end_timestamp) for coin in coins
            )
        )

        return {coin: exchange for coin, exchange in zip(coins, exchanges)}
        

    async def save_exchange(self, coin: str, timestamp: int, value: float) -> None:
        if coin not in self.exchanges_db:
            self.exchanges_db[coin] = []
        self.exchanges_db[coin].append((timestamp, value))

    async def compact_exchanges(self, coin: str, until_timestamp: int) -> None:
        self.exchanges_db[coin] = [exchange for exchange in self.exchanges_db[coin] if exchange[0] >= until_timestamp]

    async def get_coins_registered(self) -> list[str]:
        return sorted(list(self.exchanges_db.keys()))

    async def get_coins(self, *coin_names: str) -> list[Coin]:
        return [
            self.coins_db[coin_name]
            for coin_name in coin_names
            if self.coins_db.get(coin_name)
        ]

    async def save_coins(self, *coins: Coin):
        for coin in coins:
            self.coins_db[coin.name] = coin


def get_test_repository() -> CoinsTestRepository:
    return CoinsTestRepository()


async def add_values_for_coin(
    repository: CoinsTestRepository, coin: str, *values: float
):
    await asyncio.gather(
        *(
            repository.save_exchange(coin, i, exchange)
            for i, exchange in enumerate(values)
        )
    )
