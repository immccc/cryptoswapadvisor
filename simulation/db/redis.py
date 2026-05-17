from datetime import datetime, timezone
import json
import os
from typing import Generator, Optional
from redis import Redis

from simulation.db.config import SimulationConfig
from simulation.db.repository import SimulationsRepository
from simulation.model import (
    _DEFAULT_MIN_DELTA_FROM_SMALL_WINDOWS_CONFIDENCE_DIFF,
    _DEFAULT_PANIC_MODE_THRESHOLD,
    _DEFAULT_RATIO_DELTAS_SMALL_WINDOWS,
    _DEFAULT_RATIO_POSITIVE_CONFIDENCES_TO_RECOVER,
    _DEFAULT_MIN_CONFIDENCE_TO_RECOVER,
    _DEFAULT_RATIO_RECOVERY_SIGNS,
    INITIAL_SIMULATION_FIAT_KEY,
    UPDATED_SIMULATION_FIAT_KEY,
    Simulation,
    SimulationParams,
)

_SIMULATIONS_DB = 2
_SIMULATIONS_HISTORY_DB = 3
_SIMULATIONS_PARAMS_DB = 6

_TIMESPAN_HRS_KEY = "timespan_hr"
_LAST_ROTATION_KEY = "created_at"
_OPERATIONAL_PERCENTAGE_FEE_KEY = "fee"
_TRADER_PRO_KEY = "pro"
_PANIC_MODE_KEY = "panic"
_PROFIT_ACHIEVED = "last_recovered"
_RATIO_PER_COINS_KEY = "ratio_per_coins"


class SimulationsRedisRepository(SimulationsRepository):
    _redis_client_sims: Redis
    _redis_client_sims_history: Redis

    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))

        self._redis_client_sims = Redis(
            redis_host, redis_port, db=_SIMULATIONS_DB, decode_responses=True
        )
        self._redis_client_sims_history = Redis(
            redis_host, redis_port, db=_SIMULATIONS_HISTORY_DB, decode_responses=True
        )

    def remove_simulation(self, id: str):
        self._redis_client_sims.delete(str(id))
        self._redis_client_sims_history.delete(str(id))

    def get_simulation(self, id: str) -> Optional[Simulation]:
        sim_hset: dict[str, str] = self._redis_client_sims.hgetall(str(id))
        if not sim_hset:
            return None

        initial_fiat = float(sim_hset.pop(INITIAL_SIMULATION_FIAT_KEY, "0"))
        updated_fiat = float(sim_hset.pop(UPDATED_SIMULATION_FIAT_KEY, "0"))
        timespan = float(sim_hset.pop(_TIMESPAN_HRS_KEY, "12"))
        last_rotated_at = int(sim_hset.pop(_LAST_ROTATION_KEY, "0"))
        operational_percentage_fee = float(
            sim_hset.pop(_OPERATIONAL_PERCENTAGE_FEE_KEY, "0")
        )
        panic_mode = bool(sim_hset.pop(_PANIC_MODE_KEY, ""))
        trader_pro = bool(sim_hset.pop(_TRADER_PRO_KEY, ""))
        profit_achieved = float(sim_hset.pop(_PROFIT_ACHIEVED, "0"))
        ratio_per_coins = json.loads(sim_hset.pop(_RATIO_PER_COINS_KEY, "{}"))

        simulation = Simulation(
            user_id=id,
            initial_fiat_amount=initial_fiat,
            updated_fiat_amount=updated_fiat,
            timespan_in_hours=timespan,
            last_rotated_at=last_rotated_at,
            operational_fee_percentage=operational_percentage_fee,
            trader_pro=trader_pro,
            panic_mode=panic_mode,
            profit_achieved_since_last_rotation=profit_achieved,
            amount_per_coins={coin: float(amount) for coin, amount in sim_hset.items()},
            ratio_per_coins=ratio_per_coins,
        )
        return simulation

    def get_simulations_outdated(self, timestamp: int) -> Generator[Simulation, None, None]:
        raise NotImplementedError

    def save_simulation(self, sim: Simulation, at_timestamp: Optional[int] = None):
        if not at_timestamp:
            at_timestamp = int(datetime.now(timezone.utc).timestamp())

        id_as_str = str(sim.user_id)

        self._redis_client_sims.delete(id_as_str)
        self._redis_client_sims.hset(
            id_as_str,
            mapping={
                INITIAL_SIMULATION_FIAT_KEY: str(sim.initial_fiat_amount),
                UPDATED_SIMULATION_FIAT_KEY: str(sim.updated_fiat_amount),
                _TIMESPAN_HRS_KEY: str(sim.timespan_in_hours),
                _LAST_ROTATION_KEY: str(sim.last_rotated_at),
                _OPERATIONAL_PERCENTAGE_FEE_KEY: str(sim.operational_fee_percentage),
                _PANIC_MODE_KEY: "1" if sim.panic_mode else "",
                _TRADER_PRO_KEY: "1" if sim.trader_pro else "",
                _PROFIT_ACHIEVED: str(sim.profit_achieved_since_last_rotation),
                _RATIO_PER_COINS_KEY: json.dumps(sim.ratio_per_coins),
            },
        )

        self._redis_client_sims.hset(
            id_as_str,
            mapping={
                coin: str(amount) for coin, amount in sim.amount_per_coins.items()
            },
        )

        self._redis_client_sims_history.zadd(
            sim.user_id,
            {
                json.dumps(
                    {
                        UPDATED_SIMULATION_FIAT_KEY: sim.updated_fiat_amount,
                    }
                    | sim.ratio_per_coins
                ): at_timestamp
            },
        )

    def get_history(self, id: str) -> dict[int, dict[str, float]]:
        result = self._redis_client_sims_history.zrangebyscore(
            id, min="-inf", max="+inf", withscores=True
        )
        return {int(timestamp): json.loads(entry) for entry, timestamp in result}

class SimulationRedisConfig(SimulationConfig):
    _redis_client_sims_params: Redis
    
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))

        self._redis_client_sims_params = Redis(
            redis_host, redis_port, db=_SIMULATIONS_PARAMS_DB, decode_responses=True
        )

    def get(self) -> SimulationParams:
        return SimulationParams(
            panic_mode_threshold=float(
                self._redis_client_sims_params.get("panic_mode_threshold")
                or _DEFAULT_PANIC_MODE_THRESHOLD
            ),
            min_confidence_to_recover=float(
                self._redis_client_sims_params.get("min_confidence_to_recover")
                or _DEFAULT_MIN_CONFIDENCE_TO_RECOVER
            ),
            ratio_positive_confidences_to_recover=float(
                self._redis_client_sims_params.get(
                    "ratio_positive_confidences_to_recover"
                )
                or _DEFAULT_RATIO_POSITIVE_CONFIDENCES_TO_RECOVER
            ),
            ratio_deltas_windows=float(
                self._redis_client_sims_params.get("ratio_deltas_windows")
                or _DEFAULT_RATIO_DELTAS_SMALL_WINDOWS
            ),
            min_delta_from_windows_diff=float(
                self._redis_client_sims_params.get("min_delta_from_windows_diff")
                or _DEFAULT_MIN_DELTA_FROM_SMALL_WINDOWS_CONFIDENCE_DIFF
            ),
            ratio_recovery_signs=float(
                self._redis_client_sims_params.get("ratio_recovery_signs")
                or _DEFAULT_RATIO_RECOVERY_SIGNS
            ),
        )