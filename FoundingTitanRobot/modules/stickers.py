import os
import math
import requests
import urllib.request as urllib
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO
import textwrap
from html import escape
from bs4 import BeautifulSoup as bs

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, InputSticker
from telegram.ext import CallbackContext, ContextTypes
from telegram.constants import ParseMode
from telegram.helpers import mention_html
from telegram.error import TelegramError

from FoundingTitanRobot import application
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from FoundingTitanRobot.events import register as Eren
from FoundingTitanRobot import LOGGER
from FoundingTitanRobot import TEMP_DOWNLOAD_DIRECTORY
from FoundingTitanRobot import telethn as tbot

combot_stickers_url = "https://combot.org/telegram/stickers?q="


async def stickerid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        await update.effective_message.reply_text(
            "Hello "
            + f"{mention_html(msg.from_user.id, msg.from_user.first_name)}"
            + ", The sticker id you are replying is :\n <code>"
            + escape(msg.reply_to_message.sticker.file_id)
            + "</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.effective_message.reply_text(
            "Hello "
            + f"{mention_html(msg.from_user.id, msg.from_user.first_name)}"
            + ", Please reply to sticker message to get id sticker",
            parse_mode=ParseMode.HTML,
        )



async def cb_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    split = msg.text.split(" ", 1)
    if len(split) == 1:
        await msg.reply_text("Provide some name to search for pack.")
        return
    text = requests.get(combot_stickers_url + split[1]).text
    soup = bs(text, "lxml")
    results = soup.find_all("a", {"class": "sticker-pack__btn"})
    titles = soup.find_all("div", "sticker-pack__title")
    if not results:
        await msg.reply_text("No results found :(.")
        return
    reply = f"Stickers for *{split[1]}*:"
    for result, title in zip(results, titles):
        link = result["href"]
        reply += f"\n• [{title.get_text()}]({link})"
    await msg.reply_text(reply, parse_mode=ParseMode.MARKDOWN)



async def getsticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    msg = update.effective_message
    chat_id = update.effective_chat.id
    if msg.reply_to_message and msg.reply_to_message.sticker:
        file_id = msg.reply_to_message.sticker.file_id
        new_file = await bot.get_file(file_id)
        if msg.reply_to_message.sticker.is_video:
            await new_file.download_to_drive("sticker.webm")
            await bot.send_document(chat_id, document=open("sticker.webm", 'rb'))
            os.remove("sticker.webm")
        elif msg.reply_to_message.sticker.is_animated:
            await new_file.download_to_drive("sticker.tgs")
            await bot.send_document(
                chat_id,
                document=open("sticker.tgs", "rb"),
                filename="sticker._tgs",
                caption="Remove the '_' before tgs",
            )
            os.remove("sticker.tgs")
        else:
            await new_file.download_to_drive("sticker.png")
            await bot.send_document(chat_id, document=open("sticker.png", "rb"))
            os.remove("sticker.png")
    else:
        await msg.reply_text(
            "Please reply to a sticker for me to upload its raw file."
        )

