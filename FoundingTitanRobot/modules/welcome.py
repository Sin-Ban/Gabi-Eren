import html
import random
import re
import time
from functools import partial
from contextlib import suppress
from typing import Tuple, Optional
from telethon import events
import FoundingTitanRobot.modules.sql.welcome_sql as sql
import FoundingTitanRobot
from FoundingTitanRobot import (
    ACKERMANS,
    LOGGER,
    OWNER_ID,
    TITANSHIFTERS,
    ROYALS,
    SCOUTS,
    GARRISONS,
    BOT_USERNAME,
    application,
    JOIN_LOGGER,
    telethn,
    BL_CHATS,
)
from FoundingTitanRobot.modules.helper_funcs.chat_status import (
    is_user_ban_protected,
    user_admin,
)
from FoundingTitanRobot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from FoundingTitanRobot.modules.helper_funcs.msg_types import get_welcome_type
from FoundingTitanRobot.modules.helper_funcs.string_handling import (
    escape_invalid_curly_brackets,
    markdown_parser,
)
from FoundingTitanRobot.modules.log_channel import loggable
from FoundingTitanRobot.modules.sql.global_bans_sql import is_user_gbanned
from telegram import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ChatMemberUpdated,
    ChatMember,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    ContextTypes,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    filters,
    MessageHandler,
    ChatMemberHandler,
)
from telegram.helpers import escape_markdown, mention_html, mention_markdown

VALID_WELCOME_FORMATTERS = [
    "first",
    "last",
    "fullname",
    "username",
    "id",
    "count",
    "chatname",
    "mention",
]

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: application.bot.send_message,
    sql.Types.BUTTON_TEXT.value: application.bot.send_message,
    sql.Types.STICKER.value: application.bot.send_sticker,
    sql.Types.DOCUMENT.value: application.bot.send_document,
    sql.Types.PHOTO.value: application.bot.send_photo,
    sql.Types.AUDIO.value: application.bot.send_audio,
    sql.Types.VOICE.value: application.bot.send_voice,
    sql.Types.VIDEO.value: application.bot.send_video,
}

VERIFIED_USER_WAITLIST = {}

def extract_status_change(
    chat_member_update: ChatMemberUpdated,
) -> Optional[Tuple[bool, bool]]:
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = (
        old_status
        in [
            ChatMember.MEMBER,
            ChatMember.OWNER,
            ChatMember.ADMINISTRATOR,
        ]
        or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    )
    is_member = (
        new_status
        in [
            ChatMember.MEMBER,
            ChatMember.OWNER,
            ChatMember.ADMINISTRATOR,
        ]
        or (new_status == ChatMember.RESTRICTED and new_is_member is True)
    )

    return was_member, is_member


