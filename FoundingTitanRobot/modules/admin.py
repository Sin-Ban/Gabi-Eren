import html

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler, filters, ContextTypes
from telegram.helpers import mention_html

from FoundingTitanRobot import TITANSHIFTERS, application
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from FoundingTitanRobot.modules.helper_funcs.chat_status import (
    bot_admin,
    can_pin,
    can_promote,
    connection_status,
    user_admin,
    ADMIN_CACHE,
)

from FoundingTitanRobot.modules.helper_funcs.extraction import (
    extract_user,
    extract_user_and_text,
)
from FoundingTitanRobot.modules.log_channel import loggable
from FoundingTitanRobot.modules.helper_funcs.alternate import send_message


@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    bot = context.bot
    args = context.args

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    promoter = await chat.get_member(user.id)

    if (
        not promoter.can_promote_members
        and promoter.status != "owner"
        and user.id not in TITANSHIFTERS
    ):
        await message.reply_text("You don't have the necessary rights to do that!")
        return

    user_id = await extract_user(message, args)

    if not user_id:
        await message.reply_text(
            "You don't seem to be referring to a user or the ID specified is incorrect..",
        )
        return

    try:
        user_member = await chat.get_member(user_id)
    except Exception:
        return

    if user_member.status in ["administrator", "owner"]:
        await message.reply_text("How am I meant to promote someone that's already an admin?")
        return

    if user_id == bot.id:
        await message.reply_text("I can't promote myself! Get an admin to do it for me.")
        return

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = await chat.get_member(bot.id)

    try:
        await bot.promoteChatMember(
            chat.id,
            user_id,
            can_change_info=bot_member.can_change_info,
            can_post_messages=bot_member.can_post_messages,
            can_edit_messages=bot_member.can_edit_messages,
            can_delete_messages=bot_member.can_delete_messages,
            can_invite_users=bot_member.can_invite_users,
            # can_promote_members=bot_member.can_promote_members,
            can_restrict_members=bot_member.can_restrict_members,
            can_pin_messages=bot_member.can_pin_messages,
        )
    except BadRequest as err:
        if err.message == "User_not_mutual_contact":
            await message.reply_text("I can't promote someone who isn't in the group.")
        else:
            await message.reply_text("An error occured while promoting.")
        return

    await bot.sendMessage(
        chat.id,
        f"Sucessfully promoted <b>{user_member.user.first_name or user_id}</b>!",
        parse_mode=ParseMode.HTML,
    )

    return f"<b>{html.escape(chat.title)}:</b>\n#PROMOTED\n<b>Admin:</b> {mention_html(user.id, user.first_name)}\n<b>User:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"


@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
async def fullpromote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    bot = context.bot
    args = context.args

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    promoter = await chat.get_member(user.id)

    if (
        not promoter.can_promote_members
        and promoter.status != "owner"
        and user.id not in TITANSHIFTERS
    ):
        await message.reply_text("You don't have the necessary rights to do that!")
        return

    user_id = await extract_user(message, args)

    if not user_id:
        await message.reply_text(
            "You don't seem to be referring to a user or the ID specified is incorrect..",
        )
        return

    try:
        user_member = await chat.get_member(user_id)
    except Exception:
        return

    if user_member.status in ["administrator", "owner"]:
        await message.reply_text("How am I meant to promote someone that's already an admin?")
        return

    if user_id == bot.id:
        await message.reply_text("I can't promote myself! Get an admin to do it for me.")
        return

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = await chat.get_member(bot.id)

    try:
        await bot.promoteChatMember(
            chat.id,
            user_id,
            can_change_info=bot_member.can_change_info,
            can_post_messages=bot_member.can_post_messages,
            can_edit_messages=bot_member.can_edit_messages,
            can_delete_messages=bot_member.can_delete_messages,
            can_invite_users=bot_member.can_invite_users,
            can_promote_members=bot_member.can_promote_members,
            can_restrict_members=bot_member.can_restrict_members,
            can_pin_messages=bot_member.can_pin_messages,
            can_manage_video_chats=bot_member.can_manage_video_chats,
        )
    except BadRequest as err:
        if err.message == "User_not_mutual_contact":
            await message.reply_text("I can't promote someone who isn't in the group.")
        else:
            await message.reply_text("An error occured while promoting.")
        return

    await bot.sendMessage(
        chat.id,
        f"Sucessfully promoted <b>{user_member.user.first_name or user_id}</b> with full rights!",
        parse_mode=ParseMode.HTML,
    )

    return f"<b>{html.escape(chat.title)}:</b>\n#FULLPROMOTED\n<b>Admin:</b> {mention_html(user.id, user.first_name)}\n<b>User:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"


