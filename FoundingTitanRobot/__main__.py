import html
import importlib
import asyncio
import json
import random
import time
import re
import traceback
import FoundingTitanRobot.modules.fun_strings as fs
from sys import argv
from typing import Optional
import telegram
# from threading import Thread 

from FoundingTitanRobot import (
    ALLOW_EXCL,
    CERT_PATH,
    DONATION_LINK,
    POLLS,
    LOGGER,
    OWNER_ID,
    PORT,
    TOKEN,
    URL,
    WEBHOOK,
    SUPPORT_CHAT,
    application,
    StartTime,
    telethn,
    pbot)

# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from FoundingTitanRobot.modules import ALL_MODULES
from FoundingTitanRobot.modules.helper_funcs.chat_status import is_user_admin
from FoundingTitanRobot.modules.helper_funcs.alternate import typing_action
from FoundingTitanRobot.modules.helper_funcs.misc import paginate_modules
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import (
    BadRequest,
    ChatMigrated,
    NetworkError,
    TelegramError,
    TimedOut,
    Forbidden,
)
from telegram.ext import (
    ContextTypes,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    filters,
    MessageHandler,
)
from telegram.ext import ApplicationHandlerStop
from telegram.helpers import escape_markdown
from pyrogram.sync import idle


def get_readable_time(seconds: float) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += f"{time_list.pop()}, "

    time_list.reverse()
    ping_time += ":".join(time_list)

    return ping_time

PM_START_TEXT = """
Hey {user}!
I'm [Eren]({links}), an Attack on Titan anime themed group management bot.
Built by weebs for weebs, I specialize in managing anime eccentric communities.
"""

buttons = [
    [
        InlineKeyboardButton(
            text="➕ Add Me", url="t.me/FoundingTitanRobot?startgroup=true"),    
        InlineKeyboardButton(
              text="⚙️ Help", callback_data="help_back"),   
   ],
    [      
       InlineKeyboardButton(
            text="🧾 Quick Setup", url="https://t.me/foundingtitanupdates/4"),        
          InlineKeyboardButton(
            text="📋 ChangeLogs", url="https://t.me/FoundingTitanupdates"),

   ],
    [      
          InlineKeyboardButton(
            text="🚑 Support", url="https://t.me/Foundingtitansupport"),
    ],
] 



HELP_STRINGS = """
Hello there, I'm Eren!
To make me functional, make sure that i have enough rights in your group.
*Helpful commands*:
- /start: Starts me! You've probably already used this.
- /help: Sends this message; I'll tell you more about myself!
- /donate: Gives you info on how to support me and my owner.
If you want to report bugs or have any questions on how to use me then feel free to reach out: @FoundingTitanSupport.
All commands can be used with the following: / !
List of all the Modules:
"""

DONATE_STRING = """Plant a tree and give water to birds, that's your donation.."""


IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []
CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module(
        f"FoundingTitanRobot.modules.{module_name}"
    )
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__ # type: ignore

    if imported_module.__mod_name__.lower() not in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


async def send_help(chat_id, text, buttons=None):
    if not buttons:
        buttons = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    await application.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=buttons,
    )


# async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # pprint(eval(str(update)))
    # await update.effective_message.reply_text("Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN)
    # await update.effective_message.reply_text("This person edited a message")
    # print(update.effective_message)


@typing_action
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    uptime = get_readable_time((time.time() - StartTime))
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                await send_help(update.effective_chat.id, HELP_STRINGS)
            elif args[0].lower().startswith("ghelp_"):
                mod = args[0].lower().split("_", 1)[1]
                if not HELPABLE.get(mod, False):
                    return
                await send_help(
                    update.effective_chat.id,
                    HELPABLE[mod].__help__,
                    InlineKeyboardMarkup(
                        [[InlineKeyboardButton(text="Back", callback_data="help_back")]]
                    ),
                )

            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = await application.bot.getChat(match[1])

                if await is_user_admin(chat, update.effective_user.id):
                    await send_settings(match[1], update.effective_user.id, False)
                else:
                    await send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            first_name = update.effective_user.first_name
            links = random.choice(fs.START_PICS)
            await update.effective_message.reply_text(
                PM_START_TEXT.format(
                user=escape_markdown(first_name), links=links),                
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                read_timeout=60,
            )
    else:
        await update.effective_message.reply_text(
            f"I'm awake already!\n<b>Haven't slept since:</b> <code>{uptime}</code>",
            parse_mode=ParseMode.HTML,
        )


