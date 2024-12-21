from FoundingTitanRobot import REDIS 

def is_nsfw(chat_id: int):
    return bool(chat := REDIS.get(f'nsfw_on_{chat_id}'))


def add_nsfw(chat_id: int):
    REDIS.set(f'nsfw_on_{chat_id}', chat_id)
	

def rem_nsfw(chat_id: int):
    REDIS.delete(f'nsfw_on_{chat_id}')
