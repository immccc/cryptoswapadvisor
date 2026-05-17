from datetime import datetime, timezone
from typing import Optional
import pytest

from conftest import (
    COIN_BEARISH_1,
    COIN_BEARISH_2,
    COIN_BULLISH_1,
    COIN_BULLISH_2,
    COIN_VALLEY,
    USER_ID,
)
from coins.db.test_db import CoinsTestRepository
from coins.model import RESERVE_DEFAULT_FIAT_CURRENCY, Coin
from simulation.actions import swap_cryptos
from simulation.db.test_db import SimulationTestConfig, SimulationsTestRepository
from simulation.model import Simulation

_COIN_BEARISH_1_AMOUNT = 23.0
_COIN_BEARISH_2_AMOUNT = 34.0
_COIN_BULLISH_1_AMOUNT = 14.2
_COIN_BULLISH_2_AMOUNT = 15.0
_COIN_VALLEY_AMOUNT = 20.21


@pytest.mark.asyncio
async def test_bearish_moved_to_bullish_with_weights(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_standard_coin_evaluations,
    with_exchanges,
):
    await coins_repository.save_coins(
        *(
            Coin(name=COIN_BULLISH_1, confidences_per_period={12: 80}),
            Coin(name=COIN_BULLISH_2, confidences_per_period={12: 15}),
            Coin(name=COIN_VALLEY, confidences_per_period={12: 5}),
        )
    )

    amount_per_coins_before = {
        COIN_BEARISH_1: _COIN_BEARISH_1_AMOUNT,
        COIN_BEARISH_2: _COIN_BEARISH_2_AMOUNT,
        COIN_BULLISH_1: _COIN_BULLISH_1_AMOUNT,
        COIN_VALLEY: _COIN_VALLEY_AMOUNT,
    }

    sim = Simulation(
        user_id=USER_ID,
        initial_fiat_amount=100.0,
        updated_fiat_amount=100.0,
        timespan_in_hours=13,  # We want to prove also that closest stored period of confidence is taken
        amount_per_coins=amount_per_coins_before,
    )

    sim_params = sim_config.get()

    await swap_cryptos(coins_repository, simulations_repository, sim_params, sim)

    await _assert_swapping(
        coins_repository,
        sim,
        amount_per_coins_before,
        expected_weights={COIN_BULLISH_1: 0.8, COIN_BULLISH_2: 0.15, COIN_VALLEY: 0.05},
    )


@pytest.mark.asyncio
async def test_bearish_moved_to_bullish_with_fee(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_standard_coin_evaluations,
    with_exchanges,
):
    await coins_repository.save_coins(
        *(
            Coin(name=COIN_BULLISH_1, confidences_per_period={12: 80}),
            Coin(name=COIN_BULLISH_2, confidences_per_period={12: 80}),
            Coin(name=COIN_VALLEY, confidences_per_period={12: 80}),
        )
    )

    amount_per_coins_before = {
        COIN_BEARISH_1: _COIN_BEARISH_1_AMOUNT,
        COIN_BEARISH_2: _COIN_BEARISH_2_AMOUNT,
        COIN_BULLISH_1: _COIN_BULLISH_1_AMOUNT,
        COIN_VALLEY: _COIN_VALLEY_AMOUNT,
    }

    sim = Simulation(
        user_id=USER_ID,
        initial_fiat_amount=100.0,
        updated_fiat_amount=100.0,
        operational_fee_percentage=1,
        amount_per_coins=amount_per_coins_before,
    )

    sim_params = sim_config.get()
    await swap_cryptos(coins_repository, simulations_repository, sim_params, sim)

    await _assert_swapping(coins_repository, sim, amount_per_coins_before)


@pytest.mark.asyncio
async def test_hold_to_fiat_when_no_uptrends(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_all_coins_evaluated_downtrend,
    with_exchanges,
):
    previous_fiat_amount = 33
    sim = Simulation(
        user_id=USER_ID,
        initial_fiat_amount=100.0,
        updated_fiat_amount=100.0,
        amount_per_coins={
            COIN_BEARISH_1: _COIN_BEARISH_1_AMOUNT,
            COIN_BEARISH_2: _COIN_BEARISH_2_AMOUNT,
            RESERVE_DEFAULT_FIAT_CURRENCY: previous_fiat_amount,
        },
    )

    sim_params = sim_config.get()
    await swap_cryptos(coins_repository, simulations_repository, sim_params, sim)

    await _assert_holding_to_fiat(coins_repository, sim, previous_fiat_amount)


