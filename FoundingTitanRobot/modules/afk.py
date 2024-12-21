from typing import Optional
import time
import random
from datetime import datetime
import humanize

from telegram import Message, User
from telegram import MessageEntity
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import filters, MessageHandler, ContextTypes

from FoundingTitanRobot import application
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler, DisableAbleMessageHandler
from FoundingTitanRobot.modules.redis.afk_redis import start_afk, end_afk, is_user_afk, afk_reason
from FoundingTitanRobot import REDIS
from FoundingTitanRobot.modules.users import get_user_id

from FoundingTitanRobot.modules.helper_funcs.alternate import send_message
from FoundingTitanRobot.modules.helper_funcs.readable_time import get_readable_time

AFK_GROUP = 7
AFK_REPLY_GROUP = 8


async def afk(update, context: ContextTypes.DEFAULT_TYPE):
    args = update.effective_message.text.split(None, 1)
    user = update.effective_user
    if not user:  # ignore channels
        return

    if user.id == 777000:
        return
    start_afk_time = time.time()
    reason = args[1] if len(args) >= 2 else "none"
    start_afk(update.effective_user.id, reason)
    REDIS.set(f'afk_time_{update.effective_user.id}', start_afk_time)
    fname = update.effective_user.first_name
    try:
        await update.effective_message.reply_text(f"{fname} is now Away!")
    except BadRequest:
        pass

async def no_longer_afk(update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    if not user:  # ignore channels
        return

    if not is_user_afk(user.id):  #Check if user is afk or not
        return
    end_afk_time = get_readable_time((time.time() - float(REDIS.get(f'afk_time_{user.id}'))))
    REDIS.delete(f'afk_time_{user.id}')
    if res := end_afk(user.id):
        if message.new_chat_members:  # dont say msg
            return
        firstname = update.effective_user.first_name
        try:
            options = [
                "{} Is wasting his time in the chat! The time he was studying {}",
                "The Dead {} Came Back From His Grave! The time he was dead {}",
                "Welcome back {}! Time you were afk {}",
                "Good to hear from you again {}, the chat was waiting for you since {}",
                "Hey {}! Why weren't you online for {}",
                "{} why did you came back after {}",
                "{} Is now back online!, he was offline for {}",
                "OwO, Welcome back {}, time you were afk {}",
                "Welcome to hell again {}, time you were in heaven was {}",
                "{} is no longer Afk Time you were afk: {}",
            ]
            chosen_option = random.choice(options)
            await update.effective_message.reply_text(
                chosen_option.format(firstname, end_afk_time),
            )
        except Exception:
            return
            


async def reply_afk(update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    userc = update.effective_user
    userc_id = userc.id
    if message.entities and message.parse_entities(
        [MessageEntity.TEXT_MENTION, MessageEntity.MENTION]):
        entities = message.parse_entities(
            [MessageEntity.TEXT_MENTION, MessageEntity.MENTION])

        chk_users = []
        for ent in entities:
            if ent.type == MessageEntity.TEXT_MENTION:
                user_id = ent.user.id
                fst_name = ent.user.first_name

                if user_id in chk_users:
                    return
                chk_users.append(user_id)

            elif ent.type == MessageEntity.MENTION:
                user_id = await get_user_id(message.text[ent.offset:ent.offset +
                                                   ent.length])
                if not user_id:
                    # Should never happen, since for a user to become AFK they must have spoken. Maybe changed username?
                    return

                if user_id in chk_users:
                    return
                chk_users.append(user_id)

                try:
                    chat = await context.bot.get_chat(user_id)
                except BadRequest:
                    print(f"Error: Could not fetch userid {user_id} for AFK module")
                    return
                fst_name = chat.first_name

            else:
                return

            await check_afk(update, context, user_id, fst_name, userc_id)

    elif message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        fst_name = message.reply_to_message.from_user.first_name
        await check_afk(update, context, user_id, fst_name, userc_id)


async def check_afk(update, context, user_id, fst_name, userc_id):
    if is_user_afk(user_id):
        reason = afk_reason(user_id)
        since_afk = get_readable_time((time.time() - float(REDIS.get(f'afk_time_{user_id}'))))
        if int(userc_id) == int(user_id):
            return
        if reason == "none":
            res = f"{fst_name} is afk!\nLast seen: {since_afk} Ago."
        else:
            res = f"{fst_name} is afk!\nReason: {reason}\nLast seen: {since_afk} Ago."

        await update.effective_message.reply_text(res)


def __user_info__(user_id):
    is_afk = is_user_afk(user_id)
    text = ""
    if is_afk:
        since_afk = get_readable_time((time.time() - float(REDIS.get(f'afk_time_{user_id}'))))
        text = "This user is currently afk (away from keyboard)."
        text += f"\nLast Seen: {since_afk} Ago."
       
    else:
        text = "This user currently isn't afk (not away from keyboard)."
    return text


def __gdpr__(user_id):
    end_afk(user_id)


AFK_HANDLER = DisableAbleCommandHandler("afk", afk, block=False)
AFK_REGEX_HANDLER = MessageHandler(filters.Regex("(?i)brb"), afk)
NO_AFK_HANDLER = MessageHandler(filters.ALL & filters.ChatType.GROUPS, no_longer_afk, block=False)
AFK_REPLY_HANDLER = MessageHandler(filters.ALL & filters.ChatType.GROUPS, reply_afk, block=False)

application.add_handler(AFK_HANDLER, AFK_GROUP)
application.add_handler(AFK_REGEX_HANDLER, AFK_GROUP)
application.add_handler(NO_AFK_HANDLER, AFK_GROUP)
application.add_handler(AFK_REPLY_HANDLER, AFK_REPLY_GROUP)
