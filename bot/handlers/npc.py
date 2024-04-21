import copy
import datetime
import random
import uuid

import generators
import resources_manager
import helpers

import pymongo
import pymongo.errors as mongo_errors
import telebot.types

import messages as msgs
import typing
from states import BotStates

from base_handler import BaseMessageHandler
from utils import consts
import yandex_gpt
from npc_utils import NpcMessageHandler


MAX_USER_NPCS = 100
MAX_USER_NPC_NOTES = 500

INTERACTION_FEATURES = [
        'Спорит',
        'Честен',
        'Высокомерен',
        'Вспыльчив',
        'Хвастается',
        'Раздражителен',
        'Груб',
        'Нудный',
        'Любознателен',
        'Тихий',
        'Дружелюбен',
        'Подозрителен',
    ]
MANNERS = [
        'Склонен тихо петь',
        'Что-то насвистывает',
        'Мычит',
        'Говорит рифмами',
        'Причудливо разговариает',
        'Тихий голос',
        'Громкий голос',
        'Проглатывает слова',
        'Шепелявит',
        'Заикается',
        'Чрезвычайно чётко проговаривает слова',
        'Говорит очень громко',
        'Шепчет',
        'Использует помпезную речь',
        'Использует длинные слова',
        'Часто использует неправильные слова',
        'Часто клянётся',
        'Произносит пафосные фразы',
        'Постоянно шутит или каламбурит',
        'Часто предрекает неудачи',
        'Нервно дёргается',
        'Косоглазие',
        'Глядит вдаль',
        'Что-то жуёт',
        'Ходит из угла в угол',
        'Барабанит пальцами',
        'Кусает ногти',
        'Накручивает на палец волосы',
        'Дёргает бороду',
    ]


def make_initial_chat_message(npc: dict):
    if npc.get('interaction_features'):
        interaction_features = npc['interaction_features']
    else:
        interaction_features = generators.sample(INTERACTION_FEATURES)
    if npc.get('manners'):
        manners = npc['manners']
    else:
        manners = generators.sample(MANNERS)
    return f"""Мы находимся в фэнтези-мире Dungeon&Dragons. Ассистент, ты - {npc['race']} по имени {npc['name']}, 
    тебе {npc['age']} лет. Про твою внешноть можно сказать следующее: {npc.get('appearance', '(не задано)')}, 
    а твои особенности: {npc.get('features', '(не задано)')},
    Особенности общения с тобой: {interaction_features},
    Твои манеры: {manners}
    """


class NpcStartMenuHandler(NpcMessageHandler):
    DEFAULT_MESSAGE = 'Создание NPC и учёт истории'
    STATE = BotStates.npc_start_menu
    STATE_BY_MESSAGE = {
        'Создать': {'state': BotStates.npc_create_race},
        'Назад': {'state': BotStates.main},
    }

    BUTTONS = [['Создать'], ['Ваши NPC', 'Назад']]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text == 'Ваши NPC':
            return self.switch_to_state(
                BotStates.npc_search, msgs.NPC_SEARCH_DESCRIPTION, self.last_view_markup(), parse_mode='MarkdownV2',
            )
        return self.try_again(msgs.PARSE_BUTTON_ERROR)