@connection_status
@bot_admin
@can_promote
@user_admin
@loggable
async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    bot = context.bot
    args = context.args

    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user

    user_id = await extract_user(message, args)
    if not user_id:
        await message.reply_text(
            "You don't seem to be referring to a user or the ID specified is incorrect..",
        )
        return

    try:
        user_member = await chat.get_member(user_id)
    except Exception:
        return

    if user_member.status == "owner":
        await message.reply_text("This person CREATED the chat, how would I demote them?")
        return

    if user_member.status != "administrator":
        await message.reply_text("Can't demote what wasn't promoted!")
        return

    if user_id == bot.id:
        await message.reply_text("I can't demote myself! Get an admin to do it for me.")
        return

    try:
        await bot.promoteChatMember(
            chat.id,
            user_id,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_video_chats=False,
        )

        await bot.sendMessage(
            chat.id,
            f"Sucessfully demoted <b>{user_member.user.first_name or user_id}</b>!",
            parse_mode=ParseMode.HTML,
        )

        return f"<b>{html.escape(chat.title)}:</b>\n#DEMOTED\n<b>Admin:</b> {mention_html(user.id, user.first_name)}\n<b>User:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
    except BadRequest:
        await message.reply_text(
            "Could not demote. I might not be admin, or the admin status was appointed by another"
            " user, so I can't act upon them!",
        )
        return


@user_admin
async def refresh_admin(update, _: ContextTypes.DEFAULT_TYPE):
    try:
        ADMIN_CACHE.pop(update.effective_chat.id)
    except KeyError:
        pass

    await update.effective_message.reply_text("Admins cache refreshed!")

@connection_status
@bot_admin
@can_promote
@user_admin
async def set_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    args = context.args

    chat = update.effective_chat
    message = update.effective_message

    user_id, title = await extract_user_and_text(message, args)
    try:
        user_member = await chat.get_member(user_id)
    except Exception:
        return

    if not user_id:
        await message.reply_text(
            "You don't seem to be referring to a user or the ID specified is incorrect..",
        )
        return

    if user_member.status == "owner":
        await message.reply_text(
            "This person CREATED the chat, how can i set custom title for him?",
        )
        return

    if user_member.status != "administrator":
        await message.reply_text(
            "Can't set title for non-admins!\nPromote them first to set custom title!",
        )
        return

    if user_id == bot.id:
        await message.reply_text(
            "I can't set my own title myself! Get the one who made me admin to do it for me.",
        )
        return

    if not title:
        await message.reply_text("Setting blank title doesn't do anything!")
        return

    if len(title) > 16:
        await message.reply_text(
            "The title length is longer than 16 characters.\nTruncating it to 16 characters.",
        )

    try:
        await bot.setChatAdministratorCustomTitle(chat.id, user_id, title)
    except BadRequest:
        await message.reply_text(
            "Either they aren't promoted by me or you set a title text that is impossible to set."
        )
        return

    await bot.sendMessage(
        chat.id,
        f"Sucessfully set title for <code>{user_member.user.first_name or user_id}</code> "
        f"to <code>{html.escape(title[:16])}</code>!",
        parse_mode=ParseMode.HTML,
    )


