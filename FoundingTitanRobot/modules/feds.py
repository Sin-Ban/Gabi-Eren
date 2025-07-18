import ast
import csv
import json
import os
import re
import time
import uuid
from io import BytesIO

import FoundingTitanRobot.modules.sql.feds_sql as sql
from FoundingTitanRobot import (
    EVENT_LOGS,
    LOGGER,
    SUPPORT_CHAT,
    OWNER_ID,
    TITANSHIFTERS,
    SCOUTS,
    GARRISONS,
    application,
)
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from FoundingTitanRobot.modules.helper_funcs.alternate import send_message
from FoundingTitanRobot.modules.helper_funcs.chat_status import is_user_admin
from FoundingTitanRobot.modules.helper_funcs.extraction import (
    extract_unt_fedban,
    extract_user,
    extract_user_fban,
)
from FoundingTitanRobot.modules.helper_funcs.string_handling import markdown_parser
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError, Forbidden
from telegram.ext import (
    ContextTypes,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
)
from telegram.helpers import mention_html, mention_markdown

# Hello bot owner, I spended for feds many hours of my life, Please don't remove this if you still respect MrYacha and peaktogoo and AyraHikari too
# Federation by MrYacha 2018-2019
# Federation rework by Mizukito Akito 2019
# Federation update v2 by Ayra Hikari 2019
# Time spended on feds = 10h by #MrYacha
# Time spended on reworking on the whole feds = 22+ hours by @peaktogoo
# Time spended on updating version to v2 = 26+ hours by @AyraHikari
# Total spended for making this features is 68+ hours
# LOGGER.info("Original federation module by MrYacha, reworked by Mizukito Akito (@peaktogoo) on Telegram.")

FBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the owner of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat",
    "Have no rights to send a message",
}

UNFBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Method is available for supergroup and channel chats only",
    "Not in the chat",
    "Channel_private",
    "Chat_admin_required",
    "Have no rights to send a message",
}


async def new_fed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if chat.type != "private":
        await update.effective_message.reply_text(
            "Federations can only be created by privately messaging me.",
        )
        return
    if len(message.text) == 1:
        await send_message(
            update.effective_message, "Please write the name of the federation!",
        )
        return
    fednam = message.text.split(None, 1)[1]
    if fednam != "":
        fed_id = str(uuid.uuid4())
        fed_name = fednam
        LOGGER.info(fed_id)

        # Currently only for owner
        # if fednam == 'Team Nusantara Disciplinary Circle':
        # fed_id = "TeamNusantaraDevs"

        x = sql.new_fed(user.id, fed_name, fed_id)
        if not x:
            await update.effective_message.reply_text(
                f"Can't federate! Please contact @{SUPPORT_CHAT} if the problem persist.",
            )
            return

        await update.effective_message.reply_text(
            f"*You have succeeded in creating a new federation!*\nName: `{fed_name}`\nID: `{fed_id}`\n\nUse the command below to join the federation:\n`/joinfed {fed_id}`",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            await bot.send_message(
                EVENT_LOGS,
                f"New Federation: <b>{fed_name}</b>\nID: <pre>{fed_id}</pre>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            LOGGER.warning("Cannot send a message to EVENT_LOGS")
    else:
        await update.effective_message.reply_text(
            "Please write down the name of the federation",
        )


async def del_fed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    if chat.type != "private":
        await update.effective_message.reply_text(
            "Federations can only be deleted by privately messaging me.",
        )
        return
    if args:
        is_fed_id = args[0]
        getinfo = sql.get_fed_info(is_fed_id)
        if getinfo is False:
            await update.effective_message.reply_text("This federation does not exist.")
            return
        if int(getinfo["owner"]) == int(user.id) or int(user.id) == OWNER_ID:
            fed_id = is_fed_id
        else:
            await update.effective_message.reply_text("Only federation owners can do this!")
            return
    else:
        await update.effective_message.reply_text("What should I delete?")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        await update.effective_message.reply_text("Only federation owners can do this!")
        return

    await update.effective_message.reply_text(
        f"""You sure you want to delete your federation? This cannot be reverted, you will lose your entire ban list, and '{getinfo["fname"]}' will be permanently lost.""",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="⚠️ Delete Federation ⚠️",
                        callback_data=f"rmfed_{fed_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Cancel", callback_data="rmfed_cancel"
                    )
                ],
            ]
        ),
    )


async def rename_fed(update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.effective_message
    args = msg.text.split(None, 2)

    if len(args) < 3:
        return await msg.reply_text("usage: /renamefed <fed_id> <newname>")

    fed_id, newname = args[1], args[2]
    verify_fed = sql.get_fed_info(fed_id)

    if not verify_fed:
        return await msg.reply_text("This fed not exist in my database!")

    if is_user_fed_owner(fed_id, user.id):
        sql.rename_fed(fed_id, user.id, newname)
        await msg.reply_text(f"Successfully renamed your fed name to {newname}!")
    else:
        await msg.reply_text("Only federation owner can do this!")


async def fed_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    fed_id = sql.get_fed_id(chat.id)

    user_id = update.effective_message.from_user.id
    if not await is_user_admin(update.effective_chat, user_id):
        await update.effective_message.reply_text(
            "You must be an admin to execute this command",
        )
        return

    if not fed_id:
        await update.effective_message.reply_text("This group is not in any federation!")
        return

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = f'This group is part of the following federation:\n{info["fname"]} (ID: <code>{fed_id}</code>)'
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def join_fed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    message = update.effective_message
    administrators = chat.get_administrators()
    fed_id = sql.get_fed_id(chat.id)

    if user.id not in TITANSHIFTERS:
        for admin in administrators:
            status = admin.status
            if str(admin.user.id) != str(user.id) and status == "owner":
                await update.effective_message.reply_text(
                    "Only group creators can use this command!",
                )
                return
    if fed_id:
        await message.reply_text("You cannot join two federations from one chat")
        return

    if len(args) >= 1:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            await message.reply_text("Please enter a valid federation ID")
            return

        x = sql.chat_join_fed(args[0], chat.title, chat.id)
        if not x:
            await message.reply_text(
                f"Failed to join federation! Please contact @{SUPPORT_CHAT} should this problem persist!",
            )
            return

        if get_fedlog := sql.get_fed_log(args[0]):
            if ast.literal_eval(get_fedlog):
                await bot.send_message(
                    get_fedlog,
                    f'Chat *{chat.title}* has joined the federation *{getfed["fname"]}*',
                    parse_mode="markdown",
                )

        await message.reply_text(
            f'This group has joined the federation: {getfed["fname"]}!'
        )


async def leave_fed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our PM!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fed_info = sql.get_fed_info(fed_id)

    # administrators = chat.get_administrators().status
    getuser = await bot.get_chat_member(chat.id, user.id).status
    if getuser in "owner" or user.id in TITANSHIFTERS:
        if sql.chat_leave_fed(chat.id) is True:
            if get_fedlog := sql.get_fed_log(fed_id):
                if ast.literal_eval(get_fedlog):
                    await bot.send_message(
                        get_fedlog,
                        f'Chat *{chat.title}* has left the federation *{fed_info["fname"]}*',
                        parse_mode="markdown",
                    )
            await send_message(
                update.effective_message,
                f'This group has left the federation {fed_info["fname"]}!',
            )
        else:
            await update.effective_message.reply_text(
                "How can you leave a federation that you never joined?!",
            )
    else:
        await update.effective_message.reply_text("Only group creators can use this command!")


async def user_join_fed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id) or user.id in TITANSHIFTERS:
        user_id = await extract_user(msg, args)
        if user_id:
            user = await bot.get_chat(user_id)
        elif not msg.reply_to_message and not args:
            user = msg.from_user
        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            await msg.reply_text("I cannot extract user from this message")
            return
        else:
            LOGGER.warning("error")
        getuser = sql.search_user_in_fed(fed_id, user_id)
        fed_id = sql.get_fed_id(chat.id)
        info = sql.get_fed_info(fed_id)
        get_owner = ast.literal_eval(info["fusers"])["owner"]
        get_owner = await bot.get_chat(get_owner).id
        if user_id == get_owner:
            await update.effective_message.reply_text(
                "You do know that the user is the federation owner, right? RIGHT?",
            )
            return
        if getuser:
            await update.effective_message.reply_text(
                "I cannot promote users who are already federation admins! Can remove them if you want!",
            )
            return
        if user_id == bot.id:
            await update.effective_message.reply_text(
                "I already am a federation admin in all federations!",
            )
            return
        if res := sql.user_join_fed(fed_id, user_id):
            await update.effective_message.reply_text("Successfully Promoted!")
        else:
            await update.effective_message.reply_text("Failed to promote!")
    else:
        await update.effective_message.reply_text("Only federation owners can do this!")