class NpcCreateRace(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Раса?'
    STATE = BotStates.npc_create_race
    STATE_BY_MESSAGE = {}

    BUTTONS = consts.races_buttons()

    validation = BaseMessageHandler.MessageValidation(
        prohibited_symbols={';', '<'},
        max_length=20,
    )

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if message.text == consts.RANDOM_RACE:
            race = generators.sample(generators.RACES)
            self.send_message(msgs.RACE_CHOOSED.format(race))
        else:
            race = message.text
        self.set_user_cache(race)  # save race
        return self.switch_to_state(BotStates.npc_create_gender)


class NpcCreateGender(NpcMessageHandler):
    DEFAULT_MESSAGE = 'Пол?'
    STATE = BotStates.npc_create_gender
    STATE_BY_MESSAGE = {}

    BUTTONS = [NpcMessageHandler.GENDERS]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if message.text not in self.GENDERS:
            return self.try_again(msgs.PARSE_BUTTON_ERROR)
        race = self.get_user_cache()
        gender = self.map_gender(message.text)
        self.set_user_cache(';'.join([race, gender]))  # save gender
        return self.switch_to_state(BotStates.npc_create_age)


class NpcCreateAge(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Возраст?'
    STATE = BotStates.npc_create_age
    STATE_BY_MESSAGE = {}

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        race = self.get_user_cache().split(';')[0]
        ages_list = self.gm.race_age_levels(race)
        ages_list = list(map(str, ages_list))
        return [ages_list[:3], ages_list[3:]]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if not self.message.text.isdigit():
            return self.try_again(msgs.MUST_BY_COMPOSED_BY_DIGITS)
        previous_cache = self.get_user_cache()
        self.set_user_cache(';'.join([previous_cache, message.text]))  # save age
        return self.switch_to_state(BotStates.npc_create_name)


class NpcCreateName(NpcMessageHandler):
    DEFAULT_MESSAGE = 'Имя?'
    STATE = BotStates.npc_create_name
    STATE_BY_MESSAGE = {}

    validation = BaseMessageHandler.MessageValidation(
        max_length=NpcMessageHandler.MAX_NAME_LENGTH,
        prohibited_symbols={';', '<'},
    )

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        race, gender, age = self.get_user_cache().split(';')
        options = self.make_names_options(race, gender, age, 6)
        return [options[:2], options[2:4], options[4:]]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        race, gender, age = self.get_user_cache().split(';')
        age = int(age)
        name = self.message.text
        user_npcs_count = self.mongo.user_npcs.count_documents({'user': self.message.from_user.id})
        if user_npcs_count >= MAX_USER_NPCS:
            return self.switch_to_state(
                BotStates.npc_start_menu, msgs.TOO_MUCH_NPCS.format(MAX_USER_NPCS),
            )
        npc_doc = {
            '_id': uuid.uuid4().hex,
            'user': self.message.from_user.id,
            'last_viewed': datetime.datetime.utcnow(),
            'race': race,
            'gender': gender,
            'age': age,
            'name': name,
        }
        try:
            self.mongo.user_npcs.insert_one(
                npc_doc,
            )
        except mongo_errors.DuplicateKeyError:
            return self.try_again(msgs.DUPLICATE_NPC_NAME_ERROR)
        self.send_message('NPC успешно сохранен')
        return self.switch_to_npc_edit(npc_doc)


class NpcSearch(NpcMessageHandler):
    STATE = BotStates.npc_search
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.npc_start_menu},
    }

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        search_query = {'user': message.from_user.id}
        message = message.text
        while message.startswith('#'):
            token_end = message.find(' ')
            if token_end == -1:
                tag = message
                message = ''
            else:
                tag = message[:token_end]
                message = message[token_end + 1:].strip()
            tag = tag.replace('#', '')
            GENDERS_MAP = {
                'Мужчина': 'male',
                'Мужчины': 'male',
                'Мальчик': 'male',
                'Парень': 'male',
                'Женщина': 'female',
                'Женщины': 'female',
                'Девочка': 'female',
                'Девушка': 'female',
            }
            if tag.capitalize() in generators.RACES:
                search_query.update({'race': tag.capitalize()})
            elif tag.capitalize() in GENDERS_MAP.keys():
                search_query.update({'gender': GENDERS_MAP[tag]})
            else:
                search_query.update({'tags': {'$elemMatch': {'$eq': tag}}})
        if message:
            search_query.update({'$text': {'$search': f'{message}'}})
        user_npcs = list(
            self.mongo.user_npcs.find(
                search_query,
            ).sort('last_viewed', pymongo.DESCENDING).limit(5)
        )
        if not user_npcs:
            return self.try_again(msgs.NO_SUGGESTIONS, markup=self.last_view_markup())
        for npc in user_npcs:
            if npc['name'] == message:
                return self.switch_to_npc_view(npc, update_last_viewed=True)
        if len(user_npcs) == 1:
            return self.switch_to_npc_view(user_npcs[0], update_last_viewed=True)
        buttons = [npc['name'] for npc in user_npcs] + ['Назад']
        return self.try_again(
            msgs.SEARCH_RESULT, markup=helpers.make_aligned_markup(buttons, 2),
        )


