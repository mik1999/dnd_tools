import copy

import telebot.types

import messages as msgs
import typing
from states import BotStates

from base_handler import BaseMessageHandler


class GeneratorsHandler(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Что нужно сгенерировать?'
    STATE = BotStates.generators_menu
    STATE_BY_MESSAGE = {
        'Имя': {'state': BotStates.names_generator},
        'Назад': {'state': BotStates.main},
    }

    BUTTONS = [['Волна дикой магии', 'Имя'], ['Таверна', 'Назад']]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if message.text == 'Таверна':
            return self.try_again(self.gm.gen_tavern())
        if message.text == 'Волна дикой магии':
            return self.try_again(self.gm.sample_wild_magic())
        return self.try_again(msgs.PARSE_BUTTON_ERROR)


class NamesGeneratorHandler(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Выберите расу'
    STATE = BotStates.names_generator

    BUTTONS = [
        ['Случайная раса', 'Человек'],
        ['Дварф', 'Полурослик', 'Эльф'],
        ['Гном', 'Полуорк', 'Полуэльф'],
        ['Драконорождённый', 'Сатир', 'Тифлинг'],
    ]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if message.text == 'Случайная раса':
            return self.switch_to_state(BotStates.generators_menu, self.gm.sample_name())
        race = message.text
        if race not in self.gm.RACES:
            return self.try_again(msgs.PARSE_BUTTON_ERROR)
        self.set_user_cache(message.text)
        return self.switch_to_state(BotStates.names_generator_sex_choice)


class SexGeneratorHandler(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Кто это будет?'
    STATE = BotStates.names_generator_sex_choice

    BUTTONS = [['Мужчина', 'Женщина'], ['Ребёнок', 'Случайно']]
    SEX_MAP = {
        'Мужчина': 'male',
        'Женщина': 'female',
        'Ребёнок': 'child',
    }

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        race = self.get_user_cache()
        if message.text == 'Случайно':
            return self.switch_to_state(BotStates.generators_menu, self.gm.sample_name(race=race))
        if message.text not in self.SEX_MAP.keys():
            return self.try_again(msgs.PARSE_BUTTON_ERROR)
        sex = self.SEX_MAP[message.text]
        return self.switch_to_state(BotStates.generators_menu, self.gm.sample_name(race=race, sex=sex))