# do not async
async def send(update, message, keyboard, backup_message):
    chat = update.effective_chat
    reply = None

    try:
        msg = await update.effective_chat.send_message(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            reply_to_message_id=reply,
        )
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = await update.effective_chat.send_message(
                markdown_parser(
                    backup_message + "\nNote: the current message has an invalid url "
                                     "in one of its buttons. Please update.",
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
        elif excp.message == "Have no rights to send a message":
            return
        elif excp.message == "Replied message not found":
            msg = await update.effective_chat.send_message(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
                quote=False,
            )
        elif excp.message == "Unsupported url protocol":
            msg = await update.effective_chat.send_message(
                markdown_parser(
                    backup_message + "\nNote: the current message has buttons which "
                                     "use url protocols that are unsupported by "
                                     "telegram. Please update.",
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
        elif excp.message == "Wrong url host":
            msg = await update.effective_chat.send_message(
                markdown_parser(
                    backup_message + "\nNote: the current message has some bad urls. "
                                     "Please update.",
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("Could not parse! got invalid url host errors")
        else:
            msg = await update.effective_chat.send_message(
                markdown_parser(
                    backup_message + "\nNote: An error occured when sending the "
                                     "custom message. Please update.",
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
            LOGGER.exception()
    return msg


async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, job_queue = context.bot, context.job_queue
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    result = extract_status_change(update.chat_member)
    if chat.type != "supergroup":
        return
    if result is None:
        return
    was_member, is_member = result
    should_welc, cust_welcome, cust_content, welc_type = sql.get_welc_pref(chat.id)
    welc_mutes = sql.welcome_mutes(chat.id)
    human_checks = sql.get_human_checks(user.id, chat.id)

    if not was_member and is_member:
        new_mem = update.chat_member.new_chat_member.user

        if new_mem.id == bot.id and chat.id in BL_CHATS:                
                await update.effective_message.reply_text(f"This is a Blacklisted Group! Join @FoundingTitanSupport for Appeal.")
                await bot.leave_chat(BL_CHATS)

        if new_mem.id == bot.id and not FoundingTitanRobot.ALLOW_CHATS:
            with suppress(BadRequest):
                await update.effective_message.reply_text(f"Groups are disabled for {bot.first_name}, I'm outta here.")
            await bot.leave_chat(update.effective_chat.id)
            return

        welcome_log = None
        res = None
        sent = None
        should_mute = True
        welcome_bool = True
        media_wel = False

        if is_user_gbanned(new_mem.id):
            return

        reply = None

        if should_welc:

            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
                await bot.send_message(chat.id,
                               text=f"Founding Titan? THE RUMBLER JUST JOINED THE GROUP!!",
                               reply_to_message_id=reply,
                               )
                welcome_log = (
                    f"{html.escape(chat.title)}\n"
                    f"#USER_JOINED\n"
                    f"Bot Owner just joined the group"
                )

            elif new_mem.id in ACKERMANS:
                await bot.send_message(chat.id,
                               text=f"Be Cool! An Ackerman just Joined the Group",
                               reply_to_message_id=reply,
                               )
                welcome_log = (
                    f"{html.escape(chat.title)}\n"
                    f"#USER_JOINED\n"
                    f"Bot Dev just joined the group"
                )

            elif new_mem.id in TITANSHIFTERS:
                await bot.send_message(chat.id,
                                text=f"Beware! A Titan Shifter just Joined the group!!",
                                reply_to_message_id=reply,
                               )
                welcome_log = (
                    f"{html.escape(chat.title)}\n"
                    f"#USER_JOINED\n"
                    f"Bot Sudo just joined the group"
                )

            elif new_mem.id in ROYALS:
                await bot.send_message(chat.id,
                                text=f"Somone With Royal Blood just joined the group! Stay Alert!! ",
                                reply_to_message_id=reply,
                               )
                welcome_log = (
                    f"{html.escape(chat.title)}\n"
                    f"#USER_JOINED\n"
                    f"Bot Support just joined the group"
                )


            elif new_mem.id in GARRISONS:
                await bot.send_message(chat.id,
                                text=f"Oof! A Garrison from the garrison regiment just joined the group",
                                reply_to_message_id=reply,
                               )
                welcome_log = (
                    f"{html.escape(chat.title)}\n"
                    f"#USER_JOINED\n"
                    f"A whitelisted user joined the chat"
                )


            elif new_mem.id in SCOUTS:
                await bot.send_message(chat.id,
                               text=f"Shinzou Sasageyo! A Scout just joined the group!",
                               reply_to_message_id=reply,
                               )
                welcome_log = (
                    f"{html.escape(chat.title)}\n"
                    f"#USER_JOINED\n"
                    f"A whitelisted user joined the chat"
                )

            elif new_mem.id == bot.id:
                owner = next(
                    (
                        x.user
                        for x in await bot.bot.get_chat_administrators(
                            update.effective_chat.id
                        )
                        if x.status == "owner"
                    ),
                    None,
                )
                if owner:
                    await bot.send_message(
                        JOIN_LOGGER,
                        "#NEW_GROUP\n<b>Group name:</b> {}\n<b>ID:</b> <code>{}</code>\n<b>Owner:</b> <code>{}</code>".format(
                            html.escape(chat.title), chat.id, html.escape(owner),
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    await bot.send_message(
                        JOIN_LOGGER,
                        "#NEW_GROUP\n<b>Group name:</b> {}\n<b>ID:</b> <code>{}</code>".format(
                            html.escape(chat.title), chat.id,
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                await update.effective_chat.send_message(
                    "Watashi ga kita!",
                )

            else:
                buttons = sql.get_welc_buttons(chat.id)
                keyb = build_keyboard(buttons)

                if welc_type not in (sql.Types.TEXT, sql.Types.BUTTON_TEXT):
                    media_wel = True

                first_name = (
                    new_mem.first_name or "PersonWithNoName"
                )  # edge case of empty name - occurs for some bugs.

                if cust_welcome:
                    if cust_welcome == sql.DEFAULT_WELCOME:
                        cust_welcome = random.choice(
                            sql.DEFAULT_WELCOME_MESSAGES,
                        ).format(first=escape_markdown(first_name))

                    if new_mem.last_name:
                        fullname = escape_markdown(f"{first_name} {new_mem.last_name}")
                    else:
                        fullname = escape_markdown(first_name)
                    count = chat.get_member_count()
                    mention = mention_markdown(new_mem.id, escape_markdown(first_name))
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(
                        cust_welcome, VALID_WELCOME_FORMATTERS,
                    )
                    res = valid_format.format(
                        first=escape_markdown(first_name),
                        last=escape_markdown(new_mem.last_name or first_name),
                        fullname=escape_markdown(fullname),
                        username=username,
                        mention=mention,
                        count=count,
                        chatname=escape_markdown(chat.title),
                        id=new_mem.id,
                    )

                else:
                    res = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                        first=escape_markdown(first_name),
                    )
                    keyb = []

                backup_message = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                    first=escape_markdown(first_name),
                )
                keyboard = InlineKeyboardMarkup(keyb)

        else:
            welcome_bool = False
            res = None
            keyboard = None
            backup_message = None
        # User exceptions from welcomemutes
        chat_mem = await chat.get_member(new_mem.id)
        if (
            await is_user_ban_protected(chat, new_mem.id, chat_mem)
            or human_checks
        ):
            should_mute = False
        # Join welcome: soft mute
        if new_mem.is_bot:
            should_mute = False

        if should_mute and user.id == new_mem.id:
            if welc_mutes == "soft":
                await bot.restrict_chat_member(
                    chat.id,
                    new_mem.id,
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_send_polls=False,
                        can_change_info=False,
                        can_add_web_page_previews=False,
                    ),
                    until_date=(int(time.time() + 24 * 60 * 60)),
                )
            if welc_mutes == "strong":
                welcome_bool = False
                if not media_wel:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            new_mem.id: {
                                "should_welc": should_welc,
                                "media_wel": False,
                                "status": False,
                                "update": update,
                                "res": res,
                                "keyboard": keyboard,
                                "backup_message": backup_message,
                            },
                        },
                    )
                else:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            new_mem.id: {
                                "should_welc": should_welc,
                                "chat_id": chat.id,
                                "status": False,
                                "media_wel": True,
                                "cust_content": cust_content,
                                "welc_type": welc_type,
                                "res": res,
                                "keyboard": keyboard,
                            },
                        },
                    )
                new_join_mem = f'<a href="tg://user?id={user.id}">{html.escape(new_mem.first_name)}</a>'
                message = await bot.send_message(
                    chat.id,
                    f"{new_join_mem}, click the button below to prove you're human.\nYou have 120 seconds.",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            {
                                InlineKeyboardButton(
                                    text="Yes, I'm human.",
                                    callback_data=f"user_join_({new_mem.id})",
                                ),
                            },
                        ],
                    ),
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=reply,
                )
                await bot.restrict_chat_member(
                    chat.id,
                    new_mem.id,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_send_polls=False,
                        can_change_info=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                    ),
                )
                job_queue.run_once(
                    partial(check_not_bot, new_mem, chat.id, message.message_id),
                    120,
                    name="welcomemute",
                )

        if welcome_bool:
            if media_wel:
                if ENUM_FUNC_MAP[welc_type] == application.bot.send_sticker:
                    sent = await ENUM_FUNC_MAP[welc_type](
                        chat.id,
                        cust_content,
                        reply_markup=keyboard,
                        reply_to_message_id=reply,
                    )
                else:
                    sent = await ENUM_FUNC_MAP[welc_type](
                        chat.id,
                        cust_content,
                        caption=res,
                        reply_markup=keyboard,
                        reply_to_message_id=reply,
                        parse_mode="markdown",
                    )
            else:
                sent = await send(update, res, keyboard, backup_message)
            if prev_welc := sql.get_clean_pref(chat.id):
                try:
                    await bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

        if welcome_log:
            return welcome_log

        if user.id == new_mem.id:
            welcome_log = (
                f"{html.escape(chat.title)}\n"
                f"#USER_JOINED\n"
                f"<b>User</b>: {mention_html(user.id, user.first_name)}\n"
                f"<b>ID</b>: <code>{user.id}</code>"
            )
        elif new_mem.is_bot:
            welcome_log = (
                f"{html.escape(chat.title)}\n"
                f"#BOT_ADDED\n"
                f"<b>Bot</b>: {mention_html(new_mem.id, new_mem.first_name)}\n"
                f"<b>ID</b>: <code>{new_mem.id}</code>"
            )
        else:
            welcome_log = (
                f"{html.escape(chat.title)}\n"
                f"#USER_ADDED\n"
                f"<b>User</b>: {mention_html(new_mem.id, new_mem.first_name)}\n"
                f"<b>ID</b>: <code>{new_mem.id}</code>"
            )
        return welcome_log

# cleanservice
@telethn.on(events.ChatAction)
async def delete_service(event):
    clean = sql.clean_service(event.chat_id)
    if not clean:
        return
    with suppress(BadRequest):
        if event.user_joined or event.user_added or event.user_left or event.user_kicked:
            await event.delete()


async def check_not_bot(member, chat_id, message_id, context):
    bot = context.bot
    member_dict = VERIFIED_USER_WAITLIST.pop(member.id)
    member_status = member_dict.get("status")
    if not member_status:
        with suppress(Exception):
            await bot.unban_chat_member(chat_id, member.id)
        with suppress(Exception):
            await bot.edit_message_text(
                "*kicks user*\nThey can always rejoin and try.",
                chat_id=chat_id,
                message_id=message_id,
            )



async def left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    chat = update.effective_chat
    user = update.effective_user
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)

    if user.id == bot.id:
        return

    if should_goodbye:
        reply = update.message.message_id
        if cleanserv := sql.clean_service(chat.id):
            with suppress(BadRequest):
                await application.bot.delete_message(chat.id, update.message.message_id)
            reply = False

        if left_mem := update.effective_message.left_chat_member:
            # Dont say goodbyes to gbanned users
            if is_user_gbanned(left_mem.id):
                return

            # Ignore bot being kicked
            elif left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            elif left_mem.id == OWNER_ID:
                await update.effective_message.reply_text(
                    "Oi! Armin! He left..", reply_to_message_id=reply,
                )
                return

            # Give the devs a special goodbye
            elif left_mem.id in ACKERMANS:
                await update.effective_message.reply_text(
                    "See you later at the Ackerman Clan!",
                    reply_to_message_id=reply,
                )
                return

            # if media goodbye, use appropriate function for it
            if goodbye_type not in [sql.Types.TEXT, sql.Types.BUTTON_TEXT]:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = (
                left_mem.first_name or "PersonWithNoName"
            )  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if cust_goodbye == sql.DEFAULT_GOODBYE:
                    cust_goodbye = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(
                        first=escape_markdown(first_name),
                    )
                if left_mem.last_name:
                    fullname = escape_markdown(f"{first_name} {left_mem.last_name}")
                else:
                    fullname = escape_markdown(first_name)
                count = chat.get_member_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = f"@{escape_markdown(left_mem.username)}"
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(
                    cust_goodbye, VALID_WELCOME_FORMATTERS,
                )
                res = valid_format.format(
                    first=escape_markdown(first_name),
                    last=escape_markdown(left_mem.last_name or first_name),
                    fullname=escape_markdown(fullname),
                    username=username,
                    mention=mention,
                    count=count,
                    chatname=escape_markdown(chat.title),
                    id=left_mem.id,
                )
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(
                    first=first_name,
                )
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            await send(
                update,
                res,
                keyboard,
                random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(first=first_name),
            )



@user_admin
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat = update.effective_chat
    # if no args, show current replies.
    if not args or args[0].lower() == "noformat":
        noformat = True
        pref, welcome_m, cust_content, welcome_type = sql.get_welc_pref(chat.id)
        await update.effective_message.reply_text(
            f"This chat has it's welcome setting set to: `{pref}`.\n"
            f"*The welcome message (not filling the {{}}) is:*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if welcome_type in [sql.Types.BUTTON_TEXT, sql.Types.TEXT]:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                await update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                await send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)
        else:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                ENUM_FUNC_MAP[welcome_type](chat.id, cust_content, caption=welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)
                await ENUM_FUNC_MAP[welcome_type](
                    chat.id,
                    cust_content,
                    caption=welcome_m,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            await update.effective_message.reply_text(
                "Okay! I'll greet members when they join.",
            )

        elif args[0].lower() in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            await update.effective_message.reply_text(
                "I'll go loaf around and not welcome anyone then.",
            )

        else:
            await update.effective_message.reply_text(
                "I understand 'on/yes' or 'off/no' only!",
            )



@user_admin
async def goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat = update.effective_chat

    if not args or args[0] == "noformat":
        noformat = True
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        await update.effective_message.reply_text(
            f"This chat has it's goodbye setting set to: `{pref}`.\n"
            f"*The goodbye  message (not filling the {{}}) is:*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                await update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                await send(update, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)

        elif noformat:
            await ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

        else:
            await ENUM_FUNC_MAP[goodbye_type](
                chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN,
            )

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            await update.effective_message.reply_text("Ok!")

        elif args[0].lower() in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            await update.effective_message.reply_text("Ok!")

        else:
            # idek what you're writing, say yes or no
            await update.effective_message.reply_text(
                "I understand 'on/yes' or 'off/no' only!",
            )


@user_admin
@loggable
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        await msg.reply_text("You didn't specify what to reply with!")
        return ""

    sql.set_custom_welcome(chat.id, content, text, data_type, buttons)
    await msg.reply_text("Successfully set custom welcome message!")

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Set the welcome message."
    )



@user_admin
@loggable
async def reset_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_welcome(chat.id, None, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    await update.effective_message.reply_text(
        "Successfully reset welcome message to default!",
    )

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Reset the welcome message to default."
    )



@user_admin
@loggable
async def set_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        await msg.reply_text("You didn't specify what to reply with!")
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    await msg.reply_text("Successfully set custom goodbye message!")
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_GOODBYE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Set the goodbye message."
    )



@user_admin
@loggable
async def reset_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    await update.effective_message.reply_text(
        "Successfully reset goodbye message to default!",
    )

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_GOODBYE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Reset the goodbye message."
    )



@user_admin
@loggable
async def welcomemute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if len(args) >= 1:
        if args[0].lower() in ("off", "no"):
            sql.set_welcome_mutes(chat.id, False)
            await msg.reply_text("I will no longer mute people on joining!")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>OFF</b>."
            )
        elif args[0].lower() in ["soft"]:
            sql.set_welcome_mutes(chat.id, "soft")
            await msg.reply_text(
                "I will restrict users' permission to send media for 24 hours.",
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>SOFT</b>."
            )
        elif args[0].lower() in ["strong"]:
            sql.set_welcome_mutes(chat.id, "strong")
            await msg.reply_text(
                "I will now mute people when they join until they prove they're not a bot.\nThey will have 120seconds before they get kicked.",
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>STRONG</b>."
            )
        else:
            await msg.reply_text(
                "Please enter <code>off</code>/<code>no</code>/<code>soft</code>/<code>strong</code>!",
                parse_mode=ParseMode.HTML,
            )
            return ""
    else:
        curr_setting = sql.welcome_mutes(chat.id)
        reply = (
            f"\n Give me a setting!\nChoose one out of: <code>off</code>/<code>no</code> or <code>soft</code> or <code>strong</code> only! \n"
            f"Current setting: <code>{curr_setting}</code>"
        )
        await msg.reply_text(reply, parse_mode=ParseMode.HTML)
        return ""