class NpcView(NpcMessageHandler):
    STATE = BotStates.npc_view
    STATE_BY_MESSAGE = {
        'Удалить заметку': {'state': BotStates.npc_remove_note},
        'Удалить NPC': {'state': BotStates.npc_remove_npc},
        'Назад': {'state': BotStates.npc_start_menu},
    }
    PARSE_MODE = 'HTML'
    PREHISTORY_INSTRUCTION = """Сгенерируй предысторию персонажа из фэнтези мира в dungeon&dragons на основе следующих данных о персонаже.
    В предыстории укажи, где родился персонаж, кто его родители, каким образом получил свои особенности. Должно получиться примерно 500 символов"""
    NEXT_NOTE_INSTRUCTION = """Сгенерируй историю о персонаже из фэнтези мира в dungeon&dragons, которая продолжает предыдущую историю:
    Также нужно принять во внимание данные о персонаже:
    Расскажи историю кратко, примерно на 500 символов"""
    MAX_TITLE_LENGHT = 35

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        first_row = ['Редактировать', 'Поговорить']
        npc_id, note_id = self.get_user_cache().split(';')
        first_note = self.mongo.user_npc_notes.find({'npc_id': npc_id}).sort('created').limit(1)
        if first_note and note_id and note_id != first_note[0]['_id']:
            first_row += ['Следующая заметка']
        second_row = ['Удалить NPC']
        if note_id:
            second_row += ['Удалить заметку']
        second_row += ['Сгенерировать заметку']
        return [
            first_row,
            second_row,
            ['Назад'],
        ]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        npc_id, note_id = self.get_user_cache().split(';')
        if message.text == 'Редактировать':
            self.set_user_cache(npc_id)
            npc = self.mongo.user_npcs.find_one({'_id': npc_id})
            return self.switch_to_npc_edit(npc)
        elif message.text == 'Следующая заметка':
            current_note = self.mongo.user_npc_notes.find_one({'_id': note_id})
            next_note = self.mongo.user_npc_notes.find(
                {'npc_id': npc_id, 'created': {'$lt': current_note['created']}}
            ).sort('created', pymongo.DESCENDING).limit(1)[0]
            self.set_user_cache(f'{npc_id};{next_note["_id"]}')
            return self.try_again(self.make_note_description(next_note))
        elif message.text == 'Поговорить':
            npc = self.mongo.user_npcs.find_one({'_id': npc_id})
            npc_message = {
                'text': make_initial_chat_message(npc),
                'role': yandex_gpt.MessageRole.SYSTEM.value,
            }
            fake_user_message = {
                'text': 'Привет!',
                'role': yandex_gpt.MessageRole.USER.value,
            }
            fake_server_message = {
                'text': f'Привет! Меня зовут {npc["name"]}',
                'role': yandex_gpt.MessageRole.SERVER.value,
            }
            self.mongo.user_info.update_one(
                {'user': message.from_user.id},
                {'$set': {'npc_chat_messages': [npc_message, fake_user_message, fake_server_message]}},
                upsert=True,
            )
            return self.switch_to_state(BotStates.npc_chat)
        elif message.text == 'Сгенерировать заметку':
            npc = self.mongo.user_npcs.find_one({'_id': npc_id})
            npc_description = self.make_npc_description(npc, remind_new_notice=False)
            if note_id:
                title = 'Сгенерированная заметка'
                last_note = self.mongo.user_npc_notes.find(
                    {'npc_id': npc_id}
                ).sort('created', pymongo.DESCENDING).limit(1)[0]
                instruction = self.NEXT_NOTE_INSTRUCTION
                request_text = f'Предыдущая история: {last_note["text"]}\nДанные о персонаже: {npc_description}'
            else:
                title = 'Сгенерированная предыстория'
                instruction = self.PREHISTORY_INSTRUCTION
                request_text = f'Данные о персонаже: {npc_description}'
            try:
                next_note = self.gm.gpt.generate(
                    instruction,
                    request_text,
                    self.account(),
                )
            except resources_manager.LimitIsOver as limit_over:
                if limit_over.period == 'day':
                    return self.try_again(msgs.DAY_LIMIT_IS_OVER)
                return self.try_again(msgs.MONTH_LIMIT_IS_OVER)
            except resources_manager.YandexGPTNetworkError:
                return self.try_again(msgs.YANDEX_GPT_NETWORK_ERROR)
            return self.insert_note(next_note, npc, title)
        if message.photo:
            self.mongo.user_npcs.update_one({'_id': npc_id}, {'$set': {'photo_id': message.photo[-1].file_id}})
            return self.try_again(msgs.NPC_PHOTO_SAVED)
        npc = self.mongo.user_npcs.find_one({'_id': npc_id})
        note = message.text
        title = None
        if 0 < note.find('\n') < self.MAX_TITLE_LENGHT:
            title, note = note.split('\n', 1)
        return self.insert_note(note, npc, title)

    def insert_note(self, text: str, npc: dict, title: typing.Optional[str] = None):
        user_note_count = self.mongo.user_npc_notes.count_documents(
            {'user': self.message.from_user.id},
        )
        if user_note_count >= MAX_USER_NPC_NOTES:
            return self.try_again(msgs.TOO_MUCH_NPC_NOTES.format(MAX_USER_NPC_NOTES))
        new_note = {
            '_id': uuid.uuid4().hex,
            'user': self.message.from_user.id,
            'npc_id': npc['_id'],
            'created': datetime.datetime.utcnow(),
            'text': text,
        }
        if title is not None:
            new_note.update({'title': title})
        self.mongo.user_npc_notes.insert_one(new_note)
        self.set_user_cache(f'{npc["_id"]};{new_note["_id"]}')
        return self.try_again(self.make_npc_description(npc, new_note))


