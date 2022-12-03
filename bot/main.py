import telebot.types

from alchemy import components_manager
from alchemy import parameters_manager
from alchemy import potion
import helpers
import logging
import menu
import messages as msgs
import pymongo.errors as mongo_errors
from states import BotStates

from base_handler import BaseMessageHandler
import handlers_controller


logger = logging.getLogger()


class MainStateHandler(BaseMessageHandler):
    STATE = BotStates.main
    STATE_BY_MESSAGE = {
        'Кинуть кости': {'state': BotStates.dices},
        'Алхимия': {'state': BotStates.alchemy},
    }


class DicesStateHandler(BaseMessageHandler):
    STATE = BotStates.dices
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.main}}

    def handle_message(self, message: telebot.types.Message):
        helpers.handle_dices_formula(message, message.text, BotStates.dices, self.bot)


class DummyHandler(BaseMessageHandler):
    STATE = BotStates.dummy
    STATE_BY_MESSAGE = {'В меню': {'state': BotStates.main}}


class AlchemyMenuHandler(BaseMessageHandler):
    STATE = BotStates.alchemy
    STATE_BY_MESSAGE = {
        'Параметры': {
            'state': BotStates.parameters,
            'message': msgs.PARAMETER_CHOICE,
        },
        'Ингредиенты': {'state': BotStates.components_menu},
        'Зелья': {'state': BotStates.potions_menu},
        'Что это такое?': {'state': BotStates.alchemy_doc},
        'Назад': {'state': BotStates.main},
    }


class AlchemyDocHandler(BaseMessageHandler):
    STATE = BotStates.alchemy_doc
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.alchemy},
    }


class ParametersHandler(BaseMessageHandler):
    STATE = BotStates.parameters
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.alchemy},
        'В главное меню': {'state': BotStates.main},
    }

    def handle_message(self, message: telebot.types.Message):
        try:
            text = self.pm.parameter_brief(message.text)
        except parameters_manager.NoSuchParameter:
            text = msgs.NO_SUCH_PARAMETER
        menu.switch_to_state(self.bot, BotStates.parameters, message, text)


class ComponentsMenuHandler(BaseMessageHandler):
    STATE = BotStates.components_menu
    STATE_BY_MESSAGE = {
        'Об ингредиенте': {
            'state': BotStates.components_enter_name,
        },
        'Назад': {'state': BotStates.alchemy},
    }

    def handle_message(self, message: telebot.types.Message):
        if message.text == 'Список ингредиентов':
            response = self.cm.components_list(show_telegram_links=True)
            self.switch_to_state(BotStates.components_enter_name, response)
            return
        self.process_state_by_message(unknown_pass_enabled=False)


class ComponentsEnterHandler(BaseMessageHandler):
    STATE = BotStates.components_enter_name
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.components_menu}}

    def handle_message(self, message: telebot.types.Message):
        if message.text.startswith('/'):
            component_name = message.text[1:].split()[0]
            try:
                bot_message = self.cm.info(component_name, self.pm)
                self.switch_to_state(
                    BotStates.components_component_show, bot_message,
                )
                return
            except components_manager.UnrecognizedComponent:
                self.switch_to_state(
                    BotStates.components_enter_name, msgs.UNRECOGNIZED_COMPONENT,
                )
                return
        try:
            bot_message = self.cm.info(message.text, self.pm)
            self.switch_to_state(
                BotStates.components_component_show, bot_message,
            )
            return
        except components_manager.UnrecognizedComponent:
            self.bot.set_state(
                message.from_user.id,
                BotStates.components_enter_name,
                message.chat.id,
            )
            suggestions = self.cm.suggest_components(message.text)
            markup = telebot.types.ReplyKeyboardMarkup(
                resize_keyboard=True, row_width=6,
            )
            if not suggestions:
                markup.add('Назад')
                self.bot.send_message(
                    message.chat.id,
                    msgs.COMPONENT_NO_SUGGESTIONS,
                    reply_markup=markup,
                )
                return

            buttons = suggestions + ['Назад']
            for i in range(len(buttons) // 2):
                markup.add(buttons[2 * i], buttons[2 * i + 1])
            if len(buttons) % 2 == 1:
                markup.add(buttons[-1])
            self.bot.send_message(
                message.chat.id,
                msgs.COMPONENTS_SUGGESTIONS_FOUND,
                reply_markup=markup,
            )


class ComponentShowHandler(BaseMessageHandler):
    STATE = BotStates.components_component_show
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.components_menu},
    }


