from typing import Optional

import FoundingTitanRobot.modules.sql.rules_sql as sql
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from FoundingTitanRobot import application
from FoundingTitanRobot.modules.helper_funcs.chat_status import user_admin
from FoundingTitanRobot.modules.helper_funcs.string_handling import markdown_parser
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
    User,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler, filters, ContextTypes
from telegram.helpers import escape_markdown


async def get_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    send_rules(update, chat_id)


# Do not async - not from a handler
async def send_rules(update, chat_id, from_pm=False):
    bot = application.bot
    user = update.effective_user  # type: Optional[User]
    reply_msg = update.message.reply_to_message
    try:
        chat = await bot.get_chat(chat_id)
    except BadRequest as excp:
        if excp.message != "Chat not found" or not from_pm:
            raise

        await bot.send_message(
            user.id,
            "The rules shortcut for this chat hasn't been set properly! Ask admins to "
            "fix this.\nMaybe they forgot the hyphen in ID",
        )
        return
    rules = sql.get_rules(chat_id)
    text = f"The rules for *{escape_markdown(chat.title)}* are:\n\n{rules}"

    if from_pm and rules:
        await bot.send_message(
            user.id, text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True,
        )
    elif from_pm:
        await bot.send_message(
            user.id,
            "The group admins haven't set any rules for this chat yet. "
            "This probably doesn't mean it's lawless though...!",
        )
    elif rules and reply_msg:
        await reply_msg.reply_text(
            "Please click the button below to see the rules.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Rules", url=f"t.me/{bot.username}?start={chat_id}",
                        ),
                    ],
                ],
            ),
        )
    elif rules:
        await update.effective_message.reply_text(
            "Please click the button below to see the rules.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Rules", url=f"t.me/{bot.username}?start={chat_id}",
                        ),
                    ],
                ],
            ),
        )
    else:
        await update.effective_message.reply_text(
            "The group admins haven't set any rules for this chat yet. "
            "This probably doesn't mean it's lawless though...!",
        )


@user_admin
async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]
    raw_text = msg.text
    args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
    if len(args) == 2:
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        markdown_rules = markdown_parser(
            txt, entities=msg.parse_entities(), offset=offset,
        )

        sql.set_rules(chat_id, markdown_rules)
        await update.effective_message.reply_text("Successfully set rules for this group.")


@user_admin
async def clear_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sql.set_rules(chat_id, "")
    await update.effective_message.reply_text("Successfully cleared rules!")


def __stats__():
    return f"• {sql.num_chats()} chats have rules set."


def __import_data__(chat_id, data):
    # set chat rules
    rules = data.get("info", {}).get("rules", "")
    sql.set_rules(chat_id, rules)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return f"This chat has had it's rules set: `{bool(sql.get_rules(chat_id))}`"


__mod_name__ = "Rules"

GET_RULES_HANDLER = DisableAbleCommandHandler("rules", get_rules, filters=filters.ChatType.GROUPS, block=False)
SET_RULES_HANDLER = DisableAbleCommandHandler("setrules", set_rules, filters=filters.ChatType.GROUPS, block=False)
RESET_RULES_HANDLER = DisableAbleCommandHandler("clearrules", clear_rules, filters=filters.ChatType.GROUPS, block=False)

application.add_handler(GET_RULES_HANDLER)
application.add_handler(SET_RULES_HANDLER)
application.add_handler(RESET_RULES_HANDLER)