class NpcRemoveNpc(BaseMessageHandler):
    STATE = BotStates.npc_remove_npc
    BUTTONS = [['Да'], ['Нет']]
    DEFAULT_MESSAGE = 'Удалить этого NPC?'

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text == 'Да':
            npc_id, _ = self.get_user_cache().split(';')
            self.mongo.user_npcs.delete_one({'_id': npc_id})
            self.send_message(msgs.DELETED)
            return self.switch_to_state(BotStates.npc_start_menu)
        elif message.text == 'Нет':
            return self.switch_to_state(BotStates.npc_view, msgs.CANCELLED)
        else:
            return self.try_again(msgs.PARSE_BUTTON_ERROR)


class NpcRemoveNpcNote(NpcMessageHandler):
    STATE = BotStates.npc_remove_note
    BUTTONS = [['Да'], ['Нет']]
    DEFAULT_MESSAGE = 'Удалить заметку?'

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text == 'Да':
            npc_id, note_id = self.get_user_cache().split(';')
            self.mongo.user_npc_notes.delete_one({'_id': note_id})
            self.send_message(msgs.DELETED)
            npc = self.mongo.user_npcs.find_one({'_id': npc_id})
            return self.switch_to_npc_view(npc)

        elif message.text == 'Нет':
            return self.switch_to_state(BotStates.npc_view, msgs.CANCELLED)
        else:
            return self.try_again(msgs.PARSE_BUTTON_ERROR)


