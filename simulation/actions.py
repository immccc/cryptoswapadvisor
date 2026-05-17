from datetime import datetime, timezone
from typing import Optional

import structlog
from structlog.contextvars import bind_contextvars, reset_contextvars

from coins.actions import get_uptrend_coins
from coins.actions import get_exchange_rates_at
from coins.conversion import convert_crypto_to_fiat, convert_fiat_to_crypto
from coins.db.repository import CoinsRepository as CoinsRepository
from coins.model import RESERVE_DEFAULT_FIAT_CURRENCY, Coin

from simulation.db.repository import SimulationsRepository
from simulation.model import Simulation, SimulationParams

log = structlog.get_logger()


async def start_simulation(
    coins_repository: CoinsRepository,
    sims_repository: SimulationsRepository,
    sim_params: SimulationParams,
    user_id: str,
    amount: float,
    timespan_in_hours: int,
    operational_fee_percentage: float,
    at_timestamp: Optional[int] = None,
    trader_pro: bool = False,
    exchange_rates: Optional[dict[str, float]] = {},
    uptrend_coins: Optional[list[Coin]] = [],
    webhook_endpoint: Optional[str] = None,
) -> Simulation:
    
    tokens = bind_contextvars(user_id=user_id, op="start_simulation")

    sim = Simulation(
        user_id=user_id,
        initial_fiat_amount=amount,
        updated_fiat_amount=amount,
        timespan_in_hours=timespan_in_hours,
        operational_fee_percentage=operational_fee_percentage,
        trader_pro=trader_pro,
        webhook_endpoint=webhook_endpoint,
    )
    sim.amount_per_coins[RESERVE_DEFAULT_FIAT_CURRENCY] = sim.initial_fiat_amount

    await _calculate_swap_cryptos(
        coins_repository,
        sim_params,
        sim,
        at_timestamp=at_timestamp,
        exchange_rates=exchange_rates,
        uptrend_coins=uptrend_coins,
    )
    sims_repository.save_simulation(sim, at_timestamp=at_timestamp)

    log.info("Simulation created")
    reset_contextvars(**tokens)

    return sim


async def get_fiat_balance(
    repository: CoinsRepository,
    at_timestamp: int,
    sim: Simulation,
    exchange_rates: Optional[dict[str, float]] = {},
) -> float:
    if not exchange_rates:
        exchange_rates = await get_exchange_rates_at(repository, at_timestamp)

    updated_balance = sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0.0)
    for coin, amount in sim.amount_per_coins.items():
        if coin == RESERVE_DEFAULT_FIAT_CURRENCY:
            continue

        updated_balance += convert_crypto_to_fiat(exchange_rates, coin, amount)

    return round(updated_balance, 2)


async def swap_cryptos(
    coins_repository: CoinsRepository,
    sims_repository: SimulationsRepository,
    sim_params: SimulationParams,
    sim: Simulation,
    at_timestamp: Optional[int] = None,
    exchange_rates: Optional[dict[str, float]] = [],
    uptrend_coins: Optional[list[Coin]] = [],
):
    if not sim:
        raise ValueError("Sim does not exist")

    tokens = bind_contextvars(user_id=sim.user_id, op="swap_cryptos")

    await _calculate_swap_cryptos(
        coins_repository,
        sim_params,
        sim,
        at_timestamp=at_timestamp,
        exchange_rates=exchange_rates,
        uptrend_coins=uptrend_coins,
    )

    sims_repository.save_simulation(sim, at_timestamp=at_timestamp)

    reset_contextvars(**tokens)


async def get_market_recover_signs_over_total(
    repository: CoinsRepository,
    sim_params: SimulationParams,
    timespan_in_hours: int,
    *uptrend_coins: Coin,
) -> tuple[int, int]:
    if not uptrend_coins:
        return (0, 3)

    # Priority is to recover lost balance if panic mode is on, so safer trends are going to be taken:
    coins = await repository.get_coins(*(coin.name for coin in uptrend_coins))
    confidences = [
        coin.get_confidence_for_closest_timespan(timespan_in_hours) for coin in coins
    ]

    num_positive_signals_to_exit_panic = 0

    positive_confidences = [c for c in confidences if c > 0]

    # First good signal check: Positive confidences over a threshold
    if (
        positive_confidences
        and min(positive_confidences) >= sim_params.min_confidence_to_recover
    ):
        num_positive_signals_to_exit_panic += 1

    # Second good signal check: Amount of positive confidences found
    if (
        len(positive_confidences) / len(confidences)
        >= sim_params.ratio_positive_confidences_to_recover
    ):
        num_positive_signals_to_exit_panic += 1

    # Third good signal: In smallest timespans, confidence is growing for most of coins
    confidence_delta_from_smallest_timespans_per_coin = [
        coin.confidences_per_period.get(12, 0.0)
        - coin.confidences_per_period.get(24, 0.0)  # TODO MOVE TO CONSTANTS IN COINS!!
        for coin in coins
    ]

    if (
        len(
            [
                delta
                for delta in confidence_delta_from_smallest_timespans_per_coin
                if delta > sim_params.min_delta_from_windows_diff
            ]
        )
        / len(coins)
        >= sim_params.ratio_deltas_windows
    ):
        num_positive_signals_to_exit_panic += 1

    return (num_positive_signals_to_exit_panic, 3)


