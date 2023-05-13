from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import vk_api

from datetime import datetime, date

from db import Database

def calculate_age(bday: str) -> int:
    born = datetime.strptime(bday, "%d.%m.%Y").date()
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

class User():
    def __init__(self, user_info) -> None:
        self.sex = user_info['sex']
        self.city = user_info['city']
        try:
            self.age = calculate_age(user_info['bdate'])
        
        except:
            self.age = user_info['age']
        self.id = user_info['id']
        self.offset = user_info['offset']

class VkTools():
    def __init__(self, community_token, access_token) -> None:
        self.api = vk_api.VkApi(token=community_token)
        self.access_api = vk_api.VkApi(token=access_token)

    def get_city_by_id(self, city_id: int) -> str:
        # print(self.access_api.method('database.getCitiesById', {'city_ids': f'{city_id}'}))
        return self.access_api.method('database.getCitiesById', {'city_ids': f'{city_id}'})['title']

    def get_id_by_city(self, city: str) -> int:
        return self.access_api.method('database.getCities', {'country_id': 1, 'q': city.title(), 'need_all': 1})['items'][0]['id']

    def get_first_name(self, user_id):
        info, = self.api.method('users.get',
                                {'user_id': user_id
                                })
        return info['first_name']

    def get_user_info(self, user_id):
        info, = self.api.method('users.get',
                            {'user_id': user_id,
                            'fields': 'bdate,sex,city' 
                            })
        
        try:
            user_info = {'id': user_id, 
                'bdate': info['bdate'],
                'sex': info['sex'],
                'city': info['city']['id'],
                'first_name': info['first_name'],
                'offset': 0}
            
        except KeyError:
            return False
            
        return user_info
    
    def get_search_info(self, user: User):
        user_other = self.access_api.method('users.search',
                                {'count': 10,
                                 'offset': user.offset,
                                 'age_from': user.age - 5,
                                 'age_to': user.age + 5,
                                 'sex': 1 if user.sex == 2 else 2,
                                 'city': int(user.city),
                                 'status': 6,
                                 'is_closed': False,
                                 'fields': 'bdate, city'
                                }
                            )['items']

        return user_other
    
    def get_missing_info(self, user_info: dict):
        missing_info = []

        if user_info['sex'] == 0:
            missing_info.append('пол')
        if user_info['city'] == '':
            missing_info.append('город')

        return missing_info
    
    def get_3_top_photos(self, owner_id):
        photos = self.access_api.method('photos.getAll', {'owner_id': owner_id, 'extended': 1})['items']

        photos.sort(key=lambda x: int(x['likes']['count']) + int(x['reposts']['count']), reverse=True)
        return f'photo{owner_id}_{photos[0]["id"]},photo{owner_id}_{photos[1]["id"]},photo{owner_id}_{photos[2]["id"]}'
   

    def write_msg(self, text, user_id):
        self.api.method('messages.send', {'user_id': user_id, "random_id": 
            get_random_id(), 'message': text})
        
    def write_main(self, user_id):
        settings_start = dict(one_time=False, inline=False)

        keyboard_start = VkKeyboard(**settings_start)
        keyboard_start.add_button(label='Начать поиск')
        keyboard_start.add_line()
        keyboard_start.add_button(label="Просмотренные")

        self.api.method('messages.send', {'user_id': user_id, "random_id": 
            get_random_id(), 'message': "Основное меню", "keyboard": keyboard_start.get_keyboard()})
        
    def create_search(self, user: User, db: Database):
        number = 0

        users = self.get_search_info(user)

        if not users:
            user.offset = 0
            users = self.get_search_info(user)
        
        count = len(users)

        id_received =  get_random_id()
        current_description = ''

        for received_user in users:

            try:
                try:
                    description = f"{received_user['first_name']} {received_user['last_name']}\nВозраст: {calculate_age(received_user['bdate'])} лет\nГород: {received_user['city']['title']}\nСсылка: vk.com/id{received_user['id']}"

                except KeyError:
                    description = f"{received_user['first_name']} {received_user['last_name']}\nВозраст: {calculate_age(received_user['bdate'])} лет\nСсылка: vk.com/id{received_user['id']}"

            except ValueError:
                description = f"{received_user['first_name']} {received_user['last_name']}\nСсылка: vk.com/id{received_user['id']}"
        
            if users.index(received_user) == 0:
                current_description = current_description + description

            db.add_received(received_user['id'], id_received, description)

        current_user = users[number]

        settings_start = dict(one_time=False, inline=True)

        keyboard_search = VkKeyboard(**settings_start)
        keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT", "id_received": id_received, "number": number + 1, 'leng': count})
        
        try:
            self.api.method('messages.send', {'user_id': user.id, "random_id":
            get_random_id(), 'message': description, 'keyboard': keyboard_search.get_keyboard(), 'attachment': self.get_3_top_photos(received_user['id'])})
        
        except (vk_api.exceptions.ApiError, IndexError):
            self.api.method('messages.send', {'user_id': user.id, "random_id":
            get_random_id(), 'message': "Нету изображения\n" + description, 'keyboard': keyboard_search.get_keyboard()})

        db.add_candidate(user.id, current_user['id'], description)
        
        return user.offset + count

    def next_search(self, user, id_received, number, leng, message_id, db):

        settings_start = dict(one_time=False, inline=True)
        keyboard_search = VkKeyboard(**settings_start)

        print(number, leng)

        if number + 1 == leng:
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT", "id_received": id_received, "number": number - 1, 'leng': leng})

        elif number - 1 < 0:
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT", "id_received": id_received, "number": number + 1, 'leng': leng})

        else:
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT", "id_received": id_received, "number": number - 1, 'leng': leng})
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT", "id_received": id_received, "number": number + 1, 'leng': leng})

        received_user = db.get_received_user(number, id_received)

        # self.api.method('messages.edit', {'peer_id': user.id, 'conversation_message_id': message_id,'message': received_user[2], 'keyboard': keyboard_search.get_keyboard(), 'attachment': self.get_3_top_photos(received_user[1])})

        try:
            self.api.method('messages.edit', {'peer_id': user.id, 'conversation_message_id': message_id,'message': received_user[2], 'keyboard': keyboard_search.get_keyboard(), 'attachment': self.get_3_top_photos(received_user[1])})
        
        except (vk_api.exceptions.ApiError, IndexError):
            self.api.method('messages.edit', {'peer_id': user.id, 'conversation_message_id': message_id,'message': "Нету изображения\n" + received_user[2], 'keyboard': keyboard_search.get_keyboard()})

        db.add_candidate(user.id, received_user[1], received_user[2])

    def create_viewed(self, user, db: Database):
        number = 0
        candidates = db.get_candidates(user.id)

        current_candidate = candidates[number]
        description = db.get_description(current_candidate[0])

        settings_start = dict(one_time=False, inline=True)

        keyboard_search = VkKeyboard(**settings_start)
        keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT_VIEWED", "number": number + 1})
        
        try:
            self.api.method('messages.send', {'user_id': user.id, "random_id":
            get_random_id(), 'message': description, 'keyboard': keyboard_search.get_keyboard(), 'attachment': self.get_3_top_photos(current_candidate[0])})
        
        except (vk_api.exceptions.ApiError, IndexError):
            self.api.method('messages.send', {'user_id': user.id, "random_id":
            get_random_id(), 'message': "Нету изображения\n" + description, 'keyboard': keyboard_search.get_keyboard()})

    def next_viewed(self, user: User, number: int, message_id: int, db: Database):
        candidates = db.get_candidates(user.id)
        len_candidates = len(candidates)

        current_candidate = candidates[number]
        description = db.get_description(current_candidate[0])

        settings_start = dict(one_time=False, inline=True)

        keyboard_search = VkKeyboard(**settings_start)

        if number + 1 == len_candidates:
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT_VIEWED", "number": number - 1})

        elif number - 1 < 0:
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT_VIEWED", "number": number + 1})

        else:
            keyboard_search.add_callback_button(label="Назад", payload={"type": "LEFT_VIEWED", "number": number - 1})
            keyboard_search.add_callback_button(label="Вперед", payload={"type": "RIGHT_VIEWED", "number": number + 1})

        try:
            self.api.method('messages.edit', {'peer_id': user.id, 'conversation_message_id': message_id,'message': description, 'keyboard': keyboard_search.get_keyboard(), 'attachment': self.get_3_top_photos(current_candidate[0])})
        
        except (vk_api.exceptions.ApiError, IndexError):
            self.api.method('messages.edit', {'peer_id': user.id, 'conversation_message_id': message_id,'message': "Нету изображения\n" + description, 'keyboard': keyboard_search.get_keyboard()})
