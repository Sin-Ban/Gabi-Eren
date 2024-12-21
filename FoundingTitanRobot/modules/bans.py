import html
import re
from typing import Optional

from telegram.constants import ParseMode
from telegram import (
    Chat,
    Update,
    User,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.helpers import mention_html

from FoundingTitanRobot import (
    ACKERMANS,
    LOGGER,
    OWNER_ID,
    TITANSHIFTERS,
    ROYALS,
    SCOUTS,
    GARRISONS,
    application,
)
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from FoundingTitanRobot.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    connection_status,
    is_user_admin,
    is_user_ban_protected,
    is_user_in_chat,
    user_admin,
    user_can_ban,
    can_delete,
    user_admin_no_reply,
)
from FoundingTitanRobot.modules.helper_funcs.extraction import extract_user_and_text
from FoundingTitanRobot.modules.helper_funcs.string_handling import extract_time
from FoundingTitanRobot.modules.log_channel import gloggable, loggable
from FoundingTitanRobot.modules.redis.approvals_redis import is_approved

@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot = context.bot
    args = context.args
    user_id, reason = await extract_user_and_text(message, args)
    if message.reply_to_message and message.reply_to_message.sender_chat:
        bam = await bot.ban_chat_sender_chat(chat_id=chat.id, sender_chat_id=message.reply_to_message.sender_chat.id)
        if bam:
            channel = await bot.get_chat(message.reply_to_message.sender_chat.id)
            reply = (
                f"<b>Ban Event</b>\n"
                f"<b>• Channel:</b> <b> @{channel['username']}</b>"
            )
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Unban",
                            callback_data=f"unban_({message.reply_to_message.sender_chat.id})",
                        )
                    ]
                ]
            )
            if reason:
                reply += f"\n<b>• Reason:</b> \n{html.escape(reason)}"
            await bot.sendMessage(chat.id, reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            return f"<b>{html.escape(chat.title)}:</b>\n#BANNED_CHANNEL\n<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n<b>Channel:</b> <b>@{channel['username']}</b>"
    if not user_id:
        await message.reply_text("I doubt that's a user.")
        return log_message
    try:
        member = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "User not found":
            raise
        await message.reply_text("Can't seem to find this person.")
        return log_message

    if user_id == bot.id:
        await message.reply_text("Oh yeah, ban myself, noob!")
        return log_message

    if is_approved(chat.id, user_id):
        await message.reply_text("This user is approved in this chat and Approved users cant be banned!")
        return log_message

    if await is_user_ban_protected(chat, user_id, member) and user not in ACKERMANS:
        if user_id == OWNER_ID:
            await message.reply_text("Trying to put me against the Founding Titan huh?")
        elif user_id in ACKERMANS:
            await message.reply_text("I can't act against our own.")
        elif user_id in TITANSHIFTERS:
            await message.reply_text(
                "Fighting this Titan Shifter here will put civilian lives at risk.",
            )
        elif user_id in ROYALS:
            await message.reply_text(
                "Bring an order from The Ackermans to fight a Royal Blood.",
            )
        elif user_id in SCOUTS:
            await message.reply_text(
                "Bring an order from Ackermans to fight a Scout.",
            )
        elif user_id in GARRISONS:
            await message.reply_text("Garrison abilities make them ban immune!")
        else:
            await message.reply_text("This user has immunity and cannot be banned.")
        return log_message
    if message.text.startswith("/s"):
        silent = True
        if not await can_delete(chat, context.bot.id):
            return ""
    else:
        silent = False
    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#{'S' if silent else ''}BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )
    if reason:
        log += f"\n<b>Reason:</b> {reason}"

    try:
        await chat.ban_member(user_id)

        if silent:
            if message.reply_to_message:
                await message.reply_to_message.delete()
            await message.delete()
            return log

        # await bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        reply = (
            f"<code>❕</code><b>Ban Event</b>\n"
            f"<code> </code><b>•  User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
        )
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Unban", callback_data=f"unban_({member.user.id})"
                    )
                ]
            ]
        )
        if reason:
            reply += f"\n<code> </code><b>•  Reason:</b> \n{html.escape(reason)}"
        await bot.sendMessage(chat.id, reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            if silent:
                return log
            await message.reply_text("Banned!", quote=False)
            return log
        LOGGER.warning(update)
        LOGGER.exception(
            "ERROR banning user %s in chat %s (%s) due to %s",
            user_id,
            chat.title,
            chat.id,
            excp.message,
        )
        await message.reply_text("Uhm...that didn't work...")

    return log_message


@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
async def temp_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = await extract_user_and_text(message, args)
    if message.reply_to_message and message.reply_to_message.sender_chat:
        await message.reply_text("Channels cant be temporarily banned!")
    if not user_id:
        await message.reply_text("I doubt that's a user.")
        return log_message

    try:
        member = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "User not found":
            raise
        await message.reply_text("I can't seem to find this user.")
        return log_message
    if user_id == bot.id:
        await message.reply_text("I'm not gonna BAN myself, are you crazy?")
        return log_message

    if await is_user_ban_protected(chat, user_id, member):
        await message.reply_text("I don't feel like it.")
        return log_message

    if is_approved(chat.id, user_id):
        await message.reply_text("This user is approved in this chat and Approved users cant be banned!")
        return log_message

    if not reason:
        await message.reply_text("You haven't specified a time to ban this user for!")
        return log_message

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    reason = split_reason[1] if len(split_reason) > 1 else ""
    bantime = extract_time(message, time_val)

    if not bantime:
        return log_message

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        "#TEMP BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}\n"
        f"<b>Time:</b> {time_val}"
    )
    msg = (
        f"<code>❗</code><b>Temp Ban Event</b>\n"
        f"<code> </code><b>• Banned User:</b> {mention_html(member.user.id, member.user.first_name)}\n"
        f"<code> </code><b>• User will be Banned for </b> {time_val}\n"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Unban", callback_data=f"unban_({member.user.id})"
                )
            ]
        ]
    )
    if reason:
        log += f"\n<b>Reason:</b> {reason}"

    try:
        await chat.ban_member(user_id, until_date=bantime)
        # await bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        await bot.sendMessage(
            chat.id,
            msg,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            await bot.send_message(
                chat.id,
                msg,
                reply_markup=keyboard,
                quote=False,
            )
            return log
        LOGGER.warning(update)
        LOGGER.exception(
            "ERROR banning user %s in chat %s (%s) due to %s",
            user_id,
            chat.title,
            chat.id,
            excp.message,
        )
        await message.reply_text("Well damn, I can't ban that user.")

    return log_message

