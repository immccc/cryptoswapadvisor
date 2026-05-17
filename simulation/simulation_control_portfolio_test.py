import pytest

from coins.db.repository import CoinsRepository
from coins.model import RESERVE_DEFAULT_FIAT_CURRENCY
from conftest import COIN_BEARISH_1, COIN_BULLISH_1
from simulation.actions import control_portfolio
from simulation.db.repository import SimulationsRepository
from simulation.db.test_db import SimulationTestConfig
from simulation.model import Simulation

_USER_ID = 1
_COIN_BULLISH_1_EXCHANGE = 1000.0
_COIN_BEARISH_1_EXCHANGE = 5.0


def _fiat_after_fee(coin_amount: float, exchange: float, fee_pct: float) -> float:
    fiat = coin_amount * exchange
    return fiat - round(fiat * (fee_pct / 100), 2)


@pytest.mark.asyncio
async def test_control_portfolio_enters_panic_if_balance_notably_lower_than_updated(
    coins_repository: CoinsRepository,
    simulations_repository: SimulationsRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_exchanges,
    with_all_coins_evaluated_downtrend,
):
    coin_amount = 20
    sim = Simulation(
        user_id=_USER_ID,
        initial_fiat_amount=12,
        updated_fiat_amount=1_000_000_000,
        amount_per_coins={COIN_BEARISH_1: coin_amount},
        operational_fee_percentage=1,
    )

    await control_portfolio(coins_repository, simulations_repository, sim_config.get(), sim)

    assert sim.panic_mode
    assert sim.amount_per_coins.get(COIN_BEARISH_1, 0.0) == pytest.approx(0.0)
    expected_fiat = _fiat_after_fee(coin_amount, _COIN_BEARISH_1_EXCHANGE, 1)
    assert sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0.0) == pytest.approx(expected_fiat)


@pytest.mark.asyncio
async def test_control_portfolio_enters_panic_if_balance_notably_lower_than_initial(
    coins_repository: CoinsRepository,
    simulations_repository: SimulationsRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_exchanges,
    with_all_coins_evaluated_downtrend,
):
    coin_amount = 2.0
    sim = Simulation(
        user_id=_USER_ID,
        initial_fiat_amount=10_000_000,
        updated_fiat_amount=12,
        amount_per_coins={COIN_BEARISH_1: coin_amount},
        operational_fee_percentage=1,
    )

    await control_portfolio(coins_repository, simulations_repository, sim_config.get(), sim)

    assert sim.panic_mode
    assert sim.amount_per_coins.get(COIN_BEARISH_1, 0.0) == pytest.approx(0.0)
    expected_fiat = _fiat_after_fee(coin_amount, _COIN_BEARISH_1_EXCHANGE, 1)
    assert sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0.0) == pytest.approx(expected_fiat)


@pytest.mark.asyncio
async def test_control_portfolio_does_not_enter_panic_if_loss_is_small(
    coins_repository: CoinsRepository,
    simulations_repository: SimulationsRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_exchanges,
    with_standard_coin_evaluations,
):
    sim = Simulation(
        user_id=_USER_ID,
        initial_fiat_amount=100,
        updated_fiat_amount=100,
        amount_per_coins={COIN_BULLISH_1: 0.091},
        operational_fee_percentage=1,
        panic_mode=False,
    )

    await control_portfolio(coins_repository, simulations_repository, sim_config.get(), sim)

    assert not sim.panic_mode


@pytest.mark.asyncio
async def test_control_portfolio_stays_in_panic_and_holds_fiat_if_not_recovered(
    coins_repository: CoinsRepository,
    simulations_repository: SimulationsRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_exchanges,
    with_standard_coin_evaluations,
):
    coin_amount = 2.0
    sim = Simulation(
        user_id=_USER_ID,
        initial_fiat_amount=10_000_000,
        updated_fiat_amount=10_000_000,
        amount_per_coins={COIN_BULLISH_1: coin_amount},
        operational_fee_percentage=1,
        panic_mode=True,
    )

    await control_portfolio(coins_repository, simulations_repository, sim_config.get(), sim)

    assert sim.panic_mode
    assert sim.amount_per_coins.get(COIN_BULLISH_1, 0.0) == pytest.approx(0.0)
    assert sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0.0) > 0


