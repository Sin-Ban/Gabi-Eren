import json
import html
import requests
from time import sleep

from requests.exceptions import (
RequestException, 
Timeout,
TooManyRedirects, 
ConnectionError, 
ReadTimeout, 
)
        
from telegram import Message, Update
from telegram.helpers import mention_html, mention_markdown, escape_markdown
from telegram.error import BadRequest, RetryAfter, Forbidden
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ContextTypes,
    filters,
    MessageHandler
)

import FoundingTitanRobot.modules.redis.chatbot_redis as redis
from FoundingTitanRobot import application
from FoundingTitanRobot.modules.log_channel import gloggable
from FoundingTitanRobot.modules.helper_funcs.filters import CustomFilters
from FoundingTitanRobot.modules.helper_funcs.chat_status import user_admin, sudo_plus

@user_admin
@gloggable
async def add_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    is_enabled = redis.is_chatbot(chat.id)
    if chat.type == "private":
        await msg.reply_text("You can't enable AI in PM.")
        return
    if not is_enabled:
        redis.set_chatbot(chat.id)
        await msg.reply_text("Chat Bot successfully enabled for this chat!")
        return f"<b>{html.escape(chat.title)}:</b>\nAI_ENABLED\n<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
    await msg.reply_text("Chat Bot is already enabled for this chat!")
    return ""

@user_admin
@gloggable
async def rem_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    is_enabled = redis.is_chatbot(chat.id)
    if chat.type == "private":
        await msg.reply_text("You can't enable/disable AI in PM.")
        return
    if not is_enabled:
        await msg.reply_text("Chat Bot isn't enabled here in the first place!")
        return ""
    redis.rem_chatbot(chat.id)
    await msg.reply_text("ChatBot disabled successfully!")
    return f"<b>{html.escape(chat.title)}:</b>\nAI_DISABLED\n<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"

async def check_message(context: CallbackContext, message):
    reply_msg = message.reply_to_message
    bot_data = await context.bot.get_me()

    bot_id, bot_name, bot_username = bot_data.id, bot_data.first_name, bot_data.name
    triggers = ["Eren", "ereh", bot_name, bot_username]
    msg = message.text.lower()
    for x in triggers:
        if x.lower() in msg.split():
            return True
    if reply_msg:
        if reply_msg.from_user.id == bot_id:
            return True
    else:
        return False

async def chatbot_talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = update.effective_message
    bot = context.bot   
    query = update.message.text     
    is_chatbot = redis.is_chatbot(chat_id)
    if not is_chatbot:
        return
    if not await check_message(context, msg):
        return                
    try:
        user_id = update.message.from_user.id
        api = f"http://api.brainshop.ai/get?bid=158496&key=ovxzFQTiezBoUkZf&uid={user_id}&msg={query}"
        armin = requests.get(api)
        eren = json.loads(armin.text)
        await bot.send_chat_action(chat_id, action="typing")
        mikasa = eren["cnt"]
        sleep(0.3)
        await msg.reply_text(mikasa)       
    except (RequestException, Timeout, TooManyRedirects, ConnectionError, ReadTimeout, BadRequest) as e:
        print(e)
        await msg.reply_text("Encountered {e}! Report it at @FoundingTitanSupport as soon as possible!")

@sudo_plus
async def list_chatbot_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chats = redis.list_chatbots()
    text = "<b>AI-Enabled Chats</b>\n"
    for chat in chats:
        try:
            x = await context.bot.get_chat(chat)
            name = x.title or x.first_name
            text += f"• <code>{name}</code>\n"
        except (BadRequest, Forbidden):
            redis.rem_chatbot(chat)
        except RetryAfter as e:
            sleep(e.retry_after)
    await update.effective_message.reply_text(text, parse_mode="HTML")

    
__help__ = """
Chatbot utilizes the Brain Shop's api which allows Eren to talk and provide a more interactive group chat experience.
*Admins only Commands*:
`/addchat`*:* Enables Chatbot mode in the chat.
`/rmchat`*:* Disables Chatbot mode in the chat.
"""

__mod_name__ = "ChatBot"

ADD_CHAT_HANDLER = CommandHandler("addchat", add_chat, block=False)
REMOVE_CHAT_HANDLER = CommandHandler("rmchat", rem_chat, block=False)
CHATBOT_HANDLER = MessageHandler(
    filters.TEXT & (~filters.Regex(r"^#[^\s]+") & ~filters.Regex(r"^!")
                    & ~filters.Regex(r"^\/")), chatbot_talk, block=False)
LIST_AI_HANDLER = CommandHandler(["listchats", "listai", "listchatbots"], list_chatbot_chats, block=False)

application.add_handler(ADD_CHAT_HANDLER)
application.add_handler(REMOVE_CHAT_HANDLER)
application.add_handler(CHATBOT_HANDLER)
application.add_handler(LIST_AI_HANDLER)

__handlers__ = [
    ADD_CHAT_HANDLER,
    REMOVE_CHAT_HANDLER,
    CHATBOT_HANDLER,
    LIST_AI_HANDLER,
]