@bot_admin
@can_pin
@user_admin
@loggable
async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat

    is_group = chat.type not in ["private", "channel"]
    prev_message = update.effective_message.reply_to_message

    if prev_message and is_group:
        args = context.args

        is_silent = (
            args[0].lower() not in ["notify", "loud", "violent"]
            if len(args) >= 1
            else True
        )
        bot = context.bot
        try:
            await bot.pinChatMessage(
                chat.id,
                prev_message.message_id,
                disable_notification=is_silent,
            )
        except BadRequest as excp:
            if excp.message != "Chat_not_modified":
                raise
        user = update.effective_user
        return f"<b>{html.escape(chat.title)}:</b>\n#PINNED\n<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}"


@bot_admin
@can_pin
@user_admin
@loggable
async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    bot = context.bot
    chat = update.effective_chat
    user = update.effective_user

    try:
        await bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message != "Chat_not_modified":
            raise

    return f"<b>{html.escape(chat.title)}:</b>\n#UNPINNED\n<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}"


@bot_admin
@user_admin
@connection_status
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    chat = update.effective_chat

    if chat.username:
        await update.effective_message.reply_text(f"https://t.me/{chat.username}")
    elif chat.type in [chat.SUPERGROUP, chat.CHANNEL]:
        bot_member = await chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = await bot.exportChatInviteLink(chat.id)
            await update.effective_message.reply_text(invitelink)
        else:
            await update.effective_message.reply_text(
                "I don't have access to the invite link, try changing my permissions!",
            )
    else:
        await update.effective_message.reply_text(
            "I can only give you invite links for supergroups and channels, sorry!",
        )