@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = await extract_user_and_text(message, args)

    if not user_id:
        await message.reply_text("I doubt that's a user.")
        return log_message

    try:
        member = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "User not found":
            raise

        await message.reply_text("I can't seem to find this user.")
        return log_message

    if is_approved(chat.id, user_id):
        await message.reply_text("This user is approved in this chat and Approved users cant be banned!")
        return log_message

    if user_id == bot.id:
        await message.reply_text("Yeahhh I'm not gonna do that.")
        return log_message

    if await is_user_ban_protected(chat, user_id):
        await message.reply_text("I really wish I could kick this user....")
        return log_message


    if res := await chat.unban_member(user_id):
        # await bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        await bot.sendMessage(
            chat.id,
            f"kicked! {mention_html(member.user.id, html.escape(member.user.first_name))}.",
            parse_mode=ParseMode.HTML,
        )
        log = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#KICKED\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
        )
        if reason:
            log += f"\n<b>Reason:</b> {reason}"

        return log

    else:
        await message.reply_text("Well damn, I can't kick that user.")

    return log_message



@bot_admin
@can_restrict
async def kickme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_message.from_user.id
    if await is_user_admin(update.effective_chat, user_id):
        await update.effective_message.reply_text("I wish I could... but you're an admin.")
        return

    res = await update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        await update.effective_message.reply_text("*Kicks you out of the group*")
    else:
        await update.effective_message.reply_text("Huh? I can't :/")



@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = await extract_user_and_text(message, args)
    if message.reply_to_message and message.reply_to_message.sender_chat:
        unbam = await bot.unban_chat_sender_chat(chat_id=chat.id, sender_chat_id=message.reply_to_message.sender_chat.id)
        if unbam:
            channel = await bot.get_chat(message.reply_to_message.sender_chat.id)
            log = (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#UNBANNED_CHANNEL\n"
                f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
                f"<b>Channel:</b> <b>@{channel['username']}</b>"
            )
            await message.reply_text("Yep, they can join back again!")
            return log
    if not user_id:
        await message.reply_text("I doubt that's a user.")
        return log_message

    try:
        member = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "User not found":
            raise
        await message.reply_text("I can't seem to find this user.")

        return log_message
    if user_id == bot.id:
        await message.reply_text("How would I unban myself if I wasn't here...?")
        return log_message

    if is_user_in_chat(chat, user_id):
        await message.reply_text("Isn't this person already here??")
        return log_message

    await chat.unban_member(user_id)
    await message.reply_text("Yep, they can join back again!")
    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )
    if reason:
        log += f"\n<b>Reason:</b> {reason}"

    return log



