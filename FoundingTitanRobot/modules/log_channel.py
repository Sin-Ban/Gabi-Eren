from datetime import datetime
from functools import wraps

from telegram.ext import CallbackContext

from FoundingTitanRobot.modules.helper_funcs.misc import is_module_loaded

FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from telegram import Update
    from telegram.constants import ParseMode
    from telegram.error import BadRequest, Forbidden
    from telegram.ext import CommandHandler, JobQueue, ContextTypes
    from telegram.helpers import escape_markdown

    from FoundingTitanRobot import EVENT_LOGS, LOGGER, application
    from FoundingTitanRobot.modules.helper_funcs.chat_status import user_admin
    from FoundingTitanRobot.modules.sql import log_channel_sql as sql

    def loggable(func):
        @wraps(func)
        async def log_action(
            update: Update,
            context: CallbackContext,
            job_queue: JobQueue = None,
            *args,
            **kwargs,
        ):
            if not job_queue:
                result = await func(update, context, *args, **kwargs)
            else:
                result = await func(update, context, job_queue, *args, **kwargs)

            chat = update.effective_chat
            message = update.effective_message

            if result:
                datetime_fmt = "%H:%M - %d-%m-%Y"
                result += f"\n<b>Event Stamp</b>: <code>{datetime.utcnow().strftime(datetime_fmt)}</code>"

                if message.chat.type == chat.SUPERGROUP and message.chat.username:
                    result += f'\n<b>Link:</b> <a href="https://t.me/{chat.username}/{message.message_id}">click here</a>'
                log_chat = sql.get_chat_log_channel(chat.id)
                if log_chat:
                    await send_log(context, log_chat, chat.id, result)

            return result

        return log_action

    def gloggable(func):
        @wraps(func)
        async def glog_action(update: Update, context: CallbackContext, *args, **kwargs):
            result = await func(update, context, *args, **kwargs)
            chat = update.effective_chat
            message = update.effective_message

            if result:
                datetime_fmt = "%H:%M - %d-%m-%Y"
                result += "\n<b>Event Stamp</b>: <code>{}</code>".format(
                    datetime.utcnow().strftime(datetime_fmt),
                )

                if message.chat.type == chat.SUPERGROUP and message.chat.username:
                    result += f'\n<b>Link:</b> <a href="https://t.me/{chat.username}/{message.message_id}">click here</a>'
                log_chat = str(EVENT_LOGS)
                if log_chat:
                    await send_log(context, log_chat, chat.id, result)

            return result

        return glog_action

    async def send_log(
        context: CallbackContext, log_chat_id: str, orig_chat_id: str, result: str,
    ):
        bot = context.bot
        try:
            await bot.send_message(
                log_chat_id,
                result,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except BadRequest as excp:
            if excp.message == "Chat not found":
                await bot.send_message(
                    orig_chat_id, "This log channel has been deleted - unsetting.",
                )
                sql.stop_chat_logging(orig_chat_id)
            else:
                LOGGER.warning(excp.message)
                LOGGER.warning(result)
                LOGGER.exception("Could not parse")

                await bot.send_message(
                    log_chat_id,
                    result
                    + "\n\nFormatting has been disabled due to an unexpected error.",
                )

    @user_admin
    async def logging(update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat

        if log_channel := sql.get_chat_log_channel(chat.id):
            log_channel_info = await bot.get_chat(log_channel)
            await message.reply_text(
                f"This group has all it's logs sent to:"
                f" {escape_markdown(log_channel_info.title)} (`{log_channel}`)",
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            await message.reply_text("No log channel has been set for this group!")

    @user_admin
    async def setlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat
        if chat.type == chat.CHANNEL:
            await message.reply_text(
                "Now, forward the /setlog to the group you want to tie this channel to!",
            )

        elif message.forward_origin:
            sql.set_chat_log_channel(chat.id, message.forward_origin.id)
            try:
                await message.delete()
            except BadRequest as excp:
                if excp.message != "Message to delete not found":
                    LOGGER.exception(
                        "Error deleting message in log channel. Should work anyway though.",
                    )

            try:
                await bot.send_message(
                    message.forward_origin.id,
                    f"This channel has been set as the log channel for {chat.title or chat.first_name}.",
                )
            except Forbidden as excp:
                if excp.message == "Forbidden: bot is not a member of the channel chat":
                    await bot.send_message(chat.id, "Successfully set log channel!")
                else:
                    LOGGER.exception("ERROR in setting the log channel.")

            await bot.send_message(chat.id, "Successfully set log channel!")

        else:
            await message.reply_text(
                "The steps to set a log channel are:\n"
                " - add bot to the desired channel\n"
                " - send /setlog to the channel\n"
                " - forward the /setlog to the group\n",
            )

    @user_admin
    async def unsetlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat

        if log_channel := sql.stop_chat_logging(chat.id):
            await bot.send_message(
                log_channel, f"Channel has been unlinked from {chat.title}",
            )
            await message.reply_text("Log channel has been un-set.")

        else:
            await message.reply_text("No log channel has been set yet!")

    async def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)

    async def __chat_settings__(chat_id, user_id):
        if log_channel := sql.get_chat_log_channel(chat_id):
            log_channel_info = await application.bot.get_chat(log_channel)
            return f"This group has all it's logs sent to: {escape_markdown(log_channel_info.title)} (`{log_channel}`)"
        return "No log channel is set for this group!"
    
    def __stats__():
        return f"• {sql.num_logchannels()} log channels set."


    LOG_HANDLER = CommandHandler("logchannel", logging, block=False)
    SET_LOG_HANDLER = CommandHandler("setlog", setlog, block=False)
    UNSET_LOG_HANDLER = CommandHandler("unsetlog", unsetlog, block=False)

    application.add_handler(LOG_HANDLER)
    application.add_handler(SET_LOG_HANDLER)
    application.add_handler(UNSET_LOG_HANDLER)

else:
    # run anyway if module not loaded
    def loggable(func):
        return func

    def gloggable(func):
        return func
