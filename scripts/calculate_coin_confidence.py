import asyncio
import datetime
import logging

from dotenv import load_dotenv
from coins.actions import update_all_coins
from coins.db.repository import CoinsRepository
from coins.model import INTERVAL_CALCULATE_CONFIDENCE_SECONDS
from runner.dependencies import get_dependencies, register_dependencies

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("coin_confidence_calculator")

async def run_calculation():
    coins_repository = get_dependencies().resolve(CoinsRepository)
    logger.info("Starting coin confidence calculation loop...")
    while True:
        await asyncio.sleep(INTERVAL_CALCULATE_CONFIDENCE_SECONDS)
        # 2 days because this is the longest period to check
        #
        # TODO This is reversed from how dateranges are treated in other parts (reversed).
        # Ideally this should be unified.
        check_from = int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).timestamp())
        check_to = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

        logger.info(f"Calculating coin confidence from {check_from} to {check_to}...")
        await update_all_coins(coins_repository, check_from, check_to)


if __name__ == "__main__":
    register_dependencies()
    asyncio.run(run_calculation())