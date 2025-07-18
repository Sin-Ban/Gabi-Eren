import html
from typing import Optional, List

from telegram.constants import ParseMode
from telegram import Message, Chat, User, ChatPermissions
from telegram.error import BadRequest
from telegram.ext import filters, MessageHandler, CommandHandler, ContextTypes
from telegram.helpers import mention_html

from FoundingTitanRobot import application, TITANSHIFTERS
from FoundingTitanRobot.modules.helper_funcs.chat_status import is_user_admin, user_admin
from FoundingTitanRobot.modules.helper_funcs.string_handling import extract_time
from FoundingTitanRobot.modules.log_channel import loggable
from FoundingTitanRobot.modules.sql import antiflood_sql as sql
from FoundingTitanRobot.modules.connection import connected
from FoundingTitanRobot.modules.redis.approvals_redis import is_approved

from FoundingTitanRobot.modules.helper_funcs.alternate import send_message, typing_action

FLOOD_GROUP = 3



@loggable
async def check_flood(update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]    

    if is_approved(chat.id, user.id):
        sql.update_flood(chat.id, None)
        return

    if not user:  # ignore channels
        return ""

    # ignore admins
    if await is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            await chat.ban_member(user.id)
            execstrings = "Banned"
            tag = "BANNED"
        elif getmode == 2:
            await chat.ban_member(user.id)
            await chat.unban_member(user.id)
            execstrings = "Kicked"
            tag = "KICKED"
        elif getmode == 3:
            await context.bot.restrict_chat_member(
                chat.id, user.id, permissions=ChatPermissions(can_send_messages=False)
            )
            execstrings = "Muted"
            tag = "MUTED"
        elif getmode == 4:
            bantime = await extract_time(msg, getvalue)
            await chat.ban_member(user.id, until_date=bantime)
            execstrings = f"Banned for {getvalue}"
            tag = "TBAN"
        elif getmode == 5:
            mutetime = await extract_time(msg, getvalue)
            await context.bot.restrict_chat_member(
                chat.id,
                user.id,
                until_date=mutetime,
                permissions=ChatPermissions(can_send_messages=False),
            )
            execstrings = f"Muted for {getvalue}"
            tag = "TMUTE"
        await send_message(
            update.effective_message,
            f"Wanna Spam?! Sorry it's not your house Man!\n{execstrings}!",
        )

        return f"<b>{html.escape(chat.title)}:</b>\n#{tag}\n<b>User:</b> {mention_html(user.id, user.first_name)}\nFlooded the group."

    except BadRequest:
        await msg.reply_text(
            "I can't restrict people here, give me permissions first! Until then, I'll disable anti-flood."
        )
        sql.set_flood(chat.id, 0)
        return f"<b>{chat.title}:</b>\n#INFO\nDon't have enough permission to restrict users so automatically disabled anti-flood"



@user_admin
@loggable
@typing_action
async def set_flood(update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = context.args

    conn = await connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat_id = conn
        chat_name = (await application.bot.getChat(conn)).title
    else:
        if update.effective_message.chat.type == "private":
            await send_message(
                update.effective_message,
                "This command is meant to use in group not in PM",
            )
            return ""
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if len(args) >= 1:
        val = args[0].lower()
        if val in ["off", "no", "0"]:
            sql.set_flood(chat_id, 0)
            if conn:
                text = await message.reply_text(f"Antiflood has been disabled in {chat_name}.")
            else:
                text = await message.reply_text("Antiflood has been disabled.")
            await send_message(update.effective_message, text, parse_mode="markdown")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat_id, 0)
                if conn:
                    text = await message.reply_text(f"Antiflood has been disabled in {chat_name}.")
                else:
                    text = await message.reply_text("Antiflood has been disabled.")
                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nDisable antiflood.".format(
                        html.escape(chat_name), mention_html(user.id, user.first_name)
                    )
                )

            elif amount < 3:
                await send_message(
                    update.effective_message,
                    "Antiflood must be either 0 (disabled) or number greater than 3!",
                )
                return ""

            else:
                sql.set_flood(chat_id, amount)
                if conn:
                    text = await message.reply_text(
                        "Anti-flood has been set to {} in chat: {}".format(
                            amount, chat_name
                        )
                    )
                else:
                    text = await message.reply_text(
                        "Successfully updated anti-flood limit to {}!".format(amount)
                    )
                await send_message(update.effective_message, text, parse_mode="markdown")
                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nSet antiflood to <code>{}</code>.".format(
                        html.escape(chat_name),
                        mention_html(user.id, user.first_name),
                        amount,
                    )
                )

        else:
            await message.reply_text("Invalid argument please use a number, 'off' or 'no'")
    else:
        await message.reply_text(
            (
                "Use `/setflood number` to enable anti-flood.\nOr use `/setflood off` to disable antiflood!."
            ),
            parse_mode="markdown",
        )
    return ""


