import time
from telethon import events
from telethon.utils import get_peer_id
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


# /purge (telethon)
async def purge_messages(event):
    start = time.perf_counter()
    try:
        user_id = get_peer_id(event.from_id)
        chat_id = get_peer_id(event.chat_id)
        if user_id <= 0 or chat_id <= 0:
            return
    except Exception:
        return

    if not await user_is_admin(user_id=user_id, message=event) and user_id not in [1087968824]:
        await event.reply("Only Admins are allowed to use this command")
        return

    if not await can_delete_messages(message=event):
        await event.reply("Can't seem to purge the message")
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg and len(event.message.text[7:]) == 0:
        await event.reply("Reply to a message or provide number of messages.")
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
            await event.client.delete_messages(chat_id, messages)
            messages = []
    try:
        await event.client.delete_messages(chat_id, messages)
    except:
        pass

    duration = time.perf_counter() - start
    await event.respond(f"Purged Successfully in {duration:0.2f}s", parse_mode="markdown")


# /del (telethon)
async def delete_messages(event):
    try:
        user_id = get_peer_id(event.from_id)
        chat_id = get_peer_id(event.chat_id)
        if user_id <= 0 or chat_id <= 0:
            return
    except Exception:
        return

    if not await user_is_admin(user_id=user_id, message=event) and user_id not in [1087968824]:
        await event.reply("Only Admins are allowed to use this command")
        return

    if not await can_delete_messages(message=event):
        await event.reply("Can't delete this message.")
        return

    msg = await event.get_reply_message()
    if not msg:
        await event.reply("Reply to a message to delete it.")
        return

    await event.client.delete_messages(chat_id, [msg.id, event.message.id])


# /purgefrom (PTB)
@user_admin
async def purgefrom(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                "Marked. Now reply to another message with /purgeto to delete in between."
            )
        else:
            await msg.reply_text("Reply to a message to mark purge start.")
    return


# /purgeto (telethon)
async def purgeto_messages(event):
    start = time.perf_counter()
    try:
        user_id = get_peer_id(event.from_id)
        chat_id = get_peer_id(event.chat_id)
        if user_id <= 0 or chat_id <= 0:
            return
    except Exception:
        return

    if not await user_is_admin(user_id=user_id, message=event) and user_id not in [1087968824]:
        await event.reply("Only Admins are allowed to use this command")
        return

    if not await can_delete_messages(message=event):
        await event.reply("Can't purge these messages.")
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg:
        await event.reply("Reply to a message to select where to purge up to.")
        return

    purge_start = sql.show_purgefrom(chat_id)
    if not purge_start:
        await event.reply("No start point set. Use /purgefrom first.")
        return

    try:
        message_id = int(purge_start[0].message_from)
        sql.clear_purgefrom(chat_id, message_id)
    except:
        await event.reply("Failed to retrieve purge start point.")
        return

    messages = []
    delete_to = reply_msg.id
    for msg_id in range(message_id, delete_to + 1):
        messages.append(msg_id)
        if len(messages) == 100:
            await event.client.delete_messages(chat_id, messages)
            messages = []
    try:
        await event.client.delete_messages(chat_id, messages)
    except:
        pass

    duration = time.perf_counter() - start
    await event.respond(f"Purged Successfully in {duration:0.2f}s", parse_mode="markdown")


# Help text
__help__ = """
*Admins only:*
 • `/del`*:* deletes the replied message
 • `/purge`*:* purges messages from replied to this
 • `/purge <number>`*:* purges that many messages up
 • `/purgefrom`*:* set start of purge
 • `/purgeto`*:* set end of purge and delete in between
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

__mod_name__ = "Purges"
__command_list__ = ["del", "purge", "purgefrom", "purgeto"]
__handlers__ = [PURGE_HANDLER, DEL_HANDLER]
