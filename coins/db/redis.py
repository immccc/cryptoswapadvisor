from collections.abc import Iterable
import os
import statistics
from redis import Redis
from coins.db.repository import CoinsRepository
from coins.model import Coin

_EXCHANGES_DB = 0
_COINS_DB = 5


class CoinsRedisRepository(CoinsRepository):
    _redis_client_exchanges: Redis
    _redis_client_coins: Redis

    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))

        self._redis_client_exchanges = Redis(
            redis_host, redis_port, db=_EXCHANGES_DB, decode_responses=True
        )
        self._redis_client_coins = Redis(
            redis_host, redis_port, db=_COINS_DB, decode_responses=True
        )

    async def get_exchanges_from_range(
        self, coin: str, start_timestamp: int, end_timestamp: int
    ) -> list[float]:
        return [
            float(value)
            for value in self._redis_client_exchanges.zrangebyscore(
                coin, start_timestamp, end_timestamp
            )
        ]

    async def get_exchanges_from_range_multi(
        self, coins: Iterable[str], start_timestamp: int, end_timestamp: int
    ) -> dict[str, list[float]]:
        pipeline = self._redis_client_exchanges.pipeline()
        [
            pipeline.zrangebyscore(coin, start_timestamp, end_timestamp)
            for coin in coins
        ]

        results = pipeline.execute()
        results = [[float(v) for v in result] for result in results]

        return { coin: result for coin, result in zip(coins, results) }

    async def get_exchanges_from_range_with_timestamps(
        self, coin: str, start_timestamp: int, end_timestamp: int
    ) -> dict[int, float]:
        return {
            score: float(value)
            for (value, score) in self._redis_client_exchanges.zrangebyscore(
                coin, start_timestamp, end_timestamp, withscores=True
            )
        }

    async def save_exchange(self, coin: str, timestamp: int, value: float) -> None:
        self._redis_client_exchanges.zadd(coin, {str(value): timestamp})

    # Only used for manual migration Redis -> SQL, so no need to add to the base class.
    async def save_exchanges(self, coin: str, exchanges: dict[int, float]) -> None:
        mapping = {str(value): timestamp for timestamp, value in exchanges.items()}
        if not mapping:
            return
        self._redis_client_exchanges.zadd(coin, mapping)

    async def compact_exchanges(self, coin: str, until_timestamp: int) -> None:
        to_be_compacted = self._redis_client_exchanges.zrangebyscore(
            coin, 0, until_timestamp
        )
        self._redis_client_exchanges.zremrangebyscore(coin, 0, until_timestamp)
        compacted = statistics.mean(to_be_compacted)
        self._redis_client_exchanges.zadd(coin, {str(compacted): until_timestamp})

    async def get_coins_registered(self) -> list[str]:
        return sorted([key.decode("utf-8") for key in self._redis_client_exchanges.keys("*")])

    async def get_coins(self, *coin_names: str) -> list[Coin]:
        pipeline = self._redis_client_coins.pipeline()
        [pipeline.hgetall(coin_name) for coin_name in coin_names]

        raw_coins = pipeline.execute()

        return sorted(
            [
                Coin(
                    name=coin_name_and_data[0],
                    confidences_per_period={
                        int(k): float(v) for k, v in coin_name_and_data[1].items()
                    },
                )
                for coin_name_and_data in zip(coin_names, raw_coins)
                if coin_name_and_data
            ],
            key=lambda c: c.name
        )

    async def save_coins(self, *coins: Coin):
        pipeline = self._redis_client_coins.pipeline()
        [
            pipeline.hset(coin.name, mapping=coin.confidences_per_period)
            for coin in coins
        ]

        pipeline.execute()


def get_redis_repository() -> CoinsRedisRepository:
    return CoinsRedisRepository()