@connection_status
async def adminlist(update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat  # type: Optional[Chat] -> unused variable
    user = update.effective_user  # type: Optional[User]
    args = context.args  # -> unused variable
    bot = context.bot

    if update.effective_message.chat.type == "private":
        await send_message(update.effective_message, "This command only works in Groups.")
        return

    chat = update.effective_chat
    chat_id = update.effective_chat.id
    chat_name = update.effective_message.chat.title  # -> unused variable

    try:
        msg = await update.effective_message.reply_text(
            "Fetching group admins...",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest:
        msg = await update.effective_message.reply_text(
            "Fetching group admins...",
            quote=False,
            parse_mode=ParseMode.HTML,
        )

    administrators = await bot.getChatAdministrators(chat_id)
    text = f"Admins in <b>{html.escape(update.effective_chat.title)}</b>:"

    for admin in administrators:
        user = admin.user
        status = admin.status
        custom_title = admin.custom_title

        name = (
            "☠ Deleted Account"
            if user.first_name == ""
            else f'{mention_html(user.id, html.escape(user.first_name + " " + (user.last_name or "")))}'
        )

        # if user.username:
        #    name = escape_markdown("@" + user.username)
        if status == "owner":
            text += "\n 🌏 Owner:"
            text += f"\n<code> • </code>{name}\n"

            if custom_title:
                text += f"<code> ┗━ {html.escape(custom_title)}</code>\n"

    text += "\n🌟 Admins:"

    custom_admin_list = {}
    normal_admin_list = []

    for admin in administrators:
        user = admin.user
        status = admin.status
        custom_title = admin.custom_title

        name = (
            "☠ Deleted Account"
            if user.first_name == ""
            else f'{mention_html(user.id, html.escape(user.first_name + " " + (user.last_name or "")))}'
        )
        if status == "administrator":
            if custom_title:
                try:
                    custom_admin_list[custom_title].append(name)
                except KeyError:
                    custom_admin_list[custom_title] = [name]
            else:
                normal_admin_list.append(name)

    for admin in normal_admin_list:
        text += "\n<code> • </code>{}".format(admin)

    for admin_group in custom_admin_list.copy():
        if len(custom_admin_list[admin_group]) == 1:
            text += "\n<code> • </code>{} | <code>{}</code>".format(
                custom_admin_list[admin_group][0],
                html.escape(admin_group),
            )
            custom_admin_list.pop(admin_group)

    text += "\n"
    for admin_group, value in custom_admin_list.items():
        text += "\n🚨 <code>{}</code>".format(admin_group)
        for admin in value:
            text += "\n<code> • </code>{}".format(admin)
        text += "\n"

    try:
        await msg.edit_text(text, parse_mode=ParseMode.HTML)
    except BadRequest:  # if original message is deleted
        return


__help__ = """
*User Commands*:
 • `/admins`*:* list of admins in the chat

*The Following Commands are Admins only:*
 
 • `/pin`*:* silently pins the message replied to - add `'loud'` or `'notify'` to give notifs to users
 • `/unpin`*:* unpins the currently pinned message
 • `/invitelink`*:* gets invitelink
 • `/promote`*:* promotes the user replied to
 • `/fullpromote`*:* promotes the user replied to with full rights
 • `/demote`*:* demotes the user replied to
 • `/title <title here>`*:* sets a custom title for an admin that the bot promoted
 • `/admincache`*:* force refresh the admins list
 • `/del`*:* deletes the message you replied to
 • `/purge`*:* deletes all messages between this and the replied to message.
 • `/purge <integer X>`*:* deletes the replied message, and X messages following it if replied to a message.


*Log Channel*:
 • `/logchannel`*:* get log channel info
 • `/setlog`*:* set the log channel.
 • `/unsetlog`*:* unset the log channel.

*Setting the log channel is done by*:
 • adding the bot to the desired channel (as an admin!)
 • sending `/setlog` in the channel
 • forwarding the `/setlog` to the group

*Rules*:
 • `/rules`*:* get the rules for this chat.
 • `/setrules <your rules here>`*:* set the rules for this chat.
 • `/clearrules`*:* clear the rules for this chat.
"""

ADMINLIST_HANDLER = DisableAbleCommandHandler("admins", adminlist, block=False)

PIN_HANDLER = CommandHandler("pin", pin, filters=filters.ChatType.GROUPS, block=False)
UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=filters.ChatType.GROUPS, block=False)

INVITE_HANDLER = DisableAbleCommandHandler("invitelink", invite, block=False)

PROMOTE_HANDLER = DisableAbleCommandHandler("promote", promote, block=False)
FULLPROMOTE_HANDLER = DisableAbleCommandHandler("fullpromote", fullpromote, block=False)
DEMOTE_HANDLER = DisableAbleCommandHandler("demote", demote, block=False)

SET_TITLE_HANDLER = CommandHandler("title", set_title, block=False)
ADMIN_REFRESH_HANDLER = CommandHandler("admincache", refresh_admin, filters=filters.ChatType.GROUPS, block=False)

application.add_handler(ADMINLIST_HANDLER)
application.add_handler(PIN_HANDLER)
application.add_handler(UNPIN_HANDLER)
application.add_handler(INVITE_HANDLER)
application.add_handler(PROMOTE_HANDLER)
application.add_handler(FULLPROMOTE_HANDLER)
application.add_handler(DEMOTE_HANDLER)
application.add_handler(SET_TITLE_HANDLER)
application.add_handler(ADMIN_REFRESH_HANDLER)

__mod_name__ = "Admins"
__command_list__ = [
    "adminlist", "admins", "invitelink", "promote", "fullpromote", "demote", "admincache"
]
__handlers__ = [
    ADMINLIST_HANDLER, PIN_HANDLER, UNPIN_HANDLER, INVITE_HANDLER,
    PROMOTE_HANDLER, FULLPROMOTE_HANDLER, DEMOTE_HANDLER, SET_TITLE_HANDLER, ADMIN_REFRESH_HANDLER
]
