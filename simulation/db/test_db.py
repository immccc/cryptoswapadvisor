from typing import Generator, Optional

from simulation.db.config import SimulationConfig
from simulation.db.repository import SimulationsRepository
from simulation.model import UPDATED_SIMULATION_FIAT_KEY, Simulation, SimulationParams

class SimulationsTestRepository(SimulationsRepository):
    def __init__(self):
        self.simulations: dict[str, Simulation] = {}
        self.simulations_history: dict[str, dict[int, dict[str, float]]] = {}

    def remove_simulation(self, id: str):
        self.simulations.pop(id)

    def get_simulation(self, id: str) -> Optional[Simulation]:
        return self.simulations.get(id)

    def save_simulation(self, sim: Simulation, at_timestamp: Optional[int] = None):
        self.simulations[sim.user_id] = sim

        if not self.simulations_history.get(sim.user_id):
            self.simulations_history[sim.user_id] = {}

        next_entry_idx = max(self.simulations_history[sim.user_id].keys(), default=0)
        self.simulations_history[sim.user_id][next_entry_idx + 1] = sim.ratio_per_coins | {
            UPDATED_SIMULATION_FIAT_KEY: sim.updated_fiat_amount
        }

    def get_simulations_outdated(self, timestamp: int) -> Generator[Simulation, None, None]:
        selected = [sim for _, sim in self.simulations.items() if sim.last_rotated_at + sim.timespan_in_hours * 3600 <= timestamp]

        for sim in selected:
            yield sim


    def get_history(self, id: str) -> dict[int, dict[str, float]]:
        return self.simulations_history.get(id, {})

class SimulationTestConfig(SimulationConfig):
    def get(self) -> SimulationParams:
        return SimulationParams()

