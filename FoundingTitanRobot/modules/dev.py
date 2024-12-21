import os
import subprocess
import sys
import asyncio 

from contextlib import suppress
from time import sleep

import FoundingTitanRobot

from FoundingTitanRobot import application
from FoundingTitanRobot.modules.helper_funcs.chat_status import dev_plus
from telegram import Update
from telegram.error import Forbidden, TelegramError
from telegram.ext import CallbackContext, CommandHandler, ContextTypes

@dev_plus
async def allow_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        state = "off" if FoundingTitanRobot.ALLOW_CHATS else "Lockdown is " + "on"
        await update.effective_message.reply_text(f"Current state: {state}")
        return
    if args[0].lower() in ["off", "no"]:
        FoundingTitanRobot.ALLOW_CHATS = True
    elif args[0].lower() in ["yes", "on"]:
        FoundingTitanRobot.ALLOW_CHATS = False
    else:
        await update.effective_message.reply_text("Format: /lockdown Yes/No or Off/On")
        return
    await update.effective_message.reply_text("Done! Lockdown value toggled.")

@dev_plus
async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    if args := context.args:
        chat_id = str(args[0])
        try:
            await bot.send_message(int(chat_id), text="We have blacklisted this group and eren will leave this group, for appealing join @FoundingTitanSupport")
            await bot.leave_chat(int(chat_id))
        except TelegramError:
            await update.effective_message.reply_text(
                "Beep boop, I could not leave that group(dunno why tho).",
            )
            return
        with suppress(Forbidden):
            await update.effective_message.reply_text("Beep boop, I left that soup!.")
    else:
        await update.effective_message.reply_text("Send a valid chat ID")


@dev_plus
async def gitpull(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sent_msg = await update.effective_message.reply_text(
        "Pulling all changes from remote and then attempting to restart.",
    )
    subprocess.Popen("git pull", stdout=subprocess.PIPE, shell=True)

    sent_msg_text = sent_msg.text + "\n\nChanges pulled...I guess.. Restarting in "

    for i in reversed(range(5)):
        await sent_msg.edit_text(sent_msg_text + str(i + 1))
        sleep(1)

    await sent_msg.edit_text("Restarted.")
    await reboot()


@dev_plus
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
	"Exiting all Processes and starting a new Instance!"
    )
    await reboot()

async def reboot():
    pid = os.getpid()
    # Asynchronously run the subprocess command to kill the current process and restart the script
    process = await asyncio.create_subprocess_shell(
        f"kill {pid} && python3 -m FoundingTitanRobot",
        shell=True
    )

    # Wait for the subprocess to finish
    await process.communicate()

__help__ = """
*DEVELOPERS ONLY:*
• `/leave`*:* Make the bot leave a group.
• `/reboot`*:* Reboots the bot.
• `/gitpull`*:* Pulls latest changes from currently used branch.
• `/lockdown`*:* Disables the ability to add the bot to groups (maybe).
"""

LEAVE_HANDLER = CommandHandler("leave", leave, block=False)
GITPULL_HANDLER = CommandHandler("gitpull", gitpull, block=False)
RESTART_HANDLER = CommandHandler("reboot", restart, block=False)
ALLOWGROUPS_HANDLER = CommandHandler("lockdown", allow_groups, block=False)

application.add_handler(ALLOWGROUPS_HANDLER)
application.add_handler(LEAVE_HANDLER)
application.add_handler(GITPULL_HANDLER)
application.add_handler(RESTART_HANDLER)

__mod_name__ = "Dev"
__handlers__ = [LEAVE_HANDLER, GITPULL_HANDLER, RESTART_HANDLER, ALLOWGROUPS_HANDLER]