@pytest.mark.asyncio
async def test_hold_to_fiat_when_no_uptrends_with_fee(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_all_coins_evaluated_downtrend,
    with_exchanges,
):
    previous_fiat_amount = 33
    sim = Simulation(
        user_id=USER_ID,
        initial_fiat_amount=100.0,
        updated_fiat_amount=100.0,
        operational_fee_percentage=1,
        amount_per_coins={
            COIN_BEARISH_1: _COIN_BEARISH_1_AMOUNT,
            COIN_BEARISH_2: _COIN_BEARISH_2_AMOUNT,
            RESERVE_DEFAULT_FIAT_CURRENCY: previous_fiat_amount,
        },
    )

    sim_params = sim_config.get()
    await swap_cryptos(coins_repository, simulations_repository, sim_params, sim)

    await _assert_holding_to_fiat(coins_repository, sim, previous_fiat_amount)


@pytest.mark.asyncio
async def test_no_action_if_sim_is_in_panic(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_standard_coin_evaluations,
    with_exchanges,
):
    await coins_repository.save_coins(
        *(
            Coin(
                name=COIN_BULLISH_1,
                confidences_per_period={
                    12: 1,
                    24: 300,
                },
            ),
            Coin(
                name=COIN_BULLISH_2,
                confidences_per_period={
                    12: -1,
                    24: 300,
                },
            ),
            Coin(
                name=COIN_VALLEY,
                confidences_per_period={
                    12: -2,
                    24: 300,
                },
            ),
        )
    )

    amount_per_coins_expected_to_not_change = {
        COIN_BULLISH_1: 0.0001,
        COIN_BULLISH_2: 0.0000002,
        RESERVE_DEFAULT_FIAT_CURRENCY: 0,
    }
    sim = Simulation(
        user_id=USER_ID,
        initial_fiat_amount=100.0,
        updated_fiat_amount=100.0,
        amount_per_coins=amount_per_coins_expected_to_not_change,
        panic_mode=True,
    )

    sim_params = sim_config.get()
    await swap_cryptos(coins_repository, simulations_repository, sim_params, sim)

    for actual_coin, actual_value in sim.amount_per_coins.items():
        assert amount_per_coins_expected_to_not_change.get(
            actual_coin, 0.0
        ) == pytest.approx(actual_value)


@pytest.mark.asyncio
async def test_ignore_panic_if_trader_pro(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_standard_coin_evaluations,
    with_exchanges,
):
    await coins_repository.save_coins(
        *(
            Coin(
                name=COIN_BULLISH_1,
                confidences_per_period={
                    12: 1,
                    24: 300,
                },
            ),
            Coin(
                name=COIN_BULLISH_2,
                confidences_per_period={
                    12: 30,
                    24: 300,
                },
            ),
            Coin(
                name=COIN_VALLEY,
                confidences_per_period={
                    12: -2,
                    24: 300,
                },
            ),
        )
    )

    sim = Simulation(
        user_id=USER_ID,
        initial_fiat_amount=100.0,
        updated_fiat_amount=10.0,
        amount_per_coins={
            COIN_BULLISH_1: 20,
            COIN_BULLISH_2: 200,
        },
        trader_pro=True,
        panic_mode=True,
    )

    sim_params = sim_config.get()
    await swap_cryptos(coins_repository, simulations_repository, sim_params, sim)

    assert sim.amount_per_coins[COIN_BULLISH_1] > 0
    assert sim.amount_per_coins[COIN_BULLISH_2] > 0


