import dataclasses
import datetime

import generators
import helpers

import pymongo
import telebot.types

import messages as msgs
import typing
from states import BotStates

from base_handler import BaseMessageHandler


class NpcMessageHandler(BaseMessageHandler):
    GENDERS = ['Женский', 'Мужской']
    MAX_NAME_LENGTH = 40

    @staticmethod
    def map_gender(gender_name: str):
        GENDER_BY_ANSWER = {
            'Женский': 'female',
            'Мужской': 'male',
        }
        return GENDER_BY_ANSWER.get(gender_name, 'Женский')

    def last_view_markup(self) -> telebot.types.ReplyKeyboardMarkup:
        saved_npcs = self.mongo.user_npcs.find(
            {'user': self.message.from_user.id},
            projection={'name': True, 'last_viewed': True},
        ).sort('last_viewed', pymongo.DESCENDING).limit(5)
        return helpers.make_aligned_markup(
            [npc['name'] for npc in saved_npcs] + ['Назад'], 2,
        )

    def make_npc_description(
            self, npc: dict, note: typing.Optional[dict] = None, remind_new_notice: bool = True):
        result = f"{npc['name']}\n{npc['race']}, {npc['age']} {helpers.inflect_years(npc['age'])}"
        appearance = npc.get('appearance')
        features = npc.get('features')
        if appearance:
            result += '\n' + appearance
        if features:
            result += '\n' + features
        if note:
            result += '\n' + self.make_note_description(note)
        elif remind_new_notice:
            result += '\n' + msgs.REMIND_NEW_NOTICE
        return result

    def switch_to_npc_view(self, npc: dict, update_last_viewed: bool = False) -> telebot.types.Message:
        if update_last_viewed:
            self.mongo.user_npcs.update_one({'_id': npc['_id']}, {'$set': {'last_viewed': datetime.datetime.utcnow()}})
        last_notes = list(self.mongo.user_npc_notes.find(
            {'npc_id': npc['_id']}
        ).sort('created', pymongo.DESCENDING).limit(1))
        last_note = last_notes[0] if last_notes else None
        note_id = last_note['_id'] if last_note else ''
        self.set_user_cache(f'{npc["_id"]};{note_id}')
        return self.switch_to_state(BotStates.npc_view, self.make_npc_description(npc, last_note))

    def switch_to_npc_edit(self, npc: dict) -> telebot.types.Message:
        self.set_user_cache(npc['_id'])
        return self.switch_to_state(BotStates.npc_edit, self.make_npc_description(npc, remind_new_notice=False))

    def switch_to_interaction_edit(self) -> telebot.types.Message:
        npc_id = self.get_user_cache()
        npc = self.mongo.user_npcs.find_one({'_id': npc_id}, {'interaction_features': 1, 'manners': 1})
        interaction_features = npc.get('interaction_features')
        manners = npc.get('manners')
        result_message = 'Здесь можно отредактировать взаимодействие с NPC, которое учитывается при общении с вашим персонажем.'
        if interaction_features:
            result_message += '\nОсобенности взаимодействия: ' + interaction_features
        if manners:
            result_message += '\nМанеры: ' + manners
        return self.switch_to_state(BotStates.npc_edit_interaction, result_message)

    @staticmethod
    def make_note_description(note: dict) -> str:
        created = note['created'].strftime('%d.%m.%Y')
        return f'Заметка {created}\n{note["text"]}'

    def update_field_and_return(
            self, field: str, value, npc_id=None,
    ) -> telebot.types.Message:
        if not npc_id:
            npc_id = self.get_user_cache()
        updated_npc = self.mongo.user_npcs.find_one_and_update(
            {'_id': npc_id},
            {'$set': {field: value}},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        return self.switch_to_state(
            BotStates.npc_edit,
            self.make_npc_description(updated_npc, remind_new_notice=False),
        )

    def make_names_options(self, race: str, gender: str, age: int, count: int):
        if race not in generators.RACES:
            return []
        if age == self.gm.race_age_levels(race)[0]:
            gender = 'child'
        options = []
        while len(options) < count:
            name = self.gm.sample_name(race, gender).name
            if len(name) > self.MAX_NAME_LENGTH:
                continue
            options.append(name)
        return options

    GENDER_MAP = {
        'Мужчина': 'male',
        'Женщина': 'female',
        'Ребёнок': 'child',
    }

    def generate_name(self, race: str, gender: str) -> generators.Person:
        if gender not in self.GENDER_MAP.keys():
            person = self.gm.sample_name(race=race)
        else:
            person = self.gm.sample_name(race=race, gender=self.GENDER_MAP[gender])
        self.save_person(person)
        self.set_user_cache(';'.join([race, gender]))
        return person

    def generate_appearance(self, race: str, gender: str, age: int, name: str):
        INSTRUCTIONS = """Сгенерируй описание внешности персонажа для фэнтези мира так, 
            чтобы оно соответствовало расе, полу, возрасту и имени, которые заданы в тексте.
            В ответе должно быть не более трех предложений и не более 200 символов."""
        TEMPLATE = """Раса: {},
            Пол: {},
            Возраст: {} лет,
            Имя: {}.
            """
        gender = generators.SEX_TO_SEX_NAME[gender]
        return self.gm.gpt.generate(
            INSTRUCTIONS,
            TEMPLATE.format(race, gender, age, name),
            self.account(),
        )

    def generate_features(self, name: str, gender: str):
        INSTRUCTIONS = """Сгенерируй информацию о персонаже из фэнтези мира так, 
            чтобы оно соответствовало его имени.
            Нужно сгенерировать род деятельности, место работы, сильные и слабые стороны персонажа, идеал персонажа, его дарование: какое качество делает его уникальным
            В ответе должно быть не более трех предложений и не более 200 символов."""
        TEMPLATE = 'Имя: {}.\nПол: {}'
        gender = generators.SEX_TO_SEX_NAME[gender]
        return self.gm.gpt.generate(
            INSTRUCTIONS,
            TEMPLATE.format(name, gender),
            self.account(),
        )

    def save_person(self, person: generators.Person):
        self.set_user_cache_v2(dataclasses.asdict(person))

    def load_person(self) -> generators.Person:
        person_doc: dict = self.get_user_cache_v2()
        return generators.Person(**person_doc)