async def kang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    args = context.args
    packnum = 0
    packname = "f" + str(user.id) + "_by_" + context.bot.username
    packname_found = 0
    max_stickers = 120
    while packname_found == 0:
        try:
            stickerset = await context.bot.get_sticker_set(packname)
            if len(stickerset.stickers) >= max_stickers:
                packnum += 1
                packname = (
                    "f"
                    + str(packnum)
                    + "_"
                    + str(user.id)
                    + "_by_"
                    + context.bot.username
                )
            else:
                packname_found = 1
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                packname_found = 1
    kangsticker = "kangsticker.png"
    is_animated = False
    is_video = False
    file_id = ""

    if msg.reply_to_message:
        if msg.reply_to_message.sticker:
            if msg.reply_to_message.sticker.is_animated:
                is_animated = True
            elif msg.reply_to_message.sticker.is_video:
                is_video = True
            file_id = msg.reply_to_message.sticker.file_id
        elif msg.reply_to_message.video:
            file_id = msg.reply_to_message.video.file_id
        elif msg.reply_to_message.photo:
            file_id = msg.reply_to_message.photo[-1].file_id
        elif msg.reply_to_message.document:
            file_id = msg.reply_to_message.document.file_id
            if msg.reply_to_message.document.mime_type == "video/mp4":
                is_video = True
        else:
            await msg.reply_text("Yea, I can't kang that.")

        kang_file = await context.bot.get_file(file_id)
        if not is_animated and not is_video:
            await kang_file.download_to_drive("kangsticker.png")
        elif is_video:
            await kang_file.download_to_drive("kangsticker.webm")
        else:
            await kang_file.download_to_drive("kangsticker.tgs")

        if args:
            sticker_emoji = str(args[0])
        elif msg.reply_to_message.sticker and msg.reply_to_message.sticker.emoji:
            sticker_emoji = msg.reply_to_message.sticker.emoji
        else:
            sticker_emoji = "👀"

        if not is_animated and not is_video:
            try:
                im = Image.open(kangsticker)
                maxsize = (512, 512)
                if (im.width and im.height) < 512:
                    size1 = im.width
                    size2 = im.height
                    if im.width > im.height:
                        scale = 512 / size1
                        size1new = 512
                        size2new = size2 * scale
                    else:
                        scale = 512 / size2
                        size1new = size1 * scale
                        size2new = 512
                    size1new = math.floor(size1new)
                    size2new = math.floor(size2new)
                    sizenew = (size1new, size2new)
                    im = im.resize(sizenew)
                else:
                    im.thumbnail(maxsize)
                if not msg.reply_to_message.sticker:
                    im.save(kangsticker, "PNG")
                await context.bot.add_sticker_to_set(
                    user_id=user.id,
                    name=packname,
                    sticker=InputSticker(open("kangsticker.png", "rb"), sticker_emoji, format="static"),
                )
                await msg.reply_text(
                    f"Sticker successfully added to [pack](t.me/addstickers/{packname})"
                    + f"\nEmoji is: {sticker_emoji}",
                    parse_mode=ParseMode.MARKDOWN,
                )

            except OSError as e:
                await msg.reply_text("I can only kang images m8.")
                print(e)
                return

            except TelegramError as e:
                if e.message == "Stickerset_invalid":
                    await makepack_internal(
                        update,
                        context,
                        msg,
                        user,
                        sticker_emoji,
                        packname,
                        packnum,
                        png_sticker=open("kangsticker.png", "rb"),
                    )
                elif e.message == "Sticker_png_dimensions":
                    im.save(kangsticker, "PNG")
                    await context.bot.add_sticker_to_set(
                        user_id=user.id,
                        name=packname,
                        sticker=InputSticker(open("kangsticker.png", "rb"), sticker_emoji, format="static"),
                    )
                    await msg.reply_text(
                        f"Sticker successfully added to [pack](t.me/addstickers/{packname})"
                        + f"\nEmoji is: {sticker_emoji}",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                elif e.message == "Invalid sticker emojis":
                    await msg.reply_text("Invalid emoji(s).")
                elif e.message == "Stickers_too_much":
                    await msg.reply_text("Max packsize reached. Press F to pay respecc.")
                elif e.message == "Internal Server Error: sticker set not found (500)":
                    await msg.reply_text(
                        "Sticker successfully added to [pack](t.me/addstickers/%s)"
                        % packname
                        + "\n"
                        "Emoji is:" + " " + sticker_emoji,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                print(e)

        elif is_video:
            packname = "video" + str(user.id) + "_by_" + context.bot.username
            packname_found = 0
            max_stickers = 50
            while packname_found == 0:
                try:
                    stickerset = await context.bot.get_sticker_set(packname)
                    if len(stickerset.stickers) >= max_stickers:
                        packnum += 1
                        packname = (
                            "video"
                            + str(packnum)
                            + "_"
                            + str(user.id)
                            + "_by_"
                            + context.bot.username
                        )
                    else:
                        packname_found = 1
                except TelegramError as e:
                    if e.message == "Stickerset_invalid":
                        packname_found = 1
            try:
                await context.bot.add_sticker_to_set(
                    user_id=user.id,
                    name=packname,
                    sticker=InputSticker(open("kangsticker.webm", "rb"), sticker_emoji, format="video")),
                await msg.reply_text(
                    f"Sticker successfully added to [pack](t.me/addstickers/{packname})"
                    + f"\nEmoji is: {sticker_emoji}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except TelegramError as e:
                if e.message == "Stickerset_invalid":
                   await makepack_internal(
                        update,
                        context,
                        msg,
                        user,
                        sticker_emoji,
                        packname,
                        packnum,
                        video_sticker=open("kangsticker.webm", "rb"),
                    )
                elif e.message == "Invalid sticker emojis":
                    await msg.reply_text("Invalid emoji(s).")
                elif e.message == "Internal Server Error: sticker set not found (500)":
                    await msg.reply_text(
                        "Sticker successfully added to [pack](t.me/addstickers/%s)"
                        % packname
                        + "\n"
                        "Emoji is:" + " " + sticker_emoji,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                print(e)

        else:
            packname = "animation" + str(user.id) + "_by_" + context.bot.username
            packname_found = 0
            max_stickers = 50
            while packname_found == 0:
                try:
                    stickerset = await context.bot.get_sticker_set(packname)
                    if len(stickerset.stickers) >= max_stickers:
                        packnum += 1
                        packname = (
                            "animation"
                            + str(packnum)
                            + "_"
                            + str(user.id)
                            + "_by_"
                            + context.bot.username
                        )
                    else:
                        packname_found = 1
                except TelegramError as e:
                    if e.message == "Stickerset_invalid":
                        packname_found = 1
            try:
                await context.bot.add_sticker_to_set(
                    user_id=user.id,
                    name=packname,
                    sticker=InputSticker(open("kangsticker.tgs", "rb"), sticker_emoji, format="animated")
                )
                await msg.reply_text(
                    f"Sticker successfully added to [pack](t.me/addstickers/{packname})"
                    + f"\nEmoji is: {sticker_emoji}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except TelegramError as e:
                if e.message == "Stickerset_invalid":
                   await makepack_internal(
                        update,
                        context,
                        msg,
                        user,
                        sticker_emoji,
                        packname,
                        packnum,
                        tgs_sticker=open("kangsticker.tgs", "rb"),
                    )
                elif e.message == "Invalid sticker emojis":
                    await msg.reply_text("Invalid emoji(s).")
                elif e.message == "Internal Server Error: sticker set not found (500)":
                    await msg.reply_text(
                        "Sticker successfully added to [pack](t.me/addstickers/%s)"
                        % packname
                        + "\n"
                        "Emoji is:" + " " + sticker_emoji,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                print(e)

    elif args:
        try:
            try:
                urlemoji = msg.text.split(" ")
                png_sticker = urlemoji[1]           
                sticker_emoji = urlemoji[2]
            except IndexError:
                sticker_emoji = "🤔"            
                urllib.urlretrieve(png_sticker, kangsticker)
            except ValueError:
                await msg.reply_text("invalid emoji")
            sticker_size(kangsticker)
            await msg.reply_photo(photo=open("kangsticker.png", "rb"))
            await context.bot.add_sticker_to_set(
                user_id=user.id,
                name=packname,
                sticker=InputSticker(open("kangsticker.png", "rb"), sticker_emoji, format="static"),
            )
            await msg.reply_text(
                f"Sticker successfully added to [pack](t.me/addstickers/{packname})"
                + f"\nEmoji is: {sticker_emoji}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except OSError as e:
            await msg.reply_text("I can only kang images m8.")
            print(e)
            return
        except TelegramError as e:
            if e.message == "Stickerset_invalid":
                await makepack_internal(
                    update,
                    context,
                    msg,
                    user,
                    sticker_emoji,
                    packname,
                    packnum,
                    png_sticker=open("kangsticker.png", "rb"),
                )
            elif e.message == "Sticker_png_dimensions":
                im.save(kangsticker, "PNG")
                await context.bot.add_sticker_to_set(
                    user_id=user.id,
                    name=packname,
                    sticker=InputSticker(open("kangsticker.png", "rb"), sticker_emoji, format="static"),
                )
                await msg.reply_text(
                    "Sticker successfully added to [pack](t.me/addstickers/%s)"
                    % packname
                    + "\n"
                    + "Emoji is:"
                    + " "
                    + sticker_emoji,
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif e.message == "Invalid sticker emojis":
                await msg.reply_text("Invalid emoji(s).")
            elif e.message == "Stickers_too_much":
                await msg.reply_text("Max packsize reached. Press F to pay respecc.")
            elif e.message == "Internal Server Error: sticker set not found (500)":
                await msg.reply_text(
                    "Sticker successfully added to [pack](t.me/addstickers/%s)"
                    % packname
                    + "\n"
                    "Emoji is:" + " " + sticker_emoji,
                    parse_mode=ParseMode.MARKDOWN,
                )
            print(e)
    else:
        packs = "Please reply to a sticker, or image to kang it!\nOh, by the way. here are your packs:\n"
        if packnum > 0:
            firstpackname = "f" + str(user.id) + "_by_" + context.bot.username
            for i in range(packnum + 1):
                if i == 0:
                    packs += f"[pack](t.me/addstickers/{firstpackname})\n"
                else:
                    packs += f"[pack{i}](t.me/addstickers/{packname})\n"
        else:
            packs += f"[pack](t.me/addstickers/{packname})"
        await msg.reply_text(packs, parse_mode=ParseMode.MARKDOWN)
    try:
        if os.path.isfile("kangsticker.png"):
            os.remove("kangsticker.png")
        elif os.path.isfile("kangsticker.tgs"):
            os.remove("kangsticker.tgs")
        elif os.path.isfile("kangsticker.webm"):
            os.remove("kangsticker.webm")
    except Exception:
        pass


async def makepack_internal(
    update,
    context,
    msg,
    user,
    emoji,
    packname,
    packnum,
    png_sticker=None,
    tgs_sticker=None,
    video_sticker=None,
):
    name = user.first_name
    name = name[:50]
    try:
        extra_version = f" {str(packnum)}" if packnum > 0 else ""
        if png_sticker:
            success = await context.bot.create_new_sticker_set(
                user.id,
                packname,
                f"{name}s kang pack{extra_version}",
                stickers=InputSticker(png_sticker, emoji, format="static"),
            )
        if tgs_sticker:
            success = await context.bot.create_new_sticker_set(
                user.id,
                packname,
                f"{name}s animated kang pack{extra_version}",
                stickers=InputSticker(tgs_sticker, emoji, format="animated"),
            )
        if video_sticker:
            success = await context.bot.create_new_sticker_set(
                user.id,
                packname,
                f"{name}s video kang pack{extra_version}",
                stickers=InputSticker(video_sticker, emoji, format="video")
            )

    except TelegramError as e:
        print(e)
        if e.message == "Sticker set name is already occupied":
            await msg.reply_text(
                f"Your pack can be found [here](t.me/addstickers/{packname})",
                parse_mode=ParseMode.MARKDOWN,
            )
        elif e.message in ("Peer_id_invalid", "bot was blocked by the user"):
            await msg.reply_text(
                "Contact me in PM first.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Start", url=f"t.me/{context.bot.username}"
                            )
                        ]
                    ]
                ),
            )
        elif e.message == "Internal Server Error: created sticker set not found (500)":
            await msg.reply_text(
                f"Sticker pack successfully created. Get it [here](t.me/addstickers/{packname})",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    if success:
        await msg.reply_text(
            f"Sticker pack successfully created. Get it [here](t.me/addstickers/{packname})",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await msg.reply_text("Failed to create sticker pack. Possibly due to blek mejik.")

# if your are reading this, it took me 2 hours to make delsticker 
async def delsticker(update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        file_id = msg.reply_to_message.sticker.file_id
    else:
        await msg.reply_text(
            "Please reply to the sticker which you want to delete from your pack")
    try:
        await context.bot.delete_sticker_from_set(file_id)
        await msg.reply_text(
            "Deleted That Sticker from your Pack!"
        )
   
    except TelegramError as e:
        print(e)
        if e.message == "Stickerset_invalid":
            await msg.reply_text(
                "Maybe the sticker pack is not yours or the pack was not made by me!",
                parse_mode=ParseMode.MARKDOWN,
            )
    

def sticker_size(path):
    im = Image.open(path)
    maxsize = (512, 512)
    if (im.width and im.height) < 512:
        size1 = im.width
        size2 = im.height
        if im.width > im.height:
            scale = 512 / size1
            size1new = 512
            size2new = size2 * scale
        else:
            scale = 512 / size2
            size1new = size1 * scale
            size2new = 512
        size1new = math.floor(size1new)
        size2new = math.floor(size2new)
        sizenew = (size1new, size2new)
        im = im.resize(sizenew)
    else:
        im.thumbnail(maxsize)
    im.save(path, "PNG")

@Eren(pattern="^/mmf ?(.*)")
async def handler(event):
    if event.fwd_from:
        return
    if not event.reply_to_msg_id:
        await event.reply("Reply to an image or a sticker to memeify it Nigga!!")
        return
    reply_message = await event.get_reply_message()
    if not reply_message.media:
        await event.reply("Provide some Text please")
        return
    file = await tbot.download_media(reply_message)
    msg = await event.reply("Memifying this image! Please wait")
    text = str(event.pattern_match.group(1)).strip()

    if not text:
        return await msg.reply("You might want to try `/mmf text`")
    meme = await drawText(file, text)
    await tbot.send_file(event.chat_id, file=meme, force_document=False)
    await msg.delete()
    os.remove(meme)



# Taken from https://github.com/UsergeTeam/Userge-Plugins/blob/master/plugins/memify.py#L64
# Maybe replyed to suit the needs of this module

async def drawText(image_path, text):
    img = Image.open(image_path)
    os.remove(image_path)
    shadowcolor = "black"
    i_width, i_height = img.size
    if os.name == "nt":
        fnt = "ariel.ttf"
    else:
        fnt = "./FoundingTitanRobot/resources/ArmWrestler.ttf"
    m_font = ImageFont.truetype(fnt, int((70 / 640) * i_width))
    if ";" in text:
        upper_text, lower_text = text.split(";")
    else:
        upper_text = text
        lower_text = ''
    draw = ImageDraw.Draw(img)
    current_h, pad = 10, 5
    if upper_text:
        for u_text in textwrap.wrap(upper_text, width=15):
            u_width, u_height = draw.textsize(u_text, font=m_font)
            draw.text(xy=(((i_width - u_width) / 2) - 2, int((current_h / 640)

                                                             * i_width)), text=u_text, font=m_font, fill=(0, 0, 0))

            draw.text(xy=(((i_width - u_width) / 2) + 2, int((current_h / 640)

                                                             * i_width)), text=u_text, font=m_font, fill=(0, 0, 0))
            draw.text(xy=((i_width - u_width) / 2,
                          int(((current_h / 640) * i_width)) - 2),

                      text=u_text,
                      font=m_font,
                      fill=(0,
                            0,
                            0))

            draw.text(xy=(((i_width - u_width) / 2),
                          int(((current_h / 640) * i_width)) + 2),

                      text=u_text,
                      font=m_font,
                      fill=(0,
                            0,
                            0))



            draw.text(xy=((i_width - u_width) / 2, int((current_h / 640)

                                                       * i_width)), text=u_text, font=m_font, fill=(255, 255, 255))

            current_h += u_height + pad

    if lower_text:
        for l_text in textwrap.wrap(lower_text, width=15):
            u_width, u_height = draw.textsize(l_text, font=m_font)
            draw.text(
                xy=(((i_width - u_width) / 2) - 2, i_height -
                    u_height - int((20 / 640) * i_width)),
                text=l_text, font=m_font, fill=(0, 0, 0))
            draw.text(
                xy=(((i_width - u_width) / 2) + 2, i_height -
                    u_height - int((20 / 640) * i_width)),
                text=l_text, font=m_font, fill=(0, 0, 0))
            draw.text(
                xy=((i_width - u_width) / 2, (i_height -
                                              u_height - int((20 / 640) * i_width)) - 2),
                text=l_text, font=m_font, fill=(0, 0, 0))

            draw.text(
                xy=((i_width - u_width) / 2, (i_height -

                                              u_height - int((20 / 640) * i_width)) + 2),
                text=l_text, font=m_font, fill=(0, 0, 0))


            draw.text(
                xy=((i_width - u_width) / 2, i_height -
                    u_height - int((20 / 640) * i_width)),
                text=l_text, font=m_font, fill=(255, 255, 255))
            current_h += u_height + pad          
    image_name = "memify.webp"
    webp_file = os.path.join(image_name)
    img.save(webp_file, "webp")
    return webp_file



__help__ = """
 • `/stickerid` : reply to a sticker to me to tell you its file ID.
 • `/getsticker` : reply to a sticker to me to upload its raw PNG file.
 • `/kang` : reply to a sticker to add it to your pack.
 • `/delkang` : reply to a Sticker to remove it from your pack
 • `/mmf` : memefiy any sticker and image.
 • `/stickers` : Find stickers for given term on combot sticker catalogue
"""

__mod_name__ = "Stickers"
STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid, block=False)
GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker, block=False)
KANG_HANDLER = DisableAbleCommandHandler(["kang", "steal"], kang, admin_ok=True, block=False)
DELKANG_HANDLER = DisableAbleCommandHandler(["delsticker", "delkang"], delsticker, admin_ok=True, block=False)
STICKERS_HANDLER = DisableAbleCommandHandler("stickers", cb_sticker, block=False)

application.add_handler(STICKERS_HANDLER)
application.add_handler(STICKERID_HANDLER)
application.add_handler(GETSTICKER_HANDLER)
application.add_handler(KANG_HANDLER)
application.add_handler(DELKANG_HANDLER)
