from FoundingTitanRobot import ACKERMANS, TITANSHIFTERS, ROYALS, OWNER_ID
from telegram import Message
from telegram.ext.filters import MessageFilter


class CustomFilters(object):
    class _Owner(MessageFilter):
        def filter(self, message: Message):
            return bool(message.from_user and message.from_user.id == OWNER_ID)
        
    owner_filter = _Owner()
    
    class _Supporters(MessageFilter):
        def filter(self, message: Message):
            return bool(message.from_user and message.from_user.id in ROYALS)

    support_filter = _Supporters()

    class _Sudoers(MessageFilter):
        def filter(self, message: Message):
            return bool(message.from_user and message.from_user.id in TITANSHIFTERS)

    sudo_filter = _Sudoers()

    class _Developers(MessageFilter):
        def filter(self, message: Message):
            return bool(message.from_user and message.from_user.id in ACKERMANS)

    dev_filter = _Developers()

    class _MimeType(MessageFilter):
        def __init__(self, mimetype):
            self.mime_type = mimetype
            self.name = f"Customfilters.Mime_type({self.mime_type})"

        def filter(self, message: Message):
            return bool(
                message.document and message.document.mime_type == self.mime_type,
            )

    mime_type = _MimeType

    class _HasText(MessageFilter):
        def filter(self, message: Message):
            return bool(
                message.text
                or message.sticker
                or message.photo
                or message.document
                or message.video,
            )

    has_text = _HasText()
