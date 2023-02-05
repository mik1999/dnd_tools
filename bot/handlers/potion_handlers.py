import copy
import re

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
        ['Мои зелья', 'Готовить', 'Примеры зелий'],
        ['Что это такое?', 'Назад'],
        ['Вывести список ингридиентов'],
    ]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text == 'Вывести список ингридиентов':
            return self.try_again(self.cm.components_list(show_params=True))
        if message.text == 'Примеры зелий':
            self.set_user_cache('0')
            return self.switch_to_state(BotStates.potions_common_potions_list)
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
    DEFAULT_MESSAGE = 'Введите название для нового зелья'
    BUTTONS = [['Отмена']]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        search_filter = {'user': message.from_user.id, 'name': '__cache'}
        cache_potion_doc = self.mongo.user_potions.find_one(search_filter)

        if self.message.text == 'Отмена':
            cache_potion = potion.Potion(
                self.cm, self.pm,
            )
            cache_potion.from_dict(cache_potion_doc['potion'])
            return self.switch_to_state(BotStates.potion_show, cache_potion.overall_description())
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

        cache_potion_doc['potion']['__name'] = name
        if not cache_potion_doc or not cache_potion_doc.get('potion'):
            return self.switch_to_state(BotStates.potions_menu, msgs.NOT_FOUND)
        potion_doc = {
            'user': message.from_user.id,
            'name': name,
            'potion': cache_potion_doc['potion'],
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
        ['[admin] Сделать общедоступным', 'Назад'],
    ]
    ADMIN_BUTTONS = ['[admin] Сделать общедоступным']
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
        potion_name = potion_doc['potion']['__name']
        if message.text == '[admin] Сделать общедоступным':
            self.common_potion.add_potion(potion_doc)
            return self.try_again(msgs.SUCCESS)

        cache_potion = potion.Potion(self.cm, self.pm)
        cache_potion.from_dict(potion_doc['potion'])
        if message.text == 'Сэмплировать':
            return self.try_again(cache_potion.overall_description(sample=True))
        if message.text == 'Удалить':
            reply = msgs.POTION_DELETE_CONFIRM.format(potion_name)
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


class CommonPotionsListHandler(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Страница 1.'
    STATE = BotStates.potions_common_potions_list
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.potions_menu},
    }

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        page = int(self.get_user_cache())
        top_buttons = []
        if page > 0:
            top_buttons.append(f'Страница {page}')
        if page + 1 < self.common_potion.pages_count:
            top_buttons.append(f'Страница {page + 2}')
        buttons = []
        if top_buttons:
            buttons.append(top_buttons)
        potions = self.common_potion.get_page(page)
        for i in range(0, len(potions), 2):
            buttons.append(potions[i:i+2])
        buttons.append(['Назад'])
        return buttons

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if self.message.text.startswith('Страница'):
            number = int(re.findall(r'\d+', self.message.text)[0])
            self.set_user_cache(str(number - 1))
            return self.try_again(message=f'Страница {number}.')
        potion = self.common_potion.suggest_potion(self.message.text)
        if potion is None:
            return self.try_again(msgs.NO_SUGGESTIONS)
        self.set_user_cache(potion.name)
        return self.switch_to_state(BotStates.potions_common_potion_show, potion.overall_description())


class CommonPotionShow(BaseMessageHandler):
    STATE = BotStates.potions_common_potion_show
    BUTTONS = [
        ['Сэмплировать', 'Добавить в свои зелья'],
        ['Назад'],
    ]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        potion = self.common_potion.suggest_potion(self.get_user_cache())
        if message.text == 'Сэмплировать':
            return self.try_again(potion.overall_description(sample=True))
        if message.text == 'Добавить в свои зелья':
            try:
                self.mongo.user_potions.insert_one(
                    {'user': self.message.from_user.id, 'potion': potion.to_dict(), 'name': potion.name}
                )
                return self.try_again(msgs.SUCCESS)
            except mongo_errors.DuplicateKeyError:
                return self.try_again(msgs.ALREADY_EXISTS_WITH_SAME_NAME)
        if message.text == 'Назад':
            self.set_user_cache('0')
            return self.switch_to_state(BotStates.potions_common_potions_list)

        return self.try_again(msgs.PARSE_BUTTON_ERROR)
