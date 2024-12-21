import html
import json
import os
from typing import Optional

from FoundingTitanRobot import (
    ACKERMANS,
    OWNER_ID,
    TITANSHIFTERS,
    SUPPORT_CHAT,
    ROYALS,
    SCOUTS,
    GARRISONS,
    application,
)
from FoundingTitanRobot.modules.helper_funcs.chat_status import (
    dev_plus,
    sudo_plus,
    whitelist_plus,
)
from FoundingTitanRobot.modules.helper_funcs.extraction import extract_user
from FoundingTitanRobot.modules.log_channel import gloggable
from telegram.error import TelegramError
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, CommandHandler, ContextTypes
from telegram.helpers import mention_html

ELEVATED_USERS_FILE = os.path.join(os.getcwd(), "FoundingTitanRobot/elevated_users.json")


def check_user_id(user_id: int, context: CallbackContext) -> Optional[str]:
    bot = context.bot
    if not user_id:
        return "That...is a chat! baka ka omae?"

    elif user_id == bot.id:
        return "This does not work that way."

    else:
        return None


# This can serve as a deeplink example.
# disasters =
# """ Text here """

# do not async, not a handler
# def send_disasters(update):
#    await update.effective_message.reply_text(
#        disasters, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

### Deep link example ends


@dev_plus
@gloggable
async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = await extract_user(message, args)
    user_member = await bot.getChat(user_id)
    rt = ""

    if reply := check_user_id(user_id, bot):
        await message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in TITANSHIFTERS:
        await message.reply_text("This member is already a Titan Shifter")
        return ""

    if user_id in ROYALS:
        rt += "Requested the Ackermans to promote a Royal Blood to Titan Shifter."
        data["supports"].remove(user_id)
        ROYALS.remove(user_id)

    if user_id in GARRISONS:
        rt += "Requested the Ackermans to promote a Garrison to Titan Shifter."
        data["whitelists"].remove(user_id)
        GARRISONS.remove(user_id)

    data["sudos"].append(user_id)
    TITANSHIFTERS.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    await update.effective_message.reply_text(
        f"{rt}\nSuccessfully set Disaster level of {user_member.first_name} to Titan Shifter!"
    )

    log_message = (
        f"#SUDO\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n{log_message}"

    return log_message


@sudo_plus
@gloggable
async def addsupport(
    update: Update,
    context: CallbackContext,
) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = await extract_user(message, args)
    user_member = await bot.getChat(user_id)
    rt = ""

    if reply := check_user_id(user_id, bot):
        await message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in TITANSHIFTERS:
        rt += "Requested the Ackermans to demote this Titan Shifter to Royal Blood"
        data["sudos"].remove(user_id)
        TITANSHIFTERS.remove(user_id)

    if user_id in ROYALS:
        await message.reply_text("This user is already a Royal Blood.")
        return ""

    if user_id in GARRISONS:
        rt += "Requested the Ackermans to promote this Garrison to Royal Blood"
        data["whitelists"].remove(user_id)
        GARRISONS.remove(user_id)

    data["supports"].append(user_id)
    ROYALS.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    await update.effective_message.reply_text(
        f"{rt}\n{user_member.first_name} was added as a Royal Blood!"
    )

    log_message = (
        f"#SUPPORT\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n{log_message}"

    return log_message


@sudo_plus
@gloggable
async def addwhitelist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = await extract_user(message, args)
    user_member = await bot.getChat(user_id)
    rt = ""

    if reply := check_user_id(user_id, bot):
        await message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in TITANSHIFTERS:
        rt += "This member is a Titan Shifter, Demoting to Garrison."
        data["sudos"].remove(user_id)
        TITANSHIFTERS.remove(user_id)

    if user_id in ROYALS:
        rt += "This user is already a Royal Blood, Demoting to Garrison."
        data["supports"].remove(user_id)
        ROYALS.remove(user_id)

    if user_id in GARRISONS:
        await message.reply_text("This user is already a Garrison.")
        return ""

    data["whitelists"].append(user_id)
    GARRISONS.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    await update.effective_message.reply_text(
        f"{rt}\nSuccessfully promoted {user_member.first_name} to a Garrison!"
    )

    log_message = (
        f"#WHITELIST\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))} \n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n{log_message}"

    return log_message


@sudo_plus
@gloggable
async def addtiger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = await extract_user(message, args)
    user_member = await bot.getChat(user_id)
    rt = ""

    if reply := check_user_id(user_id, bot):
        await message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in TITANSHIFTERS:
        rt += "This member is a Titan Shifter, Demoting to Scout."
        data["sudos"].remove(user_id)
        TITANSHIFTERS.remove(user_id)

    if user_id in ROYALS:
        rt += "This user is already a Royal Blood, Demoting to Scout."
        data["supports"].remove(user_id)
        ROYALS.remove(user_id)

    if user_id in GARRISONS:
        rt += "This user is already a Garrison, Demoting to No Acces.."
        data["whitelists"].remove(user_id)
        GARRISONS.remove(user_id)

    if user_id in SCOUTS:
        await message.reply_text("This user is already a Scout.")
        return ""

    data["tigers"].append(user_id)
    SCOUTS.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    await update.effective_message.reply_text(
        f"{rt}\nSuccessfully promoted {user_member.first_name} to a Scout!"
    )

    log_message = (
        f"#SCOUT\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))} \n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n{log_message}"

    return log_message


@dev_plus
@gloggable
async def removesudo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = await extract_user(message, args)
    user_member = await bot.getChat(user_id)

    if reply := check_user_id(user_id, bot):
        await message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in TITANSHIFTERS:
        await message.reply_text("Requested the Ackermans to demote this user to Civilian")
        TITANSHIFTERS.remove(user_id)
        data["sudos"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNSUDO\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n{log_message}"

        return log_message

    else:
        await message.reply_text("This user is not a Titan Shifter!")
        return ""


@sudo_plus
@gloggable
async def removesupport(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = await extract_user(message, args)
    user_member = await bot.getChat(user_id)

    if reply := check_user_id(user_id, bot):
        await message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in ROYALS:
        await message.reply_text("Requested the Ackermans to demote this user to Civilian")
        ROYALS.remove(user_id)
        data["supports"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNSUPPORT\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n{log_message}"

        return log_message

    else:
        await message.reply_text("This user is not a Royal Blood!")
        return ""


@sudo_plus
@gloggable
async def removewhitelist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = await extract_user(message, args)
    user_member = await bot.getChat(user_id)

    if reply := check_user_id(user_id, bot):
        await message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in GARRISONS:
        await message.reply_text("Demoting to normal user")
        GARRISONS.remove(user_id)
        data["whitelists"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNWHITELIST\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n{log_message}"

        return log_message
    else:
        await message.reply_text("This user is not a Garrison!")
        return ""


@sudo_plus
@gloggable
async def removetiger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = await extract_user(message, args)
    user_member = await bot.getChat(user_id)

    if reply := check_user_id(user_id, bot):
        await message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in SCOUTS:
        await message.reply_text("Demoting to normal user")
        SCOUTS.remove(user_id)
        data["Tigers"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNSCOUT\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n{log_message}"

        return log_message
    else:
        await message.reply_text("This user is not a Scout!")
        return ""


@whitelist_plus
async def whitelistlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = "<b>Known Garrisons♠️:</b>\n"
    m = await update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML,
    )
    bot = context.bot
    for each_user in GARRISONS:
        user_id = int(each_user)
        try:
            user = await bot.get_chat(user_id)

            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    await m.edit_text(reply, parse_mode=ParseMode.HTML)



@whitelist_plus
async def tigerlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = "<b>Known Scouts🔰:</b>\n"
    m = await update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML,
    )
    bot = context.bot
    for each_user in SCOUTS:
        user_id = int(each_user)
        try:
            user = await bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    await m.edit_text(reply, parse_mode=ParseMode.HTML)


@whitelist_plus
async def supportlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    m = await update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML,
    )
    reply = "<b>Known Royal Bloods⭐:</b>\n"
    for each_user in ROYALS:
        user_id = int(each_user)
        try:
            user = await bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    await m.edit_text(reply, parse_mode=ParseMode.HTML)


@whitelist_plus
async def sudolist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    m = await update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML,
    )
    true_sudo = list(set(TITANSHIFTERS) - set(ACKERMANS))
    reply = "<b>Known Titan Shifters💥:</b>\n"
    for each_user in true_sudo:
        user_id = int(each_user)
        try:
            user = await bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    await m.edit_text(reply, parse_mode=ParseMode.HTML)


@whitelist_plus
async def devlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    m = await update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML,
    )
    true_dev = list(set(ACKERMANS) - {OWNER_ID})
    reply = "<b>Ackerman Clan Members⚡️:</b>\n"
    for each_user in true_dev:
        user_id = int(each_user)
        try:
            user = await bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    await m.edit_text(reply, parse_mode=ParseMode.HTML)




SUDO_HANDLER = CommandHandler(("addsudo", "addtitanshifter"), addsudo, block=False)
SUPPORT_HANDLER = CommandHandler(("addsupport", "addroyalblood"), addsupport, block=False)
TIGER_HANDLER = CommandHandler(("addscout"), addtiger)
WHITELIST_HANDLER = CommandHandler(("addgarrison", "addwhitelist"), addwhitelist, block=False)
UNSUDO_HANDLER = CommandHandler(("removesudo", "removetitanshifter"), removesudo, block=False)
UNSUPPORT_HANDLER = CommandHandler(("removesupport", "removeroyalblood"), removesupport, block=False)
UNTIGER_HANDLER = CommandHandler(("removescout"), removetiger)
UNWHITELIST_HANDLER = CommandHandler(("removewhitelist", "removegarrison"), removewhitelist, block=False)

WHITELISTLIST_HANDLER = CommandHandler(["whitelistlist", "garrisons"], whitelistlist, block=False)
TIGERLIST_HANDLER = CommandHandler(["scouts"], tigerlist, block=False)
SUPPORTLIST_HANDLER = CommandHandler(["supportlist", "royalbloods"], supportlist, block=False)
SUDOLIST_HANDLER = CommandHandler(["sudolist", "titanshifters"], sudolist, block=False)
DEVLIST_HANDLER = CommandHandler(["devlist", "ackermans"], devlist, block=False)

application.add_handler(SUDO_HANDLER)
application.add_handler(SUPPORT_HANDLER)
application.add_handler(TIGER_HANDLER)
application.add_handler(WHITELIST_HANDLER)
application.add_handler(UNSUDO_HANDLER)
application.add_handler(UNSUPPORT_HANDLER)
application.add_handler(UNTIGER_HANDLER)
application.add_handler(UNWHITELIST_HANDLER)

application.add_handler(WHITELISTLIST_HANDLER)
application.add_handler(TIGERLIST_HANDLER)
application.add_handler(SUPPORTLIST_HANDLER)
application.add_handler(SUDOLIST_HANDLER)
application.add_handler(DEVLIST_HANDLER)

__mod_name__ = "Bot Owner"
__handlers__ = [
    SUDO_HANDLER,
    SUPPORT_HANDLER,
    TIGER_HANDLER,
    WHITELIST_HANDLER,
    UNSUDO_HANDLER,
    UNSUPPORT_HANDLER,
    UNTIGER_HANDLER,
    UNWHITELIST_HANDLER,
    WHITELISTLIST_HANDLER,
    TIGERLIST_HANDLER,
    SUPPORTLIST_HANDLER,
    SUDOLIST_HANDLER,
    DEVLIST_HANDLER,
]
