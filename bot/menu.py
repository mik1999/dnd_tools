import logging
import typing

import telebot
import telebot.handler_backends as telebot_backends
import telebot.types

from alchemy import parameters_manager
import messages as msgs


logger = logging.getLogger()


class BotStates(telebot_backends.StatesGroup):
    main = telebot_backends.State()
    dices = telebot_backends.State()
    alchemy = telebot_backends.State()
    parameters = telebot_backends.State()
    dummy = telebot_backends.State()

    components_menu = telebot_backends.State()
    components_enter_name = telebot_backends.State()
    components_component_show = telebot_backends.State()


class BaseStateSwitcher:
    STATE: telebot_backends.State = None
    DEFAULT_MESSAGE = None
    # redefine ROW_TEXTS (simple) or edit_markup (compl)
    ROW_TEXTS: typing.List[typing.List[str]] = [['Назад']]

    @classmethod
    def swith_to_state(
            cls,
            bot: telebot.TeleBot,
            user_message: telebot.types.Message,
            bot_message: str = None,
    ):
        """
        Update user's state and set appropriate buttons
        :param bot: the bot
        :param user_message: current user message
        :param bot_message: message to be sent
        """
        bot.set_state(user_message.from_user.id, cls.STATE, user_message.chat.id)
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=6)
        cls.edit_markup(user_message, markup)
        if bot_message is None:
            bot_message = cls.DEFAULT_MESSAGE
            if bot_message is None:
                bot_message = 'Извините, произошла ошибка'
                logger.error(f'Попытка использовать неустановленное дефолтное сообщение для {cls.STATE}')
        bot.send_message(user_message.chat.id, bot_message, reply_markup=markup)

    @classmethod
    def edit_markup(
            cls,
            user_message: telebot.types.Message,
            markup: telebot.types.ReplyKeyboardMarkup,
    ):
        """
        Edit reply markup, override in derived class
        or just redifine ROW_TEXTS
        :param user_message: current user message
        :param markup: markup to edit
        """
        for row in cls.ROW_TEXTS:
            markup.add(*[telebot.types.KeyboardButton(text) for text in row])


class MainStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.main
    ROW_TEXTS = [['Кинуть кости'], ['Алхимия']]


class DicesStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.dices
    ROW_TEXTS = [
            ['d4', 'd6', 'd8'],
            ['d10', 'd20', 'd100'],
            ['Назад'],
        ]


class AlchemyStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.alchemy
    DEFAULT_MESSAGE = msgs.ALCHEMY_SWITCH
    ROW_TEXTS = [
            ['Параметры', 'Ингредиенты', 'Зелья'],
            ['Что это такое?', 'Назад'],
        ]


class ParametersStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.parameters
    ROW_TEXTS = None
    SOFT_MAX_BUTTONS = 5
    MIN_BUTTONS = 2

    @classmethod
    def calculate_row_texts(cls):
        if cls.ROW_TEXTS is None:
            logger.info('Start collection parameter symbols')
            pm = parameters_manager.ParametersManager('../parameters.json')
            symbols = pm.parameter_symbols()
            batch = []
            row_texts = []
            for symbol in symbols:
                batch.append(symbol)
                if len(batch) == cls.SOFT_MAX_BUTTONS:
                    row_texts.append(batch)
                    batch = []
            if len(batch) < cls.MIN_BUTTONS:
                row_texts[-1] += batch
            elif batch:
                row_texts.append(batch)
            row_texts += [['В главное меню', 'Назад']]
            cls.ROW_TEXTS = row_texts


class DummyStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.dummy
    ROW_TEXTS = [['Назад']]


class ComponentsMenuStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.components_menu
    DEFAULT_MESSAGE = 'Можете посмотреть список ингридиентов или ввести название конкретного'
    ROW_TEXTS = [['Список ингредиентов', 'Об ингредиенте'],
                 ['Назад']]


class CompEnterNameStateSwitcher(BaseStateSwitcher):
    DEFAULT_MESSAGE = 'Введите название ингредиента'
    STATE = BotStates.components_enter_name
    ROW_TEXTS = [['Назад']]


class ComponentShowStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.components_component_show
    ROW_TEXTS = [['Назад']]


def _state_name(state):
    if isinstance(state, str):
        return state
    return state.name


def switch_to_state(
        bot: telebot.TeleBot,
        state: telebot_backends.State,
        user_message: telebot.types.Message,
        bot_message: typing.Optional[str] = None,
):
    """
    Switch to a state and write message using appropriate Switcher
    :param bot: the bot
    :param state: state to switch to
    :param user_message: current user message
    :param bot_message: message to be sent
    """
    for switcher in BaseStateSwitcher.__subclasses__():
        if switcher.STATE.name == _state_name(state):
            switcher.swith_to_state(bot, user_message, bot_message)
            return
    logger.error(f'Failed to switch to {state} state')
    # send the message at least
    bot.send_message(user_message.chat.id, bot_message or 'Ошибка')