async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    LOGGER.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    message = (
        "An exception was raised while handling an update\n"
        "<pre>update = {}</pre>\n\n"
        "<pre>{}</pre>"
    ).format(
        html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False)),
        html.escape(tb),
    )

    if len(message) >= 4096:
        message = message[:4096]
    # Finally, send the message
    await context.bot.send_message(chat_id=OWNER_ID, text=message, parse_mode=ParseMode.HTML)


# for test purposes
def error_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    try:
        raise error
    except Forbidden:
        print("no nono1")
        print(error)
        # remove update.message.chat_id from conversation list
    except BadRequest as err:
        print("no nono2")
        print(f"BadRequest caught, full traceback: {err}")
        print(error)

        # handle malformed requests - read more below!
    except TimedOut:
        print("Timed Out!")
        # handle slow connection problems
    except NetworkError:
        print("network error!")
        # handle other connection problems
    except ChatMigrated as err:
        print(f"Chat migrated to {err.new_chat_id}")
        print(err)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        print(error)
        # handle all other telegram related errors


async def help_button(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)

    print(query.message.chat.id)

    try:
        if mod_match:
            module = mod_match[1]
            text = f"Here is the help for the *{HELPABLE[module].__mod_name__}* module:\n{HELPABLE[module].__help__}"
            await query.message.edit_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="Back", callback_data="help_back")]]
                ),
            )

        elif prev_match:
            curr_page = int(prev_match[1])
            await query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, HELPABLE, "help")
                ),
            )

        elif next_match:
            next_page = int(next_match[1])
            await query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, HELPABLE, "help")
                ),
            )

        elif back_match:
            await query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, HELPABLE, "help")
                ),
            )

        # ensure no spinny white circle
        await context.bot.answer_callback_query(query.id)
            # await query.message.delete()

    except BadRequest:
        pass

async def eren_callback_data(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "eren_back":
        first_name = update.effective_user.first_name
        links = random.choice(fs.START_PICS)
        await query.message.edit_text(
                PM_START_TEXT.format(
                user=escape_markdown(first_name), links=links),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                write_timeout=60,
                disable_web_page_preview=False,
        )


@typing_action
async def get_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:
        if len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
            module = args[1].lower()
            await update.effective_message.reply_text(
                f"Contact me in PM to get help of {module.capitalize()}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Help",
                                url=f"t.me/{context.bot.username}?start=ghelp_{module}",
                            )
                        ]
                    ]
                ),
            )
            return
        await update.effective_message.reply_text(
            "Contact me in PM to get the list of possible commands.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Help",
                            url=f"t.me/{context.bot.username}?start=help",
                        )
                    ]
                ]
            ),
        )
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = f"Here is the available help for the *{HELPABLE[module].__mod_name__}* module:\n{HELPABLE[module].__help__}"
        await send_help(
            chat.id,
            text,
            InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="help_back")]]
            ),
        )

    else:
        await send_help(chat.id, HELP_STRINGS)


async def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                f"*{mod.__mod_name__}*:\n{mod.__user_settings__(user_id)}"
                for mod in USER_SETTINGS.values()
            )
            await application.bot.send_message(
                user_id,
                "These are your current settings:" + "\n\n" + settings,
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            await application.bot.send_message(
                user_id,
                "Seems like there aren't any user specific settings available :'(",
                parse_mode=ParseMode.MARKDOWN,
            )

    elif CHAT_SETTINGS:
        chat_name = await application.bot.getChat(chat_id).title
        await application.bot.send_message(
            user_id,
            text=f"Which module would you like to check {chat_name}'s settings for?",
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
            ),
        )
    else:
        await application.bot.send_message(
            user_id,
            "Seems like there aren't any chat settings available :'(\nSend this "
            "in a group chat you're admin in to find its current settings!",
            parse_mode=ParseMode.MARKDOWN,
        )


async def settings_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    bot = context.bot
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match[1]
            module = mod_match[2]
            chat = await bot.get_chat(chat_id)
            text = f"*{escape_markdown(chat.title)}* has the following settings for the *{CHAT_SETTINGS[module].__mod_name__}* module:\n\n{CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)}"
            await query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Back",
                                callback_data=f"stngs_back({chat_id})",
                            )
                        ]
                    ]
                ),
            )

        elif prev_match:
            chat_id = prev_match[1]
            curr_page = int(prev_match[2])
            chat = await bot.get_chat(chat_id)
            await query.message.reply_text(
                f"Hi there! There are quite a few settings for {chat.title} - go ahead and pick what you're interested in.",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif next_match:
            chat_id = next_match[1]
            next_page = int(next_match[2])
            chat = await bot.get_chat(chat_id)
            await query.message.reply_text(
                f"Hi there! There are quite a few settings for {chat.title} - go ahead and pick what you're interested in.",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif back_match:
            chat_id = back_match[1]
            chat = await bot.get_chat(chat_id)
            await query.message.reply_text(
                text=f"Hi there! There are quite a few settings for {escape_markdown(chat.title)} - go ahead and pick what you're interested in.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        # ensure no spinny white circle
        await bot.answer_callback_query(query.id)
        await query.message.delete()
    except BadRequest as excp:
        if excp.message not in [
            "Message is not modified",
            "Query_id_invalid",
            "Message can't be deleted",
        ]:
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))


async def get_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    # ONLY send settings in PM
    if chat.type == chat.PRIVATE:
        await send_settings(chat.id, user.id, True)

    elif await is_user_admin(chat, user.id): # type: ignore
        text = "Click here to get this chat's settings, as well as yours."
        await msg.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Settings",
                            url=f"t.me/{context.bot.username}?start=stngs_{chat.id}",
                        )
                    ]
                ]
            ),
        )
    else:
        text = "Click here to check your settings."


