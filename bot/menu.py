import logging

import telebot
import telebot.handler_backends as telebot_backends
import telebot.types


logger = logging.getLogger()


class BotStates(telebot_backends.StatesGroup):
    main = telebot_backends.State()
    dices = telebot_backends.State()


class BaseStateSwitcher:
    STATE: telebot_backends.State = None

    @classmethod
    def swith_to_state(
            cls,
            bot: telebot.TeleBot,
            user_message: telebot.types.Message,
            bot_message: str,
    ):
        """
        Update user's state and set appropriate buttons
        :param bot: the bot
        :param user_message: current user message
        :param bot_message: message to be sent
        """
        bot.set_state(user_message.from_user.id, cls.STATE, user_message.chat.id)
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        cls.edit_markup(user_message, markup)
        bot.send_message(user_message.chat.id, bot_message, reply_markup=markup)

    @classmethod
    def edit_markup(
            cls,
            user_message: telebot.types.Message,
            markup: telebot.types.ReplyKeyboardMarkup,
    ):
        """
        Edit reply markup, to be overriden in derived classes
        :param user_message: current user message
        :param markup: markup to edit
        """
        raise NotImplemented()


class MainStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.main

    @classmethod
    def edit_markup(
            cls,
            _,
            markup: telebot.types.ReplyKeyboardMarkup,
    ):
        btn1 = telebot.types.KeyboardButton('Кинуть кости')
        markup.add(btn1)


class DicesStateSwitcher(BaseStateSwitcher):
    STATE = BotStates.dices

    @classmethod
    def edit_markup(
            cls,
            _,
            markup: telebot.types.ReplyKeyboardMarkup,
    ):
        row_texts = [
            ['d4', 'd6', 'd8'],
            ['d10', 'd20', 'd100'],
            ['Назад'],
        ]
        for row in row_texts:
            markup.add(*[telebot.types.KeyboardButton(text) for text in row])


def switch_to_state(
        bot: telebot.TeleBot,
        state: telebot_backends.State,
        user_message: telebot.types.Message,
        bot_message: str,
):
    """
    Switch to a state and write message using appropriate Switcher
    :param bot: the bot
    :param state: state to switch to
    :param user_message: current user message
    :param bot_message: message to be sent
    """
    for switcher in BaseStateSwitcher.__subclasses__():
        if switcher.STATE.name == state.name:
            switcher.swith_to_state(bot, user_message, bot_message)
            return
    logger.error(f'Failed to switch to {state} state')
    # send the message at least
    bot.send_message(user_message.chat.id, bot_message)
