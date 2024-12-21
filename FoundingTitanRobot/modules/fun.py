import html
import random
import time
from pathlib import Path
import glob
import requests as r
import urllib.request

import FoundingTitanRobot.modules.fun_strings as fun_strings
from FoundingTitanRobot import application
from FoundingTitanRobot import ROYALS, TITANSHIFTERS
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from FoundingTitanRobot.modules.helper_funcs.chat_status import is_user_admin
from FoundingTitanRobot.modules.helper_funcs.extraction import extract_user
from telegram import ChatPermissions, Update
from telegram.error import BadRequest
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ContextTypes

GIF_ID = "CgACAgQAAx0CSVUvGgAC7KpfWxMrgGyQs-GUUJgt-TSO8cOIDgACaAgAAlZD0VHT3Zynpr5nGxsE"


async def runs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    temp = random.choice(fun_strings.RUN_STRINGS)
    if update.effective_user.id == 1170714920:
        temp = "Run everyone, they just dropped a bomb 💣💣"
    await update.effective_message.reply_text(temp)


async def sanitize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    name = (
        message.reply_to_message.from_user.first_name
        if message.reply_to_message
        else message.from_user.first_name
    )
    reply_animation = (
        message.reply_to_message.reply_animation
        if message.reply_to_message
        else message.reply_animation
    )
    reply_animation(GIF_ID, caption=f"*Sanitizes {name}*")


async def sanitize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    name = (
        message.reply_to_message.from_user.first_name
        if message.reply_to_message
        else message.from_user.first_name
    )
    reply_animation = (
        message.reply_to_message.reply_animation
        if message.reply_to_message
        else message.reply_animation
    )
    reply_animation(random.choice(fun_strings.GIFS), caption=f"*Sanitizes {name}*")


async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    message = update.effective_message
    chat = update.effective_chat

    reply_text = (
        await message.reply_to_message.reply_text
        if await message.reply_to_message
        else await message.reply_text
    )

    curr_user = html.escape(message.from_user.first_name)
    user_id = await extract_user(message, args)

    if user_id == bot.id:
        temp = random.choice(fun_strings.SLAP_SAITAMA_TEMPLATES)

        if isinstance(temp, list):
            if temp[2] == "tmute":
                if await is_user_admin(chat, message.from_user.id):
                    await reply_text(temp[1])
                    return

                mutetime = int(time.time() + 60)
                await bot.restrict_chat_member(
                    chat.id,
                    message.from_user.id,
                    until_date=mutetime,
                    permissions=ChatPermissions(can_send_messages=False),
                )
            await reply_text(temp[0])
        else:
            await reply_text(temp)
        return

    if user_id:

        slapped_user = await bot.get_chat(user_id)
        user1 = curr_user
        user2 = html.escape(slapped_user.first_name)

    else:
        user1 = bot.first_name
        user2 = curr_user

    temp = random.choice(fun_strings.SLAP_TEMPLATES)
    item = random.choice(fun_strings.ITEMS)
    hit = random.choice(fun_strings.HIT)
    throw = random.choice(fun_strings.THROW)

    if update.effective_user.id == 1096215023:
        temp = "@NeoTheKitty scratches {user2}"

    reply = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)

    await reply_text(reply, parse_mode=ParseMode.HTML)


async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    args = context.args
    message = update.effective_message

    reply_to = message.reply_to_message or message

    curr_user = html.escape(message.from_user.first_name)
    user_id = await extract_user(message, args)

    if user_id:
        patted_user = await bot.get_chat(user_id)
        user1 = curr_user
        user2 = html.escape(patted_user.first_name)

    else:
        user1 = bot.first_name
        user2 = curr_user

    pat_type = random.choice(("Text", "Gif", "Sticker"))
    if pat_type == "Gif":
        try:
            temp = random.choice(fun_strings.PAT_GIFS)
            reply_to.reply_animation(temp)
        except BadRequest:
            pat_type = "Text"

    if pat_type == "Sticker":
        try:
            temp = random.choice(fun_strings.PAT_STICKERS)
            reply_to.reply_sticker(temp)
        except BadRequest:
            pat_type = "Text"

    if pat_type == "Text":
        temp = random.choice(fun_strings.PAT_TEMPLATES)
        reply = temp.format(user1=user1, user2=user2)
        await reply_to.reply_text(reply, parse_mode=ParseMode.HTML)


