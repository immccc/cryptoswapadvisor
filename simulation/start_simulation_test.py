from datetime import datetime, timezone
import pytest

from conftest import (
    COIN_BEARISH_1,
    COIN_BEARISH_2,
    COIN_BULLISH_1,
    COIN_BULLISH_2,
    COIN_NEUTRAL_1,
    COIN_NEUTRAL_2,
    COIN_PEAK,
    COIN_VALLEY,
    USER_ID,
)
from coins.db.test_db import CoinsTestRepository
from coins.model import RESERVE_DEFAULT_FIAT_CURRENCY, Coin
from simulation.db.test_db import SimulationTestConfig, SimulationsTestRepository
from simulation.model import Simulation
from simulation.actions import start_simulation


@pytest.mark.asyncio
async def test_distribute_initial_fiat_into_bullish_and_valley_coins(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_standard_coin_evaluations,
    with_exchanges,
):
    sim = await start_simulation(
        coins_repository,
        simulations_repository,
        user_id=USER_ID,
        amount=100,
        timespan_in_hours=12,
        operational_fee_percentage=0.0,
        sim_params=sim_config.get()
    )

    await _assert_sim_after_distribution(
        sim, sim.initial_fiat_amount, coins_repository, simulations_repository
    )


@pytest.mark.asyncio
async def test_distribute_initial_fiat_into_bullish_and_valley_coins_with_weights(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_standard_coin_evaluations,
    with_exchanges,
):
    # TODO Duplicated, maybe convenient to move to a fixture!
    await coins_repository.save_coins(
        *(
            Coin(name=COIN_BULLISH_1, confidences_per_period={12: 80}),
            Coin(name=COIN_BULLISH_2, confidences_per_period={12: 15}),
            Coin(name=COIN_VALLEY, confidences_per_period={12: 5}),
        )
    )

    sim = await start_simulation(
        coins_repository,
        simulations_repository,
        user_id=USER_ID,
        amount=100,
        timespan_in_hours=12,
        operational_fee_percentage=0.0,
        sim_params=sim_config.get()
    )

    await _assert_sim_after_distribution(
        sim,
        sim.initial_fiat_amount,
        coins_repository,
        simulations_repository,
        expected_weights={COIN_BULLISH_1: 0.8, COIN_BULLISH_2: 0.15, COIN_VALLEY: 0.05},
    )


@pytest.mark.asyncio
async def test_do_not_distribute_fiat_into_neutral_or_peaks_coins(
    coins_repository: CoinsTestRepository,
    simulations_repository: SimulationsTestRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_all_coins_evaluated_downtrend,
    with_exchanges,

):
    sim = await start_simulation(
        coins_repository,
        simulations_repository,
        user_id=USER_ID,
        amount=100,
        timespan_in_hours=12,
        operational_fee_percentage=0.0,
        sim_params=sim_config.get()
    )

    assert len(sim.amount_per_coins) > 0
    for coin in sim.amount_per_coins.keys():
        amount = sim.amount_per_coins.get(coin, 0.0)
        if coin == RESERVE_DEFAULT_FIAT_CURRENCY:
            assert sim.initial_fiat_amount == pytest.approx(amount)
        else:
            assert amount == pytest.approx(0.0)


async def _assert_sim_after_distribution(
    sim: Simulation,
    expected_fiat_amount: float,
    coins_repository: CoinsTestRepository,
    sims_repository: SimulationsTestRepository,
    expected_weights: dict[str, float] = None,
):
    assert not sim.amount_per_coins.get(COIN_NEUTRAL_1)
    assert not sim.amount_per_coins.get(COIN_NEUTRAL_2)
    assert not sim.amount_per_coins.get(COIN_BEARISH_1)
    assert not sim.amount_per_coins.get(COIN_BEARISH_2)
    assert not sim.amount_per_coins.get(COIN_PEAK)

    expected_fiat_for_bullish_1 = (
        expected_fiat_amount * expected_weights[COIN_BULLISH_1]
        if expected_weights
        else expected_fiat_amount / 3
    )
    expected_fiat_for_bullish_2 = (
        expected_fiat_amount * expected_weights[COIN_BULLISH_2]
        if expected_weights
        else expected_fiat_amount / 3
    )
    expected_fiat_for_valley = (
        expected_fiat_amount * expected_weights[COIN_VALLEY]
        if expected_weights
        else expected_fiat_amount / 3
    )

    bullish_1_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_BULLISH_1,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[-1]

    assert sim.amount_per_coins.get(COIN_BULLISH_1, 0.0) == pytest.approx(
        expected_fiat_for_bullish_1 / bullish_1_exchange,
    )

    bullish_2_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_BULLISH_2,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[-1]

    assert sim.amount_per_coins.get(COIN_BULLISH_2, 0.0) == pytest.approx(
        expected_fiat_for_bullish_2 / bullish_2_exchange,
    )

    valley_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_VALLEY,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[-1]

    assert sim.amount_per_coins.get(COIN_VALLEY, 0.0) == pytest.approx(
        expected_fiat_for_valley / valley_exchange,
    )

    updated_user = sims_repository.get_simulation(sim.user_id)
    assert updated_user is not None
    assert updated_user.amount_per_coins == sim.amount_per_coins
    assert updated_user.updated_fiat_amount == sim.updated_fiat_amount
