from datetime import datetime, timedelta, timezone
import os
from unittest.mock import AsyncMock
import pytest
from pytest_mock import MockerFixture

from coins import actions
from coins.db.repository import CoinsRepository
from coins.model import Evaluation, EvaluationWithRank
from conftest import (
    COIN_BEARISH_1,
    COIN_BEARISH_2,
    COIN_BULLISH_1,
    COIN_BULLISH_2,
    COIN_NEUTRAL_1,
    COIN_NEUTRAL_2,
    COIN_PEAK,
    COIN_VALLEY,
)

AVERAGE_EVALUATION_PER_COIN = {
    COIN_BULLISH_1: (Evaluation.BULLISH, 0.9),
    COIN_BULLISH_2: (Evaluation.BULLISH, 0.5),
    COIN_BEARISH_1: (Evaluation.BEARISH, -0.7),
    COIN_BEARISH_2: (Evaluation.BEARISH, -0.5),
    COIN_NEUTRAL_1: (Evaluation.NEUTRAL, 0.3),
    COIN_NEUTRAL_2: (Evaluation.NEUTRAL, 0.2),
    COIN_PEAK: (Evaluation.PEAK, 0),
    COIN_VALLEY: (Evaluation.VALLEY, 0),
}


class _NoiseDeterministicGenerator:
    def __init__(self):
        self._index = 0
        self._pattern = [0, 1, 0, -1]

    def next(self) -> int:
        val = self._pattern[self._index % len(self._pattern)]
        self._index += 1
        return val


@pytest.fixture
def noise_generator():
    return _NoiseDeterministicGenerator()


@pytest.fixture
def with_coin_static_evaluations(mocker: MockerFixture):
    mocker.patch(
        "coins.actions.get_evaluations",
        new=AsyncMock(return_value=AVERAGE_EVALUATION_PER_COIN),
    )


@pytest.fixture
def with_coin_noisy_evaluations(
    mocker: MockerFixture, noise_generator: _NoiseDeterministicGenerator
):
    noise_per_coin = {
        COIN_BULLISH_1: 5,
        COIN_BULLISH_2: 1,
        COIN_BEARISH_1: 10,
        COIN_BEARISH_2: 1,
        COIN_NEUTRAL_1: 0,
        COIN_NEUTRAL_2: 0,
        COIN_PEAK: 0,
        COIN_VALLEY: 0,
    }

    async def fake_get_evaluation_with_noise(
        _: CoinsRepository,
        __: int,
        ___: int,
        *coins: str,
    ) -> dict[str, EvaluationWithRank]:
        noise_factor = noise_generator.next()
        return {
            coin: (
                AVERAGE_EVALUATION_PER_COIN[coin][0],
                AVERAGE_EVALUATION_PER_COIN[coin][1]
                + noise_per_coin[coin] * noise_factor,
            )
            for coin in coins
        }

    mocker.patch(
        "coins.actions.get_evaluations",
        new=AsyncMock(side_effect=fake_get_evaluation_with_noise),
    )


@pytest.fixture
def without_confidence_parallel_execution():
    os.environ["CONFIDENCE_CALCULATION_IN_PARALLEL"] = ""


@pytest.mark.asyncio
async def test_update_coin_confidences_fills_periods(
    coins_repository: CoinsRepository,
    frozen_timesamp,
    with_exchanges,
    with_coin_static_evaluations,
    without_confidence_parallel_execution,
):
    await _perform(coins_repository)

    coin = (await coins_repository.get_coins(COIN_BULLISH_1))[0]

    assert len(coin.confidences_per_period) == 3  # 12, 24, 48
    for period in coin.confidences_per_period.keys():
        assert coin.confidences_per_period[period] is not None


@pytest.mark.asyncio
async def test_update_coin_confidences_bullish_positive(
    coins_repository,
    frozen_timesamp,
    with_exchanges,
    with_coin_static_evaluations,
    without_confidence_parallel_execution,
):
    await _perform(coins_repository)

    coin = (await coins_repository.get_coins(COIN_BULLISH_1))[0]

    for period in coin.confidences_per_period.keys():
        assert coin.confidences_per_period[period] > 0


@pytest.mark.asyncio
async def test_update_coin_confidences_bearish_negative(
    coins_repository,
    frozen_timesamp,
    with_exchanges,
    with_coin_static_evaluations,
    without_confidence_parallel_execution,
):
    await _perform(coins_repository)

    coin = (await coins_repository.get_coins(COIN_BEARISH_2))[0]

    for period in coin.confidences_per_period.keys():
        assert coin.confidences_per_period[period] < 0


@pytest.mark.asyncio
async def test_update_coin_confidences_noisy_are_penalized(
    coins_repository,
    frozen_timesamp,
    with_exchanges,
    with_coin_noisy_evaluations,
    without_confidence_parallel_execution,
):
    await _perform(coins_repository)

    coin_bullish_noisy = (await coins_repository.get_coins(COIN_BULLISH_1))[0]
    coin_bullish_less_noisy = (await coins_repository.get_coins(COIN_BULLISH_2))[0]

    for period in coin_bullish_noisy.confidences_per_period.keys():
        assert (
            coin_bullish_less_noisy.confidences_per_period[period]
            > coin_bullish_noisy.confidences_per_period[period]
        )


async def _perform(coins_repository: CoinsRepository):
    await actions.update_all_coins(
        coins_repository,
        check_from=int((datetime.now(timezone.utc) - timedelta(weeks=1)).timestamp()),
        check_to=int(datetime.now(timezone.utc).timestamp()),
    )
