import html

from FoundingTitanRobot import ALLOW_EXCL, CustomCommandHandler, application
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from FoundingTitanRobot.modules.helper_funcs.chat_status import (
    bot_can_delete,
    connection_status,
    dev_plus,
    user_admin,
)

from FoundingTitanRobot.modules.sql import cleaner_sql as sql
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
    CallbackContext,
    CommandHandler,
    filters,
    MessageHandler,
)

CMD_STARTERS = ("/", "!") if ALLOW_EXCL else "/"
BLUE_TEXT_CLEAN_GROUP = 13
CommandHandlerList = (CommandHandler, CustomCommandHandler, DisableAbleCommandHandler)
command_list = [
    "cleanblue",
    "ignoreblue",
    "unignoreblue",
    "listblue",
    "ungignoreblue",
    "gignoreblue" "start",
    "help",
    "settings",
    "donate",
    "stalk",
    "aka",
    "leaderboard",
]

for handler_list in application.handlers:
    for handler in application.handlers[handler_list]:
        if any(isinstance(handler, cmd_handler) for cmd_handler in CommandHandlerList):
            command_list += handler.commands


async def clean_blue_text_must_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    chat = update.effective_chat
    message = update.effective_message
    member = await chat.get_member(bot.id)
    if member.can_delete_messages and sql.is_enabled(chat.id):
        fst_word = message.text.strip().split(None, 1)[0]
    
        if len(fst_word) > 1 and any(
            fst_word.startswith(start) for start in CMD_STARTERS
        ):
    
            command = fst_word[1:].split("@")
            chat = update.effective_chat
    
            if ignored := sql.is_command_ignored(chat.id, command[0]):
                return
    
            if command[0] not in command_list:
                await message.delete()


@connection_status
@bot_can_delete
@user_admin
async def set_blue_text_must_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    bot, args = context.bot, context.args
    if len(args) >= 1:
        val = args[0].lower()
        if val in ("off", "no"):
            sql.set_cleanbt(chat.id, False)
            reply = f"Bluetext cleaning has been disabled for <b>{html.escape(chat.title)}</b>"
            await message.reply_text(reply, parse_mode=ParseMode.HTML)

        elif val in ("yes", "on"):
            sql.set_cleanbt(chat.id, True)
            reply = f"Bluetext cleaning has been enabled for <b>{html.escape(chat.title)}</b>"
            await message.reply_text(reply, parse_mode=ParseMode.HTML)

        else:
            reply = "Invalid argument.Accepted values are 'yes', 'on', 'no', 'off'"
            await message.reply_text(reply)
    else:
        clean_status = sql.is_enabled(chat.id)
        clean_status = "Enabled" if clean_status else "Disabled"
        reply = f"Bluetext cleaning for <b>{chat.title}</b> : <b>{clean_status}</b>"
        await message.reply_text(reply, parse_mode=ParseMode.HTML)


@user_admin
async def add_bluetext_ignore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    args = context.args
    if len(args) >= 1:
        val = args[0].lower()
        if added := sql.chat_ignore_command(chat.id, val):
            reply = f"<b>{args[0]}</b> has been added to bluetext cleaner ignore list."
        else:
            reply = "Command is already ignored."
        await message.reply_text(reply, parse_mode=ParseMode.HTML)

    else:
        reply = "No command supplied to be ignored."
        await message.reply_text(reply)


@user_admin
async def remove_bluetext_ignore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    args = context.args
    if len(args) >= 1:
        val = args[0].lower()
        if removed := sql.chat_unignore_command(chat.id, val):
            reply = f"<b>{args[0]}</b> has been removed from bluetext cleaner ignore list."
        else:
            reply = "Command isn't ignored currently."
        await message.reply_text(reply, parse_mode=ParseMode.HTML)

    else:
        reply = "No command supplied to be unignored."
        await message.reply_text(reply)

@dev_plus
@user_admin
async def add_bluetext_ignore_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    args = context.args
    if len(args) >= 1:
        val = args[0].lower()
        if added := sql.global_ignore_command(val):
            reply = f"<b>{args[0]}</b> has been added to global bluetext cleaner ignore list."
        else:
            reply = "Command is already ignored."
        await message.reply_text(reply, parse_mode=ParseMode.HTML)

    else:
        reply = "No command supplied to be ignored."
        await message.reply_text(reply)


