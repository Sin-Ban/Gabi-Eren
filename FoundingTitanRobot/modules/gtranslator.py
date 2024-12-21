from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ContextTypes

from gpytranslate import SyncTranslator

from FoundingTitanRobot import application
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler


trans = SyncTranslator()


async def totranslate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    reply_msg = message.reply_to_message
    if not reply_msg:
        await message.reply_text("Reply to a message to translate it!")
        return
    if reply_msg.caption:
        to_translate = reply_msg.caption
    elif reply_msg.text:
        to_translate = reply_msg.text
    try:
        args = message.text.split()[1].lower()
        if "//" in args:
            source = args.split("//")[0]
            dest = args.split("//")[1]
        else:
            source = trans.detect(to_translate)
            dest = args
    except IndexError:
        source = trans.detect(to_translate)
        dest = "en"
    translation = trans(to_translate,
                              sourcelang=source, targetlang=dest)
    reply = f"<b>Translated from {source} to {dest}</b>:\n" \
        f"<code>{translation.text}</code>"

    await message.reply_text(reply, parse_mode=ParseMode.HTML)


async def languages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Click on the button below to see the list of supported language codes.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Language codes",
                        url="https://telegra.ph/Lang-Codes-03-19-3"
                        ),
                ],
            ],
        disable_web_page_preview=True
    )
        )

__mod_name__ = "Translator"

TRANSLATE_HANDLER = DisableAbleCommandHandler(["tr", "tl"], totranslate, block=False)
LANGUAGES_HANDLER = DisableAbleCommandHandler(["langs", "languages"], languages, block=False)

application.add_handler(TRANSLATE_HANDLER)
application.add_handler(LANGUAGES_HANDLER)

__mod_name__ = "Translator"
__command_list__ = ["tr", "tl", "langs", "languages"]
__handlers__ = [TRANSLATE_HANDLER, LANGUAGES_HANDLER]
