from typing import List, Optional

from FoundingTitanRobot import LOGGER
from FoundingTitanRobot.modules.users import get_user_id
from telegram import Message, MessageEntity
from telegram.error import BadRequest


async def id_from_reply(message):
    prev_message = message.reply_to_message
    if not prev_message:
        return None, None
    user_id = prev_message.from_user.id
    res = message.text.split(None, 1)
    return (user_id, "") if len(res) < 2 else (user_id, res[1])


async def extract_user(message: Message, args: List[str]) -> Optional[int]:
    data = await extract_user_and_text(message, args)
    return data[0]


async def extract_user_and_text(
    message: Message, args: List[str],
) -> (Optional[int], Optional[str]):
    prev_message = message.reply_to_message
    split_text = message.text.split(None, 1)

    if len(split_text) < 2:
        return await id_from_reply(message)  # only option possible

    text_to_parse = split_text[1]

    text = ""

    entities = list(message.parse_entities([MessageEntity.TEXT_MENTION]))
    ent = entities[0] if entities else None
    # if entity offset matches (command end/text start) then all good
    if entities and ent and ent.offset == len(message.text) - len(text_to_parse):
        ent = entities[0]
        user_id = ent.user.id
        text = message.text[ent.offset + ent.length :]

    elif len(args) >= 1 and args[0][0] == "@":
        user = args[0]
        user_id = await get_user_id(user)
        if not user_id:
            await message.reply_text(
                "No idea who this user is. You'll be able to interact with them if "
                "you reply to that person's message instead, or forward one of that user's messages.",
            )
            return None, None

        else:
            user_id = user_id
            res = message.text.split(None, 2)
            if len(res) >= 3:
                text = res[2]

    elif len(args) >= 1 and args[0].isdigit():
        user_id = int(args[0])
        res = message.text.split(None, 2)
        if len(res) >= 3:
            text = res[2]

    elif prev_message:
        user_id, text = await id_from_reply(message)

    else:
        return None, None

    try:
        await message._bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message in ("User_id_invalid", "Chat not found"):
            await message.reply_text(
                "I don't seem to have interacted with this user before - please forward a message from "
                "them to give me control! (like a voodoo doll, I need a piece of them to be able "
                "to execute certain commands...)",
            )
        else:
            LOGGER.exception("Exception %s on user %s", excp.message, user_id)

        return None, None

    return user_id, text


def extract_text(message) -> str:
    return (
        message.text
        or message.caption
        or (message.sticker.emoji if message.sticker else None)
    )


async def extract_unt_fedban(
    message: Message, args: List[str],
) -> (Optional[int], Optional[str]):
    prev_message = message.reply_to_message
    split_text = message.text.split(None, 1)

    if len(split_text) < 2:
        return await id_from_reply(message)  # only option possible

    text_to_parse = split_text[1]

    text = ""

    entities = list(message.parse_entities([MessageEntity.TEXT_MENTION]))
    ent = entities[0] if entities else None
    # if entity offset matches (command end/text start) then all good
    if entities and ent and ent.offset == len(message.text) - len(text_to_parse):
        ent = entities[0]
        user_id = ent.user.id
        text = message.text[ent.offset + ent.length :]

    elif len(args) >= 1 and args[0][0] == "@":
        user = args[0]
        user_id = await get_user_id(user)
        if not user_id and not isinstance(user_id, int):
            await message.reply_text(
                "I don't have that user in my db.  "
                "You'll be able to interact with them if you reply to that person's message instead, or forward one of that user's messages.",
            )
            return None, None

        else:
            user_id = user_id
            res = message.text.split(None, 2)
            if len(res) >= 3:
                text = res[2]

    elif len(args) >= 1 and args[0].isdigit():
        user_id = int(args[0])
        res = message.text.split(None, 2)
        if len(res) >= 3:
            text = res[2]

    elif prev_message:
        user_id, text = await id_from_reply(message)

    else:
        return None, None

    try:
        await message._bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message in ("User_id_invalid", "Chat not found") and not isinstance(
            user_id, int,
        ):
            await message.reply_text(
                "I don't seem to have interacted with this user before "
                "please forward a message from them to give me control! "
                "(like a voodoo doll, I need a piece of them to be able to execute certain commands...)",
            )
            return None, None
        elif excp.message != "Chat not found":
            LOGGER.exception("Exception %s on user %s", excp.message, user_id)
            return None, None
        elif not isinstance(user_id, int):
            return None, None

    return user_id, text


async def extract_user_fban(message: Message, args: List[str]) -> Optional[int]:
    return await extract_unt_fedban(message, args)[0]
