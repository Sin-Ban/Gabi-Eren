import time
from telethon import events
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters

from FoundingTitanRobot import telethn, application
from FoundingTitanRobot.modules.helper_funcs.chat_status import (
    can_delete,
    user_admin,
)
from FoundingTitanRobot.modules.helper_funcs.telethn.chatstatus import (
    can_delete_messages,
    user_is_admin,
)

import FoundingTitanRobot.modules.sql.purges_sql as sql


# TELETHON: /purge
async def purge_messages(event):
    start = time.perf_counter()

    if (
        not isinstance(event.from_id, int)
        or event.from_id <= 0
        or not event.chat_id
        or (isinstance(event.chat_id, int) and event.chat_id <= 0)
    ):
        return

    if not await user_is_admin(user_id=event.sender_id, message=event) and event.from_id not in [1087968824]:
        await event.reply("Only Admins are allowed to use this command")
        return

    if not await can_delete_messages(message=event):
        await event.reply("Can't seem to purge the message")
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg and len(event.message.text[7:]) == 0:
        await event.reply("Reply to a message to select where to start purging from.")
        return

    messages = []
    delete_to = event.message.id

    if not reply_msg and len(event.message.text[7:]) > 0:
        message_id = delete_to - int(event.message.text[7:])
        messages.append(message_id)
    else:
        message_id = reply_msg.id
        messages.append(event.reply_to_msg_id)

    for msg_id in range(message_id, delete_to + 1):
        messages.append(msg_id)
        if len(messages) == 100:
            await event.client.delete_messages(event.chat_id, messages)
            messages = []
    try:
        await event.client.delete_messages(event.chat_id, messages)
    except:
        pass

    time_ = time.perf_counter() - start
    await event.respond(f"Purged Successfully in {time_:0.2f}s", parse_mode="markdown")


# TELETHON: /del
async def delete_messages(event):
    if (
        not isinstance(event.from_id, int)
        or event.from_id <= 0
        or not event.chat_id
        or (isinstance(event.chat_id, int) and event.chat_id <= 0)
    ):
        return

    if not await user_is_admin(user_id=event.sender_id, message=event) and event.from_id not in [1087968824]:
        await event.reply("Only Admins are allowed to use this command")
        return

    if not await can_delete_messages(message=event):
        await event.reply("Can't seem to delete this")
        return

    message = await event.get_reply_message()
    if not message:
        await event.reply("Whadya want to delete?")
        return
    chat = await event.get_input_chat()
    del_message = [message, event.message]
    await event.client.delete_messages(chat, del_message)


# PTB: /purgefrom
@user_admin
async def purgefrom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    bot = context.bot

    if can_delete(chat, bot.id):

        if msg.reply_to_message:
            message_id = msg.reply_to_message.message_id
            message_from = message_id - 1

            if sql.is_purgefrom(msg.chat_id, message_from):
                await msg.reply_text("The source and target are same, give me a range.")
                return

            sql.purgefrom(msg.chat_id, message_from)
            await msg.reply_to_message.reply_text(
                "Message marked for deletion. Reply to another message with /purgeto to delete all messages in between."
            )

        else:
            await msg.reply_text("Reply to a message to let me know what to delete.")
            return


# TELETHON: /purgeto
async def purgeto_messages(event):
    start = time.perf_counter()

    if (
        not isinstance(event.from_id, int)
        or event.from_id <= 0
        or not event.chat_id
        or (isinstance(event.chat_id, int) and event.chat_id <= 0)
    ):
        return

    if not await user_is_admin(user_id=event.sender_id, message=event) and event.from_id not in [1087968824]:
        await event.reply("Only Admins are allowed to use this command")
        return

    if not await can_delete_messages(message=event):
        await event.reply("Can't seem to purge the message")
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg:
        await event.reply("Reply to a message to select where to start purging from.")
        return

    messages = []
    message_id = None

    x = sql.show_purgefrom(event.chat_id)
    for i in x:
        try:
            message_id = int(i.message_from)
            sql.clear_purgefrom(event.chat_id, message_id)
        except:
            pass

    if message_id is None:
        await event.reply("No starting point found. Use /purgefrom first.")
        return

    messages.append(message_id)
    delete_to = reply_msg.id

    for msg_id in range(message_id, delete_to + 1):
        messages.append(msg_id)
        if len(messages) == 100:
            await event.client.delete_messages(event.chat_id, messages)
            messages = []
    try:
        await event.client.delete_messages(event.chat_id, messages)
    except:
        pass

    time_ = time.perf_counter() - start
    await event.respond(f"Purged Successfully in {time_:0.2f}s", parse_mode="markdown")


# Help text
__help__ = """
*Admins only:*
 • `/del`*:* deletes the message you replied to
 • `/purge`*:* deletes all messages between this and the replied to message.
 • `/purge <number>`*:* deletes that many messages above current message
 • `/purgefrom`*:* mark start of range to delete
 • `/purgeto`*:* delete from marked start to this message
"""

# Telethon Handlers
PURGE_HANDLER = purge_messages, events.NewMessage(pattern=r"^[!/]purge(?!\S+)")
PURGETO_HANDLER = purgeto_messages, events.NewMessage(pattern="^[!/]purgeto$")
DEL_HANDLER = delete_messages, events.NewMessage(pattern="^[!/]del$")

# PTB Handler
PURGEFROM_HANDLER = CommandHandler(
    "purgefrom", purgefrom, filters=filters.ChatType.GROUPS, block=False
)

# Register handlers
application.add_handler(PURGEFROM_HANDLER)
telethn.add_event_handler(*PURGE_HANDLER)
telethn.add_event_handler(*PURGETO_HANDLER)
telethn.add_event_handler(*DEL_HANDLER)

# Module Info
__mod_name__ = "Purges"
__command_list__ = ["del", "purge", "purgefrom", "purgeto"]
__handlers__ = [PURGE_HANDLER, DEL_HANDLER]