async def roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(range(1, 7)))


async def shout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    text = " ".join(args)
    result = [" ".join(list(text))]
    result.extend(
        f"{symbol} " + "  " * pos + symbol
        for pos, symbol in enumerate(text[1:])
    )
    result = list("\n".join(result))
    result[0] = text[0]
    result = "".join(result)
    msg = "```\n" + result + "```"
    return await update.effective_message.reply_text(msg, parse_mode="MARKDOWN")


async def toss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(fun_strings.TOSS))


async def shrug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    reply_text = (
        msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text
    )
    await reply_text(r"¯\_(ツ)_/¯")


async def bluetext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    reply_text = (
        msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text
    )
    await reply_text(
        "/BLUE /TEXT\n/MUST /CLICK\n/I /AM /A /STUPID /ANIMAL /THAT /IS /ATTRACTED /TO /COLORS",
    )


async def rlg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    eyes = random.choice(fun_strings.EYES)
    mouth = random.choice(fun_strings.MOUTHS)
    ears = random.choice(fun_strings.EARS)

    if len(eyes) == 2:
        repl = ears[0] + eyes[0] + mouth[0] + eyes[1] + ears[1]
    else:
        repl = ears[0] + eyes[0] + mouth[0] + eyes[0] + ears[1]
    await update.message.reply_text(repl)


async def decide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_text = (
        update.effective_message.reply_to_message.reply_text
        if update.effective_message.reply_to_message
        else update.effective_message.reply_text
    )
    await reply_text(random.choice(fun_strings.DECIDE))


async def eightball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_text = (
        await update.effective_message.reply_to_message.reply_text
        if await update.effective_message.reply_to_message
        else await update.effective_message.reply_text
    )
    await reply_text(random.choice(fun_strings.EIGHTBALL))


async def table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_text = (
        update.effective_message.reply_to_message.reply_text
        if update.effective_message.reply_to_message
        else update.effective_message.reply_text
    )
    await reply_text(random.choice(fun_strings.TABLE))


normiefont = [
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
]
weebyfont = [
    "卂",
    "乃",
    "匚",
    "刀",
    "乇",
    "下",
    "厶",
    "卄",
    "工",
    "丁",
    "长",
    "乚",
    "从",
    "𠘨",
    "口",
    "尸",
    "㔿",
    "尺",
    "丂",
    "丅",
    "凵",
    "リ",
    "山",
    "乂",
    "丫",
    "乙",
]


async def weebify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    message = update.effective_message
    string = ""

    if message.reply_to_message:
        string = await message.reply_to_message.text.lower().replace(" ", "  ")

    if args:
        string = "  ".join(args).lower()

    if not string:
        await message.reply_text("Usage is `/weebify <text>`", parse_mode=ParseMode.MARKDOWN)
        return

    for normiecharacter in string:
        if normiecharacter in normiefont:
            weebycharacter = weebyfont[normiefont.index(normiecharacter)]
            string = string.replace(normiecharacter, weebycharacter)

    if message.reply_to_message:
        await message.reply_to_message.reply_text(string)
    else:
        await message.reply_text(string)


async def meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    meme = r.get("https://meme-api.herokuapp.com/gimme/Animemes/").json()
    image = meme.get("url")
    caption = meme.get("title")
    if not image:
        await msg.reply_text("No URL was received from the API!")
        return
    msg.reply_photo(
                photo=image, caption=caption)

