import html
import re
import os
import requests
import datetime
import platform
import subprocess
from subprocess import PIPE

from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import ChannelParticipantsAdmins
from telethon import events

from telegram import Update, MessageEntity, __version__
from telegram.ext import CallbackContext, CommandHandler, ContextTypes
from telegram.constants import ParseMode, MessageLimit
MAX_TEXT_LENGTH = MessageLimit.MAX_TEXT_LENGTH
from telegram.error import BadRequest
from telegram.helpers import escape_markdown, mention_html
    
from FoundingTitanRobot import (
    ACKERMANS,
    OWNER_ID,
    TITANSHIFTERS,
    ROYALS,
    SCOUTS,
    GARRISONS,
    INFOPIC,
    MARIN,
    application,
    DEVIL_SUCCESSOR,
)
from FoundingTitanRobot.__main__ import STATS, TOKEN, USER_INFO
import FoundingTitanRobot.modules.redis.userinfo_redis as redis
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from FoundingTitanRobot.modules.sql.global_bans_sql import is_user_gbanned
from FoundingTitanRobot.modules.redis.afk_redis import is_user_afk, afk_reason
from FoundingTitanRobot.modules.sql.users_sql import get_user_num_chats
from FoundingTitanRobot.modules.helper_funcs.chat_status import sudo_plus
from FoundingTitanRobot.modules.helper_funcs.extraction import extract_user
from FoundingTitanRobot import telethn as ErenTelethonClient


async def no_by_per(totalhp, percentage):
    """
    rtype: num of `percentage` from total
    eg: 1000, 10 -> 10% of 1000 (100)
    """
    return totalhp * percentage / 100


async def get_percentage(totalhp, earnedhp):
    """
    rtype: percentage of `totalhp` num
    eg: (1000, 100) will return 10%
    """

    matched_less = totalhp - earnedhp
    per_of_totalhp = 100 - matched_less * 100.0 / totalhp
    per_of_totalhp = str(int(per_of_totalhp))
    return per_of_totalhp


async def hpmanager(user):
    total_hp = (get_user_num_chats(user.id) + 10) * 10

    if not is_user_gbanned(user.id):

        # Assign new var `new_hp` since we need `total_hp` in
        # end to calculate percentage.
        new_hp = total_hp

        # if no username decrease 25% of hp.
        if not user.username:
            new_hp -= await no_by_per(total_hp, 25)
        try:
            pfp = await application.bot.get_user_profile_photos(user.id)
            p_fp = pfp.photos[0][-1]
        except IndexError:
            # no profile photo ==> -25% of hp
            new_hp -= await no_by_per(total_hp, 25)
        # if no /setme exist ==> -20% of hp
        if not redis.get_user_info(user.id):
            new_hp -= await no_by_per(total_hp, 20)
        # if no bio exist ==> -10% of hp
        if not redis.get_user_bio(user.id):
            new_hp -= await no_by_per(total_hp, 10)

        if is_user_afk(user.id):
            afkst = afk_reason(user.id)
            # if user is afk and no reason then decrease 7%
            # else if reason exist decrease 5%
            new_hp -= await no_by_per(total_hp, 5) if afkst else no_by_per(total_hp, 7)
            # fbanned users will have (2*number of fbans) less from max HP
            # Example: if HP is 100 but user has 5 diff fbans
            # Available HP is (2*5) = 10% less than Max HP
            # So.. 10% of 100HP = 90HP

    else:
        new_hp = await no_by_per(total_hp, 5)
    hp_percnt =  await get_percentage(total_hp, new_hp)

    return {
        "earnedhp": int(new_hp),
        "totalhp": int(total_hp),
        "percentage": hp_percnt
    }


async def make_bar(per):
    done = min(round(per / 10), 10)
    return "■" * done + "□" * (10 - done)


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    message = update.effective_message
    chat = update.effective_chat
    msg = update.effective_message
    user_id = await extract_user(msg, args)

    if user_id:

        if msg.reply_to_message and msg.reply_to_message.forward_origin:

            user1 = message.reply_to_message.from_user
            user2 = message.reply_to_message.forward_origin

            await msg.reply_text(
                f"<b>Telegram ID:</b>,"
                f"• {html.escape(user2.first_name)} - <code>{user2.id}</code>.\n"
                f"• {html.escape(user1.first_name)} - <code>{user1.id}</code>.",
                parse_mode=ParseMode.HTML,
            )

        else:

            user = await bot.get_chat(user_id)
            await msg.reply_text(
                f"{html.escape(user.first_name)}'s id is <code>{user.id}</code>.",
                parse_mode=ParseMode.HTML,
            )

    elif chat.type == "private":
        await msg.reply_text(
            f"Your id is <code>{chat.id}</code>.", parse_mode=ParseMode.HTML,
        )

    else:
        await msg.reply_text(
            f"This group's id is <code>{chat.id}</code>.", parse_mode=ParseMode.HTML,
        )


