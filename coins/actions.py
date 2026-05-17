import asyncio
import datetime
from typing import List, Optional
from numba import njit

import numpy
import structlog
from coins.db.repository import CoinsRepository as CoinsRepository
from coins.model import Coin, Evaluation, EvaluationWithRank

from coins.price_tracker import PriceTracker

log = structlog.get_logger()

async def get_uptrend_coins(
    coins_repository: CoinsRepository,
    timespan_in_hours: int,
    at_timestamp: int,
    filter_by_confidence=True,
    evaluations: Optional[dict[str, EvaluationWithRank]] = None,
) -> List[Coin]:
    if not evaluations:
        evaluations = await get_evaluations(
            coins_repository, at_timestamp, timespan_in_hours * 3600
        )

    uptrend_coin_names = [
        coin
        for coin, evaluation in evaluations.items()
        if evaluation[0] in (Evaluation.BULLISH, Evaluation.VALLEY)
    ]

    uptrend_coins = await coins_repository.get_coins(*uptrend_coin_names)

    if filter_by_confidence:
        return [
            coin
            for coin in uptrend_coins
            if coin.get_confidence_for_closest_timespan(timespan_in_hours) > 0
        ]

    return uptrend_coins


async def get_evaluations(
    repository: CoinsRepository,
    timestamp: int,
    timespan_in_secs: int,
    *coins: str,
) -> dict[str, EvaluationWithRank]:

    if not coins:
        coins_as_list = await repository.get_coins_registered()
    else:
        coins_as_list = list(coins)

    price_trackers = [PriceTracker(coin) for coin in coins_as_list]
    exchanges_per_coin = await repository.get_exchanges_from_range_multi(coins_as_list, timestamp - timespan_in_secs, timestamp)

    evaluations = {
        price_tracker.coin: price_tracker.evaluate_from_prices(exchanges_per_coin.get(price_tracker.coin, []))
        for price_tracker in price_trackers
    }

    return evaluations


async def update_all_coins(
    coins_repository: CoinsRepository, check_from: int = 0, check_to: int = int(1e12), log_timing: bool = True
):
    return await _update_all_coins(check_from, check_to, coins_repository, log_timing=log_timing)


async def _update_all_coins(
    check_from: int = 0,
    check_to: int = int(1e12),
    coins_repository: Optional[CoinsRepository] = None,
    log_timing: bool = True,
):
    coin_indices = await coins_repository.get_coins_registered()
    coins = await coins_repository.get_coins(*coin_indices)

    time_before = datetime.datetime.now(datetime.timezone.utc)

    # Some coins may not have been yet captured with a confidence index.
    # We need to ensure all of them will be calculated, assuming an original 0 for those not yet captured. 
    for coin_name in coin_indices:
        existing_coin = next((c for c in coins if c.name == coin_name), None)
        if existing_coin:
            continue

        coins.append(Coin(name=coin_name))

    # We need to know the different coin evaluations, given provided periods.
    periods_in_hrs = [12, 24, 48]
    evaluations_per_coin_and_period = await _get_evaluations_per_coin_and_period(
        coins_repository, periods_in_hrs, check_from, check_to, *coins
    )

    # Some ugly mapping is needed here, looking for performance using Numba,
    # given how heavy this operation might be.
    # My apologies to the reader. I swear I had a more readable, pythonic style.
    evaluation_time_ranges = list(evaluations_per_coin_and_period.keys())

    periods_in_secs = [period * 3600 for period in periods_in_hrs]
    amount_of_slopes_per_period = numpy.array(
        [ 
            len(
                [
                    evaluation_time_range
                    for evaluation_time_range in evaluation_time_ranges
                    if (evaluation_time_range[0] - evaluation_time_range[1]) == period_in_secs
                ]
            )
            for period_in_secs  in periods_in_secs
        ]
    )
   
    evaluations = [evaluations_per_coin_and_period[period] for period in evaluation_time_ranges]
    slopes_in_coin_order = numpy.array([evaluation[coin.name][1] for coin in coins for evaluation in evaluations])

    num_coins = len(coins)
    num_periods = len(periods_in_hrs)
    confidences = _calculate_confidences(num_coins, amount_of_slopes_per_period, slopes_in_coin_order)

    # Confidences come grouped by coin in a 1-D array. They have to be distributed
    for coin_idx in range(num_coins):
        for period_idx in range(num_periods):
            period = periods_in_hrs[period_idx]
            coins[coin_idx].confidences_per_period[period] = float(confidences[num_periods * coin_idx + period_idx])

    time_after = datetime.datetime.now(datetime.timezone.utc)

    await coins_repository.save_coins(*coins)

    if log_timing:
        log.info(
            f"Updated confidence for coins: {coin_indices}, time spent: {(time_after - time_before).total_seconds()}"
        )


