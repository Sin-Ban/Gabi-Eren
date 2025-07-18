import time
import re

from telegram.constants import ParseMode
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, Bot
from telegram.error import BadRequest, Forbidden
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

import FoundingTitanRobot.modules.sql.connection_sql as sql
from FoundingTitanRobot import application, TITANSHIFTERS, ACKERMANS
from FoundingTitanRobot.modules.helper_funcs import chat_status
from FoundingTitanRobot.modules.helper_funcs.alternate import send_message, typing_action

user_admin = chat_status.user_admin


@user_admin
@typing_action
async def allow_connections(update, context: ContextTypes.DEFAULT_TYPE) -> str:

    chat = update.effective_chat
    if chat.type != chat.PRIVATE:
        args = context.args

        if len(args) >= 1:
            var = args[0]
            if var == "no":
                sql.set_allow_connect_to_chat(chat.id, False)
                await send_message(
                    update.effective_message,
                    "Connection has been disabled for this chat",
                )
            elif var == "yes":
                sql.set_allow_connect_to_chat(chat.id, True)
                await send_message(
                    update.effective_message,
                    "Connection has been enabled for this chat",
                )
            else:
                await send_message(
                    update.effective_message,
                    "Please enter `yes` or `no`!",
                    parse_mode=ParseMode.MARKDOWN,
                )
        elif get_settings := sql.allow_connect_to_chat(chat.id):
            await send_message(
                update.effective_message,
                "Connections to this group are *Allowed* for members!",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await send_message(
                update.effective_message,
                "Connection to this group are *Not Allowed* for members!",
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        await send_message(
            update.effective_message, "This command is for group only. Not in PM!",
        )



@typing_action
async def connection_chat(update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    user = update.effective_user

    conn = await connected(context.bot, update, chat, user.id, need_admin=True)

    if conn:
        chat = await application.bot.getChat(conn)
        chat_name = (await application.bot.getChat(conn)).title
    else:
        if update.effective_message.chat.type != "private":
            return
        chat = update.effective_chat
        chat_name = update.effective_message.chat.title

    if conn:
        message = f"You are currently connected to {chat_name}.\n"
    else:
        message = "You are currently not connected in any group.\n"
    await send_message(update.effective_message, message, parse_mode="markdown")



@typing_action
async def connect_chat(update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    user = update.effective_user
    args = context.args

    if update.effective_chat.type == "private":
        if args and len(args) >= 1:
            try:
                connect_chat = int(args[0])
                getstatusadmin = await context.bot.get_chat_member(
                    connect_chat, update.effective_message.from_user.id,
                )
            except ValueError:
                try:
                    connect_chat = str(args[0])
                    get_chat = await context.bot.getChat(connect_chat)
                    connect_chat = get_chat.id
                    getstatusadmin = await context.bot.get_chat_member(
                        connect_chat, update.effective_message.from_user.id,
                    )
                except BadRequest:
                    await send_message(update.effective_message, "Invalid Chat ID!")
                    return
            except BadRequest:
                await send_message(update.effective_message, "Invalid Chat ID!")
                return

            isadmin = getstatusadmin.status in ("administrator", "owner")
            ismember = getstatusadmin.status in ("member")
            isallow = sql.allow_connect_to_chat(connect_chat)

            if (isadmin) or (isallow and ismember) or (user.id in TITANSHIFTERS):
                if connection_status := sql.connect(
                    update.effective_message.from_user.id,
                    connect_chat,
                ):
                    conn_chat = await application.bot.getChat(
                        await connected(context.bot, update, chat, user.id, need_admin=False),
                    )
                    chat_name = conn_chat.title
                    await send_message(
                        update.effective_message,
                        f"Successfully connected to *{chat_name}*. \nUse /helpconnect to check available commands.",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    sql.add_history_conn(user.id, str(conn_chat.id), chat_name)
                else:
                    await send_message(update.effective_message, "Connection failed!")
            else:
                await send_message(
                    update.effective_message, "Connection to this chat is not allowed!",
                )
        else:
            gethistory = sql.get_history_conn(user.id)
            if gethistory:
                buttons = [
                    InlineKeyboardButton(
                        text="❎ Close button", callback_data="connect_close",
                    ),
                    InlineKeyboardButton(
                        text="🧹 Clear history", callback_data="connect_clear",
                    ),
                ]
            else:
                buttons = []
            conn = await connected(context.bot, update, chat, user.id, need_admin=False)
            if conn:
                connectedchat = await application.bot.getChat(conn)
                text = f"You are currently connected to *{connectedchat.title}* (`{conn}`)"
                buttons.append(
                    InlineKeyboardButton(
                        text="🔌 Disconnect", callback_data="connect_disconnect",
                    ),
                )
            else:
                text = "Write the chat ID or tag to connect!"
            if gethistory:
                text += "\n\n*Connection history:*\n"
                text += "╒═══「 *Info* 」\n"
                text += "│  Sorted: `Newest`\n"
                text += "│\n"
                buttons = [buttons]
                for x in sorted(gethistory.keys(), reverse=True):
                    htime = time.strftime("%d/%m/%Y", time.localtime(x))
                    text += f'╞═「 *{gethistory[x]["chat_name"]}* 」\n│   `{gethistory[x]["chat_id"]}`\n│   `{htime}`\n'
                    text += "│\n"
                    buttons.append(
                        [
                            InlineKeyboardButton(
                                text=gethistory[x]["chat_name"],
                                callback_data=f'connect({gethistory[x]["chat_id"]})',
                            )
                        ]
                    )
                text += "╘══「 Total {} Chats 」".format(
                    str(len(gethistory)) + " (max)"
                    if len(gethistory) == 5
                    else str(len(gethistory)),
                )
                conn_hist = InlineKeyboardMarkup(buttons)
            elif buttons:
                conn_hist = InlineKeyboardMarkup([buttons])
            else:
                conn_hist = None
            await send_message(
                update.effective_message,
                text,
                parse_mode="markdown",
                reply_markup=conn_hist,
            )

    else:
        getstatusadmin = await context.bot.get_chat_member(
            chat.id, update.effective_message.from_user.id,
        )
        isadmin = getstatusadmin.status in ("administrator", "owner")
        ismember = getstatusadmin.status in ("member")
        isallow = sql.allow_connect_to_chat(chat.id)
        if (isadmin) or (isallow and ismember) or (user.id in TITANSHIFTERS):
            if connection_status := sql.connect(
                update.effective_message.from_user.id,
                chat.id,
            ):
                chat_name = (await application.bot.getChat(chat.id)).title
                await send_message(
                    update.effective_message,
                    f"Successfully connected to *{chat_name}*.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                try:
                    sql.add_history_conn(user.id, str(chat.id), chat_name)
                    await context.bot.send_message(
                        update.effective_message.from_user.id,
                        "You are connected to *{}*. \nUse `/helpconnect` to check available commands.".format(
                            chat_name,
                        ),
                        parse_mode="markdown",
                    )
                except (BadRequest, Forbidden):
                    pass
            else:
                await send_message(update.effective_message, "Connection failed!")
        else:
            await send_message(
                update.effective_message, "Connection to this chat is not allowed!",
            )


async def disconnect_chat(update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_chat.type == "private":
        if disconnection_status := sql.disconnect(
            update.effective_message.from_user.id
        ):
            sql.disconnected_chat = await send_message(
                update.effective_message, "Disconnected from chat!",
            )
        else:
            await send_message(update.effective_message, "You're not connected!")
    else:
        await send_message(update.effective_message, "This command is only available in PM.")


async def connected(bot: Bot, update: Update, chat, user_id, need_admin=True):
    user = update.effective_user

    if chat.type == chat.PRIVATE and sql.get_connected_chat(user_id):

        conn_id = sql.get_connected_chat(user_id).chat_id
        getstatusadmin = await bot.get_chat_member(
            conn_id, update.effective_message.from_user.id,
        )
        isadmin = getstatusadmin.status in ("administrator", "owner")
        ismember = getstatusadmin.status in ("member")
        isallow = sql.allow_connect_to_chat(conn_id)

        if (
            (isadmin)
            or (isallow and ismember)
            or (user.id in TITANSHIFTERS)
            or (user.id in ACKERMANS)
        ):
            if need_admin is True:
                if (
                    getstatusadmin.status in ("administrator", "owner")
                    or user_id in TITANSHIFTERS
                    or user.id in ACKERMANS
                ):
                    return conn_id
                else:
                    await send_message(
                        update.effective_message,
                        "You must be an admin in the connected group!",
                    )
            else:
                return conn_id
        else:
            await send_message(
                update.effective_message,
                "The group changed the connection rights or you are no longer an admin.\nI've disconnected you.",
            )
            disconnect_chat(update, bot)
    else:
        return False


CONN_HELP = """
Actions which are available with connected groups:-
*User Actions:*
• View Notes
• View Filters
• View Blacklist
• View AntiFlood settings
• View Disabled Commands
• Many More in future!

*Admin Actions:*
 • View and edit Notes
 • View and edit Filters.
 • Get invite link of chat.
 • Set and control AntiFlood settings. 
 • Set and control Blacklist settings.
 • Set Locks and Unlocks in chat.
 • Enable and Disable commands in chat.
 • Export and Imports of chat backup.
 • More in future!
"""



async def help_connect_chat(update, context: ContextTypes.DEFAULT_TYPE):

    args = context.args

    if update.effective_message.chat.type != "private":
        await send_message(update.effective_message, "PM me with that command to get help.")
        return
    else:
        await send_message(update.effective_message, CONN_HELP, parse_mode="markdown")



async def connect_button(update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user

    connect_match = re.match(r"connect\((.+?)\)", query.data)
    disconnect_match = query.data == "connect_disconnect"
    clear_match = query.data == "connect_clear"
    connect_close = query.data == "connect_close"

    if connect_match:
        target_chat = connect_match[1]
        getstatusadmin = await context.bot.get_chat_member(target_chat, query.from_user.id)
        isadmin = getstatusadmin.status in ("administrator", "owner")
        ismember = getstatusadmin.status in ("member")
        isallow = sql.allow_connect_to_chat(target_chat)

        if (isadmin) or (isallow and ismember) or (user.id in TITANSHIFTERS):
            if connection_status := sql.connect(
                query.from_user.id, target_chat
            ):
                conn_chat = await application.bot.getChat(
                    connected(context.bot, update, chat, user.id, need_admin=False),
                )
                chat_name = conn_chat.title
                await query.message.edit_text(
                    f"Successfully connected to *{chat_name}*. \nUse `/helpconnect` to check available commands.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                sql.add_history_conn(user.id, str(conn_chat.id), chat_name)
            else:
                await query.message.edit_text("Connection failed!")
        else:
            await context.bot.answer_callback_query(
                query.id, "Connection to this chat is not allowed!", show_alert=True,
            )
    elif disconnect_match:
        if disconnection_status := sql.disconnect(query.from_user.id):
            sql.disconnected_chat = await query.message.edit_text("Disconnected from chat!")
        else:
            await context.bot.answer_callback_query(
                query.id, "You're not connected!", show_alert=True,
            )
    elif clear_match:
        sql.clear_history_conn(query.from_user.id)
        await query.message.edit_text("History connected has been cleared!")
    elif connect_close:
        await query.message.edit_text("Closed.\nTo open again, type /connect")
    else:
        connect_chat(update, context)


__mod_name__ = "Connection"

__help__ = """
Sometimes, you just want to add some notes and filters to a group chat, but you don't want everyone to see; This is where connections come in...
This allows you to connect to a chat's database, and add things to it without the commands appearing in chat! For obvious reasons, you need to be an admin to add things; but any member in the group can view your data.

 • /connect: Connects to chat (Can be done in a group by /connect or /connect <chat id> in PM)
 • /connection: List connected chats
 • /disconnect: Disconnect from a chat
 • /helpconnect: List available commands that can be used remotely

*Admin only:*
 • /allowconnect <yes/no>: allow an user to connect to a chat
"""

CONNECT_CHAT_HANDLER = CommandHandler("connect", connect_chat, block=False)
CONNECTION_CHAT_HANDLER = CommandHandler("connection", connection_chat, block=False)
DISCONNECT_CHAT_HANDLER = CommandHandler("disconnect", disconnect_chat, block=False)
ALLOW_CONNECTIONS_HANDLER = CommandHandler(
    "allowconnect", allow_connections, block=False
)
HELP_CONNECT_CHAT_HANDLER = CommandHandler("helpconnect", help_connect_chat, block=False)
CONNECT_BTN_HANDLER = CallbackQueryHandler(connect_button, pattern=r"connect", block=False)

application.add_handler(CONNECT_CHAT_HANDLER)
application.add_handler(CONNECTION_CHAT_HANDLER)
application.add_handler(DISCONNECT_CHAT_HANDLER)
application.add_handler(ALLOW_CONNECTIONS_HANDLER)
application.add_handler(HELP_CONNECT_CHAT_HANDLER)
application.add_handler(CONNECT_BTN_HANDLER)
