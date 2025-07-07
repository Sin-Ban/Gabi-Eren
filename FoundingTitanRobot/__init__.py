import logging
import os
import sys
import time
from pyrogram.client import Client
from pbwrap import Pastebin
import telegram.ext as tg
from telethon import TelegramClient
from redis import Redis, ConnectionPool

StartTime = time.time()
# enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)

LOGGER = logging.getLogger(__name__)
logging.getLogger('ptbcontrib.postgres_persistence.postgrespersistence').setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# if version < 3.6, stop bot.
if sys.version_info[0] < 3 or sys.version_info[1] < 6:
    LOGGER.error(
        "You MUST have a python version of at least 3.6! Multiple features depend on this. Bot quitting.",
    )
    quit(1)
# load env variables
if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()

ENV = bool(os.getenv("ENV", False))
TOKEN = os.getenv("TOKEN", "1609173332:AAHhiISpdOlKLMMsNUiLMrohDQeQvZFc2eM")

try:
    OWNER_ID = int(os.getenv("OWNER_ID", "6200648859"))
    DEVIL_SUCCESSOR = int(os.getenv("DEVIL_SUCCESSOR", 0))
except ValueError as e:
    raise Exception(
        "Your OWNER_ID and Anugay env variable is not a valid integer."
    ) from e

JOIN_LOGGER = os.getenv("JOIN_LOGGER", "-1001992945056")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "QuincyKingYhwach")

try:
    TITANSHIFTERS = {int(x) for x in os.getenv("TITANSHIFTERS", "").split()}
    ACKERMANS = {int(x) for x in os.getenv("ACKERMANS", "").split()}
except ValueError as exc:
    raise Exception(
        "Your sudo or dev users list does not contain valid integers."
    ) from exc

try:
    ROYALS = {int(x) for x in os.getenv("ROYALS", "").split()}
except ValueError as err:
    raise Exception(
        "Your support users list does not contain valid integers."
    ) from err

try:
    GARRISONS = {int(x) for x in os.getenv("GARRISONS", "").split()}
except ValueError as exception:
    raise Exception(
        "Your whitelisted users list does not contain valid integers."
    ) from exception

try:
    SCOUTS = {int(x) for x in os.getenv("SCOUTS", "").split()}
except ValueError as error:
    raise Exception(
        "Your scout users list does not contain valid integers."
    ) from error

INFOPIC = bool(os.getenv("INFOPIC", True))
EVENT_LOGS = os.getenv("EVENT_LOGS", "-1001992945056")
WEBHOOK = bool(os.getenv("WEBHOOK", False))
URL = os.getenv("URL", "")  # Does not contain token
PORT = int(os.getenv("PORT", 69))
CERT_PATH = bool(os.getenv("CERT_PATH", False))
API_ID = int(os.getenv("API_ID", "3975570"))
API_HASH = str(os.getenv("API_HASH", "680b62f2844aa1954216f6cb99d2f3d9"))
DB_URI = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_uUqmFI9bdV4y@ep-cool-lab-a142ebve-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
LOAD = os.getenv("LOAD", "").split()
NO_LOAD = os.getenv("NO_LOAD", "translation").split()
DEL_CMDS = bool(os.getenv("DEL_CMDS", False))
STRICT_GBAN = bool(os.getenv("STRICT_GBAN", False))
WORKERS = int(os.getenv("WORKERS", 5))
BAN_STICKER = os.getenv("BAN_STICKER", "CAADAgADOwADPPEcAXkko5EB3YGYAg")
ALLOW_EXCL = os.getenv("ALLOW_EXCL", False)
TEMP_DOWNLOAD_DIRECTORY = os.getenv("TEMP_DOWNLOAD_DIRECTORY", "./")
CASH_API_KEY = os.getenv("CASH_API_KEY", None)
TIME_API_KEY = os.getenv("TIME_API_KEY", None)
REDIS_URL = os.getenv("REDIS_URI", "redis://default:YLlSVYUStARjnVMgJhJgALexOAqOJymp@hopper.proxy.rlwy.net:39396")
ARQ_API = os.getenv("ARQ_API", None)
BOT_ID = int(os.getenv("BOT_ID", "1609173332"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "Gabi_Braun_Robot")
SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", None)
ALLOW_CHATS = os.getenv("ALLOW_CHATS", True)
ERROR_LOGS = os.getenv("ERROR_LOGS", None)
DEVIL_SUCCESSOR = int(os.getenv("DEVIL_SUCCESSOR", 0))
MARIN = int(os.getenv("MARIN", 0))
PASTE_API = os.getenv("PASTE_API", None)
PASTE_PASS = os.getenv("PASTE_PASS", None)
PASTE_USER = os.getenv("PASTE_USER", None)
POLLS = os.getenv("POLLS", True)


try:
    BL_CHATS = {int(x) for x in os.getenv("BL_CHATS", "").split()}
except ValueError as an_exception:
    raise Exception(
        "Your blacklisted chats list does not contain valid integers."
    ) from an_exception
            

TITANSHIFTERS.add(OWNER_ID)
ACKERMANS.add(OWNER_ID)
TITANSHIFTERS.add(DEVIL_SUCCESSOR)
ACKERMANS.add(DEVIL_SUCCESSOR)
TITANSHIFTERS.add(MARIN)

pool = ConnectionPool.from_url(REDIS_URL, decode_responses=True)
REDIS = Redis(connection_pool=pool)
try:
    REDIS.ping()
    LOGGER.info("Connecting to the Redis Database!")
except BaseException as an_error:
    raise Exception(
        "Your redis server is not alive, please check again."
    ) from an_error
finally:
    REDIS.ping()
    LOGGER.info("Connection to the Redis Database Established Successfully!")


application = tg.Application.builder().token(TOKEN).build()
telethn = TelegramClient(f"TelethonSession_{BOT_ID}", API_ID, API_HASH, use_ipv6=True)
pbot = Client(f"PyrogramSession_{BOT_ID}", api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN, workers=WORKERS, ipv6=True)
eren_paste = Pastebin(api_dev_key=PASTE_API)
#try:
#   eren_paste.authenticate(PASTE_USER, PASTE_PASS)
# except Exception as e:
#    print(f"Aunthentication values are wrong, error: {e}")

TITANSHIFTERS = list(TITANSHIFTERS) + list(ACKERMANS)
ACKERMANS = list(ACKERMANS)
GARRISONS = list(GARRISONS)
ROYALS = list(ROYALS)
SCOUTS = list(SCOUTS)
BL_CHATS = list(BL_CHATS)
# Load at end to ensure all prev variables have been set
from FoundingTitanRobot.modules.helper_funcs.handlers import (
    CustomCommandHandler,
   # CustomMessageHandler,
   # CustomRegexHandler,
)

# make sure the regex handler can take extra kwargs
# tg.StringRegexHandler = CustomRegexHandler
tg.CommandHandler = CustomCommandHandler
# tg.MessageHandler = CustomMessageHandler
