import os
from dotenv import load_dotenv
from punq import Container
from sqlalchemy import Engine
from sqlmodel import create_engine

from coins.db.repository import CoinsRepository
from coins.db.sql.repository import CoinsSQLRepository
from simulation.db.config import SimulationConfig
from simulation.db.redis import SimulationRedisConfig
from simulation.db.repository import SimulationsRepository
from simulation.db.sql.repository import SimulationsSQLRepository
from users.db.repository import UsersRepository
from users.db.sql.repository import UsersSQLRepository
from webhooks.client import WebhookClient

load_dotenv(override=True)

_container = Container()

def _register_sql_engine():
    user = os.getenv("SQL_USER")
    password = os.getenv("SQL_PASSWORD")
    host = os.getenv("SQL_HOST")
    port = os.getenv("SQL_PORT")
    db = os.getenv("SQL_DB")

    engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")
    _container.register(Engine, instance=engine)

def register_dependencies():
    _register_sql_engine()

    engine: Engine = _container.resolve(Engine)
    _container.register(CoinsRepository, instance=CoinsSQLRepository(engine))
    _container.register(UsersRepository, instance=UsersSQLRepository(engine))
    _container.register(SimulationsRepository, instance=SimulationsSQLRepository(engine))
    _container.register(SimulationConfig, instance=SimulationRedisConfig())
    _container.register(WebhookClient, instance=WebhookClient())


def get_dependencies() -> Container:
    return _container