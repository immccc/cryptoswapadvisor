import datetime
import textwrap
from saq import Status
from telegram import ForceReply, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    filters,
)

from backtest.broker.broker import get_broker_queue

from telegrm.keyboard import get_keyboard_markup_upon_user_state
from runner.model import Commands

_DATE_FORMAT = "%Y-%m-%d"
_MAX_COINS = 7
_MAX_DAYS = 15


def get_conv_handler_start_backtesting():
    (
        ask_begin_state,
        ask_end_state,
        ask_coins_state,
        ask_amount_state,
        ask_fee_state,
        ask_timespan_state,
        ask_mode_state,
        start_state,
    ) = range(8)

    def _get_simulation_modes_keyboard_markup() -> ReplyKeyboardMarkup:
        keyboard = [
            [
                KeyboardButton("Conventional"),
                KeyboardButton("Trader Pro"),
            ]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    async def _cancel(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(
            "Backtest request cancelled. You can request it anytime with /backtest",
            reply_markup=get_keyboard_markup_upon_user_state(update),
        )
        return ConversationHandler.END

    async def _ask_begin(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:

        # Check if there's already a backtest job for this user
        queue = get_broker_queue()
        already_existing_job = await queue.job(str(update.effective_chat.id))
        if already_existing_job and already_existing_job.status in [Status.QUEUED, Status.ACTIVE, Status.ABORTING, Status.NEW]:
            await update.message.reply_text(
                textwrap.dedent(
                    "Sorry, you have already a backtest task planned."
                    "\n\n"
                    "Try it again when it finishes."
                )
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "Type the start date for your backtest (yyyy-mm-dd)",
            reply_markup=ForceReply(selective=False, input_field_placeholder="2026-01-01"),
        )
        return ask_end_state

    async def _ask_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            context.user_data["sim_start_date"] = int(
                datetime.datetime.strptime(
                    update.message.text, _DATE_FORMAT
                ).replace(tzinfo=datetime.timezone.utc).timestamp()
            )
        except ValueError:
            await update.message.reply_text(
                "That's not a valid date! Try again or write /cancel",
                reply_markup=ForceReply(selective=False, input_field_placeholder="2026-01-01"),
            )
            return ask_begin_state

        await update.message.reply_text(
            "Type the end date for your backtest (yyyy-mm-dd)",
            reply_markup=ForceReply(selective=False, input_field_placeholder="2026-01-30"),
        )
        return ask_coins_state

    async def _ask_coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            end_date = int(
                datetime.datetime.strptime(
                    update.message.text, _DATE_FORMAT
                ).replace(tzinfo=datetime.timezone.utc).timestamp()
            )
        except ValueError:
            await update.message.reply_text(
                "That's not a valid date! Try again or write /cancel",
                reply_markup=ForceReply(selective=False, input_field_placeholder="2026-01-30"),
            )
            return ask_coins_state

        start_date = context.user_data["sim_start_date"]
        if end_date <= start_date:
            await update.message.reply_text(
                "End date should be after start date! Try again or write /cancel",
                reply_markup=ForceReply(selective=False, input_field_placeholder="2026-01-30"),
            )
            return ask_coins_state

        if (end_date - start_date) / (3600 * 24 * 15) > _MAX_DAYS:
            await update.message.reply_text(
                "Time range should be 15 days at max! Try again or write /cancel",
                reply_markup=ForceReply(selective=False, input_field_placeholder="2026-01-30"),
            )
            return ask_coins_state

        context.user_data["sim_end_date"] = end_date


        await update.message.reply_text(
            "Type the coins to be included in the test (max 7)",
            reply_markup=ForceReply(selective=False, input_field_placeholder="BTC,ETH,ADA"),
        )
        return ask_amount_state

    async def _ask_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        coins_csv = update.message.text
        if len(coins_csv.split(",")) > _MAX_COINS:
            await update.message.reply_text(
                "Sorry, amount of coins are limited to a maximum of 7. Try again or write /cancel",
                reply_markup=ForceReply(selective=False, input_field_placeholder="BTC,ETH,ADA"),
            )
            return ask_amount_state

        context.user_data["coins_csv"] = coins_csv

        await update.message.reply_text(
            "How much money (in USD) would you like to use for this backtest?",
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
                Invalid amount. Please use a valid number or type cancel.
                """,
                reply_markup=ForceReply(selective=False, input_field_placeholder="1000.00"),
            )
            return ask_fee_state

        if amount <= 0:
            await update.message.reply_text(
                """
                Negative amount? Really? Use a positive one!
                """,
                reply_markup=ForceReply(selective=False, input_field_placeholder="1000.00"),
            )

            return ask_fee_state

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
                    Sorry, the timespan should be between 6 and 48
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

        await update.message.reply_text(
            "Which mode you want to run the bot during the backtest?",
            parse_mode="HTML",
            reply_markup=_get_simulation_modes_keyboard_markup(),
        )

        return start_state

    async def _start_backtest(
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

        context.user_data["sim_trader_pro"] = selected_mode == "trader pro"

        await get_broker_queue().enqueue(
            "process_backtest_request",
            key=str(update.effective_chat.id),
            user_id=str(update.effective_chat.id),
            sim_timespan_in_hrs=context.user_data.get("timespan"),
            sim_initial_amount=context.user_data.get("amount"),
            sim_trader_pro=context.user_data.get("sim_trader_pro"),
            import_from_timestamp=context.user_data.get("sim_start_date"),
            import_to_timestamp=context.user_data.get("sim_end_date"),
            coins_csv=context.user_data.get("coins_csv"),
            timeout=0
        )

        await update.message.reply_text(
            textwrap.dedent(
                "🆗 Backtest request received! Results may take a while depending on load."
                "\n\n"
                "⚠️ Please keep in mind:"
                "\n- Some coins may not be available depending on the data source."
                "\n- This is a sample simulation, not an exact prediction of real bot behavior."
                "\n- Treat results as illustrative, not as precise values."
                f"\n- Amount of coins are limited to a maximum of {_MAX_COINS}. Real bot takes all coins"
            ),
            parse_mode="HTML",
            reply_markup=get_keyboard_markup_upon_user_state(update),
        )

        return ConversationHandler.END

    return ConversationHandler(
        entry_points=[CommandHandler(Commands.BACKTEST, _ask_begin)],
        states={
            ask_begin_state: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_begin)
            ],
            ask_end_state: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_end)],
            ask_coins_state: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _ask_coins)
            ],
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, _start_backtest)
            ],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
    )
