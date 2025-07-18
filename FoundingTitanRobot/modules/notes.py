import re, ast
from io import BytesIO
import random
from typing import Optional

import FoundingTitanRobot.modules.sql.notes_sql as sql
from FoundingTitanRobot import LOGGER, JOIN_LOGGER, SUPPORT_CHAT, application, TITANSHIFTERS
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from FoundingTitanRobot.modules.helper_funcs.handlers import MessageHandlerChecker
from FoundingTitanRobot.modules.helper_funcs.chat_status import user_admin, connection_status
from FoundingTitanRobot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from FoundingTitanRobot.modules.helper_funcs.msg_types import get_note_type
from FoundingTitanRobot.modules.helper_funcs.string_handling import (
    escape_invalid_curly_brackets,
)
from telegram import (
    InlineKeyboardMarkup,
    Message,
    Update,
    InlineKeyboardButton,
)
from telegram.constants import ParseMode, MessageLimit
from telegram.error import BadRequest
from telegram.helpers import escape_markdown, mention_markdown
from telegram.ext import (
    ContextTypes,
    CallbackContext,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    MessageHandler,
)
FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")
STICKER_MATCHER = re.compile(r"^###sticker(!photo)?###:")
BUTTON_MATCHER = re.compile(r"^###button(!photo)?###:(.*?)(?:\s|$)")
MYFILE_MATCHER = re.compile(r"^###file(!photo)?###:")
MYPHOTO_MATCHER = re.compile(r"^###photo(!photo)?###:")
MYAUDIO_MATCHER = re.compile(r"^###audio(!photo)?###:")
MYVOICE_MATCHER = re.compile(r"^###voice(!photo)?###:")
MYVIDEO_MATCHER = re.compile(r"^###video(!photo)?###:")
MYVIDEONOTE_MATCHER = re.compile(r"^###video_note(!photo)?###:")

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


