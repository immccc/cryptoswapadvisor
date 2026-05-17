from datetime import datetime, timezone
import io
import os
import textwrap

import requests
import structlog
from structlog.contextvars import bind_contextvars, reset_contextvars

from backtest.actions import import_prices, run_backtest
from backtest.broker.model import ComputedExchange
from coins.db.test_db import CoinsTestRepository
from coins.model import Coin
from coins.report.actions import generate_simulation_historical_graph
from simulation.db.test_db import SimulationsTestRepository
from simulation.model import Simulation, SimulationParams

log = structlog.get_logger()


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def _send_msg_report_to_user(sim: Simulation, report: io.BytesIO):
    # Given this is being run out of telegram bot lib,
    # we need to send this the manual way.
    report.seek(0)
    
    msg_caption = textwrap.dedent(
        f"<strong>📊 Your requested backtest is ready! </strong>"
        "\n\n\n"
        f"From {sim.initial_fiat_amount}, your balance has become {sim.updated_fiat_amount}. "
        "\n"
        "Below you can check how your funds evolved during time"
    )

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
        data={"chat_id": sim.user_id, "caption": msg_caption, "parse_mode": "HTML"},
        files={"photo": ("result.png", report, "image/png")}
    )

def _send_msg_error(user_id: str):
    msg_caption = textwrap.dedent(
        "<strong>🤦 Sorry, something went wrong.</strong>"
        "\n\n\n"
        "A log has been registered on our systems and we will investigate."
        "\nIn the meantime, you can continue with your simulation, or try it "
        "again later."
    )

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": user_id, "text": msg_caption, "parse_mode": "HTML"}
    )

async def process_backtest_request(
    ctx,
    user_id: int = 0, 
    sim_timespan_in_hrs: int = 0,
    sim_initial_amount: float = 0.0,
    sim_trader_pro: bool = False,
    import_from_timestamp: int = 0,
    import_to_timestamp: int = 0,
    coins_csv: str = "",
):
    tokens = bind_contextvars(user_id=user_id, broker=True)
    
    log.info("Setting up backtest")

    coins = coins_csv.split(",")
    coins = [coin.strip() for coin in coins]

    prices_per_coin = import_prices(
        import_from_timestamp,
        import_to_timestamp,
        coins
    )

    simulation_duration_in_hrs = round(
        (
            datetime.fromtimestamp(
                import_to_timestamp, timezone.utc
            ) - datetime.fromtimestamp(
                import_from_timestamp, timezone.utc
            )
        ).total_seconds() / 3600
    )

    computed_exchanges = [
        ComputedExchange(
            id,
            values=prices_per_coin.get(id),
            simulation_duration=simulation_duration_in_hrs
        )
        for id in coins
    ]

    coins_repository = CoinsTestRepository()
    sims_repository = SimulationsTestRepository()
    sim_params = SimulationParams()

    log.info("Running backtest")

    try:
        await run_backtest(
            computed_exchanges,
            [Coin(name=coin) for coin in coins],
            coins_repository,
            sims_repository,
            sim_params,
            sim_timespan_in_hrs,
            sim_initial_amount,
            sim_trader_pro,
            sim_id=user_id
        )

        sim = sims_repository.get_simulation(user_id)

        report = generate_simulation_historical_graph(
            sims_repository,
            sim
        )

        _send_msg_report_to_user(sim, report)

    except Exception:
        _send_msg_error(user_id)
        log.exception("Something went wrong on running backtest. ")

    finally:
        log.info("Backtest finished")
        reset_contextvars(**tokens)
