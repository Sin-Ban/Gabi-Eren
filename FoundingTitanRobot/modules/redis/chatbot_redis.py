from FoundingTitanRobot import REDIS 

try:
    eval(REDIS.get("ChatBotChats"))
except BaseException:
    REDIS.set("ChatBotChats", "[]")

def is_chatbot(chat_id):
    list = eval(REDIS.get("ChatBotChats"))
    return chat_id in list
	   
def set_chatbot(chat_id):
    list = eval(REDIS.get("ChatBotChats"))
    if chat_id not in list:
    	list.append(chat_id)
    	REDIS.set("ChatBotChats", str(list))
    return 
	
def rem_chatbot(chat_id):
	list = eval(REDIS.get("ChatBotChats"))
	if chat_id in list:
		list.remove(chat_id)
		REDIS.set("ChatBotChats", str(list))
	return 
 
def list_chatbots():
    return eval(REDIS.get("ChatBotChats"))       
