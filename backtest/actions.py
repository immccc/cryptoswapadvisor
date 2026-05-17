import asyncio
from collections.abc import Iterable
import math
import requests
import structlog

from datetime import datetime, timezone

from backtest.broker.model import ComputedExchange
from coins.actions import update_all_coins
from coins.db.repository import CoinsRepository
from coins.model import Coin
from simulation.actions import control_portfolio, start_simulation, swap_cryptos
from simulation.db.repository import SimulationsRepository
from simulation.model import SimulationParams

_SECS_PER_DAY = 60 * 60 * 24

log = structlog.get_logger()

def _build_binance_url(from_timestamp: int, to_timestamp: int, coin_name: str) -> str:
    return f"https://api.binance.com/api/v3/klines?symbol={coin_name}USDT&interval=5m&startTime={from_timestamp}000&endTime={to_timestamp}000"

def import_prices(
    from_timestamp: int,
    to_timestamp: int,
    coins: list[str],
) -> dict[str, list[float]]:
    prices_per_coin: dict[str, list[float]] = {}

    time_range = range(from_timestamp, to_timestamp, _SECS_PER_DAY)
    progress_ratio = 1.0 / (len(coins) * len(time_range))

    for coin in coins:
        log.info(
            "Importing data from Binance",
            coin=coin,
            total_coins=len(coins),
            progress_ratio=progress_ratio,
        )

        for timestamp in time_range:
            url = _build_binance_url(timestamp, timestamp + _SECS_PER_DAY, coin)
            response = requests.get(url)
            if response.status_code != 200:
                log.error(
                    "Error importing data", coin=coin, at_timestamp=timestamp, status_code=response.status_code, reason=response.text
                )
                if prices_per_coin.get(coin):
                    prices_per_coin[coin] = prices_per_coin.get(coin, []) + [0.0]
                continue

            response = response.json()
            prices_per_coin[coin] = prices_per_coin.get(coin, []) + [
                (float(candle[2]) + float(candle[3])) / 2.0 for candle in response
            ]

        # time.sleep(0.5) # To avoid rate limitation

    return prices_per_coin


async def run_backtest(
    computed_exchanges: Iterable[ComputedExchange],
    coins: Iterable[Coin],
    coins_repository: CoinsRepository,
    sims_repository: SimulationsRepository,
    sim_params: SimulationParams,
    timespan_in_hrs: int = 0,
    initial_amount: float = 0.0,
    trader_pro: bool = False,
    sim_id: int = 1
):
    log.info("Running backtest")
    await coins_repository.save_coins(*coins)

    timestamps = sorted(computed_exchanges[0].values_per_time.keys())
    initial_timestamp = timestamps[0]

    sim = None
    last_swap = 0

    for timestamp in timestamps:
        await asyncio.sleep(0.01)
        for computed_exchange in computed_exchanges:
            await coins_repository.save_exchange(
                computed_exchange.coin_name,
                timestamp,
                computed_exchange.values_per_time.get(timestamp, 0.0),
            )

        # Do not start simulation until enough exchanges are present to calculate trend
        seconds_spent = (
            datetime.fromtimestamp(timestamp, timezone.utc)
            - datetime.fromtimestamp(initial_timestamp, timezone.utc)
        ).total_seconds()
        minutes_spent = math.floor(seconds_spent / 60)
        hours_spent = math.floor(minutes_spent / 60)

        if hours_spent <= timespan_in_hrs:
            continue

        # Approx every 10 mins confidences are recalculated, from 2 days ahead to present
        # To avoid miscalculations, preset confidence value brought by the user will be taken
        # if time < 2 days.
        timestamp_2_days_ago = timestamp - (60 * 60 * 24 * 2)
        if timestamp_2_days_ago >= 0:
            await asyncio.gather(*(coins_repository.compact_exchanges(coin.name, until_timestamp=timestamp_2_days_ago) for coin in coins))

        if hours_spent >= 12 and minutes_spent % 10 == 0:
            await update_all_coins(
                coins_repository,
                check_from=max(0, timestamp_2_days_ago),
                check_to=timestamp,
                # This gets quiet annoying on backtests, and it's unnecessary. Tracking time is only useful on real coin samples
                log_timing=False
            )

        if not sim:
            sim = await start_simulation(
                coins_repository,
                sims_repository,
                sim_params,
                sim_id,
                initial_amount,
                timespan_in_hrs,
                0.1,  # TODO Convenient to parametrize,
                at_timestamp=timestamp,
                trader_pro=trader_pro,
            )
            continue

        # Approx every 10 mins portfolio is controlled
        if sim and minutes_spent % 10 == 0:
            await control_portfolio(
                coins_repository, sims_repository, sim_params, sim, timestamp
            )

        if last_swap != hours_spent and hours_spent % sim.timespan_in_hours == 0:
            last_swap = hours_spent
            await swap_cryptos(
                coins_repository, sims_repository, sim_params, sim, timestamp
            )

    log.info("Finished backtest")