async def user_demote_fed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id):
        msg = update.effective_message
        user_id = await extract_user(msg, args)
        if user_id:
            user = await bot.get_chat(user_id)

        elif not msg.reply_to_message and not args:
            user = msg.from_user

        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            await msg.reply_text("I cannot extract user from this message")
            return
        else:
            LOGGER.warning("error")

        if user_id == bot.id:
            await update.effective_message.reply_text(
                "The thing you are trying to demote me from will fail to work without me! Just saying.",
            )
            return

        if sql.search_user_in_fed(fed_id, user_id) is False:
            await update.effective_message.reply_text(
                "I cannot demote people who are not federation admins!",
            )
            return

        res = sql.user_demote_fed(fed_id, user_id)
        if res is True:
            await update.effective_message.reply_text("Demoted from a Fed Admin!")
        else:
            await update.effective_message.reply_text("Demotion failed!")
    else:
        await update.effective_message.reply_text("Only federation owners can do this!")
        return


async def fed_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    if args:
        fed_id = args[0]
    else:
        if chat.type == 'private':
            await send_message(
                update.effective_message, "You need to provide me a fedid to check fedinfo in my pm.",
            )
            return
        fed_id = sql.get_fed_id(chat.id)
        if not fed_id:
            await send_message(
                update.effective_message, "This group is not in any federation!",
            )
            return
    info = sql.get_fed_info(fed_id)
    if is_user_fed_admin(fed_id, user.id) is False:
        await update.effective_message.reply_text("Only a federation admin can do this!")
        return

    owner = await bot.get_chat(info["owner"])
    try:
        owner_name = f"{owner.first_name} {owner.last_name}"
    except Exception:
        owner_name = owner.first_name
    FEDADMIN = sql.all_fed_users(fed_id)
    TotalAdminFed = len(FEDADMIN)

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = f"<b>ℹ️ Federation Information:</b>\nFedID: <code>{fed_id}</code>"
    text += f'\nName: {info["fname"]}'
    text += f"\nCreator: {mention_html(owner.id, owner_name)}"
    text += f"\nAll Admins: <code>{TotalAdminFed}</code>"
    getfban = sql.get_all_fban_users(fed_id)
    text += f"\nTotal banned users: <code>{len(getfban)}</code>"
    getfchat = sql.all_fed_chats(fed_id)
    text += f"\nNumber of groups in this federation: <code>{len(getfchat)}</code>"

    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def fed_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        await update.effective_message.reply_text("This group is not in any federation!")
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        await update.effective_message.reply_text("Only federation admins can do this!")
        return

    user = update.effective_user
    chat = update.effective_chat
    info = sql.get_fed_info(fed_id)

    text = f'<b>Federation Admin {info["fname"]}:</b>\n\n' + "👑 Owner:\n"
    owner = await bot.get_chat(info["owner"])
    try:
        owner_name = f"{owner.first_name} {owner.last_name}"
    except Exception:
        owner_name = owner.first_name
    text += f" • {mention_html(owner.id, owner_name)}\n"

    members = sql.all_fed_members(fed_id)
    if len(members) == 0:
        text += "\n🔱 There are no admins in this federation"
    else:
        text += "\n🔱 Admin:\n"
        for x in members:
            user = await bot.get_chat(x)
            text += f" • {mention_html(user.id, user.first_name)}\n"

    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def fed_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        await update.effective_message.reply_text(
            "This group is not a part of any federation!",
        )
        return

    info = sql.get_fed_info(fed_id)
    getfednotif = sql.user_feds_report(info["owner"])

    if is_user_fed_admin(fed_id, user.id) is False:
        await update.effective_message.reply_text("Only federation admins can do this!")
        return

    message = update.effective_message

    user_id, reason = await extract_unt_fedban(message, args)

    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)

    if not user_id:
        await message.reply_text("You don't seem to be referring to a user")
        return

    if user_id == bot.id:
        await message.reply_text(
            "What is funnier than kicking the group owner? Self sacrifice.",
        )
        return

    if is_user_fed_owner(fed_id, user_id) is True:
        await message.reply_text("Why did you try the federation fban?")
        return

    if is_user_fed_admin(fed_id, user_id) is True:
        await message.reply_text("He is a federation admin, I can't fban him.")
        return

    if user_id == OWNER_ID:
        await message.reply_text("Disaster level God cannot be fed banned!")
        return

    if int(user_id) in TITANSHIFTERS:
        await message.reply_text("Dragons cannot be fed banned!")
        return

    if int(user_id) in SCOUTS:
        await message.reply_text("Tigers cannot be fed banned!")
        return

    if int(user_id) in GARRISONS:
        await message.reply_text("Wolves cannot be fed banned!")
        return

    if user_id in [777000, 1087968824]:
        await message.reply_text("Fool! You can't attack Telegram's native tech!")
        return

    try:
        user_chat = await bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_name = user_chat.first_name
        fban_user_lname = user_chat.last_name
        fban_user_uname = user_chat.username
    except BadRequest as excp:
        if not str(user_id).isdigit():
            await send_message(update.effective_message, excp.message)
            return
        elif len(str(user_id)) != 9:
            await send_message(update.effective_message, "That's so not a user!")
            return
        isvalid = False
        fban_user_id = int(user_id)
        fban_user_name = f"user({user_id})"
        fban_user_lname = None
        fban_user_uname = None

    if isvalid and user_chat.type != "private":
        await send_message(update.effective_message, "That's so not a user!")
        return

    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_name)
    else:
        user_target = fban_user_name

    if fban:
        fed_name = info["fname"]
        # https://t.me/OnePunchSupport/41606 // https://t.me/OnePunchSupport/41619
        # starting = "The reason fban is replaced for {} in the Federation <b>{}</b>.".format(user_target, fed_name)
        # await send_message(update.effective_message, starting, parse_mode=ParseMode.HTML)

        # if reason == "":
        #    reason = "No reason given."

        temp = sql.un_fban_user(fed_id, fban_user_id)
        if not temp:
            await message.reply_text("Failed to update the reason for fedban!")
            return
        x = sql.fban_user(
            fed_id,
            fban_user_id,
            fban_user_name,
            fban_user_lname,
            fban_user_uname,
            reason,
            int(time.time()),
        )
        if not x:
            await message.reply_text(
                f"Failed to ban from the federation! If this problem continues, contact @{SUPPORT_CHAT}.",
            )
            return

        fed_chats = sql.all_fed_chats(fed_id)
        # Will send to current chat
        await bot.send_message(
            chat.id,
            f"<b>FedBan reason updated</b>\n<b>Federation:</b> {fed_name}\n<b>Federation Admin:</b> {mention_html(user.id, user.first_name)}\n<b>User:</b> {user_target}\n<b>User ID:</b> <code>{fban_user_id}</code>\n<b>Reason:</b> {reason}",
            parse_mode="HTML",
        )
        # Send message to owner if fednotif is enabled
        if getfednotif:
            await bot.send_message(
                info["owner"],
                f"<b>FedBan reason updated</b>\n<b>Federation:</b> {fed_name}\n<b>Federation Admin:</b> {mention_html(user.id, user.first_name)}\n<b>User:</b> {user_target}\n<b>User ID:</b> <code>{fban_user_id}</code>\n<b>Reason:</b> {reason}",
                parse_mode="HTML",
            )
        if get_fedlog := sql.get_fed_log(fed_id):
            if int(get_fedlog) != int(chat.id):
                await bot.send_message(
                    get_fedlog,
                    "<b>FedBan reason updated</b>"
                    "\n<b>Federation:</b> {}"
                    "\n<b>Federation Admin:</b> {}"
                    "\n<b>User:</b> {}"
                    "\n<b>User ID:</b> <code>{}</code>"
                    "\n<b>Reason:</b> {}".format(
                        fed_name,
                        mention_html(user.id, user.first_name),
                        user_target,
                        fban_user_id,
                        reason,
                    ),
                    parse_mode="HTML",
                )
        for fedschat in fed_chats:
            try:
                # Do not spam all fed chats
                """
				bot.send_message(chat, "<b>FedBan reason updated</b>" \
							 "\n<b>Federation:</b> {}" \
							 "\n<b>Federation Admin:</b> {}" \
							 "\n<b>User:</b> {}" \
							 "\n<b>User ID:</b> <code>{}</code>" \
							 "\n<b>Reason:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
				"""
                await bot.ban_chat_member(fedschat, fban_user_id)
            except BadRequest as excp:
                if excp.message in FBAN_ERRORS:
                    try:
                        await application.bot.getChat(fedschat)
                    except Forbidden:
                        sql.chat_leave_fed(fedschat)
                        LOGGER.info(
                            "Chat {} has leave fed {} because I was kicked".format(
                                fedschat, info["fname"],
                            ),
                        )
                        continue
                elif excp.message == "User_id_invalid":
                    break
                else:
                    LOGGER.warning(
                        "Could not fban on {} because: {}".format(chat, excp.message),
                    )
            except TelegramError:
                pass
        # Also do not spam all fed admins
        """
		send_to_list(bot, FEDADMIN,
				 "<b>FedBan reason updated</b>" \
							 "\n<b>Federation:</b> {}" \
							 "\n<b>Federation Admin:</b> {}" \
							 "\n<b>User:</b> {}" \
							 "\n<b>User ID:</b> <code>{}</code>" \
							 "\n<b>Reason:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason),
							html=True)
		"""

        if subscriber := list(sql.get_subscriber(fed_id)):
            for fedsid in subscriber:
                all_fedschat = sql.all_fed_chats(fedsid)
                for fedschat in all_fedschat:
                    try:
                        await bot.ban_chat_member(fedschat, fban_user_id)
                    except BadRequest as excp:
                        if excp.message in FBAN_ERRORS:
                            try:
                                await application.bot.getChat(fedschat)
                            except Forbidden:
                                targetfed_id = sql.get_fed_id(fedschat)
                                sql.unsubs_fed(fed_id, targetfed_id)
                                LOGGER.info(
                                    "Chat {} has unsub fed {} because I was kicked".format(
                                        fedschat, info["fname"],
                                    ),
                                )
                                continue
                        elif excp.message == "User_id_invalid":
                            break
                        else:
                            LOGGER.warning(
                                "Unable to fban on {} because: {}".format(
                                    fedschat, excp.message,
                                ),
                            )
                    except TelegramError:
                        pass
        # send_message(update.effective_message, "Fedban Reason has been updated.")
        return

    fed_name = info["fname"]

    # starting = "Starting a federation ban for {} in the Federation <b>{}</b>.".format(
    #    user_target, fed_name)
    # await update.effective_message.reply_text(starting, parse_mode=ParseMode.HTML)

    # if reason == "":
    #    reason = "No reason given."

    x = sql.fban_user(
        fed_id,
        fban_user_id,
        fban_user_name,
        fban_user_lname,
        fban_user_uname,
        reason,
        int(time.time()),
    )
    if not x:
        await message.reply_text(
            f"Failed to ban from the federation! If this problem continues, contact @{SUPPORT_CHAT}.",
        )
        return

    fed_chats = sql.all_fed_chats(fed_id)
    # Will send to current chat
    await bot.send_message(
        chat.id,
        "<b>New FedBan</b>"
        "\n<b>Federation:</b> {}"
        "\n<b>Federation Admin:</b> {}"
        "\n<b>User:</b> {}"
        "\n<b>User ID:</b> <code>{}</code>"
        "\n<b>Reason:</b> {}".format(
            fed_name,
            mention_html(user.id, user.first_name),
            user_target,
            fban_user_id,
            reason,
        ),
        parse_mode="HTML",
    )
    # Send message to owner if fednotif is enabled
    if getfednotif:
        await bot.send_message(
            info["owner"],
            "<b>New FedBan</b>"
            "\n<b>Federation:</b> {}"
            "\n<b>Federation Admin:</b> {}"
            "\n<b>User:</b> {}"
            "\n<b>User ID:</b> <code>{}</code>"
            "\n<b>Reason:</b> {}".format(
                fed_name,
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
                reason,
            ),
            parse_mode="HTML",
        )
    if get_fedlog := sql.get_fed_log(fed_id):
        if int(get_fedlog) != int(chat.id):
            await bot.send_message(
                get_fedlog,
                "<b>New FedBan</b>"
                "\n<b>Federation:</b> {}"
                "\n<b>Federation Admin:</b> {}"
                "\n<b>User:</b> {}"
                "\n<b>User ID:</b> <code>{}</code>"
                "\n<b>Reason:</b> {}".format(
                    fed_name,
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
                    reason,
                ),
                parse_mode="HTML",
            )
    chats_in_fed = 0
    for fedschat in fed_chats:
        chats_in_fed += 1
        try:
            # Do not spamming all fed chats
            """
			bot.send_message(chat, "<b>FedBan reason updated</b>" \
							"\n<b>Federation:</b> {}" \
							"\n<b>Federation Admin:</b> {}" \
							"\n<b>User:</b> {}" \
							"\n<b>User ID:</b> <code>{}</code>" \
							"\n<b>Reason:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
			"""
            await bot.ban_chat_member(fedschat, fban_user_id)
        except BadRequest as excp:
            if excp.message in FBAN_ERRORS:
                pass
            elif excp.message == "User_id_invalid":
                break
            else:
                LOGGER.warning(
                    "Could not fban on {} because: {}".format(chat, excp.message),
                )
        except TelegramError:
            pass

        # Also do not spamming all fed admins
        """
		send_to_list(bot, FEDADMIN,
				 "<b>FedBan reason updated</b>" \
							 "\n<b>Federation:</b> {}" \
							 "\n<b>Federation Admin:</b> {}" \
							 "\n<b>User:</b> {}" \
							 "\n<b>User ID:</b> <code>{}</code>" \
							 "\n<b>Reason:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason),
							html=True)
		"""

        if subscriber := list(sql.get_subscriber(fed_id)):
            for fedsid in subscriber:
                all_fedschat = sql.all_fed_chats(fedsid)
                for fedschat in all_fedschat:
                    try:
                        await bot.ban_chat_member(fedschat, fban_user_id)
                    except BadRequest as excp:
                        if excp.message in FBAN_ERRORS:
                            try:
                                await application.bot.getChat(fedschat)
                            except Forbidden:
                                targetfed_id = sql.get_fed_id(fedschat)
                                sql.unsubs_fed(fed_id, targetfed_id)
                                LOGGER.info(
                                    "Chat {} has unsub fed {} because I was kicked".format(
                                        fedschat, info["fname"],
                                    ),
                                )
                                continue
                        elif excp.message == "User_id_invalid":
                            break
                        else:
                            LOGGER.warning(
                                "Unable to fban on {} because: {}".format(
                                    fedschat, excp.message,
                                ),
                            )
                    except TelegramError:
                        pass
    # if chats_in_fed == 0:
    #    send_message(update.effective_message, "Fedban affected 0 chats. ")
    # elif chats_in_fed > 0:
    #    send_message(update.effective_message,
    #                 "Fedban affected {} chats. ".format(chats_in_fed))


