import html
import re

from telegram.constants import ParseMode
from telegram import ChatPermissions
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from telegram.helpers import mention_html

import FoundingTitanRobot.modules.sql.blacklist_sql as sql
from FoundingTitanRobot import application, LOGGER
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from FoundingTitanRobot.modules.helper_funcs.chat_status import user_admin, user_not_admin
from FoundingTitanRobot.modules.helper_funcs.extraction import extract_text
from FoundingTitanRobot.modules.helper_funcs.misc import split_message
from FoundingTitanRobot.modules.log_channel import loggable
from FoundingTitanRobot.modules.warns import warn
from FoundingTitanRobot.modules.helper_funcs.string_handling import extract_time
from FoundingTitanRobot.modules.connection import connected
from FoundingTitanRobot.modules.redis.approvals_redis import is_approved

from FoundingTitanRobot.modules.helper_funcs.alternate import send_message, typing_action

BLACKLIST_GROUP = 11



@user_admin
@typing_action
async def blacklist(update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    args = context.args

    if conn := await connected(context.bot, update, chat, user.id, need_admin=False):
        chat_id = conn
        chat_name = (await application.bot.getChat(conn)).title
    else:
        if chat.type == "private":
            return
        chat_id = update.effective_chat.id
        chat_name = chat.title

    filter_list = f"Current blacklisted words in <b>{chat_name}</b>:\n"

    all_blacklisted = sql.get_chat_blacklist(chat_id)

    if len(args) > 0 and args[0].lower() == "copy":
        for trigger in all_blacklisted:
            filter_list += f"<code>{html.escape(trigger)}</code>\n"
    else:
        for trigger in all_blacklisted:
            filter_list += f" - <code>{html.escape(trigger)}</code>\n"

    # for trigger in all_blacklisted:
    #     filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message(filter_list)
    for text in split_text:
        if (
            filter_list
            == f"Current blacklisted words in <b>{html.escape(chat_name)}</b>:\n"
        ):
            await send_message(
                update.effective_message,
                f"No blacklisted words in <b>{html.escape(chat_name)}</b>!",
                parse_mode=ParseMode.HTML,
            )
            return
        await send_message(update.effective_message, text, parse_mode=ParseMode.HTML)


@user_admin
@typing_action
async def add_blacklist(update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    words = msg.text.split(None, 1)

    if conn := await connected(context.bot, update, chat, user.id):
        chat_id = conn
        chat_name = (await application.bot.getChat(conn)).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            return
        else:
            chat_name = chat.title

    if len(words) > 1:
        text = words[1]
        to_blacklist = list(
            {
                trigger.strip()
                for trigger in text.split("\n")
                if trigger.strip()
            }
        )
        for trigger in to_blacklist:
            sql.add_to_blacklist(chat_id, trigger.lower())

        if len(to_blacklist) == 1:
            await send_message(
                update.effective_message,
                f"Added blacklist <code>{html.escape(to_blacklist[0])}</code> in chat: <b>{html.escape(chat_name)}</b>!",
                parse_mode=ParseMode.HTML,
            )

        else:
            await send_message(
                update.effective_message,
                f"Added blacklist trigger: <code>{len(to_blacklist)}</code> in <b>{html.escape(chat_name)}</b>!",
                parse_mode=ParseMode.HTML,
            )

    else:
        await send_message(
            update.effective_message,
            "Tell me which words you would like to add in blacklist.",
        )



@user_admin
@typing_action
async def unblacklist(update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    words = msg.text.split(None, 1)

    if conn := await connected(context.bot, update, chat, user.id):
        chat_id = conn
        chat_name = (await application.bot.getChat(conn)).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            return
        else:
            chat_name = chat.title

    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(
            {
                trigger.strip()
                for trigger in text.split("\n")
                if trigger.strip()
            }
        )
        successful = 0
        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat_id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                await send_message(
                    update.effective_message,
                    f"Removed <code>{html.escape(to_unblacklist[0])}</code> from blacklist in <b>{html.escape(chat_name)}</b>!",
                    parse_mode=ParseMode.HTML,
                )
            else:
                await send_message(update.effective_message,
                             "This is not a blacklist trigger!")

        elif successful == len(to_unblacklist):
            await send_message(
                update.effective_message,
                f"Removed <code>{successful}</code> from blacklist in <b>{html.escape(chat_name)}</b>!",
                parse_mode=ParseMode.HTML,
            )

        elif not successful:
            await send_message(
                update.effective_message,
                "None of these triggers exist so it can't be removed.".format(
                    successful,
                    len(to_unblacklist) - successful),
                parse_mode=ParseMode.HTML,
            )

        else:
            await send_message(
                update.effective_message,
                f"Removed <code>{successful}</code> from blacklist. {len(to_unblacklist) - successful} did not exist, so were not removed.",
                parse_mode=ParseMode.HTML,
            )
    else:
        await send_message(
            update.effective_message,
            "Tell me which words you would like to remove from blacklist!",
        )


@loggable
@user_admin
@typing_action
async def blacklist_mode(update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
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
                "This command can be only used in group not in PM",
            )
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title

    if args:
        if args[0].lower() in ["off", "nothing", "no"]:
            settypeblacklist = "do nothing"
            sql.set_blacklist_strength(chat_id, 0, "0")
        elif args[0].lower() in ["del", "delete"]:
            settypeblacklist = "will delete blacklisted message"
            sql.set_blacklist_strength(chat_id, 1, "0")
        elif args[0].lower() == "warn":
            settypeblacklist = "warn the sender"
            sql.set_blacklist_strength(chat_id, 2, "0")
        elif args[0].lower() == "mute":
            settypeblacklist = "mute the sender"
            sql.set_blacklist_strength(chat_id, 3, "0")
        elif args[0].lower() == "kick":
            settypeblacklist = "kick the sender"
            sql.set_blacklist_strength(chat_id, 4, "0")
        elif args[0].lower() == "ban":
            settypeblacklist = "ban the sender"
            sql.set_blacklist_strength(chat_id, 5, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1:
                teks = """It looks like you tried to set time value for blacklist but you didn't specified time; Try, `/blacklistmode tban <timevalue>`.
				
Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                await send_message(
                    update.effective_message, teks, parse_mode="markdown")
                return ""
            restime = extract_time(msg, args[1])
            if not restime:
                teks = """Invalid time value!
Example of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                await send_message(
                    update.effective_message, teks, parse_mode="markdown")
                return ""
            settypeblacklist = "temporarily ban for {}".format(args[1])
            sql.set_blacklist_strength(chat_id, 6, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1:
                teks = """It looks like you tried to set time value for blacklist but you didn't specified  time; try, `/blacklistmode tmute <timevalue>`.

Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                await send_message(
                    update.effective_message, teks, parse_mode="markdown")
                return ""
            restime = extract_time(msg, args[1])
            if not restime:
                teks = """Invalid time value!
Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                await send_message(
                    update.effective_message, teks, parse_mode="markdown")
                return ""
            settypeblacklist = "temporarily mute for {}".format(args[1])
            sql.set_blacklist_strength(chat_id, 7, str(args[1]))
        else:
            await send_message(
                update.effective_message,
                "I only understand: off/del/warn/ban/kick/mute/tban/tmute!",
            )
            return ""
        if conn:
            text = "Changed blacklist mode: `{}` in *{}*!".format(
                settypeblacklist, chat_name)
        else:
            text = "Changed blacklist mode: `{}`!".format(settypeblacklist)
        await send_message(update.effective_message, text, parse_mode="markdown")
        return ("<b>{}:</b>\n"
                "<b>Admin:</b> {}\n"
                "Changed the blacklist mode. will {}.".format(
                    html.escape(chat.title),
                    mention_html(user.id, html.escape(user.first_name)),
                    settypeblacklist,
                ))
    else:
        getmode, getvalue = sql.get_blacklist_setting(chat.id)
        if getmode == 0:
            settypeblacklist = "do nothing"
        elif getmode == 1:
            settypeblacklist = "delete"
        elif getmode == 2:
            settypeblacklist = "warn"
        elif getmode == 3:
            settypeblacklist = "mute"
        elif getmode == 4:
            settypeblacklist = "kick"
        elif getmode == 5:
            settypeblacklist = "ban"
        elif getmode == 6:
            settypeblacklist = "temporarily ban for {}".format(getvalue)
        elif getmode == 7:
            settypeblacklist = "temporarily mute for {}".format(getvalue)
        if conn:
            text = "Current blacklistmode: *{}* in *{}*.".format(
                settypeblacklist, chat_name)
        else:
            text = "Current blacklistmode: *{}*.".format(settypeblacklist)
        await send_message(
            update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
    return ""


def findall(p, s):
    i = s.find(p)
    while i != -1:
        yield i
        i = s.find(p, i + 1)



@user_not_admin
async def del_blacklist(update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    bot = context.bot
    to_match = extract_text(message)

    if not to_match:
        return

    if is_approved(chat.id, user.id):
        return 

    getmode, value = sql.get_blacklist_setting(chat.id)

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                if getmode == 0:
                    return
                elif getmode == 1:
                    await message.delete()
                elif getmode == 2:
                    await message.delete()
                    warn(
                        update.effective_user,
                        chat,
                        f"Using blacklisted trigger: {trigger}",
                        message,
                        update.effective_user,
                    )
                    return
                elif getmode == 3:
                    await message.delete()
                    await bot.restrict_chat_member(
                        chat.id,
                        update.effective_user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                    )
                    await bot.sendMessage(
                        chat.id,
                        f"Muted {user.first_name} for using Blacklisted word: {trigger}!",
                    )
                    return
                elif getmode == 4:
                    await message.delete()
                    if res := await chat.unban_member(update.effective_user.id):
                        await bot.sendMessage(
                            chat.id,
                            f"Kicked {user.first_name} for using Blacklisted word: {trigger}!",
                        )
                    return
                elif getmode == 5:
                    await message.delete()
                    await chat.ban_member(user.id)
                    await bot.sendMessage(
                        chat.id,
                        f"Banned {user.first_name} for using Blacklisted word: {trigger}",
                    )
                    return
                elif getmode == 6:
                    await message.delete()
                    bantime = extract_time(message, value)
                    await chat.ban_member(user.id, until_date=bantime)
                    await bot.sendMessage(
                        chat.id,
                        f"Banned {user.first_name} until '{value}' for using Blacklisted word: {trigger}!",
                    )
                    return
                elif getmode == 7:
                    await message.delete()
                    mutetime = extract_time(message, value)
                    await bot.restrict_chat_member(
                        chat.id,
                        user.id,
                        until_date=mutetime,
                        permissions=ChatPermissions(can_send_messages=False),
                    )
                    await bot.sendMessage(
                        chat.id,
                        f"Muted {user.first_name} until '{value}' for using Blacklisted word: {trigger}!",
                    )
                    return
            except BadRequest as excp:
                if excp.message != "Message to delete not found":
                    LOGGER.exception("Error while deleting blacklist message.")
            break


def __import_data__(chat_id, data):
    # set chat blacklist
    blacklist = data.get("blacklist", {})
    for trigger in blacklist:
        sql.add_to_blacklist(chat_id, trigger)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return f"There are {blacklisted} blacklisted words."


def __stats__():
    return f"• {sql.num_blacklist_filters()} blacklist triggers, across {sql.num_blacklist_filter_chats()} chats."


__mod_name__ = "Blacklists"

__help__ = """

Blacklists are used to stop certain triggers from being said in a group. Any time the trigger is mentioned, the message will immediately be deleted. A good combo is sometimes to pair this up with warn filters!

NOTE: Blacklists do not affect group admins.

 • `/blacklist`*:* View the current blacklisted words.

Admins only:
 • `/addblacklist <triggers>`*:* Add a trigger to the blacklist. Each line is considered one trigger, so using different lines will allow you to add multiple triggers.
 • `/unblacklist <triggers>`*:* Remove triggers from the blacklist. Same newline logic applies here, so you can remove multiple triggers at once.
 • `/blacklistmode <off/del/warn/ban/kick/mute/tban/tmute>`*:* Action to perform when someone sends blacklisted words.

Blacklist sticker is used to stop certain stickers. Whenever a sticker is sent, the message will be deleted immediately.
NOTE: Blacklist stickers do not affect the group admin
 • `/blsticker`*:* See current blacklisted sticker
Only admin:
 • `/addblsticker <sticker link>`*:* Add the sticker trigger to the black list. Can be added via reply sticker
 • `/unblsticker <sticker link>`*:* Remove triggers from blacklist. The same newline logic applies here, so you can delete multiple triggers at once
 • `/rmblsticker <sticker link>`*:* Same as above
 • `/blstickermode <delete/ban/tban/mute/tmute>`*:* sets up a default action on what to do if users use blacklisted stickers
Note:
  <sticker link> can be https://t.me/addstickers/<stickerpackname> or just <sticker> or reply to the sticker message

"""
BLACKLIST_HANDLER = DisableAbleCommandHandler(
    "blacklist", blacklist, admin_ok=True, block=False)
ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist, block=False)
UNBLACKLIST_HANDLER = CommandHandler("unblacklist", unblacklist, block=False)
BLACKLISTMODE_HANDLER = CommandHandler(
    "blacklistmode", blacklist_mode, block=False)
BLACKLIST_DEL_HANDLER = MessageHandler(
    (filters.TEXT | filters.COMMAND | filters.Sticker.ALL | filters.PHOTO)
    & filters.ChatType.GROUPS,
    del_blacklist,
    block=False,
)

application.add_handler(BLACKLIST_HANDLER)
application.add_handler(ADD_BLACKLIST_HANDLER)
application.add_handler(UNBLACKLIST_HANDLER)
application.add_handler(BLACKLISTMODE_HANDLER)
application.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)

__handlers__ = [
    BLACKLIST_HANDLER, ADD_BLACKLIST_HANDLER, UNBLACKLIST_HANDLER,
    BLACKLISTMODE_HANDLER, (BLACKLIST_DEL_HANDLER, BLACKLIST_GROUP)
]
