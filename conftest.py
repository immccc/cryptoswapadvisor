from simulation.db.test_db import SimulationTestConfig, SimulationsTestRepository
from users.db.test_db import UsersTestRepository

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from freezegun import freeze_time
import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from coins.db.test_db import CoinsTestRepository
from coins.model import Evaluation

FIXED_TIMESTAMP = 10


# TODO Deprecate this one
def yield_fixed_times(mock):
    mock.now.return_value = datetime(2025, 12, 12, 0, 0, 0)
    mock.timestamp.return_value = 10
    mock.fromtimestamp.return_value = 10
    yield mock


USER_ID = "1"

COIN_BULLISH_1 = "CBU1"
COIN_BULLISH_2 = "CBU2"
COIN_NEUTRAL_1 = "CNE1"
COIN_NEUTRAL_2 = "CNE2"
COIN_BEARISH_1 = "CBE1"
COIN_BEARISH_2 = "CBE2"
COIN_VALLEY = "CVA"
COIN_PEAK = "CPE"

FROZEN_DATE = "2030-12-12"


@pytest.fixture
def frozen_timesamp():
    with freeze_time(FROZEN_DATE):
        yield int(datetime.now(timezone.utc).timestamp())


@pytest.fixture
def coins_repository() -> CoinsTestRepository:
    return CoinsTestRepository()


@pytest.fixture
def users_repository() -> UsersTestRepository:
    return UsersTestRepository()


@pytest.fixture
def simulations_repository() -> SimulationsTestRepository:
    return SimulationsTestRepository()

@pytest.fixture
def sim_config() -> SimulationTestConfig:
    return SimulationTestConfig()

@pytest.fixture
def with_standard_coin_evaluations(mocker: MockerFixture):
    coins = {
        COIN_BULLISH_1: (Evaluation.BULLISH, 0.9),
        COIN_BULLISH_2: (Evaluation.BULLISH, 0.5),
        COIN_BEARISH_1: (Evaluation.BEARISH, 0.7),
        COIN_BEARISH_2: (Evaluation.BEARISH, 0.5),
        COIN_NEUTRAL_1: (Evaluation.NEUTRAL, 0.3),
        COIN_PEAK: (Evaluation.PEAK, 0),
        COIN_VALLEY: (Evaluation.VALLEY, 0),
    }

    mocker.patch(
        "coins.actions.get_evaluations", new=AsyncMock(return_value=coins)
    )


@pytest.fixture
def with_all_coins_evaluated_downtrend(mocker: MockerFixture):
    coins = {
        COIN_BULLISH_1: (Evaluation.BEARISH, 0.9),
        COIN_BULLISH_2: (Evaluation.NEUTRAL, 0.5),
        COIN_BEARISH_1: (Evaluation.BEARISH, 0.7),
        COIN_BEARISH_2: (Evaluation.BEARISH, 0.6),
        COIN_NEUTRAL_1: (Evaluation.NEUTRAL, 0.3),
        COIN_PEAK: (Evaluation.BEARISH, 0),
        COIN_VALLEY: (Evaluation.NEUTRAL, 0),
    }
    mocker.patch(
        "coins.actions.get_evaluations", new=AsyncMock(return_value=coins)
    )


@pytest_asyncio.fixture
async def with_exchanges(coins_repository: CoinsTestRepository, frozen_timesamp):
    await coins_repository.save_exchange(COIN_BULLISH_1, frozen_timesamp, 1000.0)
    await coins_repository.save_exchange(COIN_BULLISH_2, frozen_timesamp, 20.0)
    await coins_repository.save_exchange(COIN_NEUTRAL_1, frozen_timesamp, 30.0)
    await coins_repository.save_exchange(COIN_NEUTRAL_2, frozen_timesamp, 10.0)
    await coins_repository.save_exchange(COIN_BEARISH_1, frozen_timesamp, 5.0)
    await coins_repository.save_exchange(COIN_BEARISH_2, frozen_timesamp, 20)
    await coins_repository.save_exchange(COIN_VALLEY, frozen_timesamp, 10)
    await coins_repository.save_exchange(COIN_PEAK, frozen_timesamp, 50)
