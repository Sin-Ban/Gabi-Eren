import threading

from FoundingTitanRobot.modules.sql import BASE, SESSION
from sqlalchemy import Column, String, UnicodeText, distinct, func


class Rules(BASE):
    __tablename__ = "rules"
    chat_id = Column(String(14), primary_key=True)
    rules = Column(UnicodeText, default="")

    def __init__(self, chat_id):
        self.chat_id = chat_id

    def __repr__(self):
        return f"<Chat {self.chat_id} rules: {self.rules}>"


Rules.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()


def set_rules(chat_id, rules_text):
    with INSERTION_LOCK:
        rules = SESSION.query(Rules).get(str(chat_id)) or Rules(str(chat_id))
        rules.rules = rules_text

        SESSION.add(rules)
        SESSION.commit()


def get_rules(chat_id):
    ret = rules.rules if (rules := SESSION.query(Rules).get(str(chat_id))) else ""
    SESSION.close()
    return ret


def num_chats():
    try:
        return SESSION.query(func.count(distinct(Rules.chat_id))).scalar()
    finally:
        SESSION.close()


def migrate_chat(old_chat_id, new_chat_id):
    with INSERTION_LOCK:
        if chat := SESSION.query(Rules).get(str(old_chat_id)):
            chat.chat_id = str(new_chat_id)
        SESSION.commit()