@connection_status
@bot_admin
@can_restrict
@gloggable
async def selfunban(context: CallbackContext, update: Update) -> str:
    message = update.effective_message
    user = update.effective_user
    bot, args = context.bot, context.args
    if user.id not in TITANSHIFTERS or user.id not in SCOUTS:
        return

    try:
        chat_id = int(args[0])
    except Exception:
        await message.reply_text("Give a valid chat ID.")
        return

    chat = await bot.getChat(chat_id)

    try:
        member = await chat.get_member(user.id)
    except BadRequest as excp:
        if excp.message != "User not found":
            raise

        await message.reply_text("I can't seem to find this user.")
        return
    if is_user_in_chat(chat, user.id):
        await message.reply_text("Aren't you already in the chat??")
        return

    await chat.unban_member(user.id)
    await message.reply_text("Yep, I have unbanned you.")

    return f"<b>{html.escape(chat.title)}:</b>\n#UNBANNED\n<b>User:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"

@user_admin_no_reply
@bot_admin
@loggable
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    bot = context.bot
    user: Optional[User] = update.effective_user
    chat: Optional[Chat] = update.effective_chat
    if match := re.match(r"unban_\((.+?)\)", query.data):
        if channel := match[1].startswith("-100"):
            channel_id = match[1]
            channel = await bot.get_chat(channel_id)
            if unban := chat.unban_sender_chat(channel_id):
                await update.effective_message.edit_text(
                    f"Admin {mention_html(user.id, user.first_name)} Unbanned @{channel['username']}",
                    parse_mode=ParseMode.HTML)
                await query.answer("Unbanned!")
                return (
                    f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#UNBANNED_CHANNEL\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"<b>Channel:</b> <b>@{channel['username']}</b>"                
                )

        user_id = match.group(1)
        member = await chat.get_member(user_id)
        if unbanned := await chat.unban_member(user_id):
            await update.effective_message.edit_text(
                f"Admin {mention_html(user.id, user.first_name)} Unbanned {mention_html(member.user.id, member.user.first_name)}!",
                parse_mode=ParseMode.HTML,
            )
            await query.answer("Unbanned!")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#UNBAN\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
            )
        
__help__ = """
*User Commands:*
 • `/kickme`*:* kicks the user who issued the command
*Admins only:*
 • `/ban <userhandle>`*:* bans a user. (via handle, or reply)
 • `/sban <userhandle>`*:* Silently ban a user. Deletes command, Replied message and doesn't reply. (via handle, or reply)
 • `/tban <userhandle> x(m/h/d)`*:* bans a user for `x` time. (via handle, or reply). `m` = `minutes`, `h` = `hours`, `d` = `days`.
 • `/unban <userhandle>`*:* unbans a user. (via handle, or reply)
 • `/kick <userhandle>`*:* kicks a user out of the group, (via handle, or reply)
 • `/mute <userhandle>`*:* silences a user. Can also be used as a reply, muting the replied to user.
 • `/tmute <userhandle> x(m/h/d)`*:* mutes a user for x time. (via handle, or reply). `m` = `minutes`, `h` = `hours`, `d` = `days`.
 • `/unmute <userhandle>`*:* unmutes a user. Can also be used as a reply, muting the replied to user.
 • `/zombies`*:* searches deleted accounts
 • `/zombies clean`*:* removes deleted accounts from the group.
"""


BAN_HANDLER = CommandHandler(["ban", "sban"], ban, block=False)
TEMPBAN_HANDLER = CommandHandler(["tban"], temp_ban, block=False)
KICK_HANDLER = CommandHandler("kick", kick, block=False)
UNBAN_HANDLER = CommandHandler("unban", unban, block=False)
ROAR_HANDLER = CommandHandler("roar", selfunban, block=False)
UNBAN_BUTTON_HANDLER = CallbackQueryHandler(button, pattern=r"unban_")
KICKME_HANDLER = DisableAbleCommandHandler("kickme", kickme, filters=filters.ChatType.GROUPS, block=False)

application.add_handler(BAN_HANDLER)
application.add_handler(TEMPBAN_HANDLER)
application.add_handler(KICK_HANDLER)
application.add_handler(UNBAN_HANDLER)
application.add_handler(ROAR_HANDLER)
application.add_handler(KICKME_HANDLER)
application.add_handler(UNBAN_BUTTON_HANDLER)

__mod_name__ = "Bans"
__handlers__ = [
    BAN_HANDLER,
    TEMPBAN_HANDLER,
    KICK_HANDLER,
    UNBAN_HANDLER,
    ROAR_HANDLER,
    KICKME_HANDLER,
    UNBAN_BUTTON_HANDLER
]
