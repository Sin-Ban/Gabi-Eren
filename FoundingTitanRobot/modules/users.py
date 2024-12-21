from io import BytesIO
from time import sleep

from telegram import Update
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import (
    ContextTypes,
    CallbackContext,
    CommandHandler,
    filters,
    MessageHandler,
)

import FoundingTitanRobot.modules.sql.users_sql as sql
from FoundingTitanRobot import ACKERMANS, LOGGER, OWNER_ID, application
from FoundingTitanRobot.modules.helper_funcs.chat_status import dev_plus, sudo_plus
from FoundingTitanRobot.modules.sql.users_sql import get_all_users
import FoundingTitanRobot.modules.redis.users_redis as redis
from FoundingTitanRobot.modules.helper_funcs.filters import CustomFilters

USERS_GROUP = 4
CHAT_GROUP = 5
DEV_AND_MORE = ACKERMANS.append(int(OWNER_ID))


async def get_user_id(username):
    # ensure valid userid
    if len(username) <= 5:
        return None

    if username.startswith("@"):
        username = username[1:]

    users = sql.get_userid_by_name(username)

    if not users:
        return None

    elif len(users) == 1:
        return users[0].user_id

    else:
        for user_obj in users:
            try:
                userdat = await application.bot.get_chat(user_obj.user_id)
                if userdat.username == username:
                    return userdat.id

            except BadRequest as excp:
                if excp.message != "Chat not found":
                    LOGGER.exception("Error extracting user ID")

    return None


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    to_send = update.effective_message.text.split(None, 1)

    if len(to_send) >= 2:
        to_group = False
        to_user = False
        if to_send[0] == "/broadcastgroups":
            to_group = True
        if to_send[0] == "/broadcastusers":
            to_user = True
        else:
            to_group = to_user = True
        chats = sql.get_all_chats() or []
        users = get_all_users()
        failed = 0
        failed_user = 0
        if to_group:
            for chat in chats:
                try:
                    await context.bot.sendMessage(
                        int(chat.chat_id),
                        to_send[1],
                        parse_mode="MARKDOWN",
                        disable_web_page_preview=True,
                    )
                    sleep(0.1)
                except TelegramError:
                    failed += 1
        if to_user:
            for user in users:
                try:
                    await context.bot.sendMessage(
                        int(user.user_id),
                        to_send[1],
                        parse_mode="MARKDOWN",
                        disable_web_page_preview=True,
                    )
                    sleep(0.1)
                except TelegramError:
                    failed_user += 1
        await update.effective_message.reply_text(
            f"Broadcast complete.\nGroups failed: {failed}.\nUsers failed: {failed_user}.",
        )


async def log_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message

    # Helper function to update user information in SQL and Redis
    async def update_user_data(user):
        try:
            sql.update_user(user.id, user.username, chat.id, chat.title)
        except Exception as error:
            print(f"An Error Occurred! Full Traceback: {error}")

        if not redis.is_added(user.id):
            redis.add_user(user.id)

    # Update sender's information
    await update_user_data(msg.from_user)

    # Update replied-to user's information, if applicable
    if msg.reply_to_message:
        await update_user_data(msg.reply_to_message.from_user)

    # Update forwarded-from user's information, if applicable
    if msg.forward_origin and msg.forward_origin.type == "user":
        await update_user_data(msg.forward_origin.sender_user)
        

@sudo_plus
async def chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_chats = sql.get_all_chats() or []
    chatfile = "List of chats.\n0. Chat name | Chat ID | Members count\n"
    P = 1
    for chat in all_chats:
        try:
            curr_chat = await context.bot.getChat(chat.chat_id)
            bot_member = await curr_chat.get_member(context.bot.id)
            chat_members = await curr_chat.get_member_count()
            chatfile += f"{P}. {chat.chat_name} | {chat.chat_id} | {chat_members}\n"
            P = P + 1
        except Exception:
            pass

    with BytesIO(str.encode(chatfile)) as output:
        output.name = "groups_list.txt"
        await update.effective_message.reply_document(
            document=output,
            filename="groups_list.txt",
            caption="Here be the list of groups in my database.",
        )


async def chat_checker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    chat = update.effective_message.chat
    try:
        member = await chat.get_member(bot.id)
        if member.status == "member":
            await bot.send_message("I'm not an admin here, Unless I'm an admin, you will be not able to use me to my fullest!")
    except BadRequest as e:
        if e.message == "Not enough rights to send text messages to the chat":
            await bot.leaveChat(update.effective_message.chat.id)
        
    except Forbidden:
        pass


def __user_info__(user_id):
    if user_id in [777000, 1087968824]:
        return """╘══「 Groups count: <code>???</code> 」"""
    if user_id == application.bot.id:
        return """╘══「 Groups count: <code>???</code> 」"""
    num_chats = sql.get_user_num_chats(user_id)
    return f"""╘══「 Groups count: <code>{num_chats}</code> 」"""


def __stats__():
    return (
        f"• {sql.num_users()} users, across {sql.num_chats()} chats"
        f"\n• {len(redis.get_all_users())} new users"
    )


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


__help__ = ""  # no help string

BROADCAST_HANDLER = CommandHandler(
    ["broadcastall", "broadcastusers", "broadcastgroups"], broadcast, block=False, filters=CustomFilters.owner_filter
)
USER_HANDLER = MessageHandler(filters.ALL & filters.ChatType.GROUPS, log_user, block=False)
CHAT_CHECKER_HANDLER = MessageHandler(filters.ALL & filters.ChatType.GROUPS, chat_checker, block=False)
CHATLIST_HANDLER = CommandHandler("groups", chats, block=False)

application.add_handler(USER_HANDLER, USERS_GROUP)
application.add_handler(BROADCAST_HANDLER)
application.add_handler(CHATLIST_HANDLER)
application.add_handler(CHAT_CHECKER_HANDLER, CHAT_GROUP)

__mod_name__ = "Users"
__handlers__ = [(USER_HANDLER, USERS_GROUP), BROADCAST_HANDLER, CHATLIST_HANDLER]
