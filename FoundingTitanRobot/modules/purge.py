import time
from telethon import events
from telethon.utils import get_peer_id
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters

from FoundingTitanRobot import telethn, application
from FoundingTitanRobot.modules.helper_funcs.chat_status import can_delete, user_admin
from FoundingTitanRobot.modules.helper_funcs.telethn.chatstatus import can_delete_messages, user_is_admin

import FoundingTitanRobot.modules.sql.purges_sql as sql

# /purge
async def purge_messages(event):
    print(">> /purge triggered")  # debug print
    start = time.perf_counter()

    try:
        user_id = get_peer_id(event.from_id)
        chat_id = get_peer_id(event.chat_id)
        if user_id <= 0 or chat_id <= 0:
            return
    except Exception as e:
        print("Error getting IDs:", e)
        return

    if not await user_is_admin(user_id=user_id, message=event) and user_id not in [1087968824]:
        await event.reply("Only admins can use this command.")
        return

    if not await can_delete_messages(message=event):
        await event.reply("I don't have delete rights here.")
        return

    reply_msg = await event.get_reply_message()
    text_args = event.message.text.split(maxsplit=1)

    messages = []
    delete_to = event.message.id

    if not reply_msg and len(text_args) == 1:
        await event.reply("Reply to a message or use `/purge <number>`.")
        return

    if not reply_msg:
        try:
            count = int(text_args[1])
            message_id = delete_to - count
        except:
            await event.reply("Invalid number.")
            return
    else:
        message_id = reply_msg.id

    for msg_id in range(message_id, delete_to + 1):
        messages.append(msg_id)
        if len(messages) >= 100:
            await event.client.delete_messages(chat_id, messages)
            messages = []

    if messages:
        await event.client.delete_messages(chat_id, messages)

    duration = time.perf_counter() - start
    await event.respond(f"Purged in `{duration:.2f}s`", parse_mode="markdown")


# /del
async def delete_messages(event):
    try:
        user_id = get_peer_id(event.from_id)
        chat_id = get_peer_id(event.chat_id)
        if user_id <= 0 or chat_id <= 0:
            return
    except:
        return

    if not await user_is_admin(user_id=user_id, message=event) and user_id not in [1087968824]:
        await event.reply("Only admins can use this command.")
        return

    if not await can_delete_messages(message=event):
        await event.reply("I can't delete here.")
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

    if await can_delete(chat, bot.id):
        if msg.reply_to_message:
            message_id = msg.reply_to_message.message_id
            message_from = message_id - 1

            if sql.is_purgefrom(msg.chat_id, message_from):
                await msg.reply_text("Start and end points are the same.")
                return

            sql.purgefrom(msg.chat_id, message_from)
            await msg.reply_to_message.reply_text("Start point marked. Now reply to end message with /purgeto.")
        else:
            await msg.reply_text("Reply to a message to mark purge start.")


# /purgeto (telethon)
async def purgeto_messages(event):
    start = time.perf_counter()
    try:
        user_id = get_peer_id(event.from_id)
        chat_id = get_peer_id(event.chat_id)
        if user_id <= 0 or chat_id <= 0:
            return
    except:
        return

    if not await user_is_admin(user_id=user_id, message=event) and user_id not in [1087968824]:
        await event.reply("Only admins can use this command.")
        return

    if not await can_delete_messages(message=event):
        await event.reply("I don't have delete rights.")
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg:
        await event.reply("Reply to a message to mark end of purge.")
        return

    purge_start = sql.show_purgefrom(chat_id)
    if not purge_start:
        await event.reply("Use /purgefrom first.")
        return

    try:
        message_id = int(purge_start[0].message_from)
        sql.clear_purgefrom(chat_id, message_id)
    except:
        await event.reply("Error retrieving purge start.")
        return

    delete_to = reply_msg.id
    messages = list(range(message_id, delete_to + 1))

    for i in range(0, len(messages), 100):
        await event.client.delete_messages(chat_id, messages[i:i + 100])

    duration = time.perf_counter() - start
    await event.respond(f"Purged in `{duration:.2f}s`", parse_mode="markdown")


# -- Help Text --
__help__ = """
*Admins only:*
 • `/del`*:* deletes the replied message
 • `/purge`*:* purges messages from replied to this
 • `/purge <number>`*:* purges that many messages above
 • `/purgefrom`*:* set start of purge
 • `/purgeto`*:* set end of purge and delete in between
"""

# -- Register Handlers --
telethn.add_event_handler(purge_messages, events.NewMessage(pattern=r"^[!/]purge(\s+\d+)?$"))
telethn.add_event_handler(purgeto_messages, events.NewMessage(pattern=r"^[!/]purgeto$"))
telethn.add_event_handler(delete_messages, events.NewMessage(pattern=r"^[!/]del$"))

application.add_handler(CommandHandler("purgefrom", purgefrom, filters=filters.ChatType.GROUPS, block=False))

__mod_name__ = "Purges"
__command_list__ = ["del", "purge", "purgefrom", "purgeto"]
__handlers__ = [
    (purge_messages, events.NewMessage(pattern=r"^[!/]purge(\s+\d+)?$")),
    (purgeto_messages, events.NewMessage(pattern=r"^[!/]purgeto$")),
    (delete_messages, events.NewMessage(pattern=r"^[!/]del$")),
]