@pytest.mark.asyncio
async def test_coins_to_hold_in_fiat_if_downtrend_and_sim_is_in_panic(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_all_coins_evaluated_downtrend,
    with_exchanges,
):
    await coins_repository.save_coins(
        *(
            Coin(
                name=COIN_BULLISH_1,
                confidences_per_period={
                    24: -3,
                    12: -3,
                },
            ),
            Coin(name=COIN_BULLISH_2, confidences_per_period={24: -4, 12: -20}),
            Coin(
                name=COIN_VALLEY,
                confidences_per_period={
                    24: -5,
                    12: -10000,
                },
            ),
        )
    )

    sim = Simulation(
        user_id=USER_ID,
        initial_fiat_amount=100.0,
        updated_fiat_amount=100.0,
        amount_per_coins={
            COIN_BULLISH_1: 0.0001,
            COIN_BULLISH_2: 0.0000002,
            RESERVE_DEFAULT_FIAT_CURRENCY: 0,
        },
        panic_mode=True,
    )

    sim_params = sim_config.get()
    await swap_cryptos(coins_repository, simulations_repository, sim_params, sim)

    assert sim.amount_per_coins.get(COIN_BULLISH_1, 0.0) == pytest.approx(0)
    assert sim.amount_per_coins.get(COIN_BULLISH_2, 0.0) == pytest.approx(0)
    assert sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0.0) > 0


@pytest.mark.asyncio
async def test_swap_and_disable_panic_when_confidence_increasing(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_standard_coin_evaluations,
    with_exchanges,
):
    await coins_repository.save_coins(
        *(
            Coin(
                name=COIN_BULLISH_1,
                confidences_per_period={
                    24: 0.016,
                    12: 0.2,
                },
            ),
            Coin(
                name=COIN_BULLISH_2,
                confidences_per_period={
                    24: 0.2,
                    12: 10,
                },
            ),
            Coin(
                name=COIN_VALLEY,
                confidences_per_period={
                    24: 0.3,
                    12: 0.00002,
                },
            ),
        )
    )

    sim = Simulation(
        user_id=USER_ID,
        initial_fiat_amount=100.0,
        updated_fiat_amount=100.0,
        amount_per_coins={RESERVE_DEFAULT_FIAT_CURRENCY: 99},
        panic_mode=True,
    )

    sim_params = sim_config.get()
    await swap_cryptos(coins_repository, simulations_repository, sim_params, sim)

    assert not sim.panic_mode
    assert sim.amount_per_coins.get(COIN_BEARISH_1, 0.0) == pytest.approx(0.0)
    assert sim.amount_per_coins.get(COIN_BULLISH_1, 0.0) > 0
    assert sim.amount_per_coins.get(COIN_BULLISH_2, 0.0) > 0
    assert sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0.0) > 0


@pytest.mark.asyncio
async def test_keep_panic_and_dont_swap_when_no_confidence_enough(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_standard_coin_evaluations,
    with_exchanges,
):
    await coins_repository.save_coins(
        *(
            Coin(name=COIN_BULLISH_1, confidences_per_period={24: 0.016, 12: 0.2}),
            Coin(name=COIN_BULLISH_2, confidences_per_period={24: 0.2, 12: 10}),
            Coin(name=COIN_VALLEY, confidences_per_period={24: 0.3, 12: 0.00002}),
        )
    )

    sim = Simulation(
        user_id=USER_ID,
        initial_fiat_amount=100.0,
        updated_fiat_amount=100.0,
        amount_per_coins={
            COIN_BEARISH_1: 0.1,
            COIN_BULLISH_1: 1,
            COIN_BULLISH_2: 2,
        },
        panic_mode=True,
    )

    sim_params = sim_config.get()
    await swap_cryptos(coins_repository, simulations_repository, sim_params, sim)

    assert sim.amount_per_coins.get(COIN_BEARISH_1, 0.0) == pytest.approx(0.0)
    assert sim.amount_per_coins.get(COIN_BULLISH_1, 0.0) > 0
    assert sim.amount_per_coins.get(COIN_BULLISH_2, 0.0) > 0
    assert sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0.0) > 0