async def unfban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        await update.effective_message.reply_text(
            "This group is not a part of any federation!",
        )
        return

    info = sql.get_fed_info(fed_id)
    getfednotif = sql.user_feds_report(info["owner"])

    if is_user_fed_admin(fed_id, user.id) is False:
        await update.effective_message.reply_text("Only federation admins can do this!")
        return

    user_id = await extract_user_fban(message, args)
    if not user_id:
        await message.reply_text("You do not seem to be referring to a user.")
        return

    try:
        user_chat = await bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_name = user_chat.first_name
        fban_user_lname = user_chat.last_name
        fban_user_uname = user_chat.username
    except BadRequest as excp:
        if not str(user_id).isdigit():
            await send_message(update.effective_message, excp.message)
            return
        elif len(str(user_id)) != 9:
            await send_message(update.effective_message, "That's so not a user!")
            return
        isvalid = False
        fban_user_id = int(user_id)
        fban_user_name = f"user({user_id})"
        fban_user_lname = None
        fban_user_uname = None

    if isvalid and user_chat.type != "private":
        await message.reply_text("That's so not a user!")
        return

    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_name)
    else:
        user_target = fban_user_name

    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, fban_user_id)
    if fban is False:
        await message.reply_text("This user is not fbanned!")
        return

    banner = update.effective_user

    # await message.reply_text("I'll give {} another chance in this federation".format(user_chat.first_name))

    chat_list = sql.all_fed_chats(fed_id)
    # Will send to current chat
    await bot.send_message(
        chat.id,
        f'<b>Un-FedBan</b>\n<b>Federation:</b> {info["fname"]}\n<b>Federation Admin:</b> {mention_html(user.id, user.first_name)}\n<b>User:</b> {user_target}\n<b>User ID:</b> <code>{fban_user_id}</code>',
        parse_mode="HTML",
    )
    # Send message to owner if fednotif is enabled
    if getfednotif:
        await bot.send_message(
            info["owner"],
            f'<b>Un-FedBan</b>\n<b>Federation:</b> {info["fname"]}\n<b>Federation Admin:</b> {mention_html(user.id, user.first_name)}\n<b>User:</b> {user_target}\n<b>User ID:</b> <code>{fban_user_id}</code>',
            parse_mode="HTML",
        )
    if get_fedlog := sql.get_fed_log(fed_id):
        if int(get_fedlog) != int(chat.id):
            await bot.send_message(
                get_fedlog,
                f'<b>Un-FedBan</b>\n<b>Federation:</b> {info["fname"]}\n<b>Federation Admin:</b> {mention_html(user.id, user.first_name)}\n<b>User:</b> {user_target}\n<b>User ID:</b> <code>{fban_user_id}</code>',
                parse_mode="HTML",
            )
    unfbanned_in_chats = 0
    for fedchats in chat_list:
        unfbanned_in_chats += 1
        try:
            member = await bot.get_chat_member(fedchats, user_id)
            if member.status == "kicked":
                await bot.unban_chat_member(fedchats, user_id)
            # Do not spamming all fed chats
            """
			bot.send_message(chat, "<b>Un-FedBan</b>" \
						 "\n<b>Federation:</b> {}" \
						 "\n<b>Federation Admin:</b> {}" \
						 "\n<b>User:</b> {}" \
						 "\n<b>User ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
			"""
        except BadRequest as excp:
            if excp.message in UNFBAN_ERRORS:
                pass
            elif excp.message == "User_id_invalid":
                break
            else:
                LOGGER.warning(
                    "Could not fban on {} because: {}".format(chat, excp.message),
                )
        except TelegramError:
            pass

    try:
        x = sql.un_fban_user(fed_id, user_id)
        if not x:
            await send_message(
                update.effective_message,
                "Un-fban failed, this user may already be un-fedbanned!",
            )
            return
    except Exception:
        pass

    if subscriber := list(sql.get_subscriber(fed_id)):
        for fedsid in subscriber:
            all_fedschat = sql.all_fed_chats(fedsid)
            for fedschat in all_fedschat:
                try:
                    await bot.unban_chat_member(fedchats, user_id)
                except BadRequest as excp:
                    if excp.message in FBAN_ERRORS:
                        try:
                            await application.bot.getChat(fedschat)
                        except Forbidden:
                            targetfed_id = sql.get_fed_id(fedschat)
                            sql.unsubs_fed(fed_id, targetfed_id)
                            LOGGER.info(
                                "Chat {} has unsub fed {} because I was kicked".format(
                                    fedschat, info["fname"],
                                ),
                            )
                            continue
                    elif excp.message == "User_id_invalid":
                        break
                    else:
                        LOGGER.warning(
                            "Unable to fban on {} because: {}".format(
                                fedschat, excp.message,
                            ),
                        )
                except TelegramError:
                    pass

    if unfbanned_in_chats == 0:
        await send_message(
            update.effective_message, "This person has been un-fbanned in 0 chats.",
        )
    if unfbanned_in_chats > 0:
        await send_message(
            update.effective_message,
            "This person has been un-fbanned in {} chats.".format(unfbanned_in_chats),
        )
    # Also do not spamming all fed admins
    """
	FEDADMIN = sql.all_fed_users(fed_id)
	for x in FEDADMIN:
		getreport = sql.user_feds_report(x)
		if getreport is False:
			FEDADMIN.remove(x)
	send_to_list(bot, FEDADMIN,
			 "<b>Un-FedBan</b>" \
			 "\n<b>Federation:</b> {}" \
			 "\n<b>Federation Admin:</b> {}" \
			 "\n<b>User:</b> {}" \
			 "\n<b>User ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name),
												 mention_html(user_chat.id, user_chat.first_name),
															  user_chat.id),
			html=True)
	"""


