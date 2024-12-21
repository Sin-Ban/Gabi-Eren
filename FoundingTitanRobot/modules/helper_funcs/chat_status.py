from time import perf_counter
from functools import wraps
from cachetools import TTLCache
from threading import RLock
from FoundingTitanRobot import (
    DEL_CMDS,
    ACKERMANS,
    TITANSHIFTERS,
    SUPPORT_CHAT,
    ROYALS,
    SCOUTS,
    GARRISONS,
    application,
)

from telegram import Chat, ChatMember, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

# stores admemes in memory for 10 min.
ADMIN_CACHE = TTLCache(maxsize=512, ttl=60 * 10, timer=perf_counter)
THREAD_LOCK = RLock()


async def is_whitelist_plus(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    return any(user_id in user for user in [GARRISONS, SCOUTS, ROYALS, TITANSHIFTERS, ACKERMANS])


async def is_support_plus(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    return user_id in ROYALS or user_id in TITANSHIFTERS or user_id in ACKERMANS


async def is_sudo_plus(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    return user_id in TITANSHIFTERS or user_id in ACKERMANS


async def is_user_admin(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if (
        chat.type == "private"
        or user_id in TITANSHIFTERS
        or user_id in ACKERMANS
        or user_id == 1087968824
    ):  # Count telegram and Group Anonymous as admin
        return True
    if member:
        return member.status in ("administrator", "owner")
    with THREAD_LOCK:
        # try to fetch from cache first.
        try:
            return user_id in ADMIN_CACHE[chat.id]
        except KeyError:
            # keyerror happend means cache is deleted,
            # so query bot api again and return user status
            # while saving it in cache for future useage...
            chat_admins = await application.bot.getChatAdministrators(chat.id)
            admin_list = [x.user.id for x in chat_admins]
            ADMIN_CACHE[chat.id] = admin_list

            return user_id in admin_list


async def is_bot_admin(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    if chat.type == "private":
        return True

    if not bot_member:
        bot_member = await chat.get_member(bot_id)

    return bot_member.status in ("administrator", "owner")


async def can_delete(chat: Chat, bot_id: int) -> bool:
    member = await chat.get_member(bot_id)
    return member.can_delete_messages


async def is_user_ban_protected(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if (
        chat.type == "private"
        or user_id in TITANSHIFTERS
        or user_id in ACKERMANS
        or user_id in GARRISONS
        or user_id in SCOUTS
        or user_id in {1087968824, 777000}
    ):  # Count telegram and Group Anonymous as ban protected 
        return True

    if not member:
        member = await chat.get_member(user_id)

    return member.status in ("administrator", "owner")


async def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    member = await chat.get_member(user_id)
    return member.status not in ("left", "kicked")


def dev_plus(func):
    @wraps(func)
    async def is_dev_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user

        if user.id in ACKERMANS:
            return await func(update, context, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete()
            except Exception:
                pass
        else:
            await update.effective_message.reply_text(
                "This is a developer restricted command."
                "You do not have permissions to run this.",
            )

    return is_dev_plus_func


def sudo_plus(func):
    @wraps(func)
    async def is_sudo_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and await is_sudo_plus(chat, user.id):
            return await func(update, context, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete()
            except Exception:
                pass
        else:
            await update.effective_message.reply_text(
                "At Least be an Admin to use these all Commands",
            )

    return is_sudo_plus_func


def support_plus(func):
    @wraps(func)
    async def is_support_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and await is_support_plus(chat, user.id):
            return await func(update, context, *args, **kwargs)
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete()
            except Exception:
                pass

    return is_support_plus_func


def whitelist_plus(func):
    @wraps(func)
    async def is_whitelist_plus_func(
        update: Update, context: CallbackContext, *args, **kwargs,
    ):
        bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and await is_whitelist_plus(chat, user.id):
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(
                f"You don't have access to use this.\nVisit @{SUPPORT_CHAT}",
            )

    return is_whitelist_plus_func


def user_admin(func):
    @wraps(func)
    async def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and await is_user_admin(chat, user.id):
            return await func(update, context, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete()
            except Exception:
                pass
        else:
            await update.effective_message.reply_text(
                "At Least be an Admin to use these all Commands",
            )

    return is_admin


def user_admin_no_reply(func):
    @wraps(func)
    async def is_not_admin_no_reply(
            update: Update, context: CallbackContext, *args, **kwargs,
        ):
        bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and await is_user_admin(chat, user.id):
            return await func(update, context, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete()
            except Exception:
                pass

    return is_not_admin_no_reply


def user_not_admin(func):
    @wraps(func)
    async def is_not_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and not await is_user_admin(chat, user.id):
            return await func(update, context, *args, **kwargs)
        elif not user:
            pass

    return is_not_admin


def bot_admin(func):
    @wraps(func)
    async def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            not_admin = "I'm not admin!"
        else:
            not_admin = f"I'm not admin in <b>{update_chat_title}</b>! "

        if await is_bot_admin(chat, bot.id):
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(not_admin, parse_mode=ParseMode.HTML)

    return is_admin


def bot_can_delete(func):
    @wraps(func)
    async def delete_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_delete = "I can't delete messages here!\nMake sure I'm admin and can delete other user's messages."
        else:
            cant_delete = f"I can't delete messages in <b>{update_chat_title}</b>!\nMake sure I'm admin and can delete other user's messages there."

        if await can_delete(chat, bot.id):
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(cant_delete, parse_mode=ParseMode.HTML)

    return delete_rights


def can_pin(func):
    @wraps(func)
    async def pin_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title
        member = await chat.get_member(bot.id)

        if update_chat_title == message_chat_title:
            cant_pin = (
                "I can't pin messages here!\nMake sure I'm admin and can pin messages."
            )
        else:
            cant_pin = f"I can't pin messages in <b>{update_chat_title}</b>!\nMake sure I'm admin and can pin messages there."

        if member.can_pin_messages:
            return func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(cant_pin, parse_mode=ParseMode.HTML)

    return pin_rights


def can_promote(func):
    @wraps(func)
    async def promote_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title
        member = await chat.get_member(bot.id)

        if update_chat_title == message_chat_title:
            cant_promote = "I can't promote/demote people here!\nMake sure I'm admin and can appoint new admins."
        else:
            cant_promote = (
                f"I can't promote/demote people in <b>{update_chat_title}</b>!\n"
                f"Make sure I'm admin there and have the permission to appoint new admins."
            )

        if member.can_promote_members:
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(cant_promote, parse_mode=ParseMode.HTML)

    return promote_rights


def can_restrict(func):
    @wraps(func)
    async def restrict_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title
        member = await chat.get_member(bot.id)

        if update_chat_title == message_chat_title:
            cant_restrict = "I can't restrict people here!\nMake sure I'm admin and can restrict users."
        else:
            cant_restrict = f"I can't restrict people in <b>{update_chat_title}</b>!\nMake sure I'm admin there and can restrict users."

        if member.can_restrict_members:
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(
                cant_restrict, parse_mode=ParseMode.HTML,
            )

    return restrict_rights


def user_can_ban(func):
    @wraps(func)
    async def user_is_banhammer(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user.id
        member = await update.effective_chat.get_member(user)
        
        if (
            member.status == "member" or
            (
                member.status == "administrator" and not member.can_restrict_members and user not in TITANSHIFTERS and user != 1087968824
            )
        ):
            await update.effective_message.reply_text(
                "Sorry son, but you're not worthy to wield the banhammer.",
            )
            return ""
        return await func(update, context, *args, **kwargs)

    return user_is_banhammer


def connection_status(func):
    @wraps(func)
    async def connected_status(update: Update, context: CallbackContext, *args, **kwargs):
        conn = await connected(
            context.bot,
            update,
            update.effective_chat,
            update.effective_user.id,
            need_admin=False,
        )

        if conn:
            chat = await application.bot.getChat(conn)
            await update.__setattr__("_effective_chat", chat)
            return await func(update, context, *args, **kwargs)
        else:
            if update.effective_message.chat.type == "private":
                await update.effective_message.reply_text(
                    "Send /connect in a group that you and I have in common first.",
                )
                return connected_status

            return await func(update, context, *args, **kwargs)

    return connected_status


# Workaround for circular import with connection.py
from FoundingTitanRobot.modules import connection

connected = connection.connected
