from datetime import datetime, timezone
import logging
import textwrap
from typing import Optional
from telegram import ForceReply, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    filters,
)

from coins.actions import get_exchange_rates_at, get_uptrend_coins
from coins.db.repository import CoinsRepository
from coins.model import RESERVE_DEFAULT_FIAT_CURRENCY
from coins.report.actions import (
    generate_coin_distribution_generic_report,
    generate_simulation_historical_graph,
)
from telegrm.keyboard import get_keyboard_markup_upon_user_state
from runner.dependencies import get_dependencies
from runner.model import Commands
from simulation import actions
from simulation.db.config import SimulationConfig
from simulation.db.repository import SimulationsRepository
from simulation.model import (
    Simulation,
    SimulationParams,
)
from simulation.report.actions import (
    generate_general_bot_stats,
    generate_market_status_report,
)
from users.db.repository import UsersRepository
from webhooks.client import WebhookClient


def get_conv_handler_start_simulation():
    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    ask_amount_state, ask_fee_state, ask_timespan_state, ask_mode_state, start_state = (
        range(5)
    )

    def _get_simulation_modes_keyboard_markup() -> ReplyKeyboardMarkup:
        keyboard = [
            [
                KeyboardButton("Conventional"),
                KeyboardButton("Trader Pro"),
            ]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def _get_running_simulation_keyboard_markup() -> ReplyKeyboardMarkup:
        keyboard = [
            [
                KeyboardButton(f"/{Commands.FORCE_UPDATE}"),
                KeyboardButton(f"/{Commands.DONATE}"),
                KeyboardButton(f"/{Commands.CHECK_BALANCE}"),
            ]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    async def _cancel(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(
            "Simulation not started. You can start it anytime with /simulate",
            reply_markup=get_keyboard_markup_upon_user_state(update),
        )
        return ConversationHandler.END

    async def _ask_amount(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
        sim = sims_repository.get_simulation(str(update.effective_chat.id))
        if sim:
            await update.message.reply_text(
                "You're already running a simulation. To stop it, use /simulate_stop",
                reply_markup=get_keyboard_markup_upon_user_state(update),
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "How much money (in USD) do you want to invest in the simulation?",
            reply_markup=ForceReply(selective=False, input_field_placeholder="1000.00"),
        )
        return ask_fee_state

    async def _ask_fee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            amount_as_text = update.message.text.replace(",", ".").strip()
            amount = float(amount_as_text)
            context.user_data["amount"] = amount
        except ValueError:
            await update.message.reply_text(
                """
                Invalid amount. Please use a valid number.
                """
            )
            return ask_fee_state

        if amount <= 0:
            await update.message.reply_text(
                """
                Negative amount? Really? Use a positive one!
                """
            )
            return ask_amount_state

        await update.message.reply_text(
            "If you expect to trade from an exchange, you can write next the fee percentage (e.g 0.1 for 0.1%). Otherwise just write anything.",
            reply_markup=ForceReply(selective=False, input_field_placeholder="0.1")
        )
        return ask_timespan_state

    async def _ask_timespan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            fee_as_text = update.message.text.replace(",", ".").strip()
            fee = max(0, float(fee_as_text))
            context.user_data["fee"] = fee
        except ValueError:
            await update.message.reply_text(
                """
                Ok, so no fee, roger that!
                """
            )

        await update.message.reply_text(
            "How frequently do you want to update your portfolio in hours? "
            "Default is 12 hours, and range has to be between 6 and 48 hours"
        )
        return ask_mode_state

    async def _ask_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        timespan = 1
        try:
            timespan = max(6, float(update.message.text))
            if not (6 <= timespan <= 48):
                await update.message.reply_text(
                    """
                    Sorry, the timespan should be between 6 and 48. Try again or /cancel .
                    """
                )
                return ask_timespan_state

            context.user_data["timespan"] = timespan
        except ValueError:
            await update.message.reply_text(
                """
                Assuming default timespan of 12 hours...
                """
            )

        if timespan < 12:
            await update.message.reply_text(
                textwrap.dedent(
                    "<strong> WARNING! </strong>\n"
                    "\n\n"
                    "Bot reacting within small timespans may take decisions "
                    "based on noise data, so results could be less predictable than they should."
                    "If you want to reconsider this, enter command /cancel and then, "
                    "setup simulation from scratch using /simulate . \n"
                    "\n"
                    "Take into consideration that default timespan by this bot is 12 hours.",
                ),
                parse_mode="HTML",
            )

        await update.message.reply_text(
            "<strong>Time to choose the mode!</strong>\n"
            "\n\n"
            "We need to know which kind of trading behavior you want from the bot, "
            "according to your needs:\n\n"
            "- <strong>Conventional</strong> You want to invest, but needs some protection against high volatility moments. "
            "Your funds will be shielded in risky scenarios, but that implies money to be hold until market gets safer. Also, it "
            "mitigates losses, but does not guarantee full protection."
            "\n\n"
            "- <strong>Trader PRO</strong> You know all the risks, accepts volatility of the market and you want the bot "
            "to let trade in any circumstance. <strong>⚠️ WARNING ⚠️</strong> You acknowledge that there won't be any control on your losses under a "
            "deep downtrending market.",
            parse_mode="HTML",
            reply_markup=_get_simulation_modes_keyboard_markup(),
        )

        return start_state

    async def _start_simulate(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        modes = {"conventional", "trader pro"}
        selected_mode = update.message.text.lower()
        if selected_mode not in modes:
            await update.message.reply_text(
                'Please type "conventional" or "trader pro"',
                reply_markup=_get_simulation_modes_keyboard_markup(),
            )
            return start_state

        coins_repository: CoinsRepository = get_dependencies().resolve(CoinsRepository)
        users_repository: UsersRepository = get_dependencies().resolve(UsersRepository)
        sim_config: SimulationConfig = get_dependencies().resolve(SimulationConfig)

        users_repository.add_user(str(update.effective_chat.id), None)
        sim = await actions.start_simulation(
            coins_repository,
            sims_repository,
            sim_config.get(),
            user_id=str(update.effective_chat.id),
            trader_pro=selected_mode == "trader pro",
            amount=context.user_data["amount"],
            timespan_in_hours=context.user_data.get("timespan", 12),
            operational_fee_percentage=context.user_data.get("fee", 0.0),
        )

        await update.message.reply_text(
            textwrap.dedent(
                f"🆗, you'll receive updates on how your ${sim.initial_fiat_amount} USD evolve!\n"
                "Updates will happen every {sim.timespan_in_hours} hours, so stay tuned."
                "Please be aware of late night messages. You're advised to silence this bot,"
                "so don't blame me if you don't! 😉\n"
                "\n"
                "💰 This is your initial distribution, given current trends:\n"
                "\n"
                f"{generate_coin_distribution_generic_report(sim)}\n"
                "\n"
                f"🤹 Your operational fee of {sim.operational_fee_percentage}% has been applied."
                "Next time, will be applied on the total of coins moved, except fiat held in reserve, if there's any."
                f"{'\n\n💡 <strong>You are a PRO TRADER!</strong> Beware of bulltraps and other strong downtrending moments!' if sim.trader_pro else ''}"
            ),
            parse_mode="HTML",
            reply_markup=_get_running_simulation_keyboard_markup(),
        )

        return ConversationHandler.END

    return ConversationHandler(
        entry_points=[CommandHandler("simulate", _ask_amount)],
        states={
            ask_amount_state: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_amount)
            ],
            ask_fee_state: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_fee)],
            ask_timespan_state: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_timespan)
            ],
            ask_mode_state: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_mode)
            ],
            start_state: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _start_simulate)
            ],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
    )


