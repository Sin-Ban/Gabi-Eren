import html
import re
from typing import Optional

from FoundingTitanRobot import LOGGER, SCOUTS, application
from FoundingTitanRobot.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    connection_status,
    is_user_admin,
    user_admin,
    user_admin_no_reply,
)
from FoundingTitanRobot.modules.helper_funcs.extraction import (
    extract_user,
    extract_user_and_text,
)
from FoundingTitanRobot.modules.helper_funcs.string_handling import extract_time
from FoundingTitanRobot.modules.log_channel import loggable
from FoundingTitanRobot.modules.redis.approvals_redis import is_approved
from telegram import (
    Bot, 
    Chat, 
    ChatPermissions,
    Update, 
    User, 
    CallbackQuery,
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.helpers import mention_html
from telegram.constants import ParseMode


async def check_user(user_id: int, bot: Bot, chat: Chat) -> Optional[str]:
    
    if not user_id:
        return "You don't seem to be referring to a user or the ID specified is incorrect.."
    if is_approved(chat.id, user_id):
        return "This is user is approved in this chat and approved users can't be muted!"
    try:
        member = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            return "I can't seem to find this user"
        else:
            raise

    if user_id == bot.id:
        return "I'm not gonna MUTE myself, How high are you?"
    if await is_user_admin(chat, user_id, member) or user_id in SCOUTS:
        return "Can't. Find someone else to mute but not this one."
    return None


@connection_status
@bot_admin
@user_admin
@loggable
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id, reason = await extract_user_and_text(message, args)
    if reply := await check_user(user_id, bot, chat):
        await message.reply_text(reply)
        return ""


    member = await chat.get_member(user_id)

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#MUTE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
    )

    if reason:
        log += f"\n<b>Reason:</b> {reason}"

    if member.can_send_messages is None or member.can_send_messages:
        chat_permissions = ChatPermissions(can_send_messages=False)
        await bot.restrict_chat_member(chat.id, user_id, chat_permissions)
        msg = (
            f"<code>🗣️</code><b>Mute Event</b>\n"
            f"<code> </code><b>• Muted User:</b> {mention_html(member.user.id, member.user.first_name)}"
            )
        if reason:
            msg += f"\n<code> </code><b>• Reason:</b> \n{html.escape(reason)}"

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Unmute", callback_data=f"unmute_({member.user.id})"
                    )
                ]
            ]
        )
        await bot.sendMessage(
            chat.id,
            msg,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
        return log
    else:
        await message.reply_text("This user is already muted!")

    return ""
            	
            	         
@connection_status
@bot_admin
@user_admin
@loggable
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id = await extract_user(message, args)
    if not user_id:
        await message.reply_text(
            "You'll need to either give me a username to unmute, or reply to someone to be unmuted.",
        )
        return ""

    member = await chat.get_member(int(user_id))

    if member.status in ["kicked", "left"]:
        await message.reply_text(
            "This user isn't even in the chat, unmuting them won't make them talk more than they "
            "already do!",
        )

    elif (
            member.can_send_messages
            and member.can_send_media_messages
            and member.can_send_other_messages
            and member.can_add_web_page_previews
        ):
        await message.reply_text("This user already has the right to speak.")
    else:
        chat_permissions = ChatPermissions(
            can_send_messages=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_send_polls=True,
            can_change_info=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        )
        try:
            await bot.restrict_chat_member(chat.id, int(user_id), chat_permissions)
        except BadRequest:
            pass
        await bot.sendMessage(
            chat.id,
            f"I shall allow <b>{html.escape(member.user.first_name)}</b> to text!",
            parse_mode=ParseMode.HTML,
        )
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#UNMUTE\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
        )
    return ""


@connection_status
@bot_admin
@can_restrict
@user_admin
@loggable
async def temp_mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id, reason = await extract_user_and_text(message, args)
    if reply := await check_user(user_id, bot, chat):
        await message.reply_text(reply)
        return ""

    member = await chat.get_member(user_id)

    if not reason:
        await message.reply_text("You haven't specified a time to mute this user for!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    reason = split_reason[1] if len(split_reason) > 1 else ""
    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#TEMP MUTED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}\n"
        f"<b>Time:</b> {time_val}"
    )
    if reason:
        log += f"\n<b>Reason:</b> {reason}"

    try:
        if member.can_send_messages is None or member.can_send_messages:
            chat_permissions = ChatPermissions(can_send_messages=False)
            await bot.restrict_chat_member(
                chat.id, user_id, chat_permissions, until_date=mutetime,
            )
            msg = (
                f"<code>🗣️</code><b>Time Mute Event</b>\n"
                f"<code> </code><b>• Muted User:</b> {mention_html(member.user.id, member.user.first_name)}\n"
                f"<code> </code><b>• User will be Muted for:</b> {time_val}\n"
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Unmute",
                            callback_data=f"unmute_({member.user.id})",
                        )
                    ]
                ]
            )
            await bot.sendMessage(chat.id, msg, reply_markup=keyboard, parse_mode=ParseMode.HTML)

            return log
        else:
            await message.reply_text("This user is already muted.")

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            await message.reply_text(f"Muted for {time_val}!", quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception(
                "ERROR muting user %s in chat %s (%s) due to %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            await message.reply_text("Well damn, I can't mute that user.")

    return ""

@user_admin_no_reply
@bot_admin
@loggable
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    bot: Optional[Bot] = context.bot
    if match := re.match(r"unmute_\((.+?)\)", query.data):
        user_id = match[1]
        chat: Optional[Chat] = update.effective_chat
        member = await chat.get_member(user_id)
        chat_permissions = ChatPermissions (
                can_send_messages=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_send_polls=True,
                can_change_info=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
        )
        unmuted = await bot.restrict_chat_member(chat.id, int(user_id), chat_permissions)
        if unmuted:
        	await update.effective_message.edit_text(
        	    f"Admin {mention_html(user.id, user.first_name)} Unmuted {mention_html(member.user.id, member.user.first_name)}!",
        	    parse_mode=ParseMode.HTML,
        	)
        	query.answer("Unmuted!")
        	return (
                    f"<b>{html.escape(chat.title)}:</b>\n" 
                    f"#UNMUTE\n" 
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
                )
    else:
        await update.effective_message.edit_text(
            "This user is not muted or has left the group!"
        )
        return ""
            

MUTE_HANDLER = CommandHandler("mute", mute, block=False)
UNMUTE_HANDLER = CommandHandler("unmute", unmute, block=False)
TEMPMUTE_HANDLER = CommandHandler(["tmute", "tempmute"], temp_mute, block=False)
UNMUTE_BUTTON_HANDLER = CallbackQueryHandler(button, pattern=r"unmute_")

application.add_handler(MUTE_HANDLER)
application.add_handler(UNMUTE_HANDLER)
application.add_handler(TEMPMUTE_HANDLER)
application.add_handler(UNMUTE_BUTTON_HANDLER)

__mod_name__ = "Muting"
__handlers__ = [MUTE_HANDLER, UNMUTE_HANDLER, TEMPMUTE_HANDLER]
