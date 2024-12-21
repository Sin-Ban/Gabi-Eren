import html
import random
import FoundingTitanRobot.modules.truth_and_dare_string as truth_and_dare_string
from FoundingTitanRobot import application
from telegram import Update, Bot
from telegram.constants import ParseMode
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from telegram.ext import CallbackContext, ContextTypes

async def truth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    await update.effective_message.reply_text(random.choice(truth_and_dare_string.TRUTH))

async def dare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    await update.effective_message.reply_text(random.choice(truth_and_dare_string.DARE))

TRUTH_HANDLER = DisableAbleCommandHandler("truth", truth, block=False)
DARE_HANDLER = DisableAbleCommandHandler("dare", dare, block=False)

application.add_handler(TRUTH_HANDLER)
application.add_handler(DARE_HANDLER)