async def control_portfolio(
    coins_repository: CoinsRepository,
    sims_repository: SimulationsRepository,
    sim_params: SimulationParams,
    sim: Simulation,
    at_timestamp: Optional[int] = None,
    exchange_rates: Optional[dict[str, float]] = {},
):
    if sim.trader_pro:
        return

    tokens = bind_contextvars(user_id=sim.user_id, op="control_portfolio")

    if not at_timestamp:
        at_timestamp = int(datetime.now(timezone.utc).timestamp())

    current_fiat_balance = await get_fiat_balance(coins_repository, at_timestamp, sim)

    if not sim.panic_mode:
        profit = current_fiat_balance - sim.updated_fiat_amount
        if (
            profit > 0
            and profit < sim.profit_achieved_since_last_rotation * sim_params.ratio_profit_protection
            and profit > current_fiat_balance * (sim.operational_fee_percentage / 100) * 3 # Round trips for reinvesting
        ):
            await _hold_portfolio_in_fiat(
                coins_repository, at_timestamp, sim, exchange_rates=exchange_rates
            )
            sims_repository.save_simulation(sim, at_timestamp=at_timestamp)
            log.info("Holding portfolio in fiat to protect profit", profit=profit, balance=current_fiat_balance, ratios=sim.ratio_per_coins, portfolio=sim.amount_per_coins)
            reset_contextvars(**tokens)
            return

        sim.profit_achieved_since_last_rotation = max(
            sim.profit_achieved_since_last_rotation, profit
        )

        sims_repository.save_simulation(sim, at_timestamp=at_timestamp)

    if _check_panic_should_hold_in_fiat(current_fiat_balance, sim_params, sim):
        if not sim.panic_mode:
            log.info("Entering panic mode and holding portfolio in fiat", balance=current_fiat_balance, ratios=sim.ratio_per_coins, portfolio=sim.amount_per_coins)

        sim.panic_mode = True
        sim.profit_achieved_since_last_rotation = current_fiat_balance
        await _hold_portfolio_in_fiat(
            coins_repository, at_timestamp, sim, exchange_rates=exchange_rates
        )

        sims_repository.save_simulation(sim, at_timestamp=at_timestamp)

    reset_contextvars(**tokens)
    return

async def _calculate_swap_cryptos(
    repository: CoinsRepository,
    sim_params: SimulationParams,
    sim: Simulation,
    at_timestamp: Optional[int] = None,
    exchange_rates: Optional[dict[str, float]] = [],
    uptrend_coins: Optional[list[Coin]] = [],
):

    if not at_timestamp:
        at_timestamp = int(datetime.timestamp(datetime.now(timezone.utc)))

    if not exchange_rates:
        exchange_rates = await get_exchange_rates_at(repository, at_timestamp)

    if not uptrend_coins:
        uptrend_coins = await get_uptrend_coins(
            repository, sim.timespan_in_hours, at_timestamp, filter_by_confidence=True
        )

    # Hold collected amount in fiat if no uptrend coins are in place
    if not uptrend_coins:
        await _hold_portfolio_in_fiat(repository, at_timestamp, sim)
        log.info("Holding portfolio in fiat as no uptrend coins found", ratios=sim.ratio_per_coins, portfolio=sim.amount_per_coins)
        return

    await _recover_from_panic_if_applicable(repository, sim_params, sim, *uptrend_coins)
    if sim.panic_mode:
        return

    # Reinvest current portfolio entirely
    funds_in_fiat_to_move = await get_fiat_balance(repository, at_timestamp, sim)
    sim.amount_per_coins = {}
    sim.ratio_per_coins = {}

    funds_in_fiat_to_move = _get_amount_after_fee_if_applicable(
        sim, funds_in_fiat_to_move
    )

    # Distribute amount into uptrend coins by coin weight
    weight_per_coin = await _get_distribution_weights_per_coin(
        repository, [coin.name for coin in uptrend_coins], sim
    )

    # Some money could be hold in FIAT to avoid unnecesary risks
    ratio_for_coins = 1.0
    confidence_threshold = sim_params.min_confidence_to_recover / 10

    # Min confidence quite low
    if uptrend_coins:
        coin_with_min_confidence = min(
            uptrend_coins,
            key=lambda coin: coin.get_confidence_for_closest_timespan(
                sim.timespan_in_hours
            ),
        )

        min_confidence = coin_with_min_confidence.get_confidence_for_closest_timespan(
            sim.timespan_in_hours
        )
    else:
        min_confidence = 1.0

    if min_confidence < confidence_threshold:
        ratio_for_coins = min_confidence / confidence_threshold

    for coin in uptrend_coins:
        weight = weight_per_coin[coin.name] * ratio_for_coins
        in_crypto = convert_fiat_to_crypto(
            exchange_rates, coin.name, funds_in_fiat_to_move * weight
        )
        sim.amount_per_coins[coin.name] = in_crypto
        sim.ratio_per_coins[coin.name] = weight

    sim.amount_per_coins[RESERVE_DEFAULT_FIAT_CURRENCY] = funds_in_fiat_to_move * (
        1 - ratio_for_coins
    )
    sim.ratio_per_coins[RESERVE_DEFAULT_FIAT_CURRENCY] = 1 - ratio_for_coins

    sim.profit_achieved_since_last_rotation = 0
    sim.updated_fiat_amount = funds_in_fiat_to_move

    log.info("Portfolio rotated", ratios=sim.ratio_per_coins, amounts=sim.amount_per_coins)


