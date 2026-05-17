from enum import StrEnum

from pydantic import BaseModel

INTERVAL_COLLECTION_SECONDS = 300
INTERVAL_COMPACTION_SECONDS = 86400


RESERVE_DEFAULT_FIAT_CURRENCY = "USD"
DEFAULT_TIMESPAN_FOR_EVALUATION_IN_SECS = 12 * 60 * 60

INTERVAL_CALCULATE_CONFIDENCE_SECONDS = 60


class Evaluation(StrEnum):
    BEARISH = "bearish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    PEAK = "peak"
    VALLEY = "valley"


EvaluationWithRank = tuple[Evaluation, float]


class Coin(BaseModel):
    name: str
    confidences_per_period: dict[int, float] = {}

    def get_confidence_for_closest_timespan(self, timespan_in_hours) -> float:
        return self.confidences_per_period.get(
            self._get_closest_registered_period(timespan_in_hours), 0.0
        )

    def _get_closest_registered_period(self, timespan_in_hours: int) -> int:
        if not self.confidences_per_period:
            return 0

        return min(
            self.confidences_per_period.keys(), key=lambda k: abs(k - timespan_in_hours)
        )
