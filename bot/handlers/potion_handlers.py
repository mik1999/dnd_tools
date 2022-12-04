import copy

import telebot.types

from alchemy import potion
import datetime
import messages as msgs
import pymongo
import pymongo.errors as mongo_errors
import typing
from states import BotStates
from utils.words_suggester import WordsSuggester

from base_handler import BaseMessageHandler


class PotionsMenuHandler(BaseMessageHandler):
    STATE = BotStates.potions_menu
    STATE_BY_MESSAGE = {
        'Мои зелья': {'state': BotStates.potions_list},
        'Готовить': {'state': BotStates.potions_enter_formula},
        'Что это такое?': {'state': BotStates.dummy},
        'Назад': {'state': BotStates.alchemy},
        'Вывести список ингридиентов': {'state': BotStates.dummy},
    }
    DEFAULT_MESSAGE = ('Вода в котле закипает, в воздухе витает запах трав, '
                       'перегонный куб готов к работе, книга рецептов раскрыта. '
                       'Что будем делать?')

    BUTTONS = [
        ['Мои зелья', 'Готовить'],
        ['Что это такое?', 'Назад'],
        ['Вывести список ингридиентов'],
    ]


class PotionsEnterFormulaHandler(BaseMessageHandler):
    STATE = BotStates.potions_enter_formula
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.potions_menu},
    }

    DEFAULT_MESSAGE = 'Введите формулу, например, зверобой + 2 гифлома'

    BUTTONS = [['Назад']]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        cook_potion = potion.Potion(self.cm, self.pm)
        try:
            cook_potion.mix_from(message.text, use_suggestions=True)
        except potion.ParsingFormulaError as parse_error:
            return self.switch_to_state(BotStates.potions_enter_formula, parse_error.message)

        search_filter = {'user': message.from_user.id, 'name': '__cache'}
        update = {'$set': {'potion': cook_potion.to_dict()}}
        self.mongo.user_potions.update_one(search_filter, update=update, upsert=True)
        return self.switch_to_state(BotStates.potions_cooked, cook_potion.overall_description())


class PotionsCookedHandler(BaseMessageHandler):
    STATE = BotStates.potions_cooked
    STATE_BY_MESSAGE = {
        'Готовить ещё': {'state': BotStates.potions_enter_formula},
        'Сохранить': {'state': BotStates.potions_enter_name},
        'В меню': {'state': BotStates.potions_menu},
    }
    BUTTONS = [['Готовить ещё', 'Сохранить'], ['В меню']]


MAX_NAME_LENGTH = 100
MAX_SAVED_POTIONS = 3


class PotionsEnterNameHandler(BaseMessageHandler):
    STATE = BotStates.potions_enter_name
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.potions_cooked},
    }
    DEFAULT_MESSAGE = 'Введите название для нового зелья'
    BUTTONS = [['Отмена']]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        potions_count = self.mongo.user_potions.count_documents(
            {'user': message.from_user.id},
        )
        # + 1 -- cached potion
        if potions_count >= MAX_SAVED_POTIONS + 1:
            return self.switch_to_state(BotStates.potions_menu, msgs.TOO_MUCH_POTIONS.format(MAX_SAVED_POTIONS))

        name = message.text
        if not name:
            return self.try_again(msgs.EMPTY_TEXT_ERROR)

        if len(name) > MAX_NAME_LENGTH:
            return self.try_again(msgs.TOO_LONG_NAME.format(MAX_NAME_LENGTH))

        search_filter = {'user': message.from_user.id, 'name': '__cache'}
        cache_potion = self.mongo.user_potions.find_one(search_filter)
        cache_potion['potion']['__name'] = name
        if not cache_potion or not cache_potion.get('potion'):
            return self.switch_to_state(BotStates.potions_menu, msgs.NOT_FOUND)
        potion_doc = {
            'user': message.from_user.id,
            'name': name,
            'potion': cache_potion['potion'],
            'last_viewed': datetime.datetime.now().isoformat(),
        }
        try:
            self.mongo.user_potions.insert_one(potion_doc)
        except mongo_errors.DuplicateKeyError:
            return self.try_again(msgs.DUPLICATE_NAME_ERROR)
        return self.switch_to_state(BotStates.potions_menu, msgs.SAVE_SUCCESS)


class PotionsListHandler(BaseMessageHandler):
    STATE = BotStates.potions_list
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.potions_menu},
    }
    DEFAULT_MESSAGE = ('Введите название зелья, по которому я могу '
                       'его искать, или воспользуйтесь предложениями в меню')
    MAX_POTION_BUTTONS = 6

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        """
        append last viewed potions
        """
        saved_potions = self.mongo.user_potions.find(
            {'user': self.message.from_user.id},
            projection={'name': True, 'last_viewed': True},
        ).sort('last_viewed', pymongo.DESCENDING)
        buttons = [['Вывести список', 'Назад']]
        batch = []
        for user_potion in saved_potions:
            potion_name = user_potion.get('name', 'ошибка')
            if potion_name == '__cache':
                continue
            batch.append(potion_name)
            if len(batch) == 2:
                buttons.append(copy.deepcopy(batch))
                batch = []
        if batch:
            buttons.append(copy.deepcopy(batch))
        return buttons

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text == 'Вывести список':
            saved_potions = self.mongo.user_potions.find(
                {'user': self.message.from_user.id},
                projection={'name': True, 'last_viewed': True},
            ).sort('last_viewed', pymongo.DESCENDING)
            bot_message = ''
            for index, user_potion in enumerate(saved_potions):
                potion_name = user_potion.get('name', 'ошибка')
                if potion_name == '__cache':
                    continue
                bot_message += f'{index + 1}\\)    `{potion_name}`\n'
            return self.try_again(bot_message, parse_mode='MarkdownV2')

        saved_potions = self.mongo.user_potions.find(
            {'user': self.message.from_user.id},
        ).sort('last_viewed', pymongo.DESCENDING)
        potions = dict()
        for index, user_potion in enumerate(saved_potions):
            potion_name = user_potion.get('name', 'ошибка')
            if potion_name == '__cache' or user_potion.get('potion') is None:
                continue
            potions.update({potion_name: user_potion['potion']})
        suggester = WordsSuggester(list(potions.keys()))
        suggestions = suggester.suggest(message.text, max_size=1)
        if not suggestions:
            self.try_again(msgs.NO_SUGGESTIONS)
        user_potion = potion.Potion(self.cm, self.pm)
        user_potion.from_dict(potions[suggestions[0]])
        return self.switch_to_state(BotStates.dummy, user_potion.overall_description())
