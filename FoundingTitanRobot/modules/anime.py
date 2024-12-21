import datetime
import html
import textwrap

import bs4
import jikanpy
import requests
from telegram.constants import ParseMode
from telegram.helpers import mention_html
from FoundingTitanRobot import OWNER_ID, TITANSHIFTERS, REDIS, application
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      Update, Message)
from telegram.ext import CallbackContext, CallbackQueryHandler, ContextTypes

info_btn = "More Information"
prequel_btn = "⬅️ Prequel"
sequel_btn = "Sequel ➡️"
close_btn = "Close ❌"

# Reworked @meanii <https://github.com/meanii>  

def shorten(description, info='anilist.co'):
    msg = ""
    if len(description) > 700:
        description = f'{description[:650]}....'
        msg += f"\n*Description*: _{description} [Read More]({info})_"
    else:
        msg += f"\n*Description*: _{description}_"
    return msg


#time formatter from uniborg
def t(milliseconds: int) -> str:
    """Inputs time in milliseconds, to get beautified time,
    as string"""
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        (f"{str(days)} Days, " if days else "")
        + (f"{str(hours)} Hours, " if hours else "")
        + (f"{str(minutes)} Minutes, " if minutes else "")
        + (f"{str(seconds)} Seconds, " if seconds else "")
        + (f"{str(milliseconds)} ms, " if milliseconds else "")
    )
    return tmp[:-2]


airing_query = '''
    query ($id: Int,$search: String) { 
      Media (id: $id, type: ANIME,search: $search) { 
        id
        episodes
        title {
          romaji
          english
          native
        }
        nextAiringEpisode {
           airingAt
           timeUntilAiring
           episode
        } 
      }
    }
    '''

fav_query = """
query ($id: Int) { 
      Media (id: $id, type: ANIME) { 
        id
        title {
          romaji
          english
          native
        }
     }
}
"""

anime_query = '''
   query ($id: Int,$search: String) { 
      Media (id: $id, type: ANIME,search: $search) { 
        id
        title {
          romaji
          english
          native
        }
        description (asHtml: false)
        startDate{
            year
          }
          episodes
          season
          type
          format
          status
          duration
          siteUrl
          studios{
              nodes{
                   name
              }
          }
          trailer{
               id
               site 
               thumbnail
          }
          averageScore
          genres
          bannerImage
      }
    }
'''
character_query = """
    query ($query: String) {
        Character (search: $query) {
               id
               name {
                     first
                     last
                     full
                     native
               }
               siteUrl
               image {
                        large
               }
               description
        }
    }
"""

manga_query = """
query ($id: Int,$search: String) { 
      Media (id: $id, type: MANGA,search: $search) { 
        id
        title {
          romaji
          english
          native
        }
        description (asHtml: false)
        startDate{
            year
          }
          type
          format
          status
          siteUrl
          averageScore
          genres
          bannerImage
      }
    }
"""

url = 'https://graphql.anilist.co'