@ErenTelethonClient.on(
    events.NewMessage(
        pattern="/ginfo ", from_users=(SCOUTS or []) + (TITANSHIFTERS or []) + (ROYALS or []),
    ),
)
async def group_info(event) -> None:
    chat = event.text.split(" ", 1)[1]
    try:
        entity = await event.client.get_entity(chat)
        totallist = await event.client.get_participants(
            entity, filter=ChannelParticipantsAdmins,
        )
        ch_full = await event.client(GetFullChannelRequest(channel=entity))
    except Exception:
        await event.reply(
            "Can't for some reason, maybe it is a private one or that I am banned there.",
        )
        return
    msg = f"**ID**: `{entity.id}`"
    msg += f"\n**Title**: `{entity.title}`"
    msg += f"\n**Datacenter**: `{entity.photo.dc_id}`"
    msg += f"\n**Video PFP**: `{entity.photo.has_video}`"
    msg += f"\n**Supergroup**: `{entity.megagroup}`"
    msg += f"\n**Restricted**: `{entity.restricted}`"
    msg += f"\n**Scam**: `{entity.scam}`"
    msg += f"\n**Slowmode**: `{entity.slowmode_enabled}`"
    if entity.username:
        msg += f"\n**Username**: {entity.username}"
    msg += "\n\n**Member Stats:**"
    msg += f"\n`Admins:` `{len(totallist)}`"
    msg += f"\n`Users`: `{totallist.total}`"
    msg += "\n\n**Admins List:**"
    for x in totallist:
        msg += f"\n• [{x.id}](tg://user?id={x.id})"
    msg += f"\n\n**Description**:\n`{ch_full.full_chat.about}`"
    await event.reply(msg)



