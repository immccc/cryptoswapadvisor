import structlog

from coins.db.repository import CoinsRepository
from coins.prices import PriceListing
from coins.collect.client import get_latest
from runner.dependencies import get_dependencies

log = structlog.get_logger()

async def collect():
    price_listing = get_latest()
    await _save_prices(price_listing)
    log.info("Collection performed")


async def _save_prices(price_listing: PriceListing) -> None:
    coins_repository: CoinsRepository = get_dependencies().resolve(CoinsRepository)

    for coin, prices in price_listing.prices_per_coin.items():
        for price in prices:
            await coins_repository.save_exchange(coin, price.timestamp, price.price)
