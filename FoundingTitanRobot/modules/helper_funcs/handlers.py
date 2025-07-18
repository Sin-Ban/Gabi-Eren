from FoundingTitanRobot import ALLOW_EXCL
from FoundingTitanRobot import ACKERMANS, TITANSHIFTERS, ROYALS, SCOUTS, GARRISONS

from telegram import Update
from telegram.ext import CommandHandler
from telegram.ext import filters as filters_mod
from pyrate_limiter import (
    BucketFullException,
    Duration,
    RequestRate,
    Limiter,
    MemoryListBucket,
)

CMD_STARTERS = ("/", "!") if ALLOW_EXCL else ("/", )


class AntiSpam:
    def __init__(self):
        self.whitelist = (
            (ACKERMANS or [])
            + (TITANSHIFTERS or [])
            + (GARRISONS or [])
            + (ROYALS or [])
            + (SCOUTS or [])
        )
        # Values are HIGHLY experimental, its recommended you pay attention to our commits as we will be adjusting the values over time with what suits best.
        Duration.CUSTOM = 15  # Custom duration, 15 seconds
        self.sec_limit = RequestRate(6, Duration.CUSTOM)  # 6 / Per 15 Seconds
        self.min_limit = RequestRate(20, Duration.MINUTE)  # 20 / Per minute
        self.hour_limit = RequestRate(100, Duration.HOUR)  # 100 / Per hour
        self.daily_limit = RequestRate(1000, Duration.DAY)  # 1000 / Per day
        self.limiter = Limiter(
            self.sec_limit,
            self.min_limit,
            self.hour_limit,
            self.daily_limit,
            bucket_class=MemoryListBucket,
        )

    def check_user(self, user):
        """
        Return True if user is to be ignored else False
        """
        if user in self.whitelist:
            return False
        try:
            self.limiter.try_acquire(user)
            return False
        except BucketFullException:
            return True


SpamChecker = AntiSpam()
MessageHandlerChecker = AntiSpam()



class CustomCommandHandler(CommandHandler):
    def __init__(self, command, callback, **kwargs):
        if "admin_ok" in kwargs:
            del kwargs["admin_ok"]
        super().__init__(command, callback, **kwargs)
        self.filters = filters_mod.BaseFilter = (
             filters_mod.UpdateType.MESSAGES
        )
        
    def check_update(self, update):
        if not isinstance(update, Update) or not update.effective_message:
            return
        message = update.effective_message

        try:
            user_id = update.effective_user.id
        except Exception:
            user_id = None

        if message.text and len(message.text) > 1:
            fst_word = message.text.split(None, 1)[0]
            if len(fst_word) > 1 and any(
                fst_word.startswith(start) for start in CMD_STARTERS
            ):
                args = message.text.split()[1:]
                command = fst_word[1:].split("@")
                command.append(
                    message._bot.username
                )  # in case the command was sent without a username

                if (
                    command[0].lower() not in self.commands
                    or command[1].lower() != message._bot.username.lower()
                ):
                    return None

                if SpamChecker.check_user(user_id):
                    return None

                if filter_result := self.filters.check_update(update):
                    return args, filter_result
                else:
                    return False
                    