@user_admin
@loggable
async def clean_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user

    if not args:
        if clean_pref := sql.get_clean_pref(chat.id):
            await update.effective_message.reply_text(
                "I should be deleting welcome messages up to two days old.",
            )
        else:
            await update.effective_message.reply_text(
                "I'm currently not deleting old welcome messages!",
            )
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        await update.effective_message.reply_text("I'll try to delete old welcome messages!")
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Has toggled clean welcomes to <code>ON</code>."
        )
    elif args[0].lower() in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        await update.effective_message.reply_text("I won't delete old welcome messages.")
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Has toggled clean welcomes to <code>OFF</code>."
        )
    else:
        await update.effective_message.reply_text("I understand 'on/yes' or 'off/no' only!")
        return ""


@user_admin
async def cleanservice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type != chat.PRIVATE:
        args = context.args
        if len(args) >= 1:
            var = args[0]
            if var in ("no", "off"):
                sql.set_clean_service(chat.id, False)
                await update.effective_message.reply_text("Welcome clean service is : off")
            elif var in ("yes", "on"):
                sql.set_clean_service(chat.id, True)
                await update.effective_message.reply_text("Welcome clean service is : on")
            else:
                await update.effective_message.reply_text(
                    "Invalid option", parse_mode=ParseMode.HTML,
                )
        else:
            await update.effective_message.reply_text(
                "Usage is <code>on</code>/<code>yes</code> or <code>off</code>/<code>no</code>",
                parse_mode=ParseMode.HTML,
            )
    elif curr := sql.clean_service(chat.id):
        await update.effective_message.reply_text(
            "Welcome clean service is : <code>on</code>", parse_mode=ParseMode.HTML,
        )
    else:
        await update.effective_message.reply_text(
            "Welcome clean service is : <code>off</code>", parse_mode=ParseMode.HTML,
        )



