from enum import StrEnum


class Commands(StrEnum):
    START = "start"
    BACKTEST = "backtest"
    UNREGISTER = "stop"
    SIMULATION_START = "simulate"
    SIMULATION_STOP = "simulate_stop"
    FORCE_UPDATE = "force_update"
    CHECK_BALANCE = "check_balance"
    CHECK_MARKET_STATUS = "market_status"
    CHECK_BOT_STATUS = "bot_status"
    DONATE = "donate"
