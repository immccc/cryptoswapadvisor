from telegram import KeyboardButton, ReplyKeyboardMarkup, Update

from runner.dependencies import get_dependencies
from runner.model import Commands
from simulation.db.repository import SimulationsRepository

def get_keyboard_markup_upon_user_state(update: Update) -> ReplyKeyboardMarkup:
    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)

    if sims_repository.get_simulation(str(update.effective_chat.id)):
        return _get_simulation_keyboard_markup()

    return _get_default_keyboard_markup()

def _get_simulation_keyboard_markup() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(f"/{Commands.FORCE_UPDATE}"),
            KeyboardButton(f"/{Commands.DONATE}"),
            KeyboardButton(f"/{Commands.CHECK_BALANCE}"),
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def _get_default_keyboard_markup() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(f"/{Commands.BACKTEST}"),
            KeyboardButton(f"/{Commands.DONATE}"),
            KeyboardButton(f"/{Commands.SIMULATION_START}"),
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)