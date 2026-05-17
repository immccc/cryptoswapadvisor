from abc import ABCMeta, abstractmethod
from typing import Generator, Optional

from simulation.model import Simulation


class SimulationsRepository(metaclass=ABCMeta):
    @abstractmethod
    def remove_simulation(self, id: str):
        raise NotImplementedError

    @abstractmethod
    def get_simulation(self, id: str) -> Optional[Simulation]:
        raise NotImplementedError

    @abstractmethod
    def get_simulations_outdated(self, timestamp: int) -> Generator[Simulation, None, None]:
        raise NotImplementedError


    @abstractmethod
    def save_simulation(self, sim: Simulation, at_timestamp: Optional[int] = None):
        raise NotImplementedError

    @abstractmethod
    def get_history(self, id: str) -> dict[int, dict[str, float]]:
        raise NotImplementedError
