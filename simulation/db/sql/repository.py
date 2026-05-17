from datetime import datetime, timezone
from typing import Generator, Optional

from sqlalchemy import Engine
from sqlmodel import Session, delete, select
from simulation.db.repository import SimulationsRepository
from simulation.db.sql._mapping import map_sim_history, map_simulation
from simulation.model import UPDATED_SIMULATION_FIAT_KEY, Simulation
from simulation.db.sql.model import Simulation as SimulationSQLModel
from simulation.db.sql.model import SimulationPortfolio as SimulationPortfolioSQLModel
from simulation.db.sql.model import SimulationPortfolioHistory as SimulationPortfolioHistorySQLModel

class SimulationsSQLRepository(SimulationsRepository):
    engine: Engine

    def __init__(self, engine: Engine):
        self.engine = engine

    def remove_simulation(self, id: str):
        with Session(self.engine) as session:
            stmt = delete(SimulationPortfolioHistorySQLModel).where(SimulationPortfolioHistorySQLModel.user_id == str(id))
            session.exec(stmt)

            stmt = delete(SimulationPortfolioSQLModel).where(SimulationPortfolioSQLModel.user_id == str(id))
            session.exec(stmt)

            stmt = delete(SimulationSQLModel).where(SimulationSQLModel.user_id == str(id))
            session.exec(stmt)

            session.commit()

    def get_simulation(self, id: str) -> Optional[Simulation]:
        with Session(self.engine) as session:
            result_sim = session.get(SimulationSQLModel, str(id))
            
            if not result_sim:
                return None

            stmt_portfolio = select(SimulationPortfolioSQLModel).where(
                SimulationPortfolioSQLModel.user_id == str(id)
            )
            result_portfolio = session.exec(stmt_portfolio).all()

            return map_simulation(result_sim, result_portfolio)

    def get_simulations_outdated(self, timestamp: int) -> Generator[Simulation, None, None]:
        batch_size = 1000
        last_user_id = ""

        with Session(self.engine) as session:
            while True:
                stmt = (
                    select(SimulationSQLModel, SimulationPortfolioSQLModel)
                    .join(
                        SimulationPortfolioSQLModel, 
                        SimulationSQLModel.user_id == SimulationPortfolioSQLModel.user_id
                    )
                    .where(
                        SimulationSQLModel.last_rotated_at + (SimulationSQLModel.timespan_in_hours * 3600) <= timestamp,
                        SimulationSQLModel.user_id > last_user_id
                    )
                    .order_by(SimulationSQLModel.user_id)
                    .limit(batch_size)
                )
                
                results = session.exec(stmt).all()

                if not results:
                    break

                # We have to group portfolio entries by simulation
                portfolio_entries_by_simulation = {}
                sims = {sim for sim, _ in results}
                for sim, portfolios in results:
                    portfolio_entries_by_simulation.setdefault(sim.user_id, []).append(portfolios)

                for sim in sims:
                    yield map_simulation(sim, portfolio_entries_by_simulation.get(sim.user_id, []))

                last_user_id = results[-1][0].user_id

    def save_simulation(self, sim: Simulation, at_timestamp: Optional[int] = None):
        if not at_timestamp:
            at_timestamp = int(datetime.now(timezone.utc).timestamp())


        with Session(self.engine) as session:
            session.merge(
                SimulationSQLModel(
                    user_id=str(sim.user_id),
                    initial_fiat_amount=sim.initial_fiat_amount,
                    updated_fiat_amount=sim.updated_fiat_amount,
                    webhook_endpoint=sim.webhook_endpoint,
                    last_rotated_at=sim.last_rotated_at,
                    timespan_in_hours=sim.timespan_in_hours,
                    operational_fee_percentage=sim.operational_fee_percentage,
                    trader_pro=sim.trader_pro,
                    panic_mode=sim.panic_mode,
                    profit_achieved_since_last_rotation=sim.profit_achieved_since_last_rotation
                )
            )
            session.merge(
                SimulationPortfolioHistorySQLModel(
                    user_id=str(sim.user_id),
                    coin=UPDATED_SIMULATION_FIAT_KEY,
                    timestamp=at_timestamp,
                    ratio=sim.updated_fiat_amount
                )
            )

            # Delete current portfolio entries. It will be replaced.
            stmt_delete_portfolio = delete(SimulationPortfolioSQLModel).where(
                SimulationPortfolioSQLModel.user_id == str(sim.user_id)
            )
            session.exec(stmt_delete_portfolio)

            # Add portfolio entries
            coins = set(sim.amount_per_coins.keys())
            coins |= set(sim.ratio_per_coins.keys())

            for coin in coins:
                session.merge(
                    SimulationPortfolioSQLModel(
                        user_id=str(sim.user_id),
                        coin=coin,
                        amount=sim.amount_per_coins.get(coin, 0.0),
                        ratio=sim.ratio_per_coins.get(coin, 0.0)
                    )
                )
                session.merge(
                    SimulationPortfolioHistorySQLModel(
                        user_id=str(sim.user_id),
                        coin=coin,
                        timestamp=at_timestamp,
                        ratio=sim.ratio_per_coins.get(coin, 0.0)
                    )
                )

            session.commit()


    def get_history(self, id: str) -> dict[int, dict[str, float]]:
        with Session(self.engine) as session:
            stmt = select(SimulationPortfolioHistorySQLModel).where(
                SimulationPortfolioHistorySQLModel.user_id == str(id)
            ).order_by(
                SimulationPortfolioHistorySQLModel.coin.asc(), # pyright: ignore[reportAttributeAccessIssue]
                SimulationPortfolioHistorySQLModel.timestamp.desc() # pyright: ignore[reportAttributeAccessIssue]
            ) 
            result = session.exec(stmt).all()
            return map_sim_history(result)
