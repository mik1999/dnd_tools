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

from base_handler import BaseMessageHandler, DocHandler


class PotionsMenuHandler(BaseMessageHandler):
    STATE = BotStates.potions_menu
    STATE_BY_MESSAGE = {
        'Мои зелья': {'state': BotStates.potions_list},
        'Готовить': {'state': BotStates.potions_enter_formula},
        'Что это такое?': {'state': BotStates.potions_cooking_doc},
        'Назад': {'state': BotStates.alchemy},
    }
    DEFAULT_MESSAGE = ('Вода в котле закипает, в воздухе витает запах трав, '
                       'перегонный куб готов к работе, книга рецептов раскрыта. '
                       'Что будем делать?')

    BUTTONS = [
        ['Мои зелья', 'Готовить'],
        ['Что это такое?', 'Назад'],
        ['Вывести список ингридиентов'],
    ]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text == 'Вывести список ингридиентов':
            return self.try_again(self.cm.components_list(show_params=True))
        return self.try_again(msgs.PARSE_BUTTON_ERROR)


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


MAX_NAME_LENGTH = 50
MAX_SAVED_POTIONS = 100


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
            'last_viewed': datetime.datetime.utcnow(),
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
            index = 1
            for user_potion in saved_potions:
                potion_name = user_potion.get('name', 'ошибка')
                if potion_name == '__cache':
                    continue
                bot_message += f'{index}\\)    `{potion_name}`\n'
                index += 1
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
            return self.try_again(msgs.NO_SUGGESTIONS)
        user_potion = potion.Potion(self.cm, self.pm)
        potion_doc = potions[suggestions[0]]
        user_potion.from_dict(potion_doc)
        self.mongo.user_potions.update_one(
            {'user': self.message.from_user.id, 'name': '__cache'},
            {'$set': {'potion': potion_doc}, '$currentDate': {'last_viewed': True}},
        )
        self.mongo.user_potions.update_one(
            {'user': self.message.from_user.id, 'name': potion_doc['__name']},
            {'$currentDate': {'last_viewed': True}},
        )
        return self.switch_to_state(BotStates.potion_show, user_potion.overall_description())


class CookingDocHandler(DocHandler):
    STATE = BotStates.potions_cooking_doc
    DEFAULT_MESSAGE = msgs.MIX_ABOUT
    PARENT_STATE = BotStates.potions_menu


class PotionShowHandler(BaseMessageHandler):
    STATE = BotStates.potion_show
    BUTTONS = [
        ['Сэмплировать', 'Удалить'],
        ['Назад'],
    ]
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.potions_menu},
    }

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        potion_doc = self.mongo.user_potions.find_one(
            {'user': message.from_user.id, 'name': '__cache'},
        )
        if not potion_doc or not potion_doc.get('potion', {}).get('__name'):
            return self.try_again(msgs.NOT_FOUND)
        cache_potion = potion.Potion(self.cm, self.pm)
        cache_potion.from_dict(potion_doc['potion'])
        if message.text == 'Сэмплировать':
            return self.try_again(cache_potion.overall_description(sample=True))
        if message.text == 'Удалить':
            reply = msgs.POTION_DELETE_CONFIRM.format(potion_doc['potion']['__name'])
            return self.switch_to_state(BotStates.potions_delete_confirm, reply)
        return self.try_again(msgs.PARSE_BUTTON_ERROR)


class PotionDeleteHandler(BaseMessageHandler):
    STATE = BotStates.potions_delete_confirm
    BUTTONS = [
        ['Да', 'Нет'],
    ]
    STATE_BY_MESSAGE = {
        'Нет': {'state': BotStates.potions_list},
    }

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text != 'Да':
            return self.try_again(msgs.PARSE_BUTTON_ERROR)
        potion_doc = self.mongo.user_potions.find_one(
            {'user': message.from_user.id, 'name': '__cache'},
        )
        if not potion_doc or not potion_doc.get('potion', {}).get('__name'):
            return self.try_again(msgs.NOT_FOUND)
        result = self.mongo.user_potions.delete_one(
            {'user': message.from_user.id, 'name': potion_doc['potion']['__name']}
        )
        reply = 'Ошибка удаления'
        if result.deleted_count == 1:
            reply = 'Успешно удалено'
        return self.switch_to_state(BotStates.potions_list, reply)