@typing_action
async def flood(update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message

    conn = await connected(context.bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = (await application.bot.getChat(conn)).title
    else:
        if update.effective_message.chat.type == "private":
            await send_message(
                update.effective_message,
                "This command is meant to use in group not in PM",
            )
            return
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        text = (
            await msg.reply_text(
                f"I'm not enforcing any flood control in {chat_name}!"
            )
            if conn
            else await msg.reply_text("I'm not enforcing any flood control here!")
        )
    elif conn:
        text = await msg.reply_text(
            f"I'm currently restricting members after {limit} consecutive messages in {chat_name}."
        )
    else:
        text = await msg.reply_text(
            f"I'm currently restricting members after {limit} consecutive messages."
        )
    await send_message(update.effective_message, text, parse_mode="markdown")



@user_admin
@loggable
@typing_action
async def set_flood_mode(update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args

    conn = await connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = await application.bot.getChat(conn)
        chat_id = conn
        chat_name = (await application.bot.getChat(conn)).title
    else:
        if update.effective_message.chat.type == "private":
            await send_message(
                update.effective_message,
                "This command is meant to use in group not in PM",
            )
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].lower() == "ban":
            settypeflood = "ban"
            sql.set_flood_strength(chat_id, 1, "0")
        elif args[0].lower() == "kick":
            settypeflood = "kick"
            sql.set_flood_strength(chat_id, 2, "0")
        elif args[0].lower() == "mute":
            settypeflood = "mute"
            sql.set_flood_strength(chat_id, 3, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1:
                teks = """It looks like you tried to set time value for antiflood but you didn't specified time; Try, `/setfloodmode tban <timevalue>`.
Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                await send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = f"tban for {args[1]}"
            sql.set_flood_strength(chat_id, 4, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1:
                teks = """It looks like you tried to set time value for antiflood but you didn't specified time; Try, `/setfloodmode tmute <timevalue>`.
Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                await send_message(update.effective_message, teks, parse_mode="markdown")
                return
            settypeflood = f"tmute for {args[1]}"
            sql.set_flood_strength(chat_id, 5, str(args[1]))
        else:
            await send_message(
                update.effective_message, "I only understand ban/kick/mute/tban/tmute!"
            )
            return
        if conn:
            text = await msg.reply_text(
                "Exceeding consecutive flood limit will result in {} in {}!".format(
                    settypeflood, chat_name
                )
            )
        else:
            text = await msg.reply_text(
                "Exceeding consecutive flood limit will result in {}!".format(
                    settypeflood
                )
            )
        await send_message(update.effective_message, text, parse_mode="markdown")
        return (
            "<b>{}:</b>\n"
            "<b>Admin:</b> {}\n"
            "Has changed antiflood mode. User will {}.".format(
                settypeflood,
                html.escape(chat.title),
                mention_html(user.id, user.first_name),
            )
        )
    else:
        getmode, getvalue = sql.get_flood_setting(chat.id)
        if getmode == 1:
            settypeflood = "ban"
        elif getmode == 2:
            settypeflood = "kick"
        elif getmode == 3:
            settypeflood = "mute"
        elif getmode == 4:
            settypeflood = "tban for {}".format(getvalue)
        elif getmode == 5:
            settypeflood = "tmute for {}".format(getvalue)
        if conn:
            text = await msg.reply_text(
                "Sending more messages than flood limit will result in {} in {}.".format(
                    settypeflood, chat_name
                )
            )
        else:
            text = await msg.reply_text(
                "Sending more message than flood limit will result in {}.".format(
                    settypeflood
                )
            )
        await send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "Not enforcing to flood control."
    else:
        return f"Antiflood has been set to`{limit}`."


__help__ = """
You know how sometimes, people join, send 100 messages, and ruin your chat? With antiflood, that happens no more!
Antiflood allows you to take action on users that send more than x messages in a row. Exceeding the set flood \
will result in restricting that user.
 - /flood: Get the current flood control setting
*Admin only*:
 - /setflood <int/'no'/'off'>: enables or disables flood control
 - /setfloodmode <ban/kick/mute/tban/tmute> <value>: Action to perform when user have exceeded flood limit. ban/kick/mute/tmute/tban
 Note:
 - Value must be filled for tban and tmute!
 It can be:
 5m = 5 minutes
 6h = 6 hours
 3d = 3 days
 1w = 1 week
 """

__mod_name__ = "Anti-Flood"

FLOOD_BAN_HANDLER = MessageHandler(
    filters.ALL & filters.StatusUpdate.ALL & filters.ChatType.GROUPS, check_flood, block=False
)
SET_FLOOD_HANDLER = CommandHandler(
    "setflood", set_flood, block=False
)  # , filters=filters.ChatType.GROUPS)
SET_FLOOD_MODE_HANDLER = CommandHandler(
    "setfloodmode", set_flood_mode, block=False
)  # , filters=filters.ChatType.GROUPS)
FLOOD_HANDLER = CommandHandler("flood", flood, block=False)  # , filters=filters.ChatType.GROUPS)

application.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
application.add_handler(SET_FLOOD_HANDLER)
application.add_handler(SET_FLOOD_MODE_HANDLER)
application.add_handler(FLOOD_HANDLER)