async def handle_stop_simulation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)

    sims_repository.remove_simulation(str(update.effective_chat.id))
    await update.message.reply_text(
        "Simulation stopped. Both portfolio and balance are lost. If you want to start again, you know the command!"
    )


async def handle_force_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    sim_config: SimulationConfig = get_dependencies().resolve(SimulationConfig)
    coins_repository: CoinsRepository = get_dependencies().resolve(CoinsRepository)

    sim = sims_repository.get_simulation(str(update.effective_chat.id))
    if not sim:
        await update.message.reply_text(
            "You're not running a simulation, it seems. Start with /simulate ."
        )
        return

    sim_params = sim_config.get()
    await actions.swap_cryptos(coins_repository, sims_repository, sim_params, sim)

    await context.bot.send_photo(
        chat_id=sim.user_id,
        photo=generate_simulation_historical_graph(sims_repository, sim),
        caption=textwrap.dedent(
            "<strong>You wanted it, you got it!</strong>\n"
            "\n\n"
            "Your portfolio has been distributed forcedly."
            "\n\n"
            "New distribution:\n"
            "\n"
            f"{generate_coin_distribution_generic_report(sim)}\n"
            "\n"
            f"💰 New total balance in fiat: {sim.updated_fiat_amount}",
        ),
        parse_mode="HTML",
    )


