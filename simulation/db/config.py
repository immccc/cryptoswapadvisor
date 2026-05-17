from abc import ABCMeta, abstractmethod

from simulation.model import SimulationParams


class SimulationConfig(metaclass=ABCMeta):
    @abstractmethod
    def get(self) -> SimulationParams:
        raise NotImplementedError