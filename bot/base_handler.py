import telebot
import telebot.handler_backends as telebot_backends
from alchemy import components_manager
from alchemy import parameters_manager
from bestiary import bestiary
import caches_context
import common_potions
import generators
import messages as msgs
import logging
from treasures import treasures_generator
from mongo_context import MongoContext

from states import BotStates, STATE_BY_COMMAND
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
            gm: generators.GeneratorsManager,
            bestiary: bestiary.Bestiary,
            mongo_context: MongoContext,
            caches: caches_context.CachesContext,
            common_potions: common_potions.CommonPotions,
            treasures: treasures_generator.TreasuresGenerator,
    ):
        if self.STATE is None:
            # do nothing if class is incomplete
            return
        self.bot = bot
        self.pm = pm
        self.cm = cm
        self.gm = gm
        self.treasures = treasures
        self.bestiary = bestiary
        self.mongo = mongo_context
        self.caches = caches
        self.common_potion = common_potions
        self.handler_by_state = None
        self.message: typing.Optional[telebot.types.Message] = None
        self.user_info = None

        @bot.message_handler(state=self.STATE)
        def _(message: telebot.types.Message):
            if __debug__:
                return self.handle_message_middleware(message)
            try:
                return self.handle_message_middleware(message)
            except Exception as ex:
                # whatever happens it must not break bot polling
                logger.error(f'Caught exception {ex} while handling message '
                             f'{message} from user {message.from_user.username}'
                             f'(id={message.from_user.id})')

    def set_handler_by_state(self, handler_by_state):
        self.handler_by_state = handler_by_state

    def handle_message_middleware(self, message: telebot.types.Message):
        """
        Do some middleware staff and call custom handling
        :param message: user message
        """
        logger.info(f'Got message {message.text} from user {message.from_user.username}')
        self.message = message
        reply_message = None
        if self.DO_DEFAULT_COMMANDS:
            reply_message = self.check_and_switch_by_command()
            if reply_message is not None:
                return
        if reply_message is None:
            reply_message = self.process_state_by_message(unknown_pass_enabled=True)
        if reply_message is None:
            reply_message = self.handle_message(message)
        logger.info(f'Reply {reply_message} to user {message.from_user.username}')

    def check_and_switch_by_command(self) -> typing.Optional[telebot.types.Message]:
        """
        If message start with command - switch to appropriate state
        and write a message
        :return: result message if swithed using a command and None otherwise
        """
        if not self.message.text.startswith('/'):
            return None
        if self.message.text.startswith('/name'):
            return self.switch_to_state(BotStates.names_generator, self.gm.sample_name())
        for command in STATE_BY_COMMAND.keys():
            if self.message.text.startswith(command):
                state = STATE_BY_COMMAND[command]
                return self.switch_to_state(state)
        return None

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        """
        State handler function. By default,
        implements menu set by cls.STATE_BY_MESSAGE
        Override it if you want a more complicated handling
        :param message: user message
        :return:
        """
        if not self.STATE_BY_MESSAGE:
            raise NotImplemented()
        return self.process_state_by_message(unknown_pass_enabled=False)

    def switch_to_state(
            self, state: telebot_backends.State,
            message: typing.Optional[str] = None,
            markup: telebot.types.ReplyKeyboardMarkup = None,
            parse_mode: typing.Optional[str] = None,
    ) -> telebot.types.Message:
        handler = self.handler_by_state[state]
        handler.message = self.message
        return handler.switch_on_me(message, markup=markup, parse_mode=parse_mode)

    def try_again(
            self, message: typing.Optional[str] = None,
            parse_mode: typing.Optional[str] = None,
            markup: telebot.types.ReplyKeyboardMarkup = None,
    ) -> telebot.types.Message:
        return self.switch_to_state(self.STATE, message, parse_mode=parse_mode, markup=markup)

    def process_state_by_message(
            self, unknown_pass_enabled=True,
    ) -> typing.Optional[telebot.types.Message]:
        if self.message.text is None and unknown_pass_enabled:
            self.switch_to_state(
                BotStates.main, msgs.ON_NO_USER_TEXT,
            )
            return None
        message_text: str = self.message.text
        if message_text in self.ADMIN_BUTTONS and not self.user_is_admin():
            return self.try_again(msgs.ACCESS_DENIED)
        state_doc = self.STATE_BY_MESSAGE.get(message_text)
        if state_doc:
            return self.switch_to_state(
                state_doc['state'], state_doc.get('message'),
            )
        if not unknown_pass_enabled:
            # ToDo nesessary ? try replace by self.send_message(msgs.PARSE_BUTTON_ERROR)
            markup = self.make_markup(self.make_buttons_list())
            return self.send_message(msgs.PARSE_BUTTON_ERROR, reply_markup=markup)
        return None

    MAX_MESSAGE_LENGTH = 4000

    def send_message(
            self, message: str, reply_markup=None, parse_mode=None,
    ) -> telebot.types.Message:
        max_iter = len(message) // self.MAX_MESSAGE_LENGTH + 1
        for i in range(max_iter):
            if i + 1 != max_iter:
                self.bot.send_message(
                    self.message.chat.id,
                    message[i * self.MAX_MESSAGE_LENGTH:(i + 1) * self.MAX_MESSAGE_LENGTH],
                    parse_mode=parse_mode, reply_markup=reply_markup,
                )
                continue
            return self.bot.send_message(
                self.message.chat.id, message[i * self.MAX_MESSAGE_LENGTH:],
                parse_mode=parse_mode, reply_markup=reply_markup,
            )

    def send_photo(
            self, photo_path: str,
    ) -> telebot.types.Message:
        photo = open(photo_path, 'rb')
        return self.bot.send_photo(self.message.chat.id, photo)

    DEFAULT_MESSAGE = None
    BUTTONS: typing.List[typing.List[str]] = [['Назад']]
    ADMIN_BUTTONS: typing.List[str] = []
    PARSE_MODE = None

    def switch_on_me(
            self,
            bot_message: str = None,
            markup: telebot.types.ReplyKeyboardMarkup = None,
            parse_mode: typing.Optional[str] = None,
    ) -> telebot.types.Message:
        """
        Update user's state and set appropriate buttons
        :param bot_message: message to send
        :param markup: markup to be set. Sets default of markup is None
        :param parse_mode: message parse mode e.g. MarkdownV2
        """
        if parse_mode is None:
            parse_mode = self.PARSE_MODE
        self.bot.set_state(
            self.message.from_user.id, self.STATE, self.message.chat.id,
        )
        if markup is None:
            markup = self.make_markup(self.make_buttons_list())
        if bot_message is None:
            bot_message = self.get_default_message()
            if bot_message is None:
                bot_message = 'Извините, произошла ошибка'
                logger.error(f'Попытка использовать неустановленное дефолтное сообщение для {self.STATE}')
        return self.send_message(bot_message, reply_markup=markup, parse_mode=parse_mode)

    @staticmethod
    def make_markup(buttons_list) -> telebot.types.ReplyKeyboardMarkup:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=6)
        for row in buttons_list:
            markup.add(*[telebot.types.KeyboardButton(text) for text in row])
        return markup

    def get_default_message(self):
        return self.DEFAULT_MESSAGE

    def make_buttons_list(
            self,
    ) -> typing.List[typing.List[str]]:
        """
        Makes list of buttons to show on switch to this state
        """
        if not self.ADMIN_BUTTONS:
            return self.BUTTONS
        result_buttons = []
        for buttons_row in self.BUTTONS:
            new_buttons_row = []
            for button in buttons_row:
                if button not in self.ADMIN_BUTTONS or self.user_is_admin():
                    new_buttons_row.append(button)
            if new_buttons_row:
                result_buttons.append(new_buttons_row)
        return result_buttons

    def set_user_cache(self, data: str):
        with self.caches.cache as conn:
            conn.set(str(self.message.from_user.id), data.encode(encoding='utf-8'))

    def get_user_cache(self) -> typing.Optional[str]:
        with self.caches.cache as conn:
            value = conn.get(str(self.message.from_user.id))
            if value is None:
                return None
            return value.decode(encoding='utf-8')

    def set_user_cache_v2(self, data: str):
        self.mongo.user_info.update_one(
            {'user': self.message.from_user.id},
            {'$set': {'cache': data}},
            upsert=True,
        )

    def get_user_cache_v2(self) -> typing.Optional[str]:
        doc = self.mongo.user_info.find_one({'user': self.message.from_user.id})
        if not doc:
            return None
        return doc.get('cache')

    def user_info_lazy(self) -> typing.Dict[str, typing.Any]:
        if self.user_info is None:
            self.user_info = self.mongo.user_info.find_one({'user': self.message.from_user.id})
            if self.user_info is None:
                self.user_info = {}
        return self.user_info

    def user_is_admin(self) -> bool:
        user_info = self.user_info_lazy()
        return user_info and user_info.get('is_admin', False)


class DocHandler(BaseMessageHandler):
    BUTTONS: typing.List[typing.List[str]] = [['Ок']]
    PARSE_MODE = 'MarkdownV2'
    PARENT_STATE: typing.Optional[telebot_backends.State] = None

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        return self.switch_to_state(self.PARENT_STATE)
