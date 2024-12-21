from FoundingTitanRobot import REDIS

def get_user_info(user_id):
    return info if (info := REDIS.get(f"info_of_{user_id}")) else None

def set_user_info(user_id, info):
    REDIS.set(f"info_of_{user_id}", str(info))

def get_user_bio(user_id):
    return bio if (bio := REDIS.get(f"bio_of_{user_id}")) else None

def set_user_bio(user_id, bio):
    REDIS.set(f"bio_of_{user_id}", str(bio))
