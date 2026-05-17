from typing import Optional

from sqlmodel import Field, SQLModel


class Simulation(SQLModel, table=True):
    __tablename__ = "simulations"
    user_id: str = Field(primary_key=True)
    initial_fiat_amount: float = Field(nullable=False)
    updated_fiat_amount: float = Field(nullable=False)
    webhook_endpoint: Optional[str] = Field(nullable=True)
    last_rotated_at: int = Field(nullable=False)
    timespan_in_hours: int = Field(nullable=False, default=12)
    operational_fee_percentage: float = Field(nullable=False, default=0.0)
    trader_pro: bool = Field(nullable=False, default=False)
    panic_mode: bool = Field(nullable=False, default=False)
    profit_achieved_since_last_rotation: float = Field(nullable=False, default=False)

    def __hash__(self):
        return hash((type(self),) + tuple(self.user_id))

class SimulationPortfolio(SQLModel, table=True):
    __tablename__ = "simulations_portfolio"

    user_id: str = Field(primary_key=True)
    coin: str = Field(primary_key=True, nullable=False)
    amount: float = Field(nullable=False, default=0.0)
    ratio: float = Field(nullable=False, default=0.0)

class SimulationPortfolioHistory(SQLModel, table=True):
    __tablename__ = "simulations_portfolio_history"

    user_id: str = Field(primary_key=True)
    coin: str = Field(primary_key=True, nullable=False)
    timestamp: int = Field(primary_key=True, nullable=False)
    ratio: float = Field(nullable=False, default=0.0)
