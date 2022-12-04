import telebot.types

from alchemy import components_manager

import messages as msgs
from states import BotStates

from base_handler import BaseMessageHandler


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
            suggestions = self.cm.suggest_components(message.text)
            markup = telebot.types.ReplyKeyboardMarkup(
                resize_keyboard=True, row_width=6,
            )
            if not suggestions:
                markup.add('Назад')
                return self.switch_to_state(
                    BotStates.components_enter_name,
                    msgs.COMPONENT_NO_SUGGESTIONS,
                    markup=markup,
                )

            buttons = suggestions + ['Назад']
            for i in range(len(buttons) // 2):
                markup.add(buttons[2 * i], buttons[2 * i + 1])
            if len(buttons) % 2 == 1:
                markup.add(buttons[-1])
            return self.switch_to_state(
                BotStates.components_enter_name,
                msgs.COMPONENTS_SUGGESTIONS_FOUND,
                markup=markup,
            )


class ComponentShowHandler(BaseMessageHandler):
    STATE = BotStates.components_component_show
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.components_menu},
    }

    BUTTONS = [['Назад']]
