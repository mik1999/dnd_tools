import telebot.types

from telebot import custom_filters
from telebot.storage import StateMemoryStorage

from alchemy import components_manager
from alchemy import parameters_manager
import helpers
import logging
import menu
import messages as msgs
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
        'Зелья': {'state': BotStates.dummy},
        'Что это такое?': {'state': BotStates.dummy},
        'Назад': {'state': BotStates.main},
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


if __name__ == '__main__':
    controller = handlers_controller.HandlersController()
    controller.run()