async def set_frules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        await update.effective_message.reply_text("This group is not in any federation!")
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        await update.effective_message.reply_text("Only fed admins can do this!")
        return

    if len(args) >= 1:
        msg = update.effective_message
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        if len(args) == 2:
            txt = args[1]
            offset = len(txt) - len(raw_text)  # set correct offset relative to command
            markdown_rules = markdown_parser(
                txt, entities=msg.parse_entities(), offset=offset,
            )
        x = sql.set_frules(fed_id, markdown_rules)
        if not x:
            await update.effective_message.reply_text(
                f"Whoa! There was an error while setting federation rules! If you wondered why please ask it in @{SUPPORT_CHAT}!",
            )
            return

        rules = sql.get_fed_info(fed_id)["frules"]
        getfed = sql.get_fed_info(fed_id)
        if get_fedlog := sql.get_fed_log(fed_id):
            if ast.literal_eval(get_fedlog):
                await bot.send_message(
                    get_fedlog,
                    f'*{user.first_name}* has updated federation rules for fed *{getfed["fname"]}*',
                    parse_mode="markdown",
                )
        await update.effective_message.reply_text(f"Rules have been changed to :\n{rules}!")
    else:
        await update.effective_message.reply_text("Please write rules to set this up!")


async def get_frules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        await update.effective_message.reply_text("This group is not in any federation!")
        return

    rules = sql.get_frules(fed_id)
    text = "*Rules in this fed:*\n"
    text += rules
    await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def fed_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    if args:
        chat = update.effective_chat
        fed_id = sql.get_fed_id(chat.id)
        fedinfo = sql.get_fed_info(fed_id)
        if is_user_fed_owner(fed_id, user.id) is False:
            await update.effective_message.reply_text("Only federation owners can do this!")
            return
        # Parsing md
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        text_parser = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
        text = text_parser
        try:
            broadcaster = user.first_name
        except Exception:
            broadcaster = f"{user.first_name} {user.last_name}"
        text += f"\n\n- {mention_markdown(user.id, broadcaster)}"
        chat_list = sql.all_fed_chats(fed_id)
        failed = 0
        for chat in chat_list:
            title = f'*New broadcast from Fed {fedinfo["fname"]}*\n'
            try:
                await bot.sendMessage(chat, title + text, parse_mode="markdown")
            except TelegramError:
                try:
                    await application.bot.getChat(chat)
                except Forbidden:
                    failed += 1
                    sql.chat_leave_fed(chat)
                    LOGGER.info(
                        f'Chat {chat} has left fed {fedinfo["fname"]} because I was punched'
                    )
                    continue
                failed += 1
                LOGGER.warning(f"Couldn't send broadcast to {str(chat)}")

        send_text = "The federation broadcast is complete"
        if failed >= 1:
            send_text += f"{failed} the group failed to receive the message, probably because it left the Federation."
        await update.effective_message.reply_text(send_text)


