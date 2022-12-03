import logging
import typing

import telebot
import telebot.handler_backends as telebot_backends
import telebot.types

from alchemy import parameters_manager
from states import BotStates
import messages as msgs

logger = logging.getLogger()


class BaseStateSwitcher:
    STATE: telebot_backends.State = None
    DEFAULT_MESSAGE = None
    # redefine ROW_TEXTS (simple) or edit_markup (compl)
    ROW_TEXTS: typing.List[typing.List[str]] = [['Назад']]
    DEFAULT_PARSE_MODE = None

    @classmethod
    def switch_to_state(
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
        :param parse_mode: a way to parse message, 
                           e.g. for docs use "Markdown"
        """
        parse_mode = cls.DEFAULT_PARSE_MODE
        bot.set_state(user_message.from_user.id, cls.STATE, user_message.chat.id)
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=6)
        cls.edit_markup(user_message, markup)
        if bot_message is None:
            bot_message = cls.DEFAULT_MESSAGE
            if bot_message is None:
                bot_message = 'Извините, произошла ошибка'
                logger.error(f'Попытка использовать неустановленное дефолтное сообщение для {cls.STATE}')
        bot.send_message(user_message.chat.id, bot_message, reply_markup=markup, parse_mode=parse_mode)

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
    DEFAULT_MESSAGE = msgs.MAIN_MENU
    ROW_TEXTS = [['Кинуть кости'], ['Алхимия']]


class DicesStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.dices
    DEFAULT_MESSAGE = msgs.DICES_CHOICE
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
    DEFAULT_MESSAGE = msgs.DUMMY
    ROW_TEXTS = [['В меню']]


class ComponentsMenuStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.components_menu
    DEFAULT_MESSAGE = 'Можете посмотреть список ингридиентов или ввести название конкретного'
    ROW_TEXTS = [['Список ингредиентов', 'Об ингредиенте'],
                 ['Назад']]


class CompEnterNameStateSwitcher(BaseStateSwitcher):
    DEFAULT_MESSAGE = 'Введите название ингредиента'
    STATE = BotStates.components_enter_name
    ROW_TEXTS = [['Назад']]


class PotionsMenuStateSwitcher(BaseStateSwitcher):
    DEFAULT_MESSAGE = ('Вода в котле закипает, в воздухе витает запах трав, '
                       'перегонный куб готов к работе, книга рецептов раскрыта. '
                       'Что будем делать?')

    STATE = BotStates.potions_menu
    ROW_TEXTS = [
        ['Мои зелья', 'Готовить'],
        ['Что это такое?', 'Назад'],
        ['Вывести список ингридиентов'],
    ]


class PotionsEnterFormulaStateSwitcher(BaseStateSwitcher):
    DEFAULT_MESSAGE = 'Введите формулу, например, зверобой + 2 гифлома'

    STATE = BotStates.potions_enter_formula
    ROW_TEXTS = [['Назад']]


class PotionsCookedMenuStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.potions_cooked
    ROW_TEXTS = [['Готовить ещё', 'Сохранить'], ['В меню']]


class PotionsEnterNameStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.potions_enter_name
    DEFAULT_MESSAGE = 'Введите название для нового зелья'
    ROW_TEXTS = [['Отмена']]


class ComponentShowStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.components_component_show
    ROW_TEXTS = [['Назад']]


class AlchemyDocSwitcher(BaseStateSwitcher):
    STATE = BotStates.alchemy_doc
    ROW_TEXTS: typing.List[typing.List[str]] = [['Назад']]
    DEFAULT_PARSE_MODE = 'MarkdownV2'
    DEFAULT_MESSAGE = msgs.ALCHEMY_ABOUT


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
    :param parse_mode: message parse mode, e.g. Markdown
    """
    for switcher in BaseStateSwitcher.__subclasses__():
        if switcher.STATE and switcher.STATE.name == _state_name(state):
            switcher.switch_to_state(bot, user_message, bot_message)
            return
    logger.error(f'Failed to switch to {state} state')
    # send the message at least
    bot.send_message(user_message.chat.id, bot_message or 'Ошибка')