# Do not async
async def get(update, context, notename, show_none=True, no_format=False):
    bot = context.bot
    chat_id = update.effective_message.chat.id
    note_chat_id = update.effective_chat.id
    note = sql.get_note(note_chat_id, notename)
    message = update.effective_message  # type: Optional[Message]

    if note:
        if MessageHandlerChecker.check_user(update.effective_user.id):
            return
        # If we're replying to a message, reply to that message (unless it's an error)
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id
        else:
            reply_id = message.message_id
        if note.is_reply:
            if JOIN_LOGGER:
                try:
                    await bot.forward_message(
                        chat_id=chat_id, from_chat_id=JOIN_LOGGER, message_id=note.value,
                    )
                except BadRequest as excp:
                    if excp.message != "Message to forward not found":
                        raise
                    await message.reply_text(
                        "This message seems to have been lost - I'll remove it "
                        "from your notes list.",
                    )
                    sql.rm_note(note_chat_id, notename)
            else:
                try:
                    await bot.forward_message(
                        chat_id=chat_id, from_chat_id=chat_id, message_id=note.value,
                    )
                except BadRequest as excp:
                    if excp.message == "Message to forward not found":
                        await message.reply_text(
                            "Looks like the original sender of this note has deleted "
                            "their message - sorry! Get your bot admin to start using a "
                            "message dump to avoid this. I'll remove this note from "
                            "your saved notes.",
                        )
                        sql.rm_note(note_chat_id, notename)
                    else:
                        raise
        else:
            VALID_NOTE_FORMATTERS = [
                "first",
                "last",
                "fullname",
                "username",
                "id",
                "chatname",
                "mention",
            ]
            if valid_format := escape_invalid_curly_brackets(
                note.value,
                VALID_NOTE_FORMATTERS,
            ):
                if not no_format and "%%%" in valid_format:
                    split = valid_format.split("%%%")
                    text = random.choice(split) if all(split) else valid_format
                else:
                    text = valid_format
                text = text.format(
                    first=escape_markdown(message.from_user.first_name),
                    last=escape_markdown(
                        message.from_user.last_name
                        or message.from_user.first_name,
                    ),
                    fullname=escape_markdown(
                        " ".join(
                            (
                                [
                                    message.from_user.first_name,
                                    message.from_user.last_name,
                                ]
                                if message.from_user.last_name
                                else [message.from_user.first_name]
                            ),
                        ),
                    ),
                    username=(
                        f"@{message.from_user.username}"
                        if message.from_user.username
                        else mention_markdown(
                            message.from_user.id,
                            message.from_user.first_name,
                        )
                    ),
                    mention=mention_markdown(
                        message.from_user.id,
                        message.from_user.first_name,
                    ),
                    chatname=escape_markdown(
                        (
                            message.chat.title
                            if message.chat.type != "private"
                            else message.from_user.first_name
                        ),
                    ),
                    id=message.from_user.id,
                )
            else:
                text = ""

            keyb = []
            parseMode = ParseMode.MARKDOWN
            buttons = sql.get_buttons(note_chat_id, notename)
            if no_format:
                parseMode = None
                text += revert_buttons(buttons)
            else:
                keyb = build_keyboard(buttons)

            keyboard = InlineKeyboardMarkup(keyb)

            try:
                if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                    await bot.send_message(
                        chat_id,
                        text,
                        reply_to_message_id=reply_id,
                        parse_mode=parseMode,
                        disable_web_page_preview=True,
                        reply_markup=keyboard,
                    )
                else:
                    if ENUM_FUNC_MAP[note.msgtype] == application.bot.send_sticker:
                        await ENUM_FUNC_MAP[note.msgtype](
                            chat_id,
                            note.file,
                            reply_to_message_id=reply_id,
                            reply_markup=keyboard,
                        )
                    else:
                        await ENUM_FUNC_MAP[note.msgtype](
                            chat_id,
                            note.file,
                            caption=text,
                            reply_to_message_id=reply_id,
                            parse_mode=parseMode,
                            reply_markup=keyboard,
                        )

            except BadRequest as excp:
                if excp.message == "Entity_mention_user_invalid":
                    await message.reply_text(
                        "Looks like you tried to mention someone I've never seen before. If you really "
                        "want to mention them, forward one of their messages to me, and I'll be able "
                        "to tag them!",
                    )
                elif FILE_MATCHER.match(note.value):
                    await message.reply_text(
                        "This note was an incorrectly imported file from another bot - I can't use "
                        "it. If you really need it, you'll have to save it again. In "
                        "the meantime, I'll remove it from your notes list.",
                    )
                    sql.rm_note(note_chat_id, notename)
                else:
                    await message.reply_text(
                        "This note could not be sent, as it is incorrectly formatted. Ask in "
                        f"@{SUPPORT_CHAT} if you can't figure out why!",
                    )
                    LOGGER.exception(
                        "Could not parse message #%s in chat %s",
                        notename,
                        str(note_chat_id),
                    )
                    LOGGER.warning("Message was: %s", str(note.value))
        return
    elif show_none:
        await message.reply_text("This note doesn't exist")


@connection_status
async def cmd_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    if len(args) >= 2 and args[1].lower() == "noformat":
        await get(update, context, args[0].lower(), show_none=True, no_format=True)
    elif len(args) >= 1:
        await get(update, context, args[0].lower(), show_none=True)
    else:
        await update.effective_message.reply_text("You did not specify the note name, check /notes for available notes.")


@connection_status
async def hash_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:].lower()
    await get(update, context, no_hash, show_none=False)


@connection_status
async def slash_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message, chat_id = update.effective_message.text, update.effective_chat.id
    no_slash = message[1:]
    note_list = sql.get_all_chat_notes(chat_id)

    try:
        noteid = note_list[int(no_slash) - 1]
        note_name = str(noteid).strip(">").split()[1]
        await get(update, context, note_name, show_none=False)
    except IndexError:
        await update.effective_message.reply_text("Wrong Note ID 😾")


@user_admin
@connection_status
async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]

    note_name, text, data_type, content, buttons = get_note_type(msg)
    note_name = note_name.lower()
    if data_type is None:
        await msg.reply_text("Dude, there's no note")
        return

    sql.add_note_to_db(
        chat_id, note_name, text, data_type, buttons=buttons, file=content,
    )

    await msg.reply_text(
        f"Yas! Added `{note_name}`.\nGet it with /get `{note_name}`, or `#{note_name}`",
        parse_mode=ParseMode.MARKDOWN,
    )

    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
        if text:
            await msg.reply_text(
                "Seems like you're trying to save a message from a bot. Unfortunately, "
                "bots can't forward bot messages, so I can't save the exact message. "
                "\nI'll save all the text I can, but if you want more, you'll have to "
                "forward the message yourself, and then save it.",
            )
        else:
            await msg.reply_text(
                "Bots are kinda handicapped by telegram, making it hard for bots to "
                "interact with other bots, so I can't save this message "
                "like I usually would - do you mind forwarding it and "
                "then saving that new message? Thanks!",
            )
        return


