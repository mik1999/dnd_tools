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
        'Собирательство': {
            'state': BotStates.components_location_choice,
        },
        'Назад': {'state': BotStates.alchemy},
    }

    DEFAULT_MESSAGE = 'Можете посмотреть список ингридиентов или ввести название конкретного'
    BUTTONS = [['Список ингредиентов', 'Об ингредиенте'],
                 ['Собирательство', 'Назад']]

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


class ComponentsLocationChoiceHandler(BaseMessageHandler):
    STATE = BotStates.components_location_choice
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.components_menu}}
    DEFAULT_MESSAGE = 'Где вы ищете?'
    BUTTONS = [['Лес', 'Луг', 'Подземелье'], ['Назад']]
    ALL_LOCATIONS = ['Лес', 'Луг', 'Подземелье']

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if message.text not in self.ALL_LOCATIONS:
            return self.try_again(msgs.PARSE_BUTTON_ERROR)
        self.set_user_cache(message.text)
        self.switch_to_state(BotStates.components_enter_roll_value)


class ComponentsRollValueEnterHandler(BaseMessageHandler):
    STATE = BotStates.components_enter_roll_value
    DEFAULT_MESSAGE = 'Сколько выпало на кубике?'



    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        location = components_manager.Location(self.get_user_cache())
        value = message.text.strip()
        if not value.isdigit():
            return self.try_again(msgs.NOT_A_NUMBER_ENTERED)
        value = int(value)
        component, number = self.cm.sample_component(value, location)
        if component is None:
            return self.switch_to_state(BotStates.components_menu, msgs.COMPONENTS_NOTHING_FOUND)
        rarity = components_manager.RARITY_NAME_MAP[component.rarity]
        message = f'Вы нашли {number} {component.name}, {rarity}. Подробнее: /{component.name_en}'
        return self.switch_to_state(BotStates.components_menu, message)