async def handle_check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    coins_repository: CoinsRepository = get_dependencies().resolve(CoinsRepository)

    sim = sims_repository.get_simulation(str(update.effective_chat.id))
    if not sim:
        await update.message.reply_text(
            "You're not running a simulation, it seems. Start with /simulate <AMOUNT>."
        )
        return

    await update.message.reply_text(
        text=textwrap.dedent(
            f"<strong>Report of your current portfolio and balance</strong>\n"
            "Distribution:\n"
            f"{generate_coin_distribution_generic_report(sim)}\n"
            "\n"
            f"💰 Total balance in fiat: {await actions.get_fiat_balance(coins_repository, int(datetime.now(timezone.utc).timestamp()), sim)}"
        ),
        parse_mode="HTML",
    )


async def handle_market_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coins_repository: CoinsRepository = get_dependencies().resolve(CoinsRepository)
    sim_config: SimulationConfig = get_dependencies().resolve(SimulationConfig)

    sim_params = sim_config.get()

    report = await generate_market_status_report(
        coins_repository, sim_params, 12
    )  # TODO Replace "12" with some parametrization
    await update.message.reply_text(text=report, parse_mode="HTML")


async def handle_bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    users_repository: UsersRepository = get_dependencies().resolve(UsersRepository)

    report = await generate_general_bot_stats(users_repository, sims_repository)
    await update.message.reply_text(text=report, parse_mode="HTML")


async def run_simulating(context: ContextTypes.DEFAULT_TYPE):
    coins_repository: CoinsRepository = get_dependencies().resolve(CoinsRepository)

    sims_repository: SimulationsRepository = get_dependencies().resolve(SimulationsRepository)
    sim_config: SimulationConfig = get_dependencies().resolve(SimulationConfig)
    
    webhook_client: WebhookClient = get_dependencies().resolve(WebhookClient)

    sim_params = sim_config.get()

    simulation_batch_time = datetime.now(timezone.utc)

    exchange_rates = await get_exchange_rates_at(
        coins_repository, int(simulation_batch_time.timestamp())
    )

    uptrend_coins_per_timespan = {}

    for sim in sims_repository.get_simulations_outdated(int(simulation_batch_time.timestamp())):
        if not uptrend_coins_per_timespan.get(sim.timespan_in_hours):
            uptrend_coins_per_timespan[sim.timespan_in_hours] = await get_uptrend_coins(
                coins_repository,
                sim.timespan_in_hours,
                int(simulation_batch_time.timestamp()),
                filter_by_confidence=True,
            )

        try:
            await _handle_portfolio(
                context,
                coins_repository,
                sims_repository,
                webhook_client,
                sim_params,
                sim,
                exchange_rates=exchange_rates,
            )
            await _handle_simulation_update(
                context,
                coins_repository,
                sims_repository,
                webhook_client,
                simulation_batch_time,
                sim_params,
                sim,
                exchange_rates=exchange_rates,
                uptrend_coins=uptrend_coins_per_timespan[sim.timespan_in_hours],
            )

        except Exception as e:
            logging.info(f"Unable to perform simulation for {sim.user_id}: {e}")


