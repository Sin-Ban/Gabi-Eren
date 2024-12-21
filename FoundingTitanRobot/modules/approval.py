import html
from FoundingTitanRobot.modules.disable import DisableAbleCommandHandler
from FoundingTitanRobot import application, TITANSHIFTERS
from FoundingTitanRobot.modules.helper_funcs.extraction import extract_user
from telegram.ext import CallbackContext, CallbackQueryHandler, ContextTypes
import FoundingTitanRobot.modules.redis.approvals_redis as redis
from FoundingTitanRobot.modules.helper_funcs.chat_status import user_admin
from FoundingTitanRobot.modules.log_channel import loggable
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.constants import ParseMode
from telegram.helpers import mention_html
from telegram.error import BadRequest


@loggable
@user_admin
async def approve(update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_title = message.chat.title
    chat = update.effective_chat
    args = context.args
    user = update.effective_user
    user_id = await extract_user(message, args)
    if not user_id:
        await message.reply_text(
            "I don't know who you're talking about, you're going to need to specify a user!"
        )
        return ""

    if chat.type == "private":
        await message.reply_text("This command is not meant to be run in my PM!")
        return "" # TODO: can be approved using connections module
    try:
        member = await chat.get_member(user_id)
    except BadRequest:
        return ""
    if member.status in ["administrator", "owner"]:
        await message.reply_text(
            "No need to approve an Admin!"
        )
        return ""
    if redis.is_approved(message.chat_id, user_id):
        await message.reply_text(
            f"[{member.user['first_name']}](tg://user?id={member.user['id']}) is already approved in {chat_title}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ""
    redis.approve(message.chat_id, user_id)
    await message.reply_text(
        f"[{member.user['first_name']}](tg://user?id={member.user['id']}) has been approved in {chat_title}! They will now be ignored by admin actions like locks, blacklists, warns, bans, mutes, kicks and antiflood",
        parse_mode=ParseMode.MARKDOWN,
    )
    return f"<b>{html.escape(chat.title)}:</b>\n#APPROVED\n<b>Admin:</b> {mention_html(user.id, user.first_name)}\n<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"


@loggable
@user_admin
async def disapprove(update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_title = message.chat.title
    chat = update.effective_chat
    args = context.args
    user = update.effective_user
    user_id = await extract_user(message, args)
    if not user_id:
        await message.reply_text(
            "I don't know who you're talking about, you're going to need to specify a user!"
        )
        return ""
    if chat.type == "private":
        await message.reply_text("This command is not meant to be run in my PM!")
        return ""
    try:
        member = await chat.get_member(user_id)
    except BadRequest:
        return ""
    if member.status in ["administrator", "owner"]:
        await message.reply_text("This user is an admin, they can't be unapproved.")
        return ""
    if not redis.is_approved(message.chat_id, user_id):
        await message.reply_text(f"{member.user['first_name']} isn't approved yet!")
        return ""
    redis.disapprove(message.chat_id, user_id)
    await message.reply_text(
        f"{member.user['first_name']} is no longer approved in {chat_title}."
    )
    return f"<b>{html.escape(chat.title)}:</b>\n#UNAPPROVED\n<b>Admin:</b> {mention_html(user.id, user.first_name)}\n<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"


@user_admin
async def approved(update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_title = message.chat.title
    chat = update.effective_chat
    approved_users = redis.list_approved(message.chat_id)
    if chat.type == "private":
        await message.reply_text("This command is not meant to be run in my PM!")
    if approved_users:
        msg = "The following users are approved.\n"
        for i in approved_users:
            member = await chat.get_member(int(i))
            msg += f"[{member.user['first_name']}](tg://user?id={i})\n"
        await message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text(f"No users are approved in {chat_title}.")
        

async def approval(update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    args = context.args
    user_id = await extract_user(message, args)
    member = await chat.get_member(int(user_id))
    if not user_id:
        await message.reply_text(
            "I don't know who you're talking about, you're going to need to specify a user!"
        )
        return ""
    if chat.type == "private":
        await message.reply_text("This command is not meant to be run in my PM!")
    if redis.is_approved(message.chat_id, user_id):
        await message.reply_text(
            f"{member.user['first_name']} is an approved user. Locks, antiflood, warns, bans, mutes, kicks and blacklists won't apply to them."
        )
    else:
        await message.reply_text(
            f"{member.user['first_name']} is not an approved user. They are affected by normal commands."
        )


async def unapproveall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    member = await chat.get_member(user.id)
    if chat.type == "private":
        await update.effective_message.reply_text("This command is not meant to be run in my PM!")
    if member.status != "owner" and user.id not in TITANSHIFTERS:
        await update.effective_message.reply_text(
            "Only the chat owner can unapprove all users at once."
        )
    else:
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Unapprove all users", callback_data="unapproveall_user"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Cancel", callback_data="unapproveall_cancel"
                    )
                ],
            ]
        )
        await update.effective_message.reply_text(
            f"Are you sure you would like to unapprove ALL users in {chat.title}? This action cannot be undone.",
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN,
        )


async def unapproveall_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat = update.effective_chat
    message = update.effective_message
    member = await chat.get_member(query.from_user.id)
    if query.data == "unapproveall_user":
        if member.status == "owner" or query.from_user.id in TITANSHIFTERS:
            approved_users = redis.list_approved(chat.id)
            users = [int(i) for i in approved_users]
            for user_id in users:
                redis.disapprove(chat.id, user_id)
            await message.edit_text("Successfully Unapproved all user in this Chat.")
            return

        if member.status == "administrator":
            await query.answer("Only owner of the chat can do this.")

        if member.status == "member":
            await query.answer("You need to be admin to do this.")
    elif query.data == "unapproveall_cancel":
        if member.status == "owner" or query.from_user.id in TITANSHIFTERS:
            await message.edit_text("Removing of all approved users has been cancelled.")
            return ""
        if member.status == "administrator":
            await query.answer("Only owner of the chat can do this.")
        if member.status == "member":
            await query.answer("You need to be admin to do this.")


__help__ = """
Sometimes, you might trust an user so much that you want him/her to be an Admin, but for some reasons you can't make him/her an Admin.
Maybe not enough to make them admin, but you might be ok with admin actions like locks, blacklists, warns, bans, mutes, kicks and antiflood not applying to them.
That's what approvals are for -:

*User commands*
- `/approval`*:* Check a user's approval status in this chat.

*Admin commands:*
- `/approve`*:* Approve of a user. Locks, blacklists, warns, bans, mutes, kicks and antiflood won't apply to them anymore.
- `/unapprove`*:* Unapprove of a user. They will now be subject to locks, blacklists, warns, bans, mutes, kicks and antiflood again.
- `/approved`*:* List all approved users.
- `/unapproveall`*:* Unapprove *ALL* users in a chat. This cannot be undone.
"""

APPROVE = DisableAbleCommandHandler("approve", approve, block=False)
DISAPPROVE = DisableAbleCommandHandler(["unapprove", "disapprove"], disapprove, block=False)
APPROVED = DisableAbleCommandHandler("approved", approved, block=False)
APPROVAL = DisableAbleCommandHandler("approval", approval, block=False)
UNAPPROVEALL = DisableAbleCommandHandler("unapproveall", unapproveall, block=False)
UNAPPROVEALL_BTN = CallbackQueryHandler(unapproveall_btn, pattern=r"unapproveall_.*", block=False)

application.add_handler(APPROVE)
application.add_handler(DISAPPROVE)
application.add_handler(APPROVED)
application.add_handler(APPROVAL)
application.add_handler(UNAPPROVEALL)
application.add_handler(UNAPPROVEALL_BTN)

__mod_name__ = "Approvals"
__command_list__ = ["approve", "unapprove", "approved", "approval"]
__handlers__ = [APPROVE, DISAPPROVE, APPROVED, APPROVAL]
