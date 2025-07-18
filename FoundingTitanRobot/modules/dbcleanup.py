from time import sleep

import FoundingTitanRobot.modules.sql.global_bans_sql as gban_sql
import FoundingTitanRobot.modules.sql.users_sql as user_sql
from FoundingTitanRobot import ACKERMANS, OWNER_ID, application
from FoundingTitanRobot.modules.helper_funcs.chat_status import dev_plus
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    ContextTypes,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
)


async def get_invalid_chats(update: Update, context: CallbackContext, remove: bool = False):
    bot = context.bot
    chat_id = update.effective_chat.id
    chats = user_sql.get_all_chats()
    kicked_chats, progress = 0, 0
    chat_list = []
    progress_message = None

    for chat in chats:

        if ((100 * chats.index(chat)) / len(chats)) > progress:
            progress_bar = f"{progress}% completed in getting invalid chats."
            if progress_message:
                try:
                    await bot.editMessageText(
                        progress_bar, chat_id, progress_message.message_id,
                    )
                except Exception:
                    pass
            else:
                progress_message = await bot.sendMessage(chat_id, progress_bar)
            progress += 5

        cid = chat.chat_id
        sleep(0.1)
        try:
            await bot.get_chat(cid, timeout=60)
        except (BadRequest, Forbidden):
            kicked_chats += 1
            chat_list.append(cid)
        except Exception:
            pass

    try:
        progress_message.delete()
    except Exception:
        pass

    if remove:
        for muted_chat in chat_list:
            sleep(0.1)
            user_sql.rem_chat(muted_chat)
    return kicked_chats


async def get_invalid_gban(update: Update, context: CallbackContext, remove: bool = False):
    bot = context.bot
    banned = gban_sql.get_gban_list()
    ungbanned_users = 0
    ungban_list = []

    for user in banned:
        user_id = user["user_id"]
        sleep(0.1)
        try:
            await bot.get_chat(user_id)
        except BadRequest:
            ungbanned_users += 1
            ungban_list.append(user_id)
        except Exception:
            pass

    if remove:
        for user_id in ungban_list:
            sleep(0.1)
            gban_sql.ungban_user(user_id)
    return ungbanned_users



@dev_plus
async def dbcleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    await msg.reply_text("Getting invalid chat count ...")
    invalid_chat_count = get_invalid_chats(update, context)

    await msg.reply_text("Getting invalid gbanned count ...")
    invalid_gban_count = get_invalid_gban(update, context)

    reply = f"Total invalid chats - {invalid_chat_count}\n"
    reply += f"Total invalid gbanned users - {invalid_gban_count}"

    buttons = [[InlineKeyboardButton("Cleanup DB", callback_data="db_cleanup")]]

    await update.effective_message.reply_text(
        reply, reply_markup=InlineKeyboardMarkup(buttons),
    )



async def callback_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    query = update.callback_query
    message = query.message
    chat_id = update.effective_chat.id
    query_type = query.data

    admin_list = [OWNER_ID] + ACKERMANS

    await bot.answer_callback_query(query.id)

    if query_type == "db_cleanup" and query.from_user.id in admin_list:
        await bot.editMessageText("Cleaning up DB ...", chat_id, message.message_id)
        invalid_chat_count = get_invalid_chats(update, context, True)
        invalid_gban_count = get_invalid_gban(update, context, True)
        reply = f"Cleaned up {invalid_chat_count} chats and {invalid_gban_count} gbanned users from db."
        await bot.sendMessage(chat_id, reply)
    elif (
        query_type == "db_cleanup"
        or query_type == "db_leave_chat"
        and query.from_user.id not in admin_list
    ):
        await query.answer("You are not allowed to use this.")

    elif query_type == "db_leave_chat":
        await bot.editMessageText("Leaving chats ...", chat_id, message.message_id)
        chat_count = get_muted_chats(update, context, True)
        await bot.sendMessage(chat_id, f"Left {chat_count} chats.")


DB_CLEANUP_HANDLER = CommandHandler("dbcleanup", dbcleanup, block=False)
BUTTON_HANDLER = CallbackQueryHandler(callback_button, pattern="db_.*", block=False)

application.add_handler(DB_CLEANUP_HANDLER)
application.add_handler(BUTTON_HANDLER)

__mod_name__ = "DB Cleanup"
__handlers__ = [DB_CLEANUP_HANDLER, BUTTON_HANDLER]
