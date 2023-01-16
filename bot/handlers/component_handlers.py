import telebot.types

from alchemy import components_manager
import helpers
import messages as msgs
from states import BotStates

from base_handler import BaseMessageHandler
from utils.words_suggester import TooManySuggestionsError


class ComponentsMenuHandler(BaseMessageHandler):
    STATE = BotStates.components_menu
    STATE_BY_MESSAGE = {
        'Об ингредиенте': {
            'state': BotStates.components_enter_name,
        },
        'Назад': {'state': BotStates.alchemy},
    }

    DEFAULT_MESSAGE = 'Можете посмотреть список ингридиентов или ввести название конкретного'
    BUTTONS = [['Список ингредиентов', 'Об ингредиенте'],
                 ['Назад']]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if message.text == 'Список ингредиентов':
            response = self.cm.components_list(show_telegram_links=True)
            return self.switch_to_state(BotStates.components_enter_name, response)

        return self.process_state_by_message(unknown_pass_enabled=False)


class ComponentsEnterHandler(BaseMessageHandler):
    STATE = BotStates.components_enter_name
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.components_menu}}
    DEFAULT_MESSAGE = 'Введите название ингредиента'
    BUTTONS = [['Назад']]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if message.text.startswith('/'):
            component_name = message.text[1:].split()[0]
            try:
                bot_message = self.cm.info(component_name, self.pm)
                return self.switch_to_state(
                    BotStates.components_component_show, bot_message,
                )

            except components_manager.UnrecognizedComponent:
                return self.switch_to_state(
                    BotStates.components_enter_name, msgs.UNRECOGNIZED_COMPONENT,
                )
        try:
            bot_message = self.cm.info(message.text, self.pm)
            return self.switch_to_state(
                BotStates.components_component_show, bot_message,
            )
        except components_manager.UnrecognizedComponent:
            try:
                suggestions = self.cm.suggest_components(message.text)
            except TooManySuggestionsError:
                return self.try_again(msgs.REQUEST_TOO_BROAD)
            if not suggestions:
                return self.switch_to_state(
                    BotStates.components_enter_name,
                    msgs.COMPONENT_NO_SUGGESTIONS,
                    markup=helpers.make_aligned_markup(['Назад'], 1),
                )

            buttons = suggestions + ['Назад']
            return self.switch_to_state(
                BotStates.components_enter_name,
                msgs.REQUEST_SUGGESTIONS_FOUND,
                markup=helpers.make_aligned_markup(buttons, 2),
            )


class ComponentShowHandler(BaseMessageHandler):
    STATE = BotStates.components_component_show
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.components_menu},
    }

    BUTTONS = [['Назад']]