@pytest.mark.asyncio
async def test_swap_leave_some_part_in_fiat_if_confidence_not_enough(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_standard_coin_evaluations,
    with_exchanges,
):
    await coins_repository.save_coins(
        *(
            Coin(
                name=COIN_BULLISH_1,
                confidences_per_period={
                    12: 0.00001,
                },
            ),
            Coin(
                name=COIN_BULLISH_2,
                confidences_per_period={
                    12: 0.00002,
                },
            ),
        )
    )

    sim = Simulation(
        user_id=USER_ID,
        initial_fiat_amount=100.0,
        updated_fiat_amount=100.0,
        amount_per_coins={
            COIN_BEARISH_1: 10000,
        },
        panic_mode=False,
    )

    sim_params = sim_config.get()
    await swap_cryptos(coins_repository, simulations_repository, sim_params, sim)

    assert sim.amount_per_coins.get(COIN_BEARISH_1, 0.0) == pytest.approx(0.0)
    assert sim.amount_per_coins.get(COIN_BULLISH_1, 0.0) > 0
    assert sim.amount_per_coins.get(COIN_BULLISH_2, 0.0) > 0
    assert sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0.0) > 0


async def _assert_swapping(
    coins_repository: CoinsTestRepository,
    sim: Simulation,
    amounts_per_coin_before_swap: dict[str, float],
    expected_weights: Optional[dict[str, float]] = {
        COIN_BULLISH_1: 1 / 3,
        COIN_BULLISH_2: 1 / 3,
        COIN_VALLEY: 1 / 3,
    },
):
    assert sim.amount_per_coins.get(COIN_BEARISH_1, 0.0) == pytest.approx(0.0)
    assert sim.amount_per_coins.get(COIN_BEARISH_2, 0.0) == pytest.approx(0.0)

    bearish_1_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_BEARISH_1,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[-1]

    bearish_2_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_BEARISH_2,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[-1]

    bullish_1_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_BULLISH_1,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[-1]

    bullish_2_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_BULLISH_2,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[-1]

    valley_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_VALLEY,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[-1]

    exchange_per_coin = {
        COIN_BEARISH_1: bearish_1_exchange,
        COIN_BEARISH_2: bearish_2_exchange,
        COIN_BULLISH_1: bullish_1_exchange,
        COIN_BULLISH_2: bullish_2_exchange,
        COIN_VALLEY: valley_exchange,
        RESERVE_DEFAULT_FIAT_CURRENCY: 1.0,
    }

    total_to_distribute_in_fiat = sum(
        [
            amount * exchange_per_coin[coin]
            for coin, amount in amounts_per_coin_before_swap.items()
        ]
    )

    total_to_distribute_in_fiat -= round(
        total_to_distribute_in_fiat * (sim.operational_fee_percentage / 100), 2
    )

    fiat_distribution_per_coin = {
        coin: total_to_distribute_in_fiat * weight
        for coin, weight in expected_weights.items()
    }

    expected_portfolio_per_coin = {
        coin: fiat_amount / exchange_per_coin[coin]
        for coin, fiat_amount in fiat_distribution_per_coin.items()
    }

    for coin, amount in expected_portfolio_per_coin.items():
        assert sim.amount_per_coins.get(coin, 0.0) == pytest.approx(amount), (
            f"For coin {coin}, expected amount: {amount}, but got {sim.amount_per_coins.get(coin, 0.0)}."
        )


async def _assert_holding_to_fiat(
    coins_repository: CoinsTestRepository, sim: Simulation, previous_fiat_amount: float
):
    assert (
        len([coin for coin, amount in sim.amount_per_coins.items() if amount > 0]) == 1
    )

    bearish_1_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_BEARISH_1,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[0]

    bearish_2_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_BEARISH_2,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[0]

    expected_total_fiat = _COIN_BEARISH_1_AMOUNT * bearish_1_exchange
    expected_total_fiat += _COIN_BEARISH_2_AMOUNT * bearish_2_exchange
    expected_total_fiat -= round(
        expected_total_fiat * (sim.operational_fee_percentage / 100), 2
    )

    expected_total_fiat += previous_fiat_amount

    assert sim.amount_per_coins[RESERVE_DEFAULT_FIAT_CURRENCY] == expected_total_fiat