async def user_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    query = update.callback_query
    bot = context.bot
    match = re.match(r"user_join_\((.+?)\)", query.data)
    join_user = int(match[1])

    if join_user == user.id:
        sql.set_human_checks(user.id, chat.id)
        member_dict = VERIFIED_USER_WAITLIST.pop(user.id)
        member_dict["status"] = True
        VERIFIED_USER_WAITLIST.update({user.id: member_dict})
        await query.answer(text="Yeet! You're a human, unmuted!")
        await bot.restrict_chat_member(
            chat.id,
            user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_send_polls=True,
                can_change_info=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        message = update.effective_message
        with suppress(Exception):
            await bot.deleteMessage(chat.id, message.message_id)
        if member_dict["should_welc"]:
            if member_dict["media_wel"]:
                sent = ENUM_FUNC_MAP[member_dict["welc_type"]](
                    member_dict["chat_id"],
                    member_dict["cust_content"],
                    caption=member_dict["res"],
                    reply_markup=member_dict["keyboard"],
                    parse_mode="markdown",
                )
            else:
                sent = send(
                    member_dict["update"],
                    member_dict["res"],
                    member_dict["keyboard"],
                    member_dict["backup_message"],
                )

            if prev_welc := sql.get_clean_pref(chat.id):
                with suppress(BadRequest):
                    await bot.delete_message(chat.id, prev_welc)
                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

    else:
        await query.answer(text="You're not allowed to do this!")


WELC_HELP_TXT = (
    "Your group's welcome/goodbye messages can be personalised in multiple ways. If you want the messages"
    " to be individually generated, like the default welcome message is, you can use *these* variables:\n"
    " • `{first}`*:* this represents the user's *first* name\n"
    " • `{last}`*:* this represents the user's *last* name. Defaults to *first name* if user has no "
    "last name.\n"
    " • `{fullname}`*:* this represents the user's *full* name. Defaults to *first name* if user has no "
    "last name.\n"
    " • `{username}`*:* this represents the user's *username*. Defaults to a *mention* of the user's "
    "first name if has no username.\n"
    " • `{mention}`*:* this simply *mentions* a user - tagging them with their first name.\n"
    " • `{id}`*:* this represents the user's *id*\n"
    " • `{count}`*:* this represents the user's *member number*.\n"
    " • `{chatname}`*:* this represents the *current chat name*.\n"
    "\nEach variable MUST be surrounded by `{}` to be replaced.\n"
    "Welcome messages also support markdown, so you can make any elements bold/italic/code/links. "
    "Buttons are also supported, so you can make your welcomes look awesome with some nice intro "
    "buttons.\n"
    f"To create a button linking to your rules, use this: `[Rules](buttonurl://t.me/{BOT_USERNAME}?start=group_id)`. "
    "Simply replace `group_id` with your group's id, which can be obtained via /id, and you're good to "
    "go. Note that group ids are usually preceded by a `-` sign; this is required, so please don't "
    "remove it.\n"
    "You can even set images/gifs/videos/voice messages as the welcome message by "
    "replying to the desired media, and calling `/setwelcome`."
)

WELC_MUTE_HELP_TXT = (
    "You can get the bot to mute new people who join your group and hence prevent spambots from flooding your group. "
    "The following options are possible:\n"
    "• `/welcomemute soft`*:* restricts new members from sending media for 24 hours.\n"
    "• `/welcomemute strong`*:* mutes new members till they tap on a button thereby verifying they're human.\n"
    "• `/welcomemute off`*:* turns off welcomemute.\n"
    "*Note:* Strong mode kicks a user from the chat if they dont verify in 120seconds. They can always rejoin though"
)


@user_admin
async def welcome_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


@user_admin
async def welcome_mute_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        WELC_MUTE_HELP_TXT, parse_mode=ParseMode.MARKDOWN,
    )


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref = sql.get_welc_pref(chat_id)[0]
    goodbye_pref = sql.get_gdbye_pref(chat_id)[0]
    return f"This chat has it's welcome preference set to `{welcome_pref}`.\nIt's goodbye preference is `{goodbye_pref}`."