async def gbun(update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_message.chat.type == "private":
        return
    if int(user.id) in TITANSHIFTERS or int(user.id) in ROYALS:
        chat = update.effective_chat

        await context.bot.sendMessage(chat.id, (random.choice(fun_strings.GBUN)))


async def gbam(update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    message = update.effective_message

    curr_user = html.escape(message.from_user.first_name)
    user_id = await extract_user(message, args)

    if user_id:
        gbam_user = await bot.get_chat(user_id)
        user1 = curr_user
        user2 = html.escape(gbam_user.first_name)

    else:
        user1 = curr_user
        user2 = bot.first_name

    if update.effective_message.chat.type == "private":
        return
    if int(user.id) in TITANSHIFTERS or int(user.id) in ROYALS:
        gbamm = fun_strings.GBAM
        reason = random.choice(fun_strings.GBAM_REASON)
        gbam = gbamm.format(user1=user1, user2=user2, chatid=chat.id, reason=reason)
        await context.bot.sendMessage(chat.id, gbam, parse_mode=ParseMode.HTML)

__help__ = """
 • `/runs`*:* reply a random string from an array of replies
 • `/slap`*:* slap a user, or get slapped if not a reply
 • `/shrug`*:* get shrug XD
 • `/table`*:* get flip/unflip :v
 • `/decide`*:* Randomly answers yes/no/maybe
 • `/toss`*:* Tosses A coin
 • `/bluetext`*:* check urself :V
 • `/roll`*:* Roll a dice
 • `/rlg`*:* Join ears,nose,mouth and create an emo ;-;
 • `/shout <keyword>`*:* write anything you want to give loud shout
 • `/weebify <text>`*:* returns a weebified text
 • `/sanitize`*:* always use this before /pat or any contact
 • `/pat`*:* pats a user, or get patted
 • `/8ball`*:* predicts using 8ball method
 • `/meme`*:* sends random anime memes
 • `/gbam`*:* troll somone with fake gbans, only Disaster People can do this
 • `/couples`*:* To Choose Couple Of The Day
"""

SANITIZE_HANDLER = DisableAbleCommandHandler("sanitize", sanitize, block=False)
RUNS_HANDLER = DisableAbleCommandHandler("runs", runs, block=False)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, block=False)
PAT_HANDLER = DisableAbleCommandHandler("pat", pat, block=False)
ROLL_HANDLER = DisableAbleCommandHandler("roll", roll, block=False)
TOSS_HANDLER = DisableAbleCommandHandler("toss", toss, block=False)
SHRUG_HANDLER = DisableAbleCommandHandler("shrug", shrug, block=False)
BLUETEXT_HANDLER = DisableAbleCommandHandler("bluetext", bluetext, block=False)
RLG_HANDLER = DisableAbleCommandHandler("rlg", rlg, block=False)
DECIDE_HANDLER = DisableAbleCommandHandler("decide", decide, block=False)
EIGHTBALL_HANDLER = DisableAbleCommandHandler("8ball", eightball, block=False)
TABLE_HANDLER = DisableAbleCommandHandler("table", table, block=False)
SHOUT_HANDLER = DisableAbleCommandHandler("shout", shout, block=False)
WEEBIFY_HANDLER = DisableAbleCommandHandler("weebify", weebify, block=False)
MEME_HANDLER = DisableAbleCommandHandler(["meme", "memes"], meme, block=False)
GBUN_HANDLER = DisableAbleCommandHandler("gbun", gbun, block=False)
GBAM_HANDLER = DisableAbleCommandHandler("gbam", gbam, block=False)

application.add_handler(GBAM_HANDLER)
application.add_handler(GBUN_HANDLER)
application.add_handler(MEME_HANDLER)
application.add_handler(WEEBIFY_HANDLER)
application.add_handler(SHOUT_HANDLER)
application.add_handler(SANITIZE_HANDLER)
application.add_handler(RUNS_HANDLER)
application.add_handler(SLAP_HANDLER)
application.add_handler(PAT_HANDLER)
application.add_handler(ROLL_HANDLER)
application.add_handler(TOSS_HANDLER)
application.add_handler(SHRUG_HANDLER)
application.add_handler(BLUETEXT_HANDLER)
application.add_handler(RLG_HANDLER)
application.add_handler(DECIDE_HANDLER)
application.add_handler(EIGHTBALL_HANDLER)
application.add_handler(TABLE_HANDLER)

__mod_name__ = "Fun"
__command_list__ = [
    "runs",
    "slap",
    "roll",
    "toss",
    "shrug",
    "bluetext",
    "rlg",
    "decide",
    "table",
    "pat",
    "sanitize",
    "shout",
    "weebify",
    "8ball",
    "meme",
    "gbun",
    "gbam",
]
__handlers__ = [
    RUNS_HANDLER,
    SLAP_HANDLER,
    PAT_HANDLER,
    ROLL_HANDLER,
    TOSS_HANDLER,
    SHRUG_HANDLER,
    BLUETEXT_HANDLER,
    RLG_HANDLER,
    DECIDE_HANDLER,
    TABLE_HANDLER,
    SANITIZE_HANDLER,
    SHOUT_HANDLER,
    WEEBIFY_HANDLER,
    EIGHTBALL_HANDLER,
    MEME_HANDLER,
    GBUN_HANDLER,
    GBAM_HANDLER,
]
