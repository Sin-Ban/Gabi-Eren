import os
import datetime

from telethon import events
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, ContextTypes

from FoundingTitanRobot import telethn, application
from FoundingTitanRobot.modules.helper_funcs.chat_status import dev_plus

DEBUG_MODE = False


@dev_plus
async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DEBUG_MODE
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    print(DEBUG_MODE)
    if len(args) > 1:
        if args[1] in ("yes", "on"):
            DEBUG_MODE = True
            await message.reply_text("Debug mode is now on.")
        elif args[1] in ("no", "off"):
            DEBUG_MODE = False
            await message.reply_text("Debug mode is now off.")
    elif DEBUG_MODE:
        await message.reply_text("Debug mode is currently on.")
    else:
        await message.reply_text("Debug mode is currently off.")


@telethn.on(events.NewMessage(pattern="[/!].*"))
async def i_do_nothing_yes(event):
    global DEBUG_MODE
    if DEBUG_MODE:
        print(f"-{event.from_id} ({event.chat_id}) : {event.text}")
        if os.path.exists("updates.txt"):
            with open("updates.txt", "r") as f:
                text = f.read()
            with open("updates.txt", "w+") as f:
                f.write(f"{text}\n-{event.from_id} ({event.chat_id}) : {event.text}")
        else:
            with open("updates.txt", "w+") as f:
                f.write(
                    f"- {event.from_id} ({event.chat_id}) : {event.text} | {datetime.datetime.now()}",
                )


support_chat = os.getenv("SUPPORT_CHAT")


@dev_plus
async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with open("log.txt", "rb") as f:
        await context.bot.send_document(document=f, filename=f.name, chat_id=user.id)


LOG_HANDLER = CommandHandler("logs", logs, block=False)
application.add_handler(LOG_HANDLER)

DEBUG_HANDLER = CommandHandler("debug", debug, block=False)
application.add_handler(DEBUG_HANDLER)

__mod_name__ = "Debug"
__command_list__ = ["debug"]
__handlers__ = [DEBUG_HANDLER]
