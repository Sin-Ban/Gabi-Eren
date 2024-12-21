import traceback
import html
import random
import sys
import pretty_errors
import io
import aiohttp
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, ContextTypes
from FoundingTitanRobot import application, ACKERMANS, ERROR_LOGS, eren_paste

pretty_errors.mono()


class ErrorsDict(dict):
    "A custom dict to store errors and their count"

    def __init__(self, *args, **kwargs):
        self.raw = []
        super().__init__(*args, **kwargs)

    def __contains__(self, error):
        self.raw.append(error)
        error.identifier = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
        for e in self:
            if type(e) is type(error) and e.args == error.args:
                self[e] += 1
                return True
        self[error] = 0
        return False

    def __len__(self):
        return len(self.raw)


errors = ErrorsDict()


async def error_callback(update: Update, context: CallbackContext):
    if not update or context.error in errors:
        return

    try:
        stringio = io.StringIO()
        pretty_errors.output_stderr = stringio
        pretty_errors.excepthook(type(context.error), context.error, context.error.__traceback__)
        pretty_errors.output_stderr = sys.stderr
        pretty_error = stringio.getvalue()
        stringio.close()
    except Exception:
        pretty_error = "Failed to create pretty error."

    tb = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
    
    pretty_message = (
        f"{pretty_error}\n"
        "-------------------------------------------------------------------------------\n"
        "An exception was raised while handling an update\n"
        f"User: {update.effective_user.id if update.effective_user else 'No User'}\n"
        f"Chat: {update.effective_chat.title if update.effective_chat else ''} {update.effective_chat.id if update.effective_chat else ''}\n"
        f"Callback data: {update.callback_query.data if update.callback_query else 'None'}\n"
        f"Message: {update.effective_message.text if update.effective_message else 'No message'}\n\n"
        f"Full Traceback: {tb}"
    )

    e = html.escape(f"{context.error}")
    err_data = pretty_message.encode('utf-8')

    async with aiohttp.ClientSession() as session:
        url_paste = "https://pastes.dev/post"
        async with session.post(url=url_paste, data=err_data) as response:
            p_json = await response.json()
            p_id = p_json["key"]
            p_url = f"https://pastes.dev/{p_id}"
            async with session.get(p_url) as r:
                if r.status == 200:
                    await context.bot.send_message(
                        ERROR_LOGS,
                        text=f"<b>An unknown error occurred:</b>\n<code>{e}</code>",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("PasteBin", url=p_url)]]),
                        parse_mode="html",
                    )
                else:
                    with open("error.txt", "w+") as f:
                        f.write(pretty_message)
                    await context.bot.send_document(
                        ERROR_LOGS,
                        open("error.txt", "rb"),
                        caption=f"<b>An unknown error occurred:</b>\n<code>{e}</code>",
                        parse_mode="html",
                    )

async def list_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ACKERMANS:
        return
    e = dict(sorted(errors.items(), key=lambda item: item[1], reverse=True))
    msg = "<b>Errors List:</b>\n"
    for x in e:
        msg += f"• <code>{x}:</code> <b>{e[x]}</b> #{x.identifier}\n"
    msg += f"{len(errors)} have occurred since startup."
    if len(msg) > 4096:
        with open("errors_msg.txt", "w+") as f:
            f.write(msg)
        await context.bot.send_document(
            update.effective_chat.id,
            open("errors_msg.txt", "rb"),
            caption="Too many errors have occured..",
            parse_mode="html",
        )
        return
    await update.effective_message.reply_text(msg, parse_mode="html")


application.add_error_handler(error_callback)
application.add_handler(CommandHandler("errors", list_errors))
