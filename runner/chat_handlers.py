import textwrap
from telegram import Update
from telegram.ext import ContextTypes

from runner.dependencies import get_dependencies
from telegrm.keyboard import get_keyboard_markup_upon_user_state
from simulation.db.repository import SimulationsRepository
from users.db.repository import UsersRepository


async def handle_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_repository: UsersRepository = get_dependencies().resolve(UsersRepository)

    users_repository.add_user(str(update.effective_chat.id), None)

    await update.message.reply_text(
        textwrap.dedent(
            """
            <strong>Welcome to the crypto swap simulator!</strong>

            This bot provides insights and simulations for automated crypto trading, 
            plus swapping advise from bearish to bullish coins.

            The final objective is trying to maximize profits for everyone
            interested, but without knowledge on trading or crypto markets.

            ⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
            <strong>BUT REMEMBER:</strong>
            ⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️

            <i>Trading is risky and you may lose part or all of your investments.
            While we are working on making internal bots to mitigate any negative impact,
            taking any action based on the bot suggestions is at your own responsbility,
            and <strong>the bot authors are not liable for any of your losses.</strong></i>

            
            Check the available commands and start playing around!
            """
        ),
        parse_mode="HTML",
        reply_markup=get_keyboard_markup_upon_user_state(update),
    )


async def handle_unregister(update: Update, _: ContextTypes.DEFAULT_TYPE):
    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    users_repository: UsersRepository = get_dependencies().resolve(UsersRepository)

    sims_repository.remove_simulation(str(update.effective_chat.id))
    users_repository.remove_user(str(update.effective_chat.id))

    await update.message.reply_text(
        textwrap.dedent(
            """
            You have been unsubscribed from this bot.

            You can rejoin at any time with /start .

            Thanks a lot for using this tooling.
            Please, if you liked it, consider supporting this project with /donate .

            👋 See ya!
            """
        )
    )