@njit
def _calculate_confidences(
    num_coins: int,
    amount_of_slopes_per_period: numpy.array,
    slopes_in_coin_order: numpy.array,  # Should come as 1-D chunks [coin1_evaluation, coin1_evaluation, ..., coin2_evaluation, coin2_evaluation,...]
) -> numpy.array:

    total_slopes_per_coin = numpy.sum(amount_of_slopes_per_period)

    confidences = numpy.zeros(num_coins * len(amount_of_slopes_per_period), dtype=numpy.float64)

    confidence_idx = 0
    for coin_idx in range(num_coins):
        slope_slice_start = 0

        # Get std deviations for each computed period of the coin represented by its index
        slope_slice_start = total_slopes_per_coin * coin_idx
        slope_slice_end = slope_slice_start
        std_deviations = numpy.zeros(amount_of_slopes_per_period.size, dtype=numpy.float64)
        std_deviations_idx = 0
        for num_slopes in amount_of_slopes_per_period:
            slope_slice_end = slope_slice_start + num_slopes
            slopes = slopes_in_coin_order[slope_slice_start: slope_slice_end]

            std_deviations[std_deviations_idx] = numpy.std(slopes)
            std_deviations_idx += 1

            slope_slice_start = slope_slice_end

        # Compute confidence value for each period of the coin
        slope_slice_start = total_slopes_per_coin * coin_idx
        slope_slice_end = slope_slice_start
        std_deviations_idx = 0
        for num_slopes in amount_of_slopes_per_period:
            slope_slice_end = slope_slice_start + num_slopes
            slopes = slopes_in_coin_order[slope_slice_start: slope_slice_end]

            confidences_per_period = slopes / (1 + std_deviations[std_deviations_idx])
            confidences[confidence_idx] = numpy.median(confidences_per_period)

            confidence_idx += 1
            std_deviations_idx += 1

            slope_slice_start = slope_slice_end

    return confidences

async def _get_evaluations_per_coin_and_period(
    coins_repository: CoinsRepository,
    periods_in_hrs: list[int],
    check_from: int,
    check_to: int,
    *coins: Coin,
) -> dict[(int, int), dict[str, float]]:
    evaluations_per_coin_and_period: dict[(int, int), dict[str, float]] = {}
    coin_names = [coin.name for coin in coins]
    for period in periods_in_hrs:
        period_in_seconds = period * 3600

        for timestamp_window_start in range(check_from, check_to, period_in_seconds):
            timestamp_window_end = timestamp_window_start + period_in_seconds
            evaluations_per_coin_and_period[
                (timestamp_window_end, timestamp_window_start)
            ] = await get_evaluations(
                coins_repository,
                timestamp_window_end,
                period_in_seconds,
                *coin_names,
            )

    return evaluations_per_coin_and_period

async def get_exchange_rates_at(
    repository: CoinsRepository, timestamp: int
) -> dict[str, float]:
    coins = await repository.get_coins_registered()

    async with asyncio.TaskGroup() as tg:
        tasks = {
            coin: tg.create_task(
                repository.get_exchanges_from_range(
                    coin, timestamp - (3600 * 12), timestamp
                )
            )
            for coin in coins
        }

    return {
        coin: (task.result())[-1]
        for coin, task in tasks.items()
        if len(task.result()) > 0
    }
