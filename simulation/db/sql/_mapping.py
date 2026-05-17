from typing import Iterable
from simulation.db.sql.model import Simulation as SimulationSQLModel
from simulation.db.sql.model import SimulationPortfolio as SimulationPortfolioSQLModel
from simulation.db.sql.model import SimulationPortfolioHistory  as SimulationPortfolioHistorySQLModel

from simulation.model import Simulation


def map_simulation(simulation: SimulationSQLModel, portfolio_entries: Iterable[SimulationPortfolioSQLModel]) -> Simulation:
    return Simulation(
        user_id=simulation.user_id,
        initial_fiat_amount=simulation.initial_fiat_amount,
        updated_fiat_amount=simulation.updated_fiat_amount,
        webhook_endpoint=simulation.webhook_endpoint,
        amount_per_coins={portfolio_entry.coin: portfolio_entry.amount for portfolio_entry in portfolio_entries},
        ratio_per_coins={portfolio_entry.coin: portfolio_entry.ratio for portfolio_entry in portfolio_entries},
        last_rotated_at=simulation.last_rotated_at,
        timespan_in_hours=simulation.timespan_in_hours,
        operational_fee_percentage=simulation.operational_fee_percentage,
        trader_pro=simulation.trader_pro,
        panic_mode=simulation.panic_mode,
        profit_achieved_since_last_rotation=simulation.profit_achieved_since_last_rotation,
    )

def map_sim_history(portfolio_history_entries: Iterable[SimulationPortfolioHistorySQLModel]) -> dict[int, dict[str, float]]:
    per_timestamp = {}
    for entry in portfolio_history_entries:
        per_timestamp[entry.timestamp] = per_timestamp.get(entry.timestamp, {}) | {entry.coin: entry.ratio}

    return per_timestamp