async def _handle_portfolio(
    context: ContextTypes.DEFAULT_TYPE,
    coins_repository: CoinsRepository,
    sims_repository: SimulationsRepository,
    webhook_client: WebhookClient,
    sim_params: SimulationParams,
    sim: Simulation,
    exchange_rates: Optional[dict[str, float]] = {},
):
    sim_before = sim.model_copy(deep=True)
    await actions.control_portfolio(
        coins_repository,
        sims_repository,
        sim_params,
        sim,
        exchange_rates=exchange_rates,
    )

    if not sim_before.panic_mode and sim.panic_mode:
        if sim.webhook_endpoint:
            webhook_client.send(
                sim.user_id,
                "simulation.panic",
                payload=sim.model_dump_only_information_fields(),
                idempotency_key=f"{sim.user_id}_panic_{int(datetime.now(timezone.utc).timestamp())}"
            )
            return

        await context.bot.send_message(
            chat_id=sim.user_id,
            text=textwrap.dedent(
                "<strong>⚠️ Heads up! ⚠️</strong>"
                "\n\n"
                "The market is moving a bit unpredictably right now, and your balance has slipped below the safety threshold we use to protect your funds.\n"
                "Your simulation has automatically switched to recovery mode — one of our safeguards designed for exactly this kind of situation."
                "\n\n"
                "<strong>What this means for you:</strong>\n"
                "- ♻️💲 Your crypto positions were moved to fiat to prevent further losses.\n"
                "- 🛡️ The bot will invest only in the strongest bullish signals while the market stays shaky.\n"
                "- 📈 Once your balance stabilises and the trend improves, recovery mode will switch off automatically and your simulation will continue as usual.\n"
            ),
            parse_mode="HTML",
        )
        return

    if not sim.panic_mode and sim_before.panic_mode:
        if sim.webhook_endpoint:
            webhook_client.send(
                sim.user_id,
                "simulation.recovery",
                payload=sim.model_dump_only_information_fields(),
                idempotency_key=f"{sim.user_id}_recovery_{int(datetime.now(timezone.utc).timestamp())}"
            )
            return

        await context.bot.send_message(
            chat_id=sim.user_id,
            text=textwrap.dedent(
                "<strong>🚀 All Clear! You're Back on Track.</strong>"
                "\n\n"
                "Your simulation has fully recovered, so Safe Mode has been disabled."
                "\n\n"
                "Market conditions look stable again, and your portfolio is healthy enough to resume normal trading. "
                "From here on, operations will follow your usual behavior as expected."
            ),
            parse_mode="HTML",
        )
        return

    # Print a message if there's an investment and had to be moved back to fiat.
    cryptos_before = {
        coin
        for coin, amount in sim_before.amount_per_coins.items()
        if coin != RESERVE_DEFAULT_FIAT_CURRENCY and amount > 0
    }
    cryptos_after = {
        coin
        for coin, amount in sim.amount_per_coins.items()
        if coin != RESERVE_DEFAULT_FIAT_CURRENCY and amount > 0
    }
    if cryptos_before and not cryptos_after:
        if sim.webhook_endpoint:
            webhook_client.send(
                sim.user_id,
                "simulation.protected",
                payload=sim.model_dump_only_information_fields(),
                idempotency_key=f"{sim.user_id}_fiat_protection_{int(datetime.now(timezone.utc).timestamp())}"
            )
            return

        await context.bot.send_message(
            chat_id=sim.user_id,
            text=textwrap.dedent(
                "<strong>🛡️ Portfolio protected in fiat!</strong>\n\n"
                "We tried to invest in strong bullish trends to help recover your funds, "
                "but the signal turned out to be unreliable and the portfolio started dropping.\n\n"
                "To protect your capital, your investment is back to fiat.\n\n"
            ),
            parse_mode="HTML",
        )


async def _handle_simulation_update(
    context: ContextTypes.DEFAULT_TYPE,
    coins_repository: CoinsRepository,
    sims_repository: SimulationsRepository,
    webhook_client: WebhookClient,
    simulation_batch_time: datetime,
    sim_params: SimulationParams,
    sim: Simulation,
    exchange_rates: Optional[dict[str, float]] = {},
    uptrend_coins: Optional[list[float]] = [],
):
    # Crypto swapping has to be done in hourly intervals
    td = simulation_batch_time - datetime.fromtimestamp(sim.last_rotated_at, timezone.utc)
    if td.total_seconds() <= sim.timespan_in_hours * 3600:
        return

    sim.last_rotated_at = int(simulation_batch_time.timestamp())
    await actions.swap_cryptos(
        coins_repository,
        sims_repository,
        sim_params,
        sim,
        exchange_rates=exchange_rates,
        uptrend_coins=uptrend_coins,
    )

    if sim.webhook_endpoint:
        webhook_client.send(
            sim.user_id,
            "simulation.update",
            payload=sim.model_dump_only_information_fields()
        )
        return


    distribution = generate_coin_distribution_generic_report(sim)

    panic_mode_text = ""
    if sim.panic_mode:
        panic_mode_text = textwrap.dedent(
            "\n\n\n"
            "<strong>🛡️ Your simulation is currently in safe mode!</strong>\n\n"
            "This changes how cryptocurrencies are selected for investment, "
            "aiming to recover your previous losses. "
            "Only the strongest and most reliable signals are considered."
        )

    await context.bot.send_photo(
        chat_id=sim.user_id,
        photo=generate_simulation_historical_graph(sims_repository, sim),
        caption=textwrap.dedent(
            f"<strong>📊 Simulation Update!</strong>\n"
            "Your portfolio has been redistributed based on market trends.\n"
            "\n"
            "New Distribution:\n"
            f"{distribution}\n"
            "\n"
            f"💰 New total balance in fiat: {sim.updated_fiat_amount}\n"
            "\n"
            f"Remember your operational fee: {sim.operational_fee_percentage}% . "
            "\n\n\n"
            f"{panic_mode_text}"
        ),
        parse_mode="HTML",
    )