async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.effective_message.reply_text(
            DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )

        if OWNER_ID != 254318997 and DONATION_LINK:
            await update.effective_message.reply_text(
                f"You can also donate to the person currently running me [here]({DONATION_LINK})",
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        user = update.effective_message.from_user
        bot = context.bot
        try:
            await bot.send_message(
                user.id,
                DONATE_STRING,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )

            await update.effective_message.reply_text(
                "I've PM'ed you about donating to my owner!"
            )
        except Forbidden:
            await update.effective_message.reply_text(
                "Contact me in PM first to get donation information."
            )

async def migrate_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = telegram.Message
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("Migrating from %s, to %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        try:
            mod.__migrate__(old_chat, new_chat)
            LOGGER.info(f"Successfully Migrated, old chat id: {old_chat}, new chat id: {new_chat}")
        except Exception as err:
            LOGGER.info(f"An Error occured while migrating old chat id:{old_chat} to new chat id {new_chat}, Full Traceback: {err}")

def main():
    if SUPPORT_CHAT is not None and isinstance(SUPPORT_CHAT, str):
        try:
            pbot.send_message(f"-1001182777212", "[I am now online!](https://telegra.ph/file/69db8d7439cd6413bc3a7.mp4)")
        except Exception as e:
            LOGGER.warning(f"Bot isnt able to send message to support_chat, go and check!, error {e}")
            
    # test_handler = CommandHandler("test", test, block=False)
    start_handler = DisableAbleCommandHandler("start", start, block=False)

    help_handler = DisableAbleCommandHandler("help", get_help, block=False)
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_.*", block=False)

    settings_handler = CommandHandler("settings", get_settings)
    settings_callback_handler = CallbackQueryHandler(settings_button, pattern=r"stngs_", block=False)

    data_callback_handler = CallbackQueryHandler(eren_callback_data, pattern=r"eren_back", block=False)
    donate_handler = CommandHandler("donate", donate, block=False)
    migrate_handler = MessageHandler(filters.StatusUpdate.MIGRATE, migrate_chats, block=False)

    # application.add_handler(test_handler)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(data_callback_handler)
    application.add_handler(settings_handler)
    application.add_handler(help_callback_handler)
    application.add_handler(settings_callback_handler)
    application.add_handler(migrate_handler)
    application.add_handler(donate_handler)
    application.add_error_handler(error_callback)

    if WEBHOOK:
        LOGGER.info("Using Webhooks to start Eren..")
        if CERT_PATH:
            application.run_webhook(listen="0.0.0.0", 
                                  port=PORT, 
                                  url_path=TOKEN, 
                                  webhook_url=URL + TOKEN, 
                                  drop_pending_updates=True,
                                  allowed_updates=Update.ALL_TYPES,
                                  max_connections=50,
                                  key='/home/sasuke/private.key',
                                  cert='/home/sasuke/cert.pem')
        else:
            application.run_webhook(listen="0.0.0.0", 
                              port=PORT, 
                              url_path=TOKEN, 
                              webhook_url=URL + TOKEN, 
                              drop_pending_updates=True,
                              allowed_updates=Update.ALL_TYPES,
                              max_connections=50)
        LOGGER.info("Eren has been started using webhooks!")
    
    else:
        LOGGER.info("Eren is now alive and functioning, using polling method to fetch updates")
        application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
        
    if len(argv) in {1, 3, 4}:
        telethn.run_until_disconnected()

    else:
        telethn.disconnect()
    idle()
    
    
    
if __name__ == '__main__':
    LOGGER.info(f"Successfully loaded modules: {str(ALL_MODULES)}")
    telethn.start(bot_token=TOKEN)
    pbot.start() # type: ignore
    main()