@user_admin
@connection_status
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) >= 1:
        notename = args[0].lower()

        chat_id = update.effective_chat.id
        if sql.rm_note(chat_id, notename):
            await update.effective_message.reply_text("Successfully removed note.")
        else:
            await update.effective_message.reply_text("That's not a note in my database!")


async def clearall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    member = await chat.get_member(user.id)
    if member.status != "owner" and user.id not in TITANSHIFTERS:
        await update.effective_message.reply_text(
            "Only the chat owner can clear all notes at once.",
        )
    else:
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Delete all notes", callback_data="notes_rmall",
                    ),
                ],
                [InlineKeyboardButton(text="Cancel", callback_data="notes_cancel")],
            ],
        )
        await update.effective_message.reply_text(
            f"Are you sure you would like to clear ALL notes in {chat.title}? This action cannot be undone.",
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN,
        )


async def clearall_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat = update.effective_chat
    message = update.effective_message
    member = await chat.get_member(query.from_user.id)
    if query.data == "notes_rmall":
        if member.status == "owner" or query.from_user.id in TITANSHIFTERS:
            note_list = sql.get_all_chat_notes(chat.id)
            try:
                for notename in note_list:
                    note = notename.name.lower()
                    sql.rm_note(chat.id, note)
                await message.edit_text("Deleted all notes.")
            except BadRequest:
                return

        if member.status == "administrator":
            await query.answer("Only owner of the chat can do this.")

        if member.status == "member":
            await query.answer("You need to be admin to do this.")
    elif query.data == "notes_cancel":
        if member.status == "owner" or query.from_user.id in TITANSHIFTERS:
            await message.edit_text("Clearing of all notes has been cancelled.")
            return
        if member.status == "administrator":
            await query.answer("Only owner of the chat can do this.")
        if member.status == "member":
            await query.answer("You need to be admin to do this.")


@connection_status
async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    MAX_TEXT_LENGTH = MessageLimit.MAX_TEXT_LENGTH
    chat_id = update.effective_chat.id
    note_list = sql.get_all_chat_notes(chat_id)
    notes = len(note_list) + 1
    msg = "Get note by `/notenumber` or `#notename` \n\n  *ID*    *Note* \n"
    for note_id, note in zip(range(1, notes), note_list):
        if note_id < 10:
            note_name = f"`{note_id:2}.`  `#{(note.name.lower())}`\n"
        else:
            note_name = f"`{note_id}.`  `#{(note.name.lower())}`\n"
        if len(msg) + len(note_name) > MAX_TEXT_LENGTH:
            await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if not note_list:
        try:
            await update.effective_message.reply_text("No notes in this chat!")
        except BadRequest:
            await update.effective_message.reply_text("No notes in this chat!", quote=False)

    elif len(msg) != 0:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def __import_data__(chat_id, data):
    failures = []
    for notename, notedata in data.get("extra", {}).items():
        match = FILE_MATCHER.match(notedata)
        matchsticker = STICKER_MATCHER.match(notedata)
        matchbtn = BUTTON_MATCHER.match(notedata)
        matchfile = MYFILE_MATCHER.match(notedata)
        matchphoto = MYPHOTO_MATCHER.match(notedata)
        matchaudio = MYAUDIO_MATCHER.match(notedata)
        matchvoice = MYVOICE_MATCHER.match(notedata)
        matchvideo = MYVIDEO_MATCHER.match(notedata)
        matchvn = MYVIDEONOTE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            if notedata := notedata[match.end() :].strip():
                sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
        elif matchsticker:
            if content := notedata[matchsticker.end() :].strip():
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.STICKER, file=content,
                )
        elif matchbtn:
            parse = notedata[matchbtn.end() :].strip()
            notedata = parse.split("<###button###>")[0]
            buttons = parse.split("<###button###>")[1]
            if buttons := ast.literal_eval(buttons):
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.BUTTON_TEXT,
                    buttons=buttons,
                )
        elif matchfile:
            file = notedata[matchfile.end() :].strip()
            file = file.split("<###TYPESPLIT###>")
            notedata = file[1]
            if content := file[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.DOCUMENT, file=content,
                )
        elif matchphoto:
            photo = notedata[matchphoto.end() :].strip()
            photo = photo.split("<###TYPESPLIT###>")
            notedata = photo[1]
            if content := photo[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.PHOTO, file=content,
                )
        elif matchaudio:
            audio = notedata[matchaudio.end() :].strip()
            audio = audio.split("<###TYPESPLIT###>")
            notedata = audio[1]
            if content := audio[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.AUDIO, file=content,
                )
        elif matchvoice:
            voice = notedata[matchvoice.end() :].strip()
            voice = voice.split("<###TYPESPLIT###>")
            notedata = voice[1]
            if content := voice[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.VOICE, file=content,
                )
        elif matchvideo:
            video = notedata[matchvideo.end() :].strip()
            video = video.split("<###TYPESPLIT###>")
            notedata = video[1]
            if content := video[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.VIDEO, file=content,
                )
        elif matchvn:
            video_note = notedata[matchvn.end() :].strip()
            video_note = video_note.split("<###TYPESPLIT###>")
            notedata = video_note[1]
            if content := video_note[0]:
                sql.add_note_to_db(
                    chat_id, notename[1:], notedata, sql.Types.VIDEO_NOTE, file=content,
                )
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            await application.bot.send_document(
                chat_id,
                document=output,
                filename="failed_imports.txt",
                caption="These files/photos failed to import due to originating "
                "from another bot. This is a telegram API restriction, and can't "
                "be avoided. Sorry for the inconvenience!",
            )


