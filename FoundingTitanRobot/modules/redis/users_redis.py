from FoundingTitanRobot import REDIS


def str_to_list(item):  # converts strings to lists
    return item.split(" ")

def list_to_str(list): # converts lists to strings
    str = "".join(f"{items} " for items in list)
    return str.strip()
    
def is_added(user_id): 
    if not str(user_id).isdigit():
        return False
    users = get_all_users()
    return str(user_id) in users
        
def add_user(user_id):
    users = get_all_users()
    try:
        users.append(user_id)
        REDIS.set("Users", list_to_str(users))
        return True
    except Exception as e:
    	print(f"Error Occurred!: {e}, while adding {user_id} to the Database")
    	return False
    	
def get_all_users():  
    users = REDIS.get("Users")
    return [""] if users is None or users == "" else str_to_list(users)