def _get_amount_after_fee_if_applicable(sim: Simulation, fiat_amount: float) -> float:
    if not sim.operational_fee_percentage > 0:
        return fiat_amount

    return fiat_amount - round(fiat_amount * (sim.operational_fee_percentage / 100), 2)


async def _get_distribution_weights_per_coin(
    coins_repository: CoinsRepository, coin_names: list[str], sim: Simulation
) -> dict[str, float]:
    coins = await coins_repository.get_coins(*coin_names)

    total_sum_of_confidences = 0
    confidence_per_coin = {}
    for coin in coins:
        confidence_per_coin[coin.name] = max(
            0, coin.get_confidence_for_closest_timespan(sim.timespan_in_hours)
        )
        total_sum_of_confidences += confidence_per_coin[coin.name]

    # Non found coins in DB will have 0 as we don't know if they can be trusted
    for coin_name in coin_names:
        if coin_name in confidence_per_coin:
            continue
        confidence_per_coin[coin_name] = 0

    # This scenario will happen if no coins have been saved in DB,
    # OR in a really bearish market appearing to recover.
    if abs(total_sum_of_confidences) <= 1e-8:
        return {coin_name: 1 / len(coin_names) for coin_name in coin_names}

    return {
        coin: confidence / total_sum_of_confidences
        for coin, confidence in confidence_per_coin.items()
    }


def _check_panic_should_hold_in_fiat(
    current_fiat_balance: float, sim_params: SimulationParams, sim: Simulation
) -> bool:
    if current_fiat_balance <= sim.initial_fiat_amount:
        return (
            current_fiat_balance / sim.initial_fiat_amount
            < sim_params.panic_mode_threshold
        )

    profit_since_beginning = current_fiat_balance - sim.initial_fiat_amount
    profit_since_beginning_ratio = profit_since_beginning / sim.initial_fiat_amount

    profit_influence = profit_since_beginning_ratio / (
        profit_since_beginning_ratio + 1.5
    )
    ratio_from_profit = (
        sim_params.panic_mode_threshold
        + (1 - sim_params.panic_mode_threshold) * profit_influence
    )

    return current_fiat_balance / sim.updated_fiat_amount < ratio_from_profit


async def _hold_portfolio_in_fiat(
    coins_repository: CoinsRepository,
    current_timestamp: int,
    sim: Simulation,
    exchange_rates: Optional[dict[str, float]] = {},
):
    if not exchange_rates:
        exchange_rates = await get_exchange_rates_at(
            coins_repository, current_timestamp
        )

    total_fiat_to_hold = 0
    for coin in sim.amount_per_coins.keys():
        if coin == RESERVE_DEFAULT_FIAT_CURRENCY:
            continue

        amount = sim.amount_per_coins.get(coin, 0)

        total_fiat_to_hold += convert_crypto_to_fiat(exchange_rates, coin, amount)
        sim.amount_per_coins[coin] = 0
        sim.ratio_per_coins[coin] = 0

    total_hold_after_fee = _get_amount_after_fee_if_applicable(sim, total_fiat_to_hold)
    sim.amount_per_coins[RESERVE_DEFAULT_FIAT_CURRENCY] = (
        sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0)
        + total_hold_after_fee
    )
    sim.ratio_per_coins[RESERVE_DEFAULT_FIAT_CURRENCY] = 1.0
    sim.profit_achieved_since_last_rotation = 0

async def _recover_from_panic_if_applicable(
    coins_repository: CoinsRepository,
    sim_params: SimulationParams,
    sim: Simulation,
    *uptrend_coins: Coin,
):
    if sim.trader_pro:
        return

    if not sim.panic_mode:
        return

    recover_signs = await get_market_recover_signs_over_total(
        coins_repository, sim_params, sim.timespan_in_hours, *uptrend_coins
    )

    log.info("Attempt to recover from panic", recover_signs=recover_signs[0], total_signs=recover_signs[1])
    if recover_signs[0] / recover_signs[1] >= sim_params.ratio_recovery_signs:
        sim.panic_mode = False