async def fed_ban_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args, chat_data = context.bot, context.args, context.chat_data
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        await update.effective_message.reply_text(
            "This group is not a part of any federation!",
        )
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        await update.effective_message.reply_text("Only Federation owners can do this!")
        return

    user = update.effective_user
    chat = update.effective_chat
    getfban = sql.get_all_fban_users(fed_id)
    if len(getfban) == 0:
        await update.effective_message.reply_text(
            f'The federation ban list of {info["fname"]} is empty',
            parse_mode=ParseMode.HTML,
        )
        return

    if args:
        if args[0] == "json":
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get("status"):
                if jam <= int(cek.get("value")):
                    waktu = time.strftime(
                        "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value")),
                    )
                    await update.effective_message.reply_text(
                        f"You can backup your data once every 30 minutes!\nYou can back up data again at `{waktu}`",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                else:
                    if user.id not in TITANSHIFTERS:
                        put_chat(chat.id, new_jam, chat_data)
            elif user.id not in TITANSHIFTERS:
                put_chat(chat.id, new_jam, chat_data)
            backups = ""
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                json_parser = {
                    "user_id": users,
                    "first_name": getuserinfo["first_name"],
                    "last_name": getuserinfo["last_name"],
                    "user_name": getuserinfo["user_name"],
                    "reason": getuserinfo["reason"],
                }
                backups += json.dumps(json_parser)
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "saitama_fbanned_users.json"
                await update.effective_message.reply_document(
                    document=output,
                    filename="saitama_fbanned_users.json",
                    caption=f'Total {len(getfban)} User are blocked by the Federation {info["fname"]}.',
                )
            return
        elif args[0] == "csv":
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get("status"):
                if jam <= int(cek.get("value")):
                    waktu = time.strftime(
                        "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value")),
                    )
                    await update.effective_message.reply_text(
                        f"You can back up data once every 30 minutes!\nYou can back up data again at `{waktu}`",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                else:
                    if user.id not in TITANSHIFTERS:
                        put_chat(chat.id, new_jam, chat_data)
            elif user.id not in TITANSHIFTERS:
                put_chat(chat.id, new_jam, chat_data)
            backups = "id,firstname,lastname,username,reason\n"
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                backups += (
                    "{user_id},{first_name},{last_name},{user_name},{reason}".format(
                        user_id=users,
                        first_name=getuserinfo["first_name"],
                        last_name=getuserinfo["last_name"],
                        user_name=getuserinfo["user_name"],
                        reason=getuserinfo["reason"],
                    )
                )
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "saitama_fbanned_users.csv"
                await update.effective_message.reply_document(
                    document=output,
                    filename="saitama_fbanned_users.csv",
                    caption=f'Total {len(getfban)} User are blocked by Federation {info["fname"]}.',
                )
            return

    text = f'<b>{len(getfban)} users have been banned from the federation {info["fname"]}:</b>\n'
    for users in getfban:
        getuserinfo = sql.get_all_fban_users_target(fed_id, users)
        if getuserinfo is False:
            text = f'There are no users banned from the federation {info["fname"]}'
            break
        user_name = getuserinfo["first_name"]
        if getuserinfo["last_name"]:
            user_name += " " + getuserinfo["last_name"]
        text += f" • {mention_html(users, user_name)} (<code>{users}</code>)\n"

    try:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get("status"):
            if jam <= int(cek.get("value")):
                waktu = time.strftime(
                    "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value")),
                )
                await update.effective_message.reply_text(
                    f"You can back up data once every 30 minutes!\nYou can back up data again at `{waktu}`",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            else:
                if user.id not in TITANSHIFTERS:
                    put_chat(chat.id, new_jam, chat_data)
        elif user.id not in TITANSHIFTERS:
            put_chat(chat.id, new_jam, chat_data)
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fbanlist.txt"
            await update.effective_message.reply_document(
                document=output,
                filename="fbanlist.txt",
                caption=f'The following is a list of users who are currently fbanned in the Federation {info["fname"]}.',
            )


async def fed_notif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        await update.effective_message.reply_text(
            "This group is not a part of any federation!",
        )
        return

    if args:
        if args[0] in ("yes", "on"):
            sql.set_feds_setting(user.id, True)
            await msg.reply_text(
                "Reporting Federation back up! Every user who is fban / unfban you will be notified via PM.",
            )
        elif args[0] in ("no", "off"):
            sql.set_feds_setting(user.id, False)
            await msg.reply_text(
                "Reporting Federation has stopped! Every user who is fban / unfban you will not be notified via PM.",
            )
        else:
            await msg.reply_text("Please enter `on`/`off`", parse_mode="markdown")
    else:
        getreport = sql.user_feds_report(user.id)
        await msg.reply_text(
            f"Your current Federation report preferences: `{getreport}`",
            parse_mode="markdown",
        )


async def fed_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        await update.effective_message.reply_text(
            "This group is not a part of any federation!",
        )
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        await update.effective_message.reply_text("Only federation admins can do this!")
        return

    getlist = sql.all_fed_chats(fed_id)
    if len(getlist) == 0:
        await update.effective_message.reply_text(
            f'No users are fbanned from the federation {info["fname"]}',
            parse_mode=ParseMode.HTML,
        )
        return

    text = f'<b>New chat joined the federation {info["fname"]}:</b>\n'
    for chats in getlist:
        try:
            chat_name = await application.bot.getChat(chats).title
        except Forbidden:
            sql.chat_leave_fed(chats)
            LOGGER.info(f'Chat {chats} has leave fed {info["fname"]} because I was kicked')
            continue
        text += f" • {chat_name} (<code>{chats}</code>)\n"

    try:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception:
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fedchats.txt"
            await update.effective_message.reply_document(
                document=output,
                filename="fedchats.txt",
                caption=f'Here is a list of all the chats that joined the federation {info["fname"]}.',
            )


async def fed_import_bans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, chat_data = context.bot, context.chat_data
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)
    getfed = sql.get_fed_info(fed_id)

    if not fed_id:
        await update.effective_message.reply_text(
            "This group is not a part of any federation!",
        )
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        await update.effective_message.reply_text("Only Federation owners can do this!")
        return

    if msg.reply_to_message and msg.reply_to_message.document:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get("status"):
            if jam <= int(cek.get("value")):
                waktu = time.strftime(
                    "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value")),
                )
                await update.effective_message.reply_text(
                    f"You can get your data once every 30 minutes!\nYou can get data again at `{waktu}`",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            else:
                if user.id not in TITANSHIFTERS:
                    put_chat(chat.id, new_jam, chat_data)
        else:
            if user.id not in TITANSHIFTERS:
                put_chat(chat.id, new_jam, chat_data)
        # if int(int(msg.reply_to_message.document.file_size)/1024) >= 200:
        # 	msg.reply_text("This file is too big!")
        # 	return
        success = 0
        failed = 0
        try:
            file_info = await bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            await msg.reply_text(
                "Try downloading and re-uploading the file, this one seems broken!",
            )
            return
        fileformat = msg.reply_to_message.document.file_name.split(".")[-1]
        if fileformat == "json":
            multi_fed_id = []
            multi_import_userid = []
            multi_import_firstname = []
            multi_import_lastname = []
            multi_import_username = []
            multi_import_reason = []
            with BytesIO() as file:
                file_info.download(out=file)
                file.seek(0)
                reading = file.read().decode("UTF-8")
                splitting = reading.split("\n")
                for x in splitting:
                    if x == "":
                        continue
                    try:
                        data = json.loads(x)
                    except json.decoder.JSONDecodeError as err:
                        failed += 1
                        continue
                    try:
                        import_userid = int(data["user_id"])  # Make sure it int
                        import_firstname = str(data["first_name"])
                        import_lastname = str(data["last_name"])
                        import_username = str(data["user_name"])
                        import_reason = str(data["reason"])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if import_userid == bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if import_userid in TITANSHIFTERS:
                        failed += 1
                        continue
                    if import_userid in SCOUTS:
                        failed += 1
                        continue
                    if import_userid in GARRISONS:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
            text = f"Blocks were successfully imported. {success} people are blocked."
            if failed >= 1:
                text += f" {failed} Failed to import."
            if get_fedlog := sql.get_fed_log(fed_id):
                if ast.literal_eval(get_fedlog):
                    teks = f'Fed *{getfed["fname"]}* has successfully imported data. {success} banned.'
                    if failed >= 1:
                        teks += f" {failed} Failed to import."
                    await bot.send_message(get_fedlog, teks, parse_mode="markdown")
        elif fileformat == "csv":
            multi_fed_id = []
            multi_import_userid = []
            multi_import_firstname = []
            multi_import_lastname = []
            multi_import_username = []
            multi_import_reason = []
            file_info.download(f"fban_{msg.reply_to_message.document.file_id}.csv")
            with open(f"fban_{msg.reply_to_message.document.file_id}.csv", "r", encoding="utf8") as csvFile:
                reader = csv.reader(csvFile)
                for data in reader:
                    try:
                        import_userid = int(data[0])  # Make sure it int
                        import_firstname = str(data[1])
                        import_lastname = str(data[2])
                        import_username = str(data[3])
                        import_reason = str(data[4])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if import_userid == bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if import_userid in TITANSHIFTERS:
                        failed += 1
                        continue
                    if import_userid in SCOUTS:
                        failed += 1
                        continue
                    if import_userid in GARRISONS:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                                    # t = ThreadWithReturnValue(target=sql.fban_user, args=(fed_id, str(import_userid), import_firstname, import_lastname, import_username, import_reason,))
                                    # t.start()
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
            csvFile.close()
            os.remove(f"fban_{msg.reply_to_message.document.file_id}.csv")
            text = f"Files were imported successfully. {success} people banned."
            if failed >= 1:
                text += f" {failed} Failed to import."
            if get_fedlog := sql.get_fed_log(fed_id):
                if ast.literal_eval(get_fedlog):
                    teks = "Fed *{}* has successfully imported data. {} banned.".format(
                        getfed["fname"], success,
                    )
                    if failed >= 1:
                        teks += " {} Failed to import.".format(failed)
                    await bot.send_message(get_fedlog, teks, parse_mode="markdown")
        else:
            await send_message(update.effective_message, "This file is not supported.")
            return
        await send_message(update.effective_message, text)


async def del_fed_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    userid = query.message.chat.id
    fed_id = query.data.split("_")[1]

    if fed_id == "cancel":
        await query.message.edit_text("Federation deletion cancelled")
        return

    if getfed := sql.get_fed_info(fed_id):
        if delete := sql.del_fed(fed_id):
            await query.message.edit_text(
                f'You have removed your Federation! Now all the Groups that are connected with `{getfed["fname"]}` do not have a Federation.',
                parse_mode="markdown",
            )


async def fed_stat_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if args and args[0].isdigit():
        user_id = args[0]
    else:
        user_id = await extract_user(msg, args)
    if user_id:
        if len(args) == 2 and args[0].isdigit():
            fed_id = args[1]
            user_name, reason, fbantime = sql.get_user_fban(fed_id, str(user_id))
            if fbantime:
                fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
            else:
                fbantime = "Unavaiable"
            if user_name is False:
                await send_message(
                    update.effective_message,
                    f"Fed {fed_id} not found!",
                    parse_mode="markdown",
                )
                return
            if user_name == "" or user_name is None:
                user_name = "He/she"
            if not reason:
                await send_message(
                    update.effective_message,
                    f"{user_name} is not banned in this federation!",
                )
            else:
                teks = "{} banned in this federation because:\n`{}`\n*Banned at:* `{}`".format(
                    user_name, reason, fbantime,
                )
                await send_message(update.effective_message, teks, parse_mode="markdown")
            return
        user_name, fbanlist = sql.get_user_fbanlist(str(user_id))
        if user_name == "":
            try:
                get_userid = await bot.get_chat(user_id)
                user_name = get_userid.first_name
            except BadRequest:
                user_name = "He/she"
            if not user_name or user_name is None:
                user_name = "He/she"
        if len(fbanlist) == 0:
            await send_message(
                update.effective_message,
                "{} is not banned in any federation!".format(user_name),
            )
            return
        else:
            teks = "{} has been banned in this federation:\n".format(user_name)
            for x in fbanlist:
                teks += "- `{}`: {}\n".format(x[0], x[1][:20])
            teks += "\nIf you want to find out more about the reasons for Fedban specifically, use /fbanstat <FedID>"
            await send_message(update.effective_message, teks, parse_mode="markdown")

    elif not msg.reply_to_message and not args:
        user_id = msg.from_user.id
        user_name, fbanlist = sql.get_user_fbanlist(user_id)
        if user_name == "":
            user_name = msg.from_user.first_name
        if len(fbanlist) == 0:
            await send_message(
                update.effective_message,
                "{} is not banned in any federation!".format(user_name),
            )
        else:
            teks = "{} has been banned in this federation:\n".format(user_name)
            for x in fbanlist:
                teks += "- `{}`: {}\n".format(x[0], x[1][:20])
            teks += "\nIf you want to find out more about the reasons for Fedban specifically, use /fbanstat <FedID>"
            await send_message(update.effective_message, teks, parse_mode="markdown")

    else:
        fed_id = args[0]
        fedinfo = sql.get_fed_info(fed_id)
        if not fedinfo:
            await send_message(update.effective_message, "Fed {} not found!".format(fed_id))
            return
        name, reason, fbantime = sql.get_user_fban(fed_id, msg.from_user.id)
        if fbantime:
            fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
        else:
            fbantime = "Unavaiable"
        if not name:
            name = msg.from_user.first_name
        if not reason:
            await send_message(
                update.effective_message,
                "{} is not banned in this federation".format(name),
            )
            return
        await send_message(
            update.effective_message,
            "{} banned in this federation because:\n`{}`\n*Banned at:* `{}`".format(
                name, reason, fbantime,
            ),
            parse_mode="markdown",
        )


async def set_fed_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    if args:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            await send_message(update.effective_message, "This Federation does not exist!")
            return
        isowner = is_user_fed_owner(args[0], user.id)
        if not isowner:
            await send_message(
                update.effective_message,
                "Only federation owner can set federation logs.",
            )
            return
        if setlog := sql.set_fed_log(args[0], chat.id):
            await send_message(
                update.effective_message,
                f'Federation log `{fedinfo["fname"]}` has been set to {chat.title}',
                parse_mode="markdown",
            )
    else:
        await send_message(
            update.effective_message, "You have not provided your federated ID!",
        )


async def unset_fed_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    if args:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            await send_message(update.effective_message, "This Federation does not exist!")
            return
        isowner = is_user_fed_owner(args[0], user.id)
        if not isowner:
            await send_message(
                update.effective_message,
                "Only federation owner can set federation logs.",
            )
            return
        if setlog := sql.set_fed_log(args[0], None):
            await send_message(
                update.effective_message,
                f'Federation log `{fedinfo["fname"]}` has been revoked on {chat.title}',
                parse_mode="markdown",
            )
    else:
        await send_message(
            update.effective_message, "You have not provided your federated ID!",
        )


async def subs_feds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        await send_message(update.effective_message, "This group is not in any federation!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        await send_message(update.effective_message, "Only fed owner can do this!")
        return

    if args:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            await send_message(
                update.effective_message, "Please enter a valid federation id.",
            )
            return
        if subfed := sql.subs_fed(args[0], fed_id):
            await send_message(
                update.effective_message,
                f'Federation `{fedinfo["fname"]}` has subscribe the federation `{getfed["fname"]}`. Every time there is a Fedban from that federation, this federation will also banned that user.',
                parse_mode="markdown",
            )
            if get_fedlog := sql.get_fed_log(args[0]):
                if int(get_fedlog) != int(chat.id):
                    await bot.send_message(
                        get_fedlog,
                        f'Federation `{fedinfo["fname"]}` has subscribe the federation `{getfed["fname"]}`',
                        parse_mode="markdown",
                    )
        else:
            await send_message(
                update.effective_message,
                f'Federation `{fedinfo["fname"]}` already subscribe the federation `{getfed["fname"]}`.',
                parse_mode="markdown",
            )
    else:
        await send_message(
            update.effective_message, "You have not provided your federated ID!",
        )


async def unsubs_feds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        await send_message(update.effective_message, "This group is not in any federation!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        await send_message(update.effective_message, "Only fed owner can do this!")
        return

    if args:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            await send_message(
                update.effective_message, "Please enter a valid federation id.",
            )
            return
        if subfed := sql.unsubs_fed(args[0], fed_id):
            await send_message(
                update.effective_message,
                f'Federation `{fedinfo["fname"]}` now unsubscribe fed `{getfed["fname"]}`.',
                parse_mode="markdown",
            )
            if get_fedlog := sql.get_fed_log(args[0]):
                if int(get_fedlog) != int(chat.id):
                    await bot.send_message(
                        get_fedlog,
                        f'Federation `{fedinfo["fname"]}` has unsubscribe fed `{getfed["fname"]}`.',
                        parse_mode="markdown",
                    )
        else:
            await send_message(
                update.effective_message,
                f'Federation `{fedinfo["fname"]}` is not subscribing `{getfed["fname"]}`.',
                parse_mode="markdown",
            )
    else:
        await send_message(
            update.effective_message, "You have not provided your federated ID!",
        )


async def get_myfedsubs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if chat.type == "private":
        await send_message(
            update.effective_message,
            "This command is specific to the group, not to our pm!",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        await send_message(update.effective_message, "This group is not in any federation!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        await send_message(update.effective_message, "Only fed owner can do this!")
        return

    try:
        getmy = sql.get_mysubs(fed_id)
    except Exception:
        getmy = []

    if not getmy:
        await send_message(
            update.effective_message,
            f'Federation `{fedinfo["fname"]}` is not subscribing any federation.',
            parse_mode="markdown",
        )
        return
    else:
        listfed = f'Federation `{fedinfo["fname"]}` is subscribing federation:\n'
        for x in getmy:
            listfed += f"- `{x}`\n"
        listfed += (
            "\nTo get fed info `/fedinfo <fedid>`. To unsubscribe `/unsubfed <fedid>`."
        )
        await send_message(update.effective_message, listfed, parse_mode="markdown")


async def get_myfeds_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if fedowner := sql.get_user_owner_fed_full(user.id):
        text = "*You are owner of feds:\n*"
        for f in fedowner:
            text += f'- `{f["fed_id"]}`: *{f["fed"]["fname"]}*\n'
    else:
        text = "*You are not have any feds!*"
    await send_message(update.effective_message, text, parse_mode="markdown")


def is_user_fed_admin(fed_id, user_id):
    fed_admins = sql.all_fed_users(fed_id)
    if fed_admins is False:
        return False
    return int(user_id) in fed_admins or int(user_id) == OWNER_ID


def is_user_fed_owner(fed_id, user_id):
    getsql = sql.get_fed_info(fed_id)
    if getsql is False:
        return False
    getfedowner = ast.literal_eval(getsql["fusers"])
    if getfedowner is None or getfedowner is False:
        return False
    getfedowner = getfedowner["owner"]
    return str(user_id) == getfedowner or int(user_id) == OWNER_ID


# There's no handler for this yet, but updating for v12 in case its used
async def welcome_fed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    fed_id = sql.get_fed_id(chat.id)
    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user.id)
    if fban:
        await update.effective_message.reply_text(
            "This user is banned in current federation! I will remove him.",
        )
        await bot.ban_chat_member(chat.id, user.id)
        return True
    else:
        return False


def __stats__():
    all_fbanned = sql.get_all_fban_users_global()
    all_feds = sql.get_all_feds_users_global()
    return f"• {len(all_fbanned)} banned users across {len(all_feds)} Federations"


def __user_info__(user_id, chat_id):
    if fed_id := sql.get_fed_id(chat_id):
        fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)
        info = sql.get_fed_info(fed_id)
        infoname = info["fname"]

        if int(info["owner"]) == user_id:
            text = f"Federation owner of: <b>{infoname}</b>."
        elif is_user_fed_admin(fed_id, user_id):
            text = f"Federation admin of: <b>{infoname}</b>."

        elif fban:
            text = f"Federation banned: <b>Yes</b>\n<b>Reason:</b> {fbanreason}"
        else:
            text = "Federation banned: <b>No</b>"
    else:
        text = ""
    return text


# Temporary data
def put_chat(chat_id, value, chat_data):
    # print(chat_data)
    status = value is not False
    chat_data[chat_id] = {"federation": {"status": status, "value": value}}


def get_chat(chat_id, chat_data):
    # print(chat_data)
    try:
        return chat_data[chat_id]["federation"]
    except KeyError:
        return {"status": False, "value": False}


async def fed_owner_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        """*👑 Fed Owner Only:*
 • `/newfed <fed_name>`*:* Creates a Federation, One allowed per user
 • `/renamefed <fed_id> <new_fed_name>`*:* Renames the fed id to a new name
 • `/delfed <fed_id>`*:* Delete a Federation, and any information related to it. Will not cancel blocked users
 • `/fpromote <user>`*:* Assigns the user as a federation admin. Enables all commands for the user under `Fed Admins`
 • `/fdemote <user>`*:* Drops the User from the admin Federation to a normal User
 • `/subfed <fed_id>`*:* Subscribes to a given fed ID, bans from that subscribed fed will also happen in your fed
 • `/unsubfed <fed_id>`*:* Unsubscribes to a given fed ID
 • `/setfedlog <fed_id>`*:* Sets the group as a fed log report base for the federation
 • `/unsetfedlog <fed_id>`*:* Removed the group as a fed log report base for the federation
 • `/fbroadcast <message>`*:* Broadcasts a messages to all groups that have joined your fed
 • `/fedsubs`*:* Shows the feds your group is subscribed to `(broken rn)`""",
        parse_mode=ParseMode.MARKDOWN,
    )


async def fed_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        """*🔱 Fed Admins:*
 • `/fban <user> <reason>`*:* Fed bans a user
 • `/unfban <user> <reason>`*:* Removes a user from a fed ban
 • `/fedinfo <fed_id>`*:* Information about the specified Federation
 • `/joinfed <fed_id>`*:* Join the current chat to the Federation. Only chat owners can do this. Every chat can only be in one Federation
 • `/leavefed <fed_id>`*:* Leave the Federation given. Only chat owners can do this
 • `/setfrules <rules>`*:* Arrange Federation rules
 • `/fedadmins`*:* Show Federation admin
 • `/fbanlist`*:* Displays all users who are victimized at the Federation at this time
 • `/fedchats`*:* Get all the chats that are connected in the Federation
 • `/chatfed `*:* See the Federation in the current chat\n""",
        parse_mode=ParseMode.MARKDOWN,
    )


async def fed_user_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        """*🎩 Any user:*
 • `/fbanstat`*:* Shows if you/or the user you are replying to or their username is fbanned somewhere or not
 • `/fednotif <on/off>`*:* Federation settings not in PM when there are users who are fbaned/unfbanned
 • `/frules`*:* See Federation regulations\n""",
        parse_mode=ParseMode.MARKDOWN,
    )


