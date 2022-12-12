import telebot.types

from alchemy import parameters_manager

import logging
import messages as msgs
from states import BotStates
import typing

from base_handler import BaseMessageHandler, DocHandler


logger = logging.getLogger()


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
    DEFAULT_MESSAGE = msgs.ALCHEMY_SWITCH
    BUTTONS = [
        ['Параметры', 'Ингредиенты', 'Зелья'],
        ['Что это такое?', 'Назад'],
    ]


class AlchemyDocHandler(DocHandler):
    STATE = BotStates.alchemy_doc
    PARENT_STATE = BotStates.alchemy
    DEFAULT_MESSAGE = msgs.ALCHEMY_ABOUT


class ParametersHandler(BaseMessageHandler):
    STATE = BotStates.parameters
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.alchemy},
        'В главное меню': {'state': BotStates.main},
    }
    BUTTONS = None
    SOFT_MAX_BUTTONS = 5
    MIN_BUTTONS = 2

    def __init__(self, *args):
        super().__init__(*args)
        self.buttons = None

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:

        if self.buttons is None:
            logger.info('Start collection parameter symbols')
            symbols = self.pm.parameter_symbols()
            batch = []
            BUTTONS = []
            for symbol in symbols:
                batch.append(symbol)
                if len(batch) == self.SOFT_MAX_BUTTONS:
                    BUTTONS.append(batch)
                    batch = []
            if len(batch) < self.MIN_BUTTONS:
                BUTTONS[-1] += batch
            elif batch:
                BUTTONS.append(batch)
            BUTTONS += [['В главное меню', 'Назад']]
            self.buttons = BUTTONS
        return self.buttons

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        try:
            text = self.pm.parameter_brief(message.text)
        except parameters_manager.NoSuchParameter:
            text = msgs.NO_SUCH_PARAMETER
        return self.switch_to_state(BotStates.parameters, text)
