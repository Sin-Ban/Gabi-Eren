import threading

from FoundingTitanRobot.modules.sql import BASE, SESSION
from sqlalchemy import Column, BigInteger, UnicodeText


class BlacklistUsers(BASE):
    __tablename__ = "blacklistusers"
    user_id = Column(BigInteger, primary_key=True)
    reason = Column(UnicodeText)

    def __init__(self, user_id, reason=None):
        self.user_id = user_id
        self.reason = reason


BlacklistUsers.__table__.create(checkfirst=True)

BLACKLIST_LOCK = threading.RLock()
BLACKLIST_USERS = set()


def blacklist_user(user_id, reason=None):
    with BLACKLIST_LOCK:
        user = SESSION.query(BlacklistUsers).get(str(user_id))
        if not user:
            user = BlacklistUsers(str(user_id), reason)
        else:
            user.reason = reason

        SESSION.add(user)
        SESSION.commit()
        __load_blacklist_userid_list()


def unblacklist_user(user_id):
    with BLACKLIST_LOCK:
        if user := SESSION.query(BlacklistUsers).get(str(user_id)):
            SESSION.delete(user)

        SESSION.commit()
        __load_blacklist_userid_list()


def get_reason(user_id):
    if user := SESSION.query(BlacklistUsers).get(str(user_id)):
        rep = user.reason
    else:
        rep = ""
    SESSION.close()
    return rep


def is_user_blacklisted(user_id):
    return user_id in BLACKLIST_USERS


def __load_blacklist_userid_list():
    global BLACKLIST_USERS
    try:
        BLACKLIST_USERS = {int(x.user_id) for x in SESSION.query(BlacklistUsers).all()}
    finally:
        SESSION.close()


__load_blacklist_userid_list()
