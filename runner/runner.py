import os

from telegram import BotCommand
from backtest.chat_handlers import get_conv_handler_start_backtesting
from coins.model import INTERVAL_COLLECTION_SECONDS
from coins.model import INTERVAL_COMPACTION_SECONDS
from runner.chat_handlers import handle_unregister, handle_welcome_message
from coins.db.chat_handlers import run_collection, run_compaction
from telegram.ext import ApplicationBuilder, CommandHandler, JobQueue, Application
from punq import Container

from monetization.chat_handlers import handle_donate
from runner.dependencies import register_dependencies
from runner.model import Commands
from simulation.model import INTERVAL_SIMULATION_CONTROL_SECONDS
from simulation.chat_handlers import (
    handle_bot_status,
    handle_check_balance,
    handle_force_update,
    get_conv_handler_start_simulation,
    handle_market_status,
    handle_stop_simulation,
    run_simulating,
)

import logging


_BOT_COMMANDS_HELP = {
    Commands.START: "Join the bot",
    Commands.BACKTEST: "Run a backtest",
    Commands.UNREGISTER: "Remove your user data, including simulations",
    Commands.SIMULATION_START: """
        Try a virtual deposit and watch your simulated portfolio grow (or shrink!) based on our automatic crypto-swap strategy.
        Make sure you’re registered with /start first."
    """,
    Commands.SIMULATION_STOP: "Stop the simulation and delete data of your portfolio",
    Commands.FORCE_UPDATE: """
    Forces an update on your portfolio without waiting preconfigured timespan. Useful for debugging purposes, but watch out of the momentum!
    """,
    Commands.CHECK_BALANCE: "Checks your current balance",
    Commands.CHECK_MARKET_STATUS: "Prints current market status",
    # Commands.CHECK_BOT_STATUS: "Prints current bot status",
    Commands.DONATE: "Support the project with a donation",
}


class Runner:
    _container = Container()

    @classmethod
    def get_instance(cls):
        if not hasattr(cls, "_runner") or not cls._runner:
            cls._runner = Runner()

        return cls._runner

    app: Application

    def __init__(self):
        register_dependencies()

        self.app = (
            ApplicationBuilder()
            .token(os.getenv("TELEGRAM_BOT_TOKEN", ""))
            .post_init(self._setup)
            .build()
        )

        logging.getLogger("httpx").setLevel(logging.WARNING)

    @staticmethod
    def _env_is_local() -> bool:
        return os.getenv("ENVIRONMENT", "") == "local"

    async def _setup(self, app: Application):
        await self.app.bot.set_my_commands(
            [BotCommand(bot, help) for bot, help in _BOT_COMMANDS_HELP.items()]
        )

        [
            self.app.add_handler(handler)
            for handler in [
                CommandHandler(Commands.START, handle_welcome_message),
                get_conv_handler_start_backtesting(),
                CommandHandler(Commands.UNREGISTER, handle_unregister),
                get_conv_handler_start_simulation(),
                CommandHandler(Commands.SIMULATION_STOP, handle_stop_simulation),
                CommandHandler(Commands.FORCE_UPDATE, handle_force_update),
                CommandHandler(Commands.CHECK_BALANCE, handle_check_balance),
                CommandHandler(Commands.CHECK_MARKET_STATUS, handle_market_status),
                # CommandHandler(Commands.CHECK_BOT_STATUS, handle_bot_status), TODO Not useful yet and may cause a breach because inefficient data load. Will work on that
                CommandHandler(Commands.DONATE, handle_donate),
            ]
        ]

        if self.app.job_queue is None:
            raise RuntimeError("Job queue is not initialized")

        job_queue: JobQueue = self.app.job_queue

        job_queue.run_repeating(
            run_simulating, interval=INTERVAL_SIMULATION_CONTROL_SECONDS
        )

        # Given my current shitty homemade env setup, we need to avoid running a local testing server consumes API credits
        if not self._env_is_local():
            job_queue.run_repeating(
                run_collection, interval=INTERVAL_COLLECTION_SECONDS
            )
            job_queue.run_repeating(
                run_compaction, interval=INTERVAL_COMPACTION_SECONDS
            )

    def run(self):
        self.app.run_polling()