__mod_name__ = "Federations"

__help__ = """
Everything is fun, until a spammer starts entering your group, and you have to block it. Then you need to start banning more, and more, and it hurts.
But then you have many groups, and you don't want this spammer to be in one of your groups - how can you deal? Do you have to manually block it, in all your groups?\n
*No longer!* With Federation, you can make a ban in one chat overlap with all other chats.\n
You can even designate federation admins, so your trusted admin can ban all the spammers from chats you want to protect.\n

*Commands:*\n
Feds are now divided into 3 sections for your ease.
• `/fedownerhelp`*:* Provides help for fed creation and owner only commands
• `/fedadminhelp`*:* Provides help for fed administration commands
• `/feduserhelp`*:* Provides help for commands anyone can use

"""

NEW_FED_HANDLER = CommandHandler("newfed", new_fed, block=False)
DEL_FED_HANDLER = CommandHandler("delfed", del_fed, block=False)
RENAME_FED = CommandHandler("renamefed", rename_fed, block=False)
JOIN_FED_HANDLER = CommandHandler("joinfed", join_fed, block=False)
LEAVE_FED_HANDLER = CommandHandler("leavefed", leave_fed, block=False)
PROMOTE_FED_HANDLER = CommandHandler("fpromote", user_join_fed, block=False)
DEMOTE_FED_HANDLER = CommandHandler("fdemote", user_demote_fed, block=False)
INFO_FED_HANDLER = CommandHandler("fedinfo", fed_info, block=False)
BAN_FED_HANDLER = DisableAbleCommandHandler("fban", fed_ban, block=False)
UN_BAN_FED_HANDLER = CommandHandler("unfban", unfban, block=False)
FED_BROADCAST_HANDLER = CommandHandler("fbroadcast", fed_broadcast, block=False)
FED_SET_RULES_HANDLER = CommandHandler("setfrules", set_frules, block=False)
FED_GET_RULES_HANDLER = CommandHandler("frules", get_frules, block=False)
FED_CHAT_HANDLER = CommandHandler("chatfed", fed_chat, block=False)
FED_ADMIN_HANDLER = CommandHandler("fedadmins", fed_admin, block=False)
FED_USERBAN_HANDLER = CommandHandler("fbanlist", fed_ban_list, block=False)
FED_NOTIF_HANDLER = CommandHandler("fednotif", fed_notif, block=False)
FED_CHATLIST_HANDLER = CommandHandler("fedchats", fed_chats, block=False)
FED_IMPORTBAN_HANDLER = CommandHandler("importfbans", fed_import_bans, block=False)
FEDSTAT_USER = DisableAbleCommandHandler(["fedstat", "fbanstat"], fed_stat_user, block=False)
SET_FED_LOG = CommandHandler("setfedlog", set_fed_log, block=False)
UNSET_FED_LOG = CommandHandler("unsetfedlog", unset_fed_log, block=False)
SUBS_FED = CommandHandler("subfed", subs_feds, block=False)
UNSUBS_FED = CommandHandler("unsubfed", unsubs_feds, block=False)
MY_SUB_FED = CommandHandler("fedsubs", get_myfedsubs, block=False)
MY_FEDS_LIST = CommandHandler("myfeds", get_myfeds_list, block=False)
DELETEBTN_FED_HANDLER = CallbackQueryHandler(del_fed_button, pattern=r"rmfed_", block=False)
FED_OWNER_HELP_HANDLER = CommandHandler("fedownerhelp", fed_owner_help, block=False)
FED_ADMIN_HELP_HANDLER = CommandHandler("fedadminhelp", fed_admin_help, block=False)
FED_USER_HELP_HANDLER = CommandHandler("feduserhelp", fed_user_help, block=False)