def __stats__():
    return f"• {sql.num_notes()} notes, across {sql.num_chats()} chats."


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return f"There are `{len(notes)}` notes in this chat."


__help__ = """
 • `/get <notename>`*:* get the note with this notename
 • `#<notename>`*:* same as /get
 • `/notes` or `/saved`*:* list all saved notes in this chat
 • `/number` *:* Will pull the note of that number in the list
If you would like to retrieve the contents of a note without any formatting, use `/get <notename> noformat`. This can \
be useful when updating a current note

*Admins only:*
 • `/save <notename> <notedata>`*:* saves notedata as a note with name notename
A button can be added to a note by using standard markdown link syntax - the link should just be prepended with a \
`buttonurl:` section, as such: `[somelink](buttonurl:example.com)`. Check `/markdownhelp` for more info
 • `/save <notename>`*:* save the replied message as a note with name notename
 Separate diff replies by `%%%` to get random notes
 *Example:*
 `/save notename
 Reply 1
 %%%
 Reply 2
 %%%
 Reply 3`
 • `/clear <notename>`*:* clear note with this name
 • `/removeallnotes`*:* removes all notes from the group
 *Note:* Note names are case-insensitive, and they are automatically converted to lowercase before getting saved.

"""

__mod_name__ = "Notes"

GET_HANDLER = CommandHandler("get", cmd_get, block=False)
HASH_GET_HANDLER = MessageHandler(filters.Regex(r"^#[^\s]+"), hash_get, block=False)
SLASH_GET_HANDLER = MessageHandler(filters.Regex(r"^/\d+$"), slash_get, block=False)
SAVE_HANDLER = CommandHandler("save", save, block=False)
DELETE_HANDLER = CommandHandler("clear", clear, block=False)

LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"], list_notes, admin_ok=True, block=False)

CLEARALL = DisableAbleCommandHandler("removeallnotes", clearall, block=False)
CLEARALL_BTN = CallbackQueryHandler(clearall_btn, pattern=r"notes_.*", block=False)

application.add_handler(GET_HANDLER)
application.add_handler(SAVE_HANDLER)
application.add_handler(LIST_HANDLER)
application.add_handler(DELETE_HANDLER)
application.add_handler(HASH_GET_HANDLER)
application.add_handler(SLASH_GET_HANDLER)
application.add_handler(CLEARALL)
application.add_handler(CLEARALL_BTN)
