from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll

from db import Database
import re

from config import community_token, access_token
from core import VkTools, User, calculate_age

db = Database('vkinder.db')

class Bot():
    def __init__(self, community_token, access_token) -> None:
        self.tools = VkTools(community_token, access_token)
        self.longpoll = VkBotLongPoll(self.tools.api, group_id=220136420)

    def event_handler(self):
        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                command = event.message.text.lower()
                
                words = command.replace(' ', '').split(':')

                if command == 'привет':
                    user_name = self.tools.get_first_name(event.message.from_id)
                    self.tools.write_msg(f"Привет, {user_name}!", event.message.from_id)

                elif command == 'пока':
                    user_name = self.tools.get_first_name(event.message.from_id)
                    self.tools.write_msg(f"Пока, {user_name}!", event.message.from_id)

                elif command == 'начать':
                    user_info = self.tools.get_user_info(event.message.from_id)
                    print(user_info)
                    if not user_info:   
                        self.tools.write_msg("Похоже ваши данные недоступны для нас, вы можете вручную ввести информацию в формате: пол:возраст:город. Пример: мужчина:36:Москва", event.message.from_id)
                        continue

                    missing_info = self.tools.get_missing_info(user_info)
                    if missing_info:
                        self.tools.write_msg(f"Следующие поля отсутствуют в вашей странице: {', '.join(missing_info)}. Вы можете вручную ввести информацию в формате: пол:возраст:город. Пример: мужчина:36:Москва", event.message.from_id)
                        continue

                    user = User(user_info)
                    if not db.add_user(user):
                        self.tools.write_msg("Вы уже зарегистрированы", user.id)

                    else:
                        self.tools.write_msg("Вы зарегистрировались", user.id)
                    
                    self.tools.write_main(user_id = event.message.from_id)
                
                elif command == 'начать поиск':
                    user = User(db.get_user(event.message.from_id))

                    new_offset = self.tools.create_search(user, db)
                    db.set_offset(event.message.from_id, new_offset)

                elif command == 'просмотренные':
                    user = User(db.get_user(event.message.from_id))
                    self.tools.create_viewed(user, db)

                elif command == 'создать таблицы':
                    db.create_tables()

                elif words[0].lower() in ['женщина', 'мужчина'] and re.match("^\d+$", words[1]) is not None and (words[2].isalpha() or "-" in words[2]):
                    user_info = {}

                    user_info['sex'] = 1 if words[0] == "Женщина" else 2
                    user_info['age'] = int(words[1])
                    user_info['city'] = self.tools.get_id_by_city(words[2])
                    user_info['id'] = event.message.from_id

                    user = User(user_info)
                    if not db.add_user(user):
                        self.tools.write_msg("Вы уже зарегистрированы", user.id)

                    else:
                        self.tools.write_msg("Вы зарегистрировались", user.id)

                    self.tools.write_main(user_id = event.message.from_id)
                
                else:
                    self.tools.write_msg(f"начать поиск - получение след 60 людей\n", event.message.from_id)

            elif event.type == VkBotEventType.MESSAGE_EVENT:
                print(event)
                user = User(db.get_user(event.obj.peer_id))
                
                if event.object.payload.get('type') in ["RIGHT", "LEFT"] :
                    number = event.object.payload.get('number')
                    id_received = event.object.payload.get('id_received')
                    leng = event.object.payload.get('leng')
                    self.tools.next_search(user, id_received, number, leng, event.obj.conversation_message_id, db)

                if event.object.payload.get('type') in ["RIGHT_VIEWED", "LEFT_VIEWED"]:
                    number = event.object.payload.get('number')
                    self.tools.next_viewed(user, number, event.obj.conversation_message_id, db)
                    
def main():
    bot = Bot(community_token, access_token)
    bot.event_handler()

if __name__ == '__main__':
    main()
