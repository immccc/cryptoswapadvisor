import asyncio
import statistics
from typing import Iterable, Sequence
from sqlalchemy import Engine
from sqlmodel import Session, col, delete, select
from coins.db.redis import CoinsRedisRepository
from coins.db.repository import CoinsRepository
from coins.db.sql._mapping import map_coin_confidences, map_exchanges
from coins.db.sql.model import CoinConfidence, Exchange
from coins.model import INTERVAL_COLLECTION_SECONDS, Coin

_CACHE_ACCEPTABLE_MISSING = 0.9

class CoinsSQLRepository(CoinsRepository):
    engine: Engine
    cache: CoinsRedisRepository

    def __init__(self, engine: Engine):
        self.engine = engine
        self.cache = CoinsRedisRepository()

    async def get_exchanges_from_range(
        self, coin: str, start_timestamp: int, end_timestamp: int
    ) -> list[float]:
        from_cache = await self.cache.get_exchanges_from_range(coin, start_timestamp, end_timestamp)
        expected_count = (end_timestamp - start_timestamp) / INTERVAL_COLLECTION_SECONDS

        if len(from_cache) / expected_count >= _CACHE_ACCEPTABLE_MISSING:
            return from_cache

        with Session(self.engine) as session:
            exchanges = self._get_exchanges_from_range(
                coin, start_timestamp, end_timestamp, session
            )

            await self.cache.save_exchanges(coin, {exchange.timestamp: exchange.value for exchange in exchanges})
            return map_exchanges(exchanges)

    async def get_exchanges_from_range_multi(
        self, coins: Iterable[str], start_timestamp: int, end_timestamp: int
    ) -> dict[str, list[float]]:
        from_cache_per_coin = await self.cache.get_exchanges_from_range_multi(coins, start_timestamp, end_timestamp)
        expected_count = (end_timestamp - start_timestamp) / INTERVAL_COLLECTION_SECONDS

        cache_fulfilled_correctly = True
        for _, from_cache in from_cache_per_coin.items():
            if len(from_cache) / expected_count < _CACHE_ACCEPTABLE_MISSING:
                cache_fulfilled_correctly = False
                break

        if cache_fulfilled_correctly:
            return from_cache_per_coin

        exchanges_per_coin = {}
        with Session(self.engine) as session:
            exchanges = self._get_exchanges_from_range_multi(coins, start_timestamp, end_timestamp, session)
            cache_coros = []
            for exchange in exchanges:
                exchanges_per_coin[exchange.coin_name] = exchanges_per_coin.get(exchange.coin_name, []) + [exchange]
                cache_coros.append(self.cache.save_exchange(exchange.coin_name, exchange.timestamp, exchange.value))
            
            await asyncio.gather(*cache_coros)
            exchanges_per_coin = {coin: map_exchanges(exchanges) for coin, exchanges in exchanges_per_coin.items()}

        return exchanges_per_coin

    async def save_exchange(self, coin: str, timestamp: int, value: float) -> None:
        await self.cache.save_exchange(coin, timestamp, value)

        exchange = Exchange(
            coin_name=coin,
            timestamp=timestamp,
            value=value
        )
        with Session(self.engine) as session:
            session.merge(exchange)
            session.commit()

    async def compact_exchanges(self, coin: str, until_timestamp: int) -> None:
        await self.cache.compact_exchanges(coin, until_timestamp)

        with Session(self.engine) as session:
            exchanges = self._get_exchanges_from_range(coin, 0, until_timestamp, session)
            compacted = statistics.mean(map_exchanges(exchanges))
            
            delete_stmt = delete(Exchange)\
                .where(
                    (Exchange.coin_name == coin) &
                    (Exchange.timestamp <= until_timestamp)
                )
            session.exec(delete_stmt)

            session.merge(
                Exchange(
                    coin_name=coin,
                    timestamp=until_timestamp,
                    value=compacted,
                )
            )
            session.commit()

    async def get_coins_registered(self) -> list[str]:
        with Session(self.engine) as session:
            stmt = select(Exchange.coin_name).distinct().order_by(Exchange.coin_name)
            result = session.exec(stmt)
            return list(result.all())


    async def get_coins(self, *coin_names: str) -> list[Coin]:
        with Session(self.engine) as session:
            stmt = select(CoinConfidence).where(CoinConfidence.coin_name.in_(coin_names)).order_by(CoinConfidence.coin_name) # type: ignore[attr-defined]

            coin_confidences = session.exec(stmt).all()

            per_coin = {}
            for coin_confidence in coin_confidences:
                per_coin[coin_confidence.coin_name] = per_coin.get(coin_confidence.coin_name, []) + [coin_confidence]

            return [
                map_coin_confidences(coin_confidences) for _, coin_confidences in per_coin.items()
            ]

    async def save_coins(self, *coins: Coin):
        with Session(self.engine) as session:
            for coin in coins:
                for period, value in coin.confidences_per_period.items():
                    session.merge(
                        CoinConfidence(
                            coin_name=coin.name,
                            period=period,
                            confidence=value
                        )
                    )
            session.commit()

    def _get_exchanges_from_range(self, coin: str, start_timestamp: int, end_timestamp: int, session: Session) -> Sequence[Exchange]:
        stmt = select(Exchange)\
            .where(
                (Exchange.coin_name == coin) &
                (Exchange.timestamp >= start_timestamp) &
                (Exchange.timestamp <= end_timestamp)
            )
        ret = session.exec(stmt)
        return ret.all()


    def _get_exchanges_from_range_multi(self, coins: list[str], start_timestamp: int, end_timestamp: int, session: Session) -> Sequence[Exchange]:
        stmt = select(Exchange)\
            .where(
                (col(Exchange.coin_name).in_(coins)) &
                (Exchange.timestamp >= start_timestamp) &
                (Exchange.timestamp <= end_timestamp)
            )
        ret = session.exec(stmt)
        return ret.all()