@pytest.mark.asyncio
async def test_control_portfolio_stays_in_panic_and_reduces_profit_tracking(
    coins_repository: CoinsRepository,
    simulations_repository: SimulationsRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_exchanges,
    with_standard_coin_evaluations,
):
    coin_amount = 2.0
    profit_before = 10_000_000
    sim = Simulation(
        user_id=_USER_ID,
        initial_fiat_amount=10_000_000,
        updated_fiat_amount=1_000,
        amount_per_coins={COIN_BULLISH_1: coin_amount},
        operational_fee_percentage=1,
        panic_mode=True,
        profit_achieved_since_last_rotation=profit_before,
    )

    await control_portfolio(coins_repository, simulations_repository, sim_config.get(), sim)

    assert sim.panic_mode
    assert sim.amount_per_coins.get(COIN_BULLISH_1, 0.0) == pytest.approx(0.0)
    assert sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0.0) > 0
    assert sim.profit_achieved_since_last_rotation < profit_before


@pytest.mark.asyncio
async def test_control_portfolio_protects_small_gains_and_holds_in_fiat(
    coins_repository: CoinsRepository,
    simulations_repository: SimulationsRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_exchanges,
    with_all_coins_evaluated_downtrend,
):
    coin_amount = 300
    sim = Simulation(
        user_id=_USER_ID,
        initial_fiat_amount=1_000,
        updated_fiat_amount=1_100,
        profit_achieved_since_last_rotation=2_000,
        amount_per_coins={COIN_BEARISH_1: coin_amount},
        operational_fee_percentage=1,
    )

    await control_portfolio(coins_repository, simulations_repository, sim_config.get(), sim)

    assert not sim.panic_mode
    assert sim.amount_per_coins.get(COIN_BEARISH_1, 0.0) == pytest.approx(0.0)
    expected_fiat = _fiat_after_fee(coin_amount, _COIN_BEARISH_1_EXCHANGE, 1)
    assert sim.amount_per_coins.get(RESERVE_DEFAULT_FIAT_CURRENCY, 0.0) == pytest.approx(expected_fiat)


@pytest.mark.asyncio
async def test_control_portfolio_does_nothing_if_trader_pro(
    coins_repository: CoinsRepository,
    simulations_repository: SimulationsRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_exchanges,
    with_standard_coin_evaluations,
):
    coin_amount = 10.0
    sim = Simulation(
        user_id=_USER_ID,
        initial_fiat_amount=1_000,
        updated_fiat_amount=1_000,
        amount_per_coins={COIN_BULLISH_1: coin_amount},
        operational_fee_percentage=1,
        trader_pro=True,
    )

    await control_portfolio(coins_repository, simulations_repository, sim_config.get(), sim)

    assert sim.amount_per_coins.get(COIN_BULLISH_1, 0.0) == pytest.approx(coin_amount)
    assert not sim.panic_mode

@pytest.mark.asyncio
async def test_control_portfolio_updates_profit_tracking_when_balance_increases(
    coins_repository: CoinsRepository,
    simulations_repository: SimulationsRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_exchanges,
    with_standard_coin_evaluations,
):
    coin_amount = 2.0
    previous_profit = 100.0
    sim = Simulation(
        user_id=_USER_ID,
        initial_fiat_amount=1000,
        updated_fiat_amount=1000,
        amount_per_coins={COIN_BULLISH_1: coin_amount},
        operational_fee_percentage=1,
        profit_achieved_since_last_rotation=previous_profit,
    )

    await control_portfolio(coins_repository, simulations_repository, sim_config.get(), sim)

    assert not sim.panic_mode
    assert sim.amount_per_coins.get(COIN_BULLISH_1, 0.0) == pytest.approx(coin_amount)
    assert sim.profit_achieved_since_last_rotation > previous_profit


@pytest.mark.asyncio
async def test_control_portfolio_does_not_update_profit_tracking_when_below_max(
    coins_repository: CoinsRepository,
    simulations_repository: SimulationsRepository,
    sim_config: SimulationTestConfig,
    frozen_timesamp,
    with_exchanges,
    with_standard_coin_evaluations,
):
    coin_amount = 0.5

    # With 0.5 * 1000 = 500, the current balance is 1500, profit = 500
    # Set profit_achieved very high so the current profit does not exceed it
    previous_max_profit = 600.0
    sim = Simulation(
        user_id=_USER_ID,
        initial_fiat_amount=100,
        updated_fiat_amount=100,
        amount_per_coins={COIN_BULLISH_1: coin_amount},
        operational_fee_percentage=1,
        profit_achieved_since_last_rotation=previous_max_profit,
    )

    await control_portfolio(coins_repository, simulations_repository, sim_config.get(), sim)

    assert not sim.panic_mode
    assert sim.amount_per_coins.get(COIN_BULLISH_1, 0.0) == pytest.approx(coin_amount)
    assert sim.profit_achieved_since_last_rotation == pytest.approx(previous_max_profit)