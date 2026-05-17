from typing import Iterable
from coins.db.sql.model import CoinConfidence, Exchange
from coins.model import Coin


def map_coin_confidences(coin_confidences: Iterable[CoinConfidence]) -> Coin:
    
    return Coin(
        name=coin_confidences[0].coin_name,
        confidences_per_period={
            coin_confidence.period: coin_confidence.confidence
            for coin_confidence in coin_confidences
        }
    )


def map_exchanges(exchanges: Iterable[Exchange]) -> list[float]:
    return [
        exchange.value for exchange in exchanges
    ]