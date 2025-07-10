import time
from telethon import events
from FoundingTitanRobot import telethn
from FoundingTitanRobot.modules.helper_funcs.telethn.chatstatus import (
    can_delete_messages,
    user_is_admin,
)


# /purge command: deletes all messages between replied message and this one
async def purge_messages(event):
    start = time.perf_counter()

    # Ignore if sender is None (anonymous or channel post)
    if not event.sender_id:
        return

    # Check if the user is admin or whitelisted
    if not await user_is_admin(user_id=event.sender_id, message=event) and event.sender_id not in [1087968824]:
        await event.reply("Only admins can use this command.")
        return

    # Check if bot can delete messages
    if not await can_delete_messages(message=event):
        await event.reply("I can't delete messages here.")
        return

    # Get replied message
    reply_msg = await event.get_reply_message()
    if not reply_msg:
        await event.reply("Reply to a message to select where to start purging from.")
        return

    start_id = reply_msg.id
    end_id = event.message.id
    chat = await event.get_input_chat()
    messages = []

    # Delete messages in batches of 100
    for msg_id in range(start_id, end_id + 1):
        messages.append(msg_id)
        if len(messages) == 100:
            await event.client.delete_messages(chat, messages)
            messages = []

    # Delete any remaining messages
    try:
        if messages:
            await event.client.delete_messages(chat, messages)
    except Exception:
        pass

    duration = time.perf_counter() - start
    await event.respond(f"✅ Purged successfully in {duration:.2f} second(s)", parse_mode="markdown")


# /del command: deletes the replied message and the command message
async def delete_messages(event):
    if not event.sender_id:
        return

    if not await user_is_admin(user_id=event.sender_id, message=event) and event.sender_id not in [1087968824]:
        await event.reply("Only admins can use this command.")
        return

    if not await can_delete_messages(message=event):
        await event.reply("I can't delete this message.")
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg:
        await event.reply("Reply to a message you want to delete.")
        return

    chat = await event.get_input_chat()
    try:
        await event.client.delete_messages(chat, [reply_msg, event.message])
    except:
        pass


# Telethon command handlers
PURGE_HANDLER = purge_messages, events.NewMessage(pattern="^[!/]purge$")
DEL_HANDLER = delete_messages, events.NewMessage(pattern="^[!/]del$")

telethn.add_event_handler(*PURGE_HANDLER)
telethn.add_event_handler(*DEL_HANDLER)

__mod_name__ = "Purges"
__command_list__ = ["del", "purge"]
__handlers__ = [PURGE_HANDLER, DEL_HANDLER]
