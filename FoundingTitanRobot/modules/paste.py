from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ContextTypes
from telegram.constants import ParseMode

from FoundingTitanRobot import application, eren_paste
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler

async def pastebin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    msg = update.effective_message
    if msg.reply_to_message:
        text = msg.reply_to_message.text
    elif len(args) >= 1:
        text = msg.text.split(None, 1)[1]
    else:
        await msg.reply_text("reply to any message or just do /paste <what you want to paste>")
    try:
        url = eren_paste.create_paste(api_paste_name="Public Paste", api_paste_code=str(text), api_paste_expire_date="2W")
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("PasteBin", url=url)]])
        await msg.reply_text("Pasted to PasteBin Service", reply_markup=markup, disable_web_page_preview=True)
    except Exception as e:
        await msg.reply_text(f"Failed to Paste because of {e}, report it at @FoundingTitanSupport")
        print(e)

PASTE_BIN_HANDLER = DisableAbleCommandHandler("paste", pastebin, block=False)

application.add_handler(PASTE_BIN_HANDLER)
