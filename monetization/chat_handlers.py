from telegram import Update
from telegram.ext import ContextTypes
import os


async def handle_donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = os.getenv("LIGHTNING_ADDRESS", "")
    if not address:
        await update.message.reply_text(
            "Author is dumb enough to not have set a donation address. Will come soon!"
        )

    await update.message.reply_text(
        f"""
        If you want to support the effort of this project and empower me to dedicate more time to it, you can invite me a coffee with sats.mobi.
        This is the address: {address}
        Thank you very much!
        """
    )