class NpcEdit(NpcMessageHandler):
    DEFAULT_MESSAGE = 'Какой параметр желаете отредактировать?'
    STATE = BotStates.npc_edit
    PARSE_MODE = 'HTML'
    STATE_BY_MESSAGE = {
        'Внешость': {'state': BotStates.npc_edit_appearance},
        'Раса': {'state': BotStates.npc_edit_race},
        'Пол': {'state': BotStates.npc_edit_gender},
        'Возраст': {'state': BotStates.npc_edit_age},
        'Имя': {'state': BotStates.npc_edit_name},
        'Особенности': {'state': BotStates.npc_edit_features},
    }
    BUTTONS = [
        ['Карточка персонажа', 'К списку NPC'],
        ['Раса', 'Пол', 'Возраст'],
        ['Имя', 'Внешость', 'Теги'],
        ['Особенности', 'Взаимодействие'],
    ]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text == 'К списку NPC':
            return self.switch_to_state(
                BotStates.npc_search, msgs.NPC_SEARCH_DESCRIPTION, self.last_view_markup(), parse_mode='MarkdownV2',
            )
        elif message.text == 'Карточка персонажа':
            npc_id = self.get_user_cache()
            npc = self.mongo.user_npcs.find_one({'_id': npc_id})
            return self.switch_to_npc_view(npc)
        elif message.text == 'Теги':
            npc_id = self.get_user_cache()
            npc = self.mongo.user_npcs.find_one({'_id': npc_id})
            markup = self.make_tags_markup(npc.get('tags', []))
            return self.switch_to_state(BotStates.npc_edit_tags, markup=markup)
        if message.text == 'Взаимодействие':
            return self.switch_to_interaction_edit()
        return self.try_again(msgs.PARSE_BUTTON_ERROR)


class NpcEditAppearance(NpcMessageHandler):
    DEFAULT_MESSAGE = 'Опишите внешность вашего персонажа или сгенерируйте с помощью YandexGPT'
    STATE = BotStates.npc_edit_appearance
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.npc_edit}}
    BUTTONS = [
        ['Сгенерировать', 'Назад'],
    ]
    validation = BaseMessageHandler.MessageValidation(
        prohibited_symbols={'<'},
    )

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        npc_id = self.get_user_cache()
        if message.text == 'Сгенерировать':
            npc = self.mongo.user_npcs.find_one({'_id': npc_id})
            try:
                appearance = self.generate_appearance(npc['race'], npc['gender'], npc['age'], npc['name'])
            except resources_manager.LimitIsOver as limit_over:
                if limit_over.period == 'day':
                    return self.switch_to_state(BotStates.npc_edit, msgs.DAY_LIMIT_IS_OVER)
                return self.switch_to_state(BotStates.npc_edit, msgs.MONTH_LIMIT_IS_OVER)
            except resources_manager.YandexGPTNetworkError:
                return self.try_again(msgs.YANDEX_GPT_NETWORK_ERROR)
        else:
            appearance = message.text
        return self.update_field_and_return('appearance', appearance, npc_id)


class NpcEditRace(NpcMessageHandler):
    DEFAULT_MESSAGE = 'Выберите или введите новую расу'
    STATE = BotStates.npc_edit_race
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.npc_edit}}
    BUTTONS = consts.races_buttons(include_back=True)
    validation = BaseMessageHandler.MessageValidation(
        prohibited_symbols={'<'},
    )

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        return self.update_field_and_return('race', message.text)


class NpcEditGender(NpcMessageHandler):
    DEFAULT_MESSAGE = 'Выберите пол'
    STATE = BotStates.npc_edit_gender
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.npc_edit}}
    BUTTONS = [NpcMessageHandler.GENDERS, ['Назад']]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text not in self.GENDERS:
            return self.try_again(msgs.PARSE_BUTTON_ERROR)
        gender = self.map_gender(message.text)
        return self.update_field_and_return('gender', gender)


class NpcEditAge(NpcMessageHandler):
    DEFAULT_MESSAGE = 'Введите новый возраст'
    STATE = BotStates.npc_edit_age
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.npc_edit}}

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        npc_id = self.get_user_cache()
        npc = self.mongo.user_npcs.find_one({'_id': npc_id})
        ages_list = self.gm.race_age_levels(npc['race'])
        ages_list = list(map(str, ages_list))
        return [ages_list[:3], ages_list[3:], ['Назад']]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if not self.message.text.isdigit():
            return self.try_again(msgs.MUST_BY_COMPOSED_BY_DIGITS)
        return self.update_field_and_return('age', int(message.text))