__help__ = """
*Admins only:*
 • `/welcome <on/off>`*:* enable/disable welcome messages.
 • `/welcome`*:* shows current welcome settings.
 • `/welcome noformat`*:* shows current welcome settings, without the formatting - useful to recycle your welcome messages!
 • `/goodbye`*:* same usage and args as `/welcome`.
 • `/setwelcome <sometext>`*:* set a custom welcome message. If used replying to media, uses that media.
 • `/setgoodbye <sometext>`*:* set a custom goodbye message. If used replying to media, uses that media.
 • `/resetwelcome`*:* reset to the default welcome message.
 • `/resetgoodbye`*:* reset to the default goodbye message.
 • `/cleanwelcome <on/off>`*:* On new member, try to delete the previous welcome message to avoid spamming the chat.
 • `/welcomemutehelp`*:* gives information about welcome mutes.
 • `/cleanservice <on/off`*:* deletes telegrams welcome/left service messages.
 *Example:*
user joined chat, user left chat.

*Welcome markdown:*
 • `/welcomehelp`*:* view more formatting information for custom welcome/goodbye messages.
"""

NEW_MEM_HANDLER = ChatMemberHandler(new_member, ChatMemberHandler.CHAT_MEMBER, block=False)
LEFT_MEM_HANDLER = MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, left_member, block=False)
WELC_PREF_HANDLER = CommandHandler("welcome", welcome, filters=filters.ChatType.GROUPS, block=False)
GOODBYE_PREF_HANDLER = CommandHandler("goodbye", goodbye, filters=filters.ChatType.GROUPS, block=False)
SET_WELCOME = CommandHandler("setwelcome", set_welcome, filters=filters.ChatType.GROUPS, block=False)
SET_GOODBYE = CommandHandler("setgoodbye", set_goodbye, filters=filters.ChatType.GROUPS, block=False)
RESET_WELCOME = CommandHandler("resetwelcome", reset_welcome, filters=filters.ChatType.GROUPS, block=False)
RESET_GOODBYE = CommandHandler("resetgoodbye", reset_goodbye, filters=filters.ChatType.GROUPS, block=False)
WELCOMEMUTE_HANDLER = CommandHandler("welcomemute", welcomemute, filters=filters.ChatType.GROUPS, block=False)
CLEAN_SERVICE_HANDLER = CommandHandler(
    "cleanservice", cleanservice, filters=filters.ChatType.GROUPS, block=False
)
CLEAN_WELCOME = CommandHandler("cleanwelcome", clean_welcome, filters=filters.ChatType.GROUPS, block=False)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help, block=False)
WELCOME_MUTE_HELP = CommandHandler("welcomemutehelp", welcome_mute_help, block=False)
BUTTON_VERIFY_HANDLER = CallbackQueryHandler(user_button, pattern=r"user_join_", block=False)

