from typing import Iterable

class ComputedExchange:
    coin_name: str
    values_per_time: dict[int, float] = {}
    max_value: float
    simulation_duration: int

    def __init__(
        self,
        coin_name: str,
        values: Iterable[float] = [],
        simulation_duration: int = 0
    ):
        self.coin_name = coin_name
        self.simulation_duration = simulation_duration

        if values:
            self.values_per_time = {
                i * 60 * 5: v for i, v in enumerate(values)
            }
            return