class NpcEditTags(NpcMessageHandler):
    DEFAULT_MESSAGE = ('Нажмите на кнопку с существующим тегом, чтобы удалить его, или введите новый, чтобы добавить. '
                       'Теги позволяют группировать ваших NPC, например, по кампании, в которых они участвуют. '
                       'Кроме того, вы можете фильтровать по вашим тегам, когда ищите NPC')
    STATE = BotStates.npc_edit_tags
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.npc_edit}}
    validation = BaseMessageHandler.MessageValidation(
        prohibited_symbols={'<'},
    )

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        npc_id = self.get_user_cache()
        npc = self.mongo.user_npcs.find_one({'_id': npc_id}, {'tags': 1})
        npc_tags = npc.get('tags', [])
        tag = message.text.replace('#', '')
        if ' ' in tag:
            return self.try_again('Тег не должен содержать пробелов', markup=self.make_tags_markup(npc_tags))
        if tag in npc_tags:
            reply_message = 'Тег удален'
            npc_tags.remove(tag)
            self.mongo.user_npcs.update_one({'_id': npc_id}, {'$pull': {'tags': tag}})
        else:
            reply_message = 'Тег добавлен'
            npc_tags.append(tag)
            self.mongo.user_npcs.update_one({'_id': npc_id}, {'$push': {'tags': tag}})
        markup = self.make_tags_markup(npc_tags)
        return self.try_again(reply_message, markup=markup)


class NpcEditName(NpcMessageHandler):
    DEFAULT_MESSAGE = 'Каким будет новое имя?'
    STATE = BotStates.npc_edit_name
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.npc_edit}}
    BUTTONS = [NpcMessageHandler.GENDERS, ['Назад']]
    validation = BaseMessageHandler.MessageValidation(
        prohibited_symbols={'<'},
    )

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        npc_id = self.get_user_cache()
        npc = self.mongo.user_npcs.find_one({'_id': npc_id})
        options = self.make_names_options(npc['race'], npc['gender'], npc['age'], 6)
        return [options[:2], options[2:4], options[4:], ['Назад']]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        return self.update_field_and_return('name', message.text)


class NpcEditFeatures(NpcMessageHandler):
    DEFAULT_MESSAGE = msgs.FEATURES_DESCRIPTION
    STATE = BotStates.npc_edit_features
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.npc_edit}}
    BUTTONS = [['Сгенерировать', 'Назад']]
    validation = BaseMessageHandler.MessageValidation(
        prohibited_symbols={'<'},
    )

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        npc_id = self.get_user_cache()
        if message.text == 'Сгенерировать':
            npc = self.mongo.user_npcs.find_one({'_id': npc_id})
            try:
                features = self.generate_features(npc['name'], npc['gender'])
            except resources_manager.LimitIsOver as limit_over:
                if limit_over.period == 'day':
                    return self.switch_to_state(BotStates.npc_edit, msgs.DAY_LIMIT_IS_OVER)
                return self.switch_to_state(BotStates.npc_edit, msgs.MONTH_LIMIT_IS_OVER)
            except resources_manager.YandexGPTNetworkError:
                return self.try_again(msgs.YANDEX_GPT_NETWORK_ERROR)
        else:
            features = message.text
        return self.update_field_and_return('features', features)


