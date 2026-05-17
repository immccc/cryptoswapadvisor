import asyncio
import datetime
from telegram.ext import ContextTypes

from coins.collect.collector import collect
from coins.db.repository import CoinsRepository
from runner.dependencies import get_dependencies


async def run_collection(_: ContextTypes.DEFAULT_TYPE):
    await collect()


async def run_compaction(_: ContextTypes.DEFAULT_TYPE):
    coins_repository: CoinsRepository = get_dependencies().resolve(CoinsRepository)

    coins = await coins_repository.get_coins_registered()

    until_timestamp = int(
        (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).timestamp()
    )

    asyncio.gather(
        *(coins_repository.compact_exchanges(coin, until_timestamp) for coin in coins)
    )