application.add_handler(NEW_MEM_HANDLER)
application.add_handler(LEFT_MEM_HANDLER)
application.add_handler(WELC_PREF_HANDLER)
application.add_handler(GOODBYE_PREF_HANDLER)
application.add_handler(SET_WELCOME)
application.add_handler(SET_GOODBYE)
application.add_handler(RESET_WELCOME)
application.add_handler(RESET_GOODBYE)
application.add_handler(CLEAN_WELCOME)
application.add_handler(WELCOME_HELP)
application.add_handler(WELCOMEMUTE_HANDLER)
application.add_handler(CLEAN_SERVICE_HANDLER)
application.add_handler(BUTTON_VERIFY_HANDLER)
application.add_handler(WELCOME_MUTE_HELP)

__mod_name__ = "Greetings"
__command_list__ = []
__handlers__ = [
    NEW_MEM_HANDLER,
    LEFT_MEM_HANDLER,
    WELC_PREF_HANDLER,
    GOODBYE_PREF_HANDLER,
    SET_WELCOME,
    SET_GOODBYE,
    RESET_WELCOME,
    RESET_GOODBYE,
    CLEAN_WELCOME,
    WELCOME_HELP,
    WELCOMEMUTE_HANDLER,
    CLEAN_SERVICE_HANDLER,
    BUTTON_VERIFY_HANDLER,
    WELCOME_MUTE_HELP,
]