class NpcChat(NpcMessageHandler):
    DEFAULT_MESSAGE = 'В этом чате можно общаться с вашим NPC. Ответы генерирует YandexGPT'
    STATE = BotStates.npc_chat
    BUTTONS = [['Прекратить общение']]
    MAX_CHAT_MESSAGE_HISTORY = 50
    INSTRUCTION_TEXT = 'Ассистент, тебя зовут {}. Ты общаешься с Пользователь в фэнтези мире от лица выдуманного персонажа. ' \
                       'Сообщения от Система дают данные о твоем персонаже.' \
                       'Отвечай на вопросы, как будто ты персонаж из фэнтези мира'

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        npc_id, _ = self.get_user_cache().split(';')
        npc = self.mongo.user_npcs.find_one({'_id': npc_id})
        if message.text == 'Прекратить общение':
            self.mongo.user_info.update_one({'user': message.from_user.id}, {'$set': {'npc_chat_messages': []}})
            return self.switch_to_npc_view(npc)
        message_docs = self.mongo.user_info.find_one(
            {'user': message.from_user.id}, {'npc_chat_messages': 1},
        )['npc_chat_messages']
        messages_to_send = [
            yandex_gpt.YandexGPTMessage(
                text=doc['text'],
                role=yandex_gpt.MessageRole(doc['role']),
            )
            for doc in message_docs
        ]
        messages_to_send.append(messages_to_send[0])  # system message
        messages_to_send = messages_to_send[1:]  # remove first message to send
        messages_to_send.append(yandex_gpt.YandexGPTMessage(message.text, yandex_gpt.MessageRole.USER))
        account = self.account()
        try:
            answer_message = self.gm.gpt.chat(self.INSTRUCTION_TEXT.format(npc['name']), messages_to_send, account)
        except resources_manager.YandexGPTNetworkError:
            return self.try_again(msgs.YANDEX_GPT_NETWORK_ERROR)
        except resources_manager.LimitIsOver as limit_over:
            if limit_over.period == 'day':
                return self.switch_to_state(BotStates.npc_start_menu, msgs.DAY_LIMIT_IS_OVER)
            return self.switch_to_state(BotStates.npc_start_menu, msgs.MONTH_LIMIT_IS_OVER)
        message_docs += [
            {
                'text': message.text,
                'role': yandex_gpt.MessageRole.USER.value,
            },
            {
                'text': answer_message.text,
                'role': answer_message.role.value,
            },
        ]
        if len(message_docs) > self.MAX_CHAT_MESSAGE_HISTORY:
            message_docs = message_docs[:1] + message_docs[3:]

        self.mongo.user_info.update_one(
            {'user': message.from_user.id},
            {'$set': {'npc_chat_messages': message_docs}},
        )
        return self.try_again(answer_message.text)


class NpcEditInteraction(NpcMessageHandler):
    STATE = BotStates.npc_edit_interaction
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.npc_edit},
        'Особенности взаимодействия': {'state': BotStates.npc_edit_interaction_features},
        'Манеры': {'state': BotStates.npc_edit_interaction_manners},
    }
    BUTTONS = [['Особенности взаимодействия', 'Манеры'], ['Назад']]


class BaseNpcInteractionEdit(NpcMessageHandler):
    FIELD = None

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message == 'Назад':
            self.send_message(msgs.CANCELLED)
            return self.switch_to_interaction_edit()
        npc_id = self.get_user_cache()
        self.mongo.user_npcs.update_one({'_id': npc_id}, {'$set': {self.FIELD: message.text}})
        return self.switch_to_interaction_edit()


class NpcEditInteractionFeatures(BaseNpcInteractionEdit):
    STATE = BotStates.npc_edit_interaction_features
    FIELD = 'interaction_features'
    DEFAULT_MESSAGE = 'Выберите особенность взаимодействие или напишите сой вариант'

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        suggestions = copy.deepcopy(INTERACTION_FEATURES)
        random.shuffle(suggestions)
        return [suggestions[:3], suggestions[3:6], ['Назад']]


class NpcEditInteractionManners(BaseNpcInteractionEdit):
    STATE = BotStates.npc_edit_interaction_manners
    FIELD = 'manners'
    DEFAULT_MESSAGE = 'Выберите манеру общения NPC или напишите свой вариант'

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        suggestions = copy.deepcopy(MANNERS)
        random.shuffle(suggestions)
        return [suggestions[:2], suggestions[2:4], ['Назад']]