@dev_plus
async def remove_bluetext_ignore_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    args = context.args
    if len(args) >= 1:
        val = args[0].lower()
        if removed := sql.global_unignore_command(val):
            reply = f"<b>{args[0]}</b> has been removed from global bluetext cleaner ignore list."
        else:
            reply = "Command isn't ignored currently."
        await message.reply_text(reply, parse_mode=ParseMode.HTML)

    else:
        reply = "No command supplied to be unignored."
        await message.reply_text(reply)


@dev_plus
async def bluetext_ignore_list(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message
    chat = update.effective_chat

    global_ignored_list, local_ignore_list = sql.get_all_ignored(chat.id)
    text = ""

    if global_ignored_list:
        text = "The following commands are currently ignored globally from bluetext cleaning :\n"

        for x in global_ignored_list:
            text += f" - <code>{x}</code>\n"

    if local_ignore_list:
        text += "\nThe following commands are currently ignored locally from bluetext cleaning :\n"

        for x in local_ignore_list:
            text += f" - <code>{x}</code>\n"

    if text == "":
        text = "No commands are currently ignored from bluetext cleaning."
        await message.reply_text(text)
        return

    await message.reply_text(text, parse_mode=ParseMode.HTML)
    return


SET_CLEAN_BLUE_TEXT_HANDLER = CommandHandler("cleanblue", set_blue_text_must_click, block=False)
ADD_CLEAN_BLUE_TEXT_HANDLER = CommandHandler("ignoreblue", add_bluetext_ignore, block=False)
REMOVE_CLEAN_BLUE_TEXT_HANDLER = CommandHandler("unignoreblue", remove_bluetext_ignore, block=False)
ADD_CLEAN_BLUE_TEXT_GLOBAL_HANDLER = CommandHandler("gignoreblue", add_bluetext_ignore_global, block=False)
REMOVE_CLEAN_BLUE_TEXT_GLOBAL_HANDLER = CommandHandler("ungignoreblue", remove_bluetext_ignore_global, block=False)
LIST_CLEAN_BLUE_TEXT_HANDLER = CommandHandler("listblue", bluetext_ignore_list, block=False)
CLEAN_BLUE_TEXT_HANDLER = MessageHandler(filters.COMMAND & filters.ChatType.GROUPS, clean_blue_text_must_click, block=False)

application.add_handler(SET_CLEAN_BLUE_TEXT_HANDLER)
application.add_handler(ADD_CLEAN_BLUE_TEXT_HANDLER)
application.add_handler(REMOVE_CLEAN_BLUE_TEXT_HANDLER)
application.add_handler(ADD_CLEAN_BLUE_TEXT_GLOBAL_HANDLER)
application.add_handler(REMOVE_CLEAN_BLUE_TEXT_GLOBAL_HANDLER)
application.add_handler(LIST_CLEAN_BLUE_TEXT_HANDLER)
application.add_handler(CLEAN_BLUE_TEXT_HANDLER, BLUE_TEXT_CLEAN_GROUP)

__mod_name__ = "Cleaning"
__handlers__ = [
    SET_CLEAN_BLUE_TEXT_HANDLER,
    ADD_CLEAN_BLUE_TEXT_HANDLER,
    REMOVE_CLEAN_BLUE_TEXT_HANDLER,
    ADD_CLEAN_BLUE_TEXT_GLOBAL_HANDLER,
    REMOVE_CLEAN_BLUE_TEXT_GLOBAL_HANDLER,
    LIST_CLEAN_BLUE_TEXT_HANDLER,
    (CLEAN_BLUE_TEXT_HANDLER, BLUE_TEXT_CLEAN_GROUP),
]

__help__ = """
Blue text cleaner removed any made up commands that people send in your chat.
 • `/cleanblue <on/off/yes/no>`*:* clean commands after sending
 • `/ignoreblue <word>`*:* prevent auto cleaning of the command
 • `/unignoreblue <word>`*:* remove prevent auto cleaning of the command
 • `/listblue`*:* list currently whitelisted commands
 *Following are Disasters only commands, admins cannot use these:*
 • `/gignoreblue <word>`*:* globally ignorea bluetext cleaning of saved word across Eren.
 • `/ungignoreblue <word>`*:* remove said command from global cleaning list
"""
