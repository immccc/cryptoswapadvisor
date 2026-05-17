import math
from typing import Callable, Optional

import numpy as np
from coins.model import Evaluation, EvaluationWithRank
from coins.db.repository import CoinsRepository


from numba import njit

_THRESHOLD_PEAK_VALUE = 2
_THRESHOLD_SLOPE = 0.0005
_DEFAULT_MIN_AMOUNT_OF_PRICES = 10
_SMA_WINDOW_SIZE = 3


class PriceTracker:
    coin: str
    prices: list[float]
    timestamps: list[str]
    min_amount_of_prices: int = _DEFAULT_MIN_AMOUNT_OF_PRICES
    _repository: Optional[CoinsRepository]

    def __init__(
        self, coin: str, repository: Optional[CoinsRepository] = None, min_amount_of_prices: int = 5
    ):
        self.coin = coin
        self.prices = []
        self.timestamps = []

        self._repository = repository
        self.min_amount_of_prices = min_amount_of_prices

    async def evaluate_from_db(
        self,
        from_timestamp: int = _DEFAULT_MIN_AMOUNT_OF_PRICES,  # TODO This is misleading. Force timestamp to be provided
        timespan: int = _DEFAULT_MIN_AMOUNT_OF_PRICES,
    ) -> EvaluationWithRank:
        assert self._repository

        start_timestamp = from_timestamp - timespan
        prices = await self._repository.get_exchanges_from_range(
            self.coin,
            start_timestamp,
            from_timestamp,
        )

        return self.evaluate_from_prices(prices)


    def evaluate_from_prices(self, prices: list[float]) -> tuple[Evaluation, float]:
        if len(prices) < self.min_amount_of_prices:
            return (Evaluation.NEUTRAL, 0.0)

        slope = float(PriceTracker._get_slope(np.array(prices)))

        if slope < -_THRESHOLD_SLOPE:
            return (Evaluation.BEARISH, slope)

        if slope > _THRESHOLD_SLOPE:
            return (Evaluation.BULLISH, slope)

        return (Evaluation.NEUTRAL, slope)


    @staticmethod
    @njit
    def _get_slope(
        prices: np.array
    ) -> np.float64:
        smas = _soften_by_sma(prices)
        emas = _get_emas(smas)

        return _theils(emas)


    @staticmethod
    @njit
    def _is_peak(slopes: np.array) -> bool:
        return _is_trend_changing(_is_trend_upwards, slopes)

    @staticmethod
    @njit
    def _is_valley(slopes: np.array) -> bool:
        return _is_trend_changing(_is_trend_downwards, slopes)

@njit
def _is_trend_changing(
    predicate: Callable[[float], bool],
    slopes: np.array,
) -> bool:
    matching_slopes = 0

    middle = math.floor(slopes.size / 2)

    for i in range(middle):
        matching_slopes += 1 if predicate(slopes[i]) else 0

    diff_matching_and_not = abs(matching_slopes - middle)
    if diff_matching_and_not > _THRESHOLD_PEAK_VALUE:
        return False

    matching_slopes = 0
    for i in range(middle, slopes.size):
        matching_slopes += 1 if not predicate(slopes[i]) else 0

    diff_matching_and_not = abs(matching_slopes - middle)
    if diff_matching_and_not >= _THRESHOLD_PEAK_VALUE:
        return False

    return True


@njit
def _get_emas(prices: np.array) -> np.array:
    smoothing = 2 / (prices.size + 1)
    emas = np.zeros(prices.size, dtype=np.float64)
    emas[0] = prices[0]
    for i in range(1, prices.size):
        emas[i] = (prices[i] - emas[i - 1]) * smoothing + emas[i - 1]

    return emas

@njit
def _is_trend_upwards(evaluation_result: float):
    return evaluation_result >= 0

@njit
def _is_trend_downwards(evaluation_result: float):
    return evaluation_result < 0

@njit
def _soften_by_sma(
    prices_arr: np.array,
    window_size: int = _SMA_WINDOW_SIZE,
) -> np.array:
    
    len_prices = prices_arr.size

    smas = np.zeros(len_prices - window_size + 1, dtype=np.float64)
    for i in range(smas.size):
        smas[i] = float(np.mean(prices_arr[i : i + window_size]))

    return smas

@njit
def _theils(points: np.array):
    num_points = points.size

    if num_points < 2:
        return np.float64(0.0)

    if num_points == 2:
        return points[1] - points[0]
    
    num_pairs = (num_points * (num_points - 1)) // 2
    slopes = np.zeros(num_pairs, dtype=np.float64)
    
    k = 0
    for point_1_idx in range(num_points - 1):
        point_1 = points[point_1_idx]
        for point_2_idx in range(point_1_idx + 1, num_points):
            slopes[k] = (points[point_2_idx] - point_1) / (point_2_idx - point_1_idx)
            k += 1

    return np.float64(np.nan_to_num(np.median(slopes), nan=0.0))