application.add_handler(NEW_FED_HANDLER)
application.add_handler(DEL_FED_HANDLER)
application.add_handler(RENAME_FED)
application.add_handler(JOIN_FED_HANDLER)
application.add_handler(LEAVE_FED_HANDLER)
application.add_handler(PROMOTE_FED_HANDLER)
application.add_handler(DEMOTE_FED_HANDLER)
application.add_handler(INFO_FED_HANDLER)
application.add_handler(BAN_FED_HANDLER)
application.add_handler(UN_BAN_FED_HANDLER)
application.add_handler(FED_BROADCAST_HANDLER)
application.add_handler(FED_SET_RULES_HANDLER)
application.add_handler(FED_GET_RULES_HANDLER)
application.add_handler(FED_CHAT_HANDLER)
application.add_handler(FED_ADMIN_HANDLER)
application.add_handler(FED_USERBAN_HANDLER)
application.add_handler(FED_NOTIF_HANDLER)
application.add_handler(FED_CHATLIST_HANDLER)
# application.add_handler(FED_IMPORTBAN_HANDLER)
application.add_handler(FEDSTAT_USER)
application.add_handler(SET_FED_LOG)
application.add_handler(UNSET_FED_LOG)
application.add_handler(SUBS_FED)
application.add_handler(UNSUBS_FED)
application.add_handler(MY_SUB_FED)
application.add_handler(MY_FEDS_LIST)
application.add_handler(DELETEBTN_FED_HANDLER)
application.add_handler(FED_OWNER_HELP_HANDLER)
application.add_handler(FED_ADMIN_HELP_HANDLER)
application.add_handler(FED_USER_HELP_HANDLER)