async def gifid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.animation:
        await update.effective_message.reply_text(
            f"Gif ID:\n<code>{msg.reply_to_message.animation.file_id}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.effective_message.reply_text("Please reply to a gif to get its ID.")


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    message = update.effective_message
    chat = update.effective_chat
    user_id = await extract_user(update.effective_message, args)

    if user_id:
        user = await bot.get_chat(user_id)

    elif not message.reply_to_message and not args:
        user = message.from_user

    elif not message.reply_to_message and (
        not args
        or (
            len(args) >= 1
            and not args[0].startswith("@")
            and not args[0].isdigit()
            and not await message.parse_entities([MessageEntity.TEXT_MENTION])
        )
    ):
        await message.reply_text("I can't extract a user from this.")
        return

    else:
        return

    rep = await message.reply_text("<code>Gathering Data...</code>", parse_mode=ParseMode.HTML)

    text = (
        f"╒═══「<b> Appraisal results:</b> 」\n"
        f"ID: <code>{user.id}</code>\n"
        f"First Name: {html.escape(user.first_name)}"
    )

    if user.last_name:
        text += f"\nLast Name: {html.escape(user.last_name)}"

    if user.username:
        text += f"\nUsername: @{html.escape(user.username)}"

    text += f"\nUserlink: {mention_html(user.id, 'link')}"

    if chat.type != "private" and user_id != bot.id:
        _stext = "\nPresence: <code>{}</code>"

        if afk_st := is_user_afk(user.id):
            text += _stext.format("AFK")
        else:
            member = await bot.get_chat_member(chat.id, user.id)
            status = member.status
            if status:
                if status in {"left", "kicked"}:
                    text += _stext.format("Not here")
                elif status == "member":
                    text += _stext.format("Detected")
                elif status in {"administrator", "owner"}:
                    text += _stext.format("Admin")
    if user_id not in [bot.id, 777000, 1087968824]:
        userhp = await hpmanager(user)
        bar = f"{await make_bar(int(userhp['percentage']))}"
        text += f"\n\n<b>Health:</b> <code>{userhp['earnedhp']}/{userhp['totalhp']}</code>\n[<i>{bar}</i>{userhp['percentage']}%]. [<a href='https://t.me/FoundingTitanupdates/19'>?</a>]"

    disaster_level_present = False

    if user.id == OWNER_ID:
        text += "\n\nThe Disaster level of this person is 'Founding Titan'."
        disaster_level_present = True
    elif user.id == DEVIL_SUCCESSOR:
        text += "\nnThe disaster level of this person is 'Devil's Successor'."
        disaster_level_present = True
    elif user.id == MARIN:
        text += "\n\nThe disaster level of this person is 'Marin'"
        disaster_level_present = True
    elif user.id in ACKERMANS:
        text += "\n\nThis user is member of the 'Ackerman Clan'."
        disaster_level_present = True
    elif user.id in TITANSHIFTERS:
        text += "\n\nThe Disaster level of this person is 'Titan Shifter'."
        disaster_level_present = True
    elif user.id in ROYALS:
        text += "\n\nThe Disaster level of this person is 'Royal Blood'."
        disaster_level_present = True 
    elif user.id in SCOUTS:
        text += "\n\nThe Disaster level of this person is 'Scout'."
        disaster_level_present = True
    elif user.id in GARRISONS:
        text += "\n\nThe Disaster level of this person is 'Garrison'."


    if disaster_level_present:
        text += ' [<a href="https://t.me/foundingtitanupdates/12">?</a>]'.format(
            bot.username,
        )

    try:
        user_member = await chat.get_member(user.id)
        if user_member.status == "administrator":
            result = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={chat.id}&user_id={user.id}",
            )
            result = result.json()["result"]
            if "custom_title" in result.keys():
                custom_title = result["custom_title"]
                text += f"\n\nTitle:\n<b>{custom_title}</b>"
    except BadRequest:
        pass

    for mod in USER_INFO:
        try:
            mod_info = mod.__user_info__(user.id).strip()
        except TypeError:
            mod_info = mod.__user_info__(user.id, chat.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    if INFOPIC:
        try:
            profile = await bot.get_user_profile_photos(user.id)
            pfp = profile.photos[0][-1]
            file = await bot.get_file(pfp.file_id)
            await file.download_to_drive(f"{user.id}.jpg")
            await context.bot.sendChatAction(chat.id, "upload_document")
            await context.bot.send_document(
            chat.id,
            document=open(f"{user.id}.jpg", "rb"),
            caption=text,
            parse_mode=ParseMode.HTML,            
        )
        # Incase user don't have profile pic, send normal text
        except IndexError:
            await message.reply_text(
                text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    else:
        await message.reply_text(
            text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    await rep.delete()
    os.remove(f"{user.id}.jpg")

async def about_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    message = update.effective_message
    user_id = await extract_user(message, args)

    user = await bot.get_chat(user_id) if user_id else message.from_user
    if info := redis.get_user_info(user.id):
        await update.effective_message.reply_text(
            f"*{user.first_name}*:\n{escape_markdown(info)}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    elif message.reply_to_message:
        username = message.reply_to_message.from_user.first_name
        await update.effective_message.reply_text(
            f"{username} hasn't set an info message about themselves yet!",
        )
    else:
        await update.effective_message.reply_text("There isnt one, use /setme to set one.")



async def set_about_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user_id = message.from_user.id
    if user_id in [777000, 1087968824]:
        await message.reply_text("Error! Unauthorized")
        return
    bot = context.bot
    if message.reply_to_message:
        repl_message = message.reply_to_message
        repl_user_id = repl_message.from_user.id
        if repl_user_id in [bot.id, 777000, 1087968824] and (user_id in ACKERMANS):
            user_id = repl_user_id
    text = message.text
    info = text.split(None, 1)
    if len(info) == 2:
        if len(info[1]) < MAX_TEXT_LENGTH // 4:
            redis.set_user_info(user_id, info[1])
            if user_id in [777000, 1087968824]:
                await message.reply_text("Authorized...Information updated!")
            elif user_id == bot.id:
                await message.reply_text("I have updated my info with the one you provided!")
            else:
                await message.reply_text("Information updated!")
        else:
            await message.reply_text(
                f"The info needs to be under {MAX_TEXT_LENGTH // 4} characters! You have {len(info[1])}."
            )


@sudo_plus
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    process = subprocess.Popen("neofetch --stdout", 
                               stdout=PIPE, 
                               shell=True,
                               text=True)
    stdout = process.communicate()[0]
    neofetch = stdout.replace("\n\n", "\n")
    status = "<b>Neofetch Results:</b>\n"
    status += f"{str(neofetch)}"   
    status += "<b>\nBot Statistics:</b>\n" + "\n".join([mod.__stats__() for mod in STATS])
    result = re.sub(r"(\d+)", r"<code>\1</code>", status)
    await update.effective_message.reply_text(result, parse_mode=ParseMode.HTML)


async def about_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    message = update.effective_message

    user_id = await extract_user(message, args)
    user = await bot.get_chat(user_id) if user_id else message.from_user
    if info := redis.get_user_bio(user.id):
        await update.effective_message.reply_text(
            f"*{user.first_name}*:\n{escape_markdown(info)}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    elif message.reply_to_message:
        username = user.first_name
        await update.effective_message.reply_text(
            f"{username} hasn't had a message set about themselves yet!\nSet one using /setbio",
        )
    else:
        await update.effective_message.reply_text(
            "You haven't had a bio set about yourself yet!",
        )


async def set_about_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    sender_id = update.effective_user.id
    bot = context.bot

    if message.reply_to_message:
        repl_message = message.reply_to_message
        user_id = repl_message.from_user.id

        if user_id == message.from_user.id:
            await message.reply_text(
                "Ha, you can't set your own bio! You're at the mercy of others here...",
            )
            return

        if user_id in [777000, 1087968824] and sender_id not in ACKERMANS:
            await message.reply_text("You are not authorised")
            return

        if user_id == bot.id and sender_id not in ACKERMANS:
            await message.reply_text(
                "Erm... yeah, I only trust the Ackermans to set my bio.",
            )
            return

        text = message.text
        bio = text.split(
            None, 1,
        )  # use python's maxsplit to only remove the cmd, hence keeping newlines.

        if len(bio) == 2:
            if len(bio[1]) < MAX_TEXT_LENGTH // 4:
                redis.set_user_bio(user_id, bio[1])
                await message.reply_text(f"Updated {repl_message.from_user.first_name}'s bio!")
            else:
                await message.reply_text(
                    f"Bio needs to be under {MAX_TEXT_LENGTH // 4} characters! You tried to set {len(bio[1])}."
                )
    else:
        await message.reply_text("Reply to someone to set their bio!")

def __user_info__(user_id):
    bio = redis.get_user_bio(user_id)
    me = redis.get_user_info(user_id)
    if bio and me:
        return f"\n<b>About user: </b>{me}\n <b>What others say:</b>{bio}\n"
    elif me:
        return f"\n<b>About user: </b>{me}\n"
    elif bio:
        return f"\n<b>What others say: </b>{bio}\n"
    else:
        return None


__help__ = """
*AFK:*
When marked as AFK, any mentions will be replied to with a message to say you're not available!
This also sends your last seen based on when you ran afk!
 • `/afk`*:* <reason>: mark yourself as AFK (away from keyboard).
 • `brb` <reason>: same as the afk command - but not a command.

*ID:*
 • `/id`*:* get the current group id. If used by replying to a message, gets that user's id.
 • `/gifid`*:* reply to a gif to me to tell you its file ID.

*Self addded information:*
 • `/setme <text>`*:* will set your info
 • `/me`*:* will get your or another user's info.
Examples:
 `/setme I am a garrison.`
 `/me @username(defaults to yours if no user specified)`

*Information others add on you:*
 • `/bio`*:* will get your or another user's bio. This cannot be set by yourself.
• `/setbio <text>`*:* while replying, will save another user's bio
Examples:
 `/bio @username(defaults to yours if not specified).`
 `/setbio This user is a wolf` (reply to the user)

*Overall Information about you:*
 • `/info`*:* get information about a user.

*What is that health thingy?*
 Come and see [HP System explained](https://t.me/foundingtitanupdates/19)
"""

SET_BIO_HANDLER = DisableAbleCommandHandler("setbio", set_about_bio, block=False)
GET_BIO_HANDLER = DisableAbleCommandHandler("bio", about_bio, block=False)

STATS_HANDLER = CommandHandler(["stats", "statistics"], stats, block=False)
ID_HANDLER = DisableAbleCommandHandler("id", get_id, block=False)
GIFID_HANDLER = DisableAbleCommandHandler("gifid", gifid, block=False)
INFO_HANDLER = DisableAbleCommandHandler("info", info, block=False)

SET_ABOUT_HANDLER = DisableAbleCommandHandler("setme", set_about_me, block=False)
GET_ABOUT_HANDLER = DisableAbleCommandHandler("me", about_me, block=False)

application.add_handler(STATS_HANDLER)
application.add_handler(ID_HANDLER)
application.add_handler(GIFID_HANDLER)
application.add_handler(INFO_HANDLER)
application.add_handler(SET_BIO_HANDLER)
application.add_handler(GET_BIO_HANDLER)
application.add_handler(SET_ABOUT_HANDLER)
application.add_handler(GET_ABOUT_HANDLER)

__mod_name__ = "Info & AFK"
__command_list__ = ["setbio", "bio", "setme", "me", "info"]
__handlers__ = [
    ID_HANDLER,
    GIFID_HANDLER,
    INFO_HANDLER,
    SET_BIO_HANDLER,
    GET_BIO_HANDLER,
    SET_ABOUT_HANDLER,
    GET_ABOUT_HANDLER,
    STATS_HANDLER,
]
