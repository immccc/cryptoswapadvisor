from datetime import datetime, timezone
import pytest

from conftest import COIN_BEARISH_1, COIN_BULLISH_1, USER_ID
from coins.db.test_db import CoinsTestRepository
from coins.model import RESERVE_DEFAULT_FIAT_CURRENCY
from simulation.actions import get_fiat_balance
from simulation.model import Simulation

_COIN_BEARISH_1_AMOUNT = 23.0
_COIN_BULLISH_1_AMOUNT = 34.0
_FIAT_AMOUNT = 202


@pytest.mark.asyncio
async def test_get_fiat_balance(
    coins_repository: CoinsTestRepository,
    frozen_timesamp,
    with_standard_coin_evaluations,
    with_exchanges,
):
    user = Simulation(
        user_id=USER_ID,
        initial_fiat_amount=100.0,
        updated_fiat_amount=100.0,
        amount_per_coins={
            RESERVE_DEFAULT_FIAT_CURRENCY: _FIAT_AMOUNT,
            COIN_BEARISH_1: _COIN_BEARISH_1_AMOUNT,
            COIN_BULLISH_1: _COIN_BULLISH_1_AMOUNT,
        },
    )

    bearish_1_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_BEARISH_1,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[0]

    bullish_1_exchange = (
        await coins_repository.get_exchanges_from_range(
            COIN_BULLISH_1,
            int(datetime.now(timezone.utc).timestamp()) - 120,
            int(datetime.now(timezone.utc).timestamp()),
        )
    )[0]

    expected_balance = _FIAT_AMOUNT
    expected_balance += _COIN_BEARISH_1_AMOUNT * bearish_1_exchange
    expected_balance += _COIN_BULLISH_1_AMOUNT * bullish_1_exchange

    actual_fiat_balance = await get_fiat_balance(
        coins_repository, frozen_timesamp, user
    )

    assert expected_balance == pytest.approx(actual_fiat_balance)
