import telebot
import telebot.handler_backends as telebot_backends
from alchemy import components_manager
from alchemy import parameters_manager
import helpers
import menu
import messages as msgs
from mongo_context import MongoContext

import logging
import typing


logger = logging.getLogger()


class BaseMessageHandler:

    DO_DEFAULT_COMMANDS = True
    STATE: typing.Optional[telebot_backends.State] = None
    STATE_BY_MESSAGE = dict()

    def __init__(
            self, bot: telebot.TeleBot,
            pm: parameters_manager.ParametersManager,
            cm: components_manager.ComponentsManager,
            mongo_context: MongoContext,
    ):
        if self.STATE is None:
            # do nothing if class is incomplete
            return
        self.bot = bot
        self.pm = pm
        self.cm = cm
        self.mongo = mongo_context
        self.message: typing.Optional[telebot.types.Message] = None

        @bot.message_handler(state=self.STATE)
        def _(message: telebot.types.Message):
            return self.handle_message_middleware(message)

    def handle_message_middleware(self, message: telebot.types.Message):
        """
        Do some middleware staff and call custom handling
        :param message: user message
        """
        try:
            logger.info(f'Got message {message.text} from user {message.from_user.username}')
            self.message = message
            if self.DO_DEFAULT_COMMANDS:
                if helpers.check_and_switch_by_command(message, self.bot):
                    return
            if self.process_state_by_message(unknown_pass_enabled=True):
                return
            self.handle_message(message)
        except Exception as ex:
            # whatever happens it must not break bot polling
            logger.error(f'Caught exception {ex} while handling message '
                         f'{message} from user {message.from_user.username}'
                         f'(id={message.from_user.id})')

    def handle_message(self, message: telebot.types.Message):
        """
        State handler function. By default,
        implements menu set by cls.STATE_BY_MESSAGE
        Override it if you want a more complicated handling
        :param message: user message
        :return:
        """
        if not self.STATE_BY_MESSAGE:
            raise NotImplemented()
        self.process_state_by_message(unknown_pass_enabled=False)

    def switch_to_state(
            self, state: telebot_backends.State,
            message: typing.Optional[str] = None,
    ):
        menu.switch_to_state(self.bot, state, self.message, message)

    def try_again(self, message: typing.Optional[str] = None):
        self.switch_to_state(self.STATE, message)

    def process_state_by_message(self, unknown_pass_enabled=True):
        if self.message.text is None and unknown_pass_enabled:
            menu.switch_to_state(
                self.bot, menu.BotStates.main,
                self.message, msgs.ON_NO_USER_TEXT,
            )
            return False
        message_text: str = self.message.text
        state_doc = self.STATE_BY_MESSAGE.get(message_text)
        if state_doc:
            menu.switch_to_state(
                self.bot, state_doc['state'],
                self.message, state_doc.get('message'),
            )
            return True
        if not unknown_pass_enabled:
            # ToDo nesessary ?
            current_state = self.bot.get_state(self.message.from_user.id, self.message.chat.id)
            menu.switch_to_state(self.bot, current_state, self.message, msgs.PARSE_BUTTON_ERROR)
        return False

