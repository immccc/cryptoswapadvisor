import pytest
from coins.model import Evaluation
from coins.price_tracker import PriceTracker
from coins.db.test_db import CoinsTestRepository
from coins.db.test_db import add_values_for_coin

_TEST_COIN = "TST"


@pytest.fixture
def price_tracker(coins_repository: CoinsTestRepository) -> PriceTracker:
    return PriceTracker(
        _TEST_COIN,
        coins_repository,
    )


@pytest.mark.asyncio
async def test_prices_bullish(
    coins_repository: CoinsTestRepository, price_tracker: PriceTracker
):
    await add_values_for_coin(
        coins_repository, _TEST_COIN, 0.1, 1, 2, 3, 4, 6, 8, 10, 12, 15
    )

    result = await price_tracker.evaluate_from_db()
    assert result[0] == Evaluation.BULLISH
    assert result[1] > 0.0


@pytest.mark.asyncio
async def test_prices_bearish(
    coins_repository: CoinsTestRepository, price_tracker: PriceTracker
):
    await add_values_for_coin(
        coins_repository,
        _TEST_COIN,
        60,
        30,
        26,
        22,
        20,
        18,
        15,
        12,
        10,
        8,
        6,
        4,
        3,
        2,
        1,
        0.1,
    )

    result = await price_tracker.evaluate_from_db()
    assert result[0] == Evaluation.BEARISH
    assert result[1] < 0


@pytest.mark.asyncio
async def test_prices_neutral(
    coins_repository: CoinsTestRepository, price_tracker: PriceTracker
):
    await add_values_for_coin(
        coins_repository, _TEST_COIN, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15
    )

    result = await price_tracker.evaluate_from_db()
    assert result[0] == Evaluation.NEUTRAL


@pytest.mark.asyncio
async def test_prices_big_fluctuations_neutral(
    coins_repository: CoinsTestRepository, price_tracker: PriceTracker
):
    await add_values_for_coin(
        coins_repository,
        _TEST_COIN,
        1000,
        500,
        1000,
        500,
        1000,
        500,
        1000,
        500,
        1000,
        500,
        1000,
        500,
        1710.87,
        500,
        1000,
        500,
        1000,
        500,
        1000,
        500,
    )

    result = await price_tracker.evaluate_from_db(from_timestamp=20, timespan=20)
    assert result[0] == Evaluation.NEUTRAL
    assert abs(result[1]) > 0


@pytest.mark.asyncio
async def test_prices_big_fluctuations_bullish(
    coins_repository: CoinsTestRepository, price_tracker: PriceTracker
):
    await add_values_for_coin(
        coins_repository,
        _TEST_COIN,
        500,
        1,
        1000,
        200,
        2000,
        0.5,
        3000,
        400,
        6000,
        200,
        7000,
        2,
        6000,
        3,
        8000,
        200,
        8001,
        100,
        9000,
        3,
    )

    result = await price_tracker.evaluate_from_db(from_timestamp=20, timespan=20)
    assert result[0] == Evaluation.BULLISH
    assert result[1] > 0


@pytest.mark.asyncio
async def test_prices_big_fluctuations_bearish(
    coins_repository: CoinsTestRepository, price_tracker: PriceTracker
):
    await add_values_for_coin(
        coins_repository,
        _TEST_COIN,
        3,
        9000,
        100,
        8001,
        200,
        8000,
        3,
        6000,
        2,
        7000,
        200,
        6000,
        400,
        3000,
        0.5,
        2000,
        200,
        1000,
        1,
        500,
    )

    result = await price_tracker.evaluate_from_db(from_timestamp=20, timespan=20)
    assert result[0] == Evaluation.BEARISH
    assert result[1] < 0
