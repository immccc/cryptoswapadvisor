import asyncio

from dotenv import load_dotenv
from sqlalchemy import Engine
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session
from coins.db.redis import CoinsRedisRepository
from coins.db.sql.model import Exchange
from coins.db.sql.repository import CoinsSQLRepository
from coins.model import Coin
from runner.dependencies import get_dependencies, register_dependencies
from simulation.db.redis import SimulationsRedisRepository
from simulation.db.sql.model import SimulationPortfolioHistory
from simulation.db.sql.repository import SimulationsSQLRepository
from users.db.redis import UsersRedisRepository
from users.db.sql.repository import UsersSQLRepository

load_dotenv(override=True)

# TODO Unfortunately we need a method to save history per simulation separately, and out of repos.
async def _save_sim_history(
    user_id: int,
    engine: Engine,
    sims_redis_repository: SimulationsRedisRepository,
):
    history = sims_redis_repository.get_history(user_id)
    
    with Session(engine) as session:
        for timestamp, values_per_coin in history.items():
            for coin, value in values_per_coin.items():
                session.merge(
                    SimulationPortfolioHistory(
                        user_id=str(user_id),
                        coin=coin,
                        timestamp=timestamp,
                        ratio=value
                    )
                )
        session.commit()    

async def _save_exchanges_all_at_once(coins_redis_repository: CoinsRedisRepository, engine: Engine, *coins: Coin):
    
    exchanges = await asyncio.gather(*(coins_redis_repository.get_exchanges_from_range_with_timestamps(coin.name, 0, 100000000000) for coin in coins))
    exchanges_per_coin = {coin_and_exchanges[0].name: coin_and_exchanges[1] for coin_and_exchanges in zip(coins, exchanges)}
    
    exchanges_orm = [
        Exchange(
            coin_name=coin_name,
            timestamp=timestamp,
            value=value
        )
        for coin_name, excs in exchanges_per_coin.items()
        for timestamp, value in excs.items()
    ]

    with Session(engine) as session:
        stmt = insert(Exchange).values([exchange.model_dump() for exchange in exchanges_orm])
        stmt = stmt.on_conflict_do_nothing()
        session.exec(stmt)


async def run_migration():
    print("Running migration Redis -> SQL...")
    print("WARNING: This is thought for small datasets for now. Consider alternatives for big ones!")

    register_dependencies()

    users_redis_repository = UsersRedisRepository()
    sims_redis_repository = SimulationsRedisRepository()
    coins_redis_repository = CoinsRedisRepository()

    engine = get_dependencies().resolve(Engine)
    users_sql_repository = UsersSQLRepository(engine)
    sims_sql_repository = SimulationsSQLRepository(engine)
    coins_sql_repository = CoinsSQLRepository(engine)

    print("Migrating users...")
    users = users_redis_repository.get_all_users()
    for user in users:
        users_sql_repository.add_user(user, None)

    print("Migrating simulations...")
    for user in users:
        sim = sims_redis_repository.get_simulation(user.id)
        if sim is None:
            continue
        sims_sql_repository.save_simulation(sim)
        await _save_sim_history(user.id, engine, sims_redis_repository)


    print("Migrating coins...")
    coins_registered = await coins_redis_repository.get_coins_registered()
    coins = await coins_redis_repository.get_coins(*coins_registered)
    await coins_sql_repository.save_coins(*coins)

    print("Migrating exchanges...")
    await _save_exchanges_all_at_once(coins_redis_repository, engine, *coins)

    print("DONE!")


if __name__ == "__main__":
    asyncio.run(run_migration())