import datetime
from typing import Optional
from pydantic import BaseModel


INITIAL_SIMULATION_FIAT_KEY = "initial_fiat_amount"
UPDATED_SIMULATION_FIAT_KEY = "updated_fiat_amount"
INTERVAL_SIMULATION_CONTROL_SECONDS = 60

class Simulation(BaseModel):
    user_id: str
    initial_fiat_amount: float
    updated_fiat_amount: float
    webhook_endpoint: Optional[str] = None
    amount_per_coins: dict[str, float] = {}
    ratio_per_coins: dict[str, float] = {}
    last_rotated_at: int = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    timespan_in_hours: int = 12
    operational_fee_percentage: float = 0.0
    trader_pro: bool = False
    panic_mode: bool = False
    profit_achieved_since_last_rotation: float = 0.0

    def model_dump_only_information_fields(self) -> dict:
        return self.model_dump(exclude={
            "webhook_endpoint", "timespan_in_hours", "operational_fee_percentage", "trader_pro", "profit_achieved_since_last_rotation"
        })


_DEFAULT_PANIC_MODE_THRESHOLD = 0.9
_DEFAULT_MIN_CONFIDENCE_TO_RECOVER = 0.015
_DEFAULT_RATIO_POSITIVE_CONFIDENCES_TO_RECOVER = 0.6
_DEFAULT_RATIO_DELTAS_SMALL_WINDOWS = 0.65
_DEFAULT_MIN_DELTA_FROM_SMALL_WINDOWS_CONFIDENCE_DIFF = 0.002
_DEFAULT_RATIO_RECOVERY_SIGNS = 0.55
_DEFAULT_RATIO_PROFIT_PROTECTION = 0.5
_DEFAULT_SMALL_PROFIT_PROTECTION_THRESHOLD = 0.01


class SimulationParams(BaseModel):
    panic_mode_threshold: float = _DEFAULT_PANIC_MODE_THRESHOLD
    min_confidence_to_recover: float = _DEFAULT_MIN_CONFIDENCE_TO_RECOVER
    ratio_positive_confidences_to_recover: float = (
        _DEFAULT_RATIO_POSITIVE_CONFIDENCES_TO_RECOVER
    )
    ratio_deltas_windows: float = _DEFAULT_RATIO_DELTAS_SMALL_WINDOWS
    min_delta_from_windows_diff: float = (
        _DEFAULT_MIN_DELTA_FROM_SMALL_WINDOWS_CONFIDENCE_DIFF
    )
    ratio_recovery_signs: float = _DEFAULT_RATIO_RECOVERY_SIGNS
    ratio_profit_protection: float = _DEFAULT_RATIO_PROFIT_PROTECTION
    small_profit_protection_threshold: float = (
        _DEFAULT_SMALL_PROFIT_PROTECTION_THRESHOLD
    )