class PotionsMenuHandler(BaseMessageHandler):
    STATE = BotStates.potions_menu
    STATE_BY_MESSAGE = {

        'Мои зелья': {'state': BotStates.dummy},
        'Готовить': {'state': BotStates.potions_enter_formula},
        'Что это такое?': {'state': BotStates.dummy},
        'Назад': {'state': BotStates.alchemy},
        'Вывести список ингридиентов': {'state': BotStates.dummy},
    }


class PotionsEnterFormulaHandler(BaseMessageHandler):
    STATE = BotStates.potions_enter_formula
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.potions_menu},
    }

    def handle_message(self, message: telebot.types.Message):
        cook_potion = potion.Potion(self.cm, self.pm)
        try:
            cook_potion.mix_from(message.text, use_suggestions=True)
        except potion.ParsingFormulaError as parse_error:
            self.switch_to_state(BotStates.potions_enter_formula, parse_error.message)
            return

        search_filter = {'user': message.from_user.id, 'name': '__cache'}
        update = {'$set': {'potion': cook_potion.to_dict()}}
        self.mongo.user_potions.update_one(search_filter, update=update, upsert=True)
        self.switch_to_state(BotStates.potions_cooked, cook_potion.overall_description())


class PotionsCookedHandler(BaseMessageHandler):
    STATE = BotStates.potions_cooked
    STATE_BY_MESSAGE = {
        'Готовить ещё': {'state': BotStates.potions_enter_formula},
        'Сохранить': {'state': BotStates.potions_enter_name},
        'В меню': {'state': BotStates.potions_menu},
    }


MAX_NAME_LENGTH = 100
MAX_SAVED_POTIONS = 3


class PotionsEnterNameHandler(BaseMessageHandler):
    STATE = BotStates.potions_enter_name
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.potions_cooked},
    }

    def handle_message(self, message: telebot.types.Message):
        potions_count = self.mongo.user_potions.count_documents(
            {'user': message.from_user.id},
        )
        # + 1 -- cached potion
        if potions_count >= MAX_SAVED_POTIONS + 1:
            self.switch_to_state(BotStates.potions_menu, msgs.TOO_MUCH_POTIONS.format(MAX_SAVED_POTIONS))
            return
        name = message.text
        if not name:
            self.try_again(msgs.EMPTY_TEXT_ERROR)
            return
        if len(name) > MAX_NAME_LENGTH:
            self.try_again(msgs.TOO_LONG_NAME.format(MAX_NAME_LENGTH))
            return
        search_filter = {'user': message.from_user.id, 'name': '__cache'}
        cache_potion = self.mongo.user_potions.find_one(search_filter)
        cache_potion['potion']['__name'] = name
        if not cache_potion or not cache_potion.get('potion'):
            self.switch_to_state(BotStates.potions_menu, msgs.NOT_FOUND)
            return
        potion_doc = {
            'user': message.from_user.id,
            'name': name,
            'potion': cache_potion['potion'],
        }
        try:
            self.mongo.user_potions.insert_one(potion_doc)
        except mongo_errors.DuplicateKeyError:
            self.try_again(msgs.DUPLICATE_NAME_ERROR)
            return
        self.switch_to_state(BotStates.potions_menu, msgs.SAVE_SUCCESS)


if __name__ == '__main__':
    controller = handlers_controller.HandlersController()
    controller.run()