async def airing(update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    search_str = message.text.split(' ', 1)
    if len(search_str) == 1:
        await update.effective_message.reply_text(
            'Format: /airing <anime name>)')
        return
    variables = {'search': search_str[1]}
    response = requests.post(
        url, json={
            'query': airing_query,
            'variables': variables
        }).json()['data']['Media']
    msg = f"*Name*: *{response['title']['romaji']}*(`{response['title']['native']}`)\n*ID*: `{response['id']}`"
    if response['nextAiringEpisode']:
        time = response['nextAiringEpisode']['timeUntilAiring'] * 1000
        time = t(time)
        msg += f"\n*Episode*: `{response['nextAiringEpisode']['episode']}`\n*Airing In*: `{time}`"
    else:
        msg += f"\n*Episode*:{response['episodes']}\n*Status*: `N/A`"
    await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def anime(update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    search = message.text.split(' ', 1)
    if len(search) == 1:
        await update.effective_message.reply_text('USAGE : /anime < anime name >')
        return
    else:
        search = search[1]
    variables = {'search': search}
    json = requests.post(
        url, json={
            'query': anime_query,
            'variables': variables
        }).json()
    if 'errors' in json.keys():
        await update.effective_message.reply_text('Anime not found')
        return
    if json:
        json = json['data']['Media']
        msg = f"*{json['title']['romaji']}*(`{json['title']['native']}`)\n*Type*: {json['format']}\n*Status*: {json['status']}\n*Episodes*: {json.get('episodes', 'N/A')}\n*Duration*: {json.get('duration', 'N/A')} Per Ep.\n*Score*: {json['averageScore']}\n*Genres*: `"
        for x in json['genres']:
            msg += f"{x}, "
        msg = msg[:-2] + '`\n'
        msg += "*Studios*: `"
        for x in json['studios']['nodes']:
            msg += f"{x['name']}, "
        msg = msg[:-2] + '`\n'
        anime_name_w = f"{json['title']['romaji']}"
        info = json.get('siteUrl')
        trailer = json.get('trailer', None)
        anime_id = json['id']
        if trailer:
            trailer_id = trailer.get('id', None)
            site = trailer.get('site', None)
            if site == "youtube":
                trailer = f'https://youtu.be/{trailer_id}'
        description = json.get('description', 'N/A').replace("<br>", "")
        print(description)
        msg += shorten(description, info)
        image = json.get('bannerImage', None)
        if trailer:
            buttons = [[
                InlineKeyboardButton("More Info", url=info),
                InlineKeyboardButton("Trailer 🎬", url=trailer)
            ]]
        else:
            buttons = [[InlineKeyboardButton("More Info", url=info)]]
        buttons += [[InlineKeyboardButton("Add to Watchlist", callback_data=f"xanime_watchlist={anime_name_w}")]]
        if image:
            try:
                await update.effective_message.reply_photo(
                    photo=image,
                    caption=msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(buttons))
            except Exception:
                msg += f" [〽️]({image})"
                await update.effective_message.reply_text(
                    msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await update.effective_message.reply_text(
                msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons))


async def character(update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    search = message.text.split(' ', 1)
    if len(search) == 1:
        await update.effective_message.reply_text(
            'Format : /character <character name>')
        return
    search = search[1]
    variables = {'query': search}
    json = requests.post(
        url, json={
            'query': character_query,
            'variables': variables
        }).json()
    if 'errors' in json.keys():
        await update.effective_message.reply_text('Character not found')
        return
    if json:
        json = json['data']['Character']
        msg = f"*{json.get('name').get('full')}*(`{json.get('name').get('native')}`)\n"
        description = f"{json['description']}"
        site_url = json.get('siteUrl')
        char_name = f"{json.get('name').get('full')}"
        msg += shorten(description, site_url)
        if image := json.get('image', None):
            image = image.get('large')
            buttons = [[InlineKeyboardButton("Add to favorite character", callback_data=f"xanime_fvrtchar={char_name}")]]
            await update.effective_message.reply_photo(
                photo=image,
                caption=msg,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN)
        else:
            await update.effective_message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN)


async def manga(update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    search = message.text.split(' ', 1)
    if len(search) == 1:
        await update.effective_message.reply_text('USAGE : /manga < manga name >')
        return
    search = search[1]
    variables = {'search': search}
    json = requests.post(
        url, json={
            'query': manga_query,
            'variables': variables
        }).json()
    msg = ''
    if 'errors' in json.keys():
        await update.effective_message.reply_text('Manga not found')
        return
    if json:
        json = json['data']['Media']
        title, title_native = json['title'].get('romaji',
                                                False), json['title'].get(
                                                    'native', False)
        start_date, status, score = json['startDate'].get(
            'year', False), json.get('status',
                                     False), json.get('averageScore', False)
        if title:
            msg += f"*{title}*"
            if title_native:
                msg += f"(`{title_native}`)"
        if start_date:
            msg += f"\n*Start Date* - `{start_date}`"
        if status:
            msg += f"\n*Status* - `{status}`"
        if score:
            msg += f"\n*Score* - `{score}`"
        msg += '\n*Genres* - '
        for x in json.get('genres', []):
            msg += f"{x}, "
        msg = msg[:-2]
        info = json['siteUrl']
        buttons = [[InlineKeyboardButton("More Info", url=info)]]
        buttons += [[InlineKeyboardButton("Add to Read list", callback_data=f"xanime_manga={title}")]]
        image = json.get("bannerImage", False)
        msg += f"_{json.get('description', None)}_"
        if image:
            try:
                await update.effective_message.reply_photo(
                    photo=image,
                    caption=msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(buttons))
            except Exception:
                msg += f" [〽️]({image})"
                await update.effective_message.reply_text(
                    msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await update.effective_message.reply_text(
                msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons))


async def user(update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    args = message.text.strip().split(" ", 1)

    try:
        search_query = args[1]
    except Exception:
        if message.reply_to_message:
            search_query = message.reply_to_message.text
        else:
            await update.effective_message.reply_text("Format : /user <MyAnimelist Username>")
            return

    jikan = jikanpy.jikan.Jikan()

    try:
        user = jikan.user(search_query)
    except jikanpy.APIException:
        await update.effective_message.reply_text("Username not found.")
        return

    progress_message = await update.effective_message.reply_text("Searching.... ")

    date_format = "%Y-%m-%d"
    if user['image_url'] is None:
        img = "https://cdn.myanimelist.net/images/questionmark_50.gif"
    else:
        img = user['image_url']

    try:
        user_birthday = datetime.datetime.fromisoformat(user['birthday'])
        user_birthday_formatted = user_birthday.strftime(date_format)
    except Exception:
        user_birthday_formatted = "Unknown"

    user_joined_date = datetime.datetime.fromisoformat(user['joined'])
    user_joined_date_formatted = user_joined_date.strftime(date_format)

    for entity in user:
        if user[entity] is None:
            user[entity] = "Unknown"

    about = user['about'].split(" ", 60)

    try:
        about.pop(60)
    except IndexError:
        pass

    about_string = ' '.join(about)
    about_string = about_string.replace("<br>",
                                        "").strip().replace("\r\n", "\n")

    caption = ""

    caption += textwrap.dedent(f"""
    *Username*: [{user['username']}]({user['url']})
    *Gender*: `{user['gender']}`
    *Birthday*: `{user_birthday_formatted}`
    *Joined*: `{user_joined_date_formatted}`
    *Days wasted watching anime*: `{user['anime_stats']['days_watched']}`
    *Days wasted reading manga*: `{user['manga_stats']['days_read']}`
    """)

    caption += f"*About*: {about_string}"

    buttons = [[InlineKeyboardButton(info_btn, url=user['url'])],
               [
                   InlineKeyboardButton(
                       close_btn,
                       callback_data=f"anime_close, {message.from_user.id}")
               ]]

    await update.effective_message.reply_photo(
        photo=img,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)),
    progress_message.delete()


async def upcoming(update, context: ContextTypes.DEFAULT_TYPE):
    jikan = jikanpy.jikan.Jikan()
    upcoming = jikan.top('anime', page=1, subtype="upcoming")

    upcoming_list = [entry['title'] for entry in upcoming['top']]
    upcoming_message = ""

    for entry_num in range(len(upcoming_list)):
        if entry_num == 10:
            break
        upcoming_message += f"{entry_num + 1}. {upcoming_list[entry_num]}\n"

    await update.effective_message.reply_text(upcoming_message)


async def watchlist(update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    watchlist = sorted(REDIS.sunion(f'anime_watch_list{user.id}'))
    if watchlist := "\n• ".join(watchlist):
        await message.reply_text(
            f"{mention_html(user.id, user.first_name)}<b>'s watchlist:</b>\n• {watchlist}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.reply_text(
            "You havn't added anything in your watchlist!"
        )

async def removewatchlist(update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user 
    message = update.effective_message 
    removewlist = message.text.split(' ', 1) 
    args = context.args
    query = " ".join(args)
    if not query:
        await message.reply_text("Please enter a anime name to remove from your watchlist.")
        return
    watchlist = list(REDIS.sunion(f'anime_watch_list{user.id}'))
    removewlist = removewlist[1]
    
    if removewlist not in watchlist:
        await message.reply_text(
            f"<code>{removewlist}</code> doesn't exist in your watch list.",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.reply_text(
            f"<code>{removewlist}</code> has been removed from your watch list.",
            parse_mode=ParseMode.HTML
        )
        REDIS.srem(f'anime_watch_list{user.id}', removewlist)


async def fvrtchar(update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    fvrt_char = sorted(REDIS.sunion(f'anime_fvrtchar{user.id}'))
    if fvrt_char := "\n• ".join(fvrt_char):
        await message.reply_text(
            f"{mention_html(user.id, user.first_name)}<b>'s favorite characters list:</b>\n• {fvrt_char}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.reply_text(
            "You havn't added anything in your favorite characters list!"
        )
        

async def removefvrtchar(update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user 
    message = update.effective_message 
    removewlist = message.text.split(' ', 1) 
    args = context.args
    query = " ".join(args)
    if not query:
        await message.reply_text("Please enter a your favorite character name to remove from your favorite characters list.")
        return
    fvrt_char = list(REDIS.sunion(f'anime_fvrtchar{user.id}'))
    removewlist = removewlist[1]
    
    if removewlist not in fvrt_char:
        await message.reply_text(
            f"<code>{removewlist}</code> doesn't exist in your favorite characters list.",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.reply_text(
            f"<code>{removewlist}</code> has been removed from your favorite characters list.",
            parse_mode=ParseMode.HTML
        )
        REDIS.srem(f'anime_fvrtchar{user.id}', removewlist)
    
async def readmanga(update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    manga_list = sorted(REDIS.sunion(f'anime_mangaread{user.id}'))
    if manga_list := "\n• ".join(manga_list):
        await message.reply_text(
            f"{mention_html(user.id, user.first_name)}<b>'s manga lists:</b>\n• {manga_list}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.reply_text(
            "You havn't added anything in your manga list!"
        )
        
async def removemangalist(update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user 
    message = update.effective_message 
    removewlist = message.text.split(' ', 1) 
    args = context.args
    query = " ".join(args)
    if not query:
        await message.reply_text("Please enter a manga name to remove from your manga list.")
        return
    fvrt_char = list(REDIS.sunion(f'anime_mangaread{user.id}'))
    removewlist = removewlist[1]
    
    if removewlist not in fvrt_char:
        await message.reply_text(
            f"<code>{removewlist}</code> doesn't exist in your manga list.",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.reply_text(
            f"<code>{removewlist}</code> has been removed from your favorite characters list.",
            parse_mode=ParseMode.HTML
        )
        REDIS.srem(f'anime_mangaread{user.id}', removewlist)

async def animestuffs(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    splitter = query.data.split('=')
    query_match = splitter[0]
    callback_anime_data = splitter[1]
    if query_match == "xanime_fvrtchar":
        fvrt_char = list(REDIS.sunion(f'anime_fvrtchar{user.id}'))
        if callback_anime_data not in fvrt_char:
            REDIS.sadd(f'anime_fvrtchar{user.id}', callback_anime_data)
            await context.bot.answer_callback_query(query.id,
                                                text=f"{callback_anime_data} is successfully added to your favorite character.",
                                                show_alert=True)
        else:
            await context.bot.answer_callback_query(query.id,
                                                text=f"{callback_anime_data} already exists in your favorite characters list!",
                                                show_alert=True)
    elif query_match == "xanime_manga":
        fvrt_char = list(REDIS.sunion(f'anime_mangaread{user.id}'))
        if callback_anime_data not in fvrt_char:
            REDIS.sadd(f'anime_mangaread{user.id}', callback_anime_data)
            await context.bot.answer_callback_query(query.id,
                                                text=f"{callback_anime_data} is successfully added to your read list.",
                                                show_alert=True)
        else:
            await context.bot.answer_callback_query(query.id,
                                                text=f"{callback_anime_data} already exists in your read list!",
                                                show_alert=True)

    elif query_match == "xanime_watchlist":
        watchlist = list(REDIS.sunion(f'anime_watch_list{user.id}'))
        if callback_anime_data not in watchlist:
            REDIS.sadd(f'anime_watch_list{user.id}', callback_anime_data)
            await context.bot.answer_callback_query(query.id,
                                                text=f"{callback_anime_data} is successfully added to your watch list.",
                                                show_alert=True)
        else:
            await context.bot.answer_callback_query(query.id,
                                                text=f"{callback_anime_data} already exists in your watch list!",
                                                show_alert=True)
            

    
async def button(update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    query = update.callback_query
    message = query.message
    data = query.data.split(", ")
    print(data)
    query_type = data[0]
    original_user_id = int(data[1])

    user_and_admin_list = [original_user_id, OWNER_ID] + TITANSHIFTERS

    await bot.answer_callback_query(query.id)
    if (
        query_type == "anime_close"
        and query.from_user.id in user_and_admin_list
    ):
        await message.delete()
    elif (
        query_type == "anime_close"
        or query_type in ('anime_anime', 'anime_manga')
        and query.from_user.id != original_user_id
    ):
        await query.answer("You are not allowed to use this.")
    elif query_type in ('anime_anime', 'anime_manga'):
        await message.delete()
        progress_message = await bot.sendMessage(message.chat.id,
                                           "Searching.... ")
        mal_id = data[2]
        caption, buttons, image = get_anime_manga(mal_id, query_type,
                                                  original_user_id)
        await bot.sendPhoto(
            message.chat.id,
            photo=image,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=False)
        await progress_message.delete()


async def extract_arg(message: Message):
    split = message.text.split(" ", 1)
    if len(split) > 1:
        return split[1]
    reply = message.reply_to_message
    return reply.text if reply is not None else None

async def site_search(update: Update, context: CallbackContext, site: str):
    message = update.effective_message
    search_query = extract_arg(message)
    more_results = True

    if not search_query:
        await message.reply_text("Give something to search")
        return

    if site == "GogoAnime":
        search_url = f"https://gogoanime.pe//search.html?keyword={search_query}"
        html_text = requests.get(search_url).text
        soup = bs4.BeautifulSoup(html_text, "html.parser")
        if search_result := soup.find_all("h2", {"class": "post-title"}):
            result = f"<b>Search results for</b> <code>{html.escape(search_query)}</code> <b>on</b> GogoAnime.pe: \n"
            for entry in search_result:
                post_link = "https://gogoanime.pe/" + entry.a["href"]
                post_name = html.escape(entry.text)
                result += f"• <a href='{post_link}'>{post_name}</a>\n"
        else:
            more_results = False
            result = f"<b>No result found for</b> <code>{html.escape(search_query)}</code> <b>on</b> GogoAnime.pe"


async def gogoanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await site_search(update, context, "GogoAnime")


__help__ = """
Get information about anime, manga or characters from [AniList](anilist.co) and [MAL](https://myanimelist.net/)

*AniList Commands:*
 • `/anime <anime>`*:* returns information about the anime from AniList
 • `/character <character>`*:* returns information about the character from AniList
 • `/manga <manga>`*:* returns information about the manga from AniList
 • `/upcoming`*:* returns a list of new anime in the upcoming seasons from AniList
 • `/airing <anime>`*:* returns anime airing info from AniList
 
*MyAnimelist Commands:*
 • `/manime <anime>`*:* returns information about the anime MAL.
 • `/mcharacter` <character>*:* returns information about the character from MAL.
 • `/mmanga <manga>`*:* returns information about the manga from MAL.
 • `/mupcoming`*:* returns a list of new anime in the upcoming seasons from MAL.
 • `/myuser <MyAnimelist Username>`*:* returns information about a MyAnimeList user
 • `/animequotes`*:* sends random anime quotes

*Anime Search Commands:*
• `/whatanime`*:* searches the anime name from media such as a video, gif or an image (Reply to the media with this command)

 *Anime WatchList and Favorite Charac*
• `/watchlist`*:* to get your saved watchlist.
• `/mangalist`*:* to get your saved manga read list.
• `/characterlist | fcl`*:* to get your favorite characters list.
• `/removewatchlist | rwl <anime>`*:* to remove a anime from your list.
• `/rfcharacter | rfcl <character>`*:* to remove a character from your list.  
• `/rmanga | rml <manga>`*:* to remove a manga from your list.
 """

ANIME_HANDLER = DisableAbleCommandHandler("anime", anime, block=False)
AIRING_HANDLER = DisableAbleCommandHandler("airing", airing, block=False)
CHARACTER_HANDLER = DisableAbleCommandHandler(["character","char"], character, block=False)
MANGA_HANDLER = DisableAbleCommandHandler("manga", manga, block=False)
USER_HANDLER = DisableAbleCommandHandler("myuser", user, block=False)
UPCOMING_HANDLER = DisableAbleCommandHandler("upcoming", upcoming, block=False)
WATCHLIST_HANDLER = DisableAbleCommandHandler("watchlist", watchlist, block=False)
MANGALIST_HANDLER = DisableAbleCommandHandler("mangalist", readmanga, block=False)
FVRT_CHAR_HANDLER = DisableAbleCommandHandler(["characterlist","fcl"], fvrtchar, block=False)
REMOVE_WATCHLIST_HANDLER = DisableAbleCommandHandler(["removewatchlist","rwl"], removewatchlist, block=False)
REMOVE_FVRT_CHAR_HANDLER = DisableAbleCommandHandler(["rfcharacter","rfcl"], removefvrtchar, block=False)
REMOVE_MANGA_CHAR_HANDLER = DisableAbleCommandHandler(["rmanga","rml"], removemangalist, block=False)
BUTTON_HANDLER = CallbackQueryHandler(button, pattern='anime_.*', block=False)
ANIME_STUFFS_HANDLER = CallbackQueryHandler(animestuffs, pattern='xanime_.*', block=False)
GOGO_ANIME_HANDLER = DisableAbleCommandHandler("gogo", gogoanime, block=False)

application.add_handler(BUTTON_HANDLER)
application.add_handler(ANIME_STUFFS_HANDLER)
application.add_handler(ANIME_HANDLER)
application.add_handler(CHARACTER_HANDLER)
application.add_handler(MANGA_HANDLER)
application.add_handler(AIRING_HANDLER)
application.add_handler(USER_HANDLER)
application.add_handler(UPCOMING_HANDLER)
application.add_handler(WATCHLIST_HANDLER)
application.add_handler(MANGALIST_HANDLER)
application.add_handler(FVRT_CHAR_HANDLER)
application.add_handler(REMOVE_FVRT_CHAR_HANDLER)
application.add_handler(REMOVE_MANGA_CHAR_HANDLER)
application.add_handler(REMOVE_WATCHLIST_HANDLER)
application.add_handler(GOGO_ANIME_HANDLER)

__mod_name__ = "Anime"

__command_list__ = [
    "anime",
    "manga",
    "character",
    "myuser",
    "upcoming",
    "airing",
    "char",
    "characterlist",
    "fcl",
    "rmanga",
    "rml",
    "rfcharacter",
    "rfcl",
    "mangalist",
    "watchlist",  
    "removewatchlist",
    "rwl",
    "mupcoming",
    "mmanga",
    "manime",
    "mcharacter",
]
__handlers__ = [
    ANIME_HANDLER,
    CHARACTER_HANDLER,
    MANGA_HANDLER,
    USER_HANDLER,
    UPCOMING_HANDLER,
    AIRING_HANDLER,
    REMOVE_MANGA_CHAR_HANDLER,
    REMOVE_FVRT_CHAR_HANDLER,
    WATCHLIST_HANDLER,
    MANGALIST_HANDLER,
    REMOVE_WATCHLIST_HANDLER,
    FVRT_CHAR_HANDLER,    

]
