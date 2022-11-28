import telebot
import telebot.types
import logging

from telebot import custom_filters
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage

import dices


logger = logging.getLogger()


def read_token():
    with open('token') as file:
        return file.read()


BOT_TOKEN = read_token()


state_storage = StateMemoryStorage()
_bot = telebot.TeleBot(BOT_TOKEN, state_storage=state_storage)
_bot.last_suggestions = {}

_bot.set_my_commands([
    telebot.types.BotCommand("/start", "Главное меню"),
    telebot.types.BotCommand("/dices", "Кинуть кости"),
])


class BotStates(StatesGroup):
    dices = State()


@_bot.message_handler(commands=['start'])
def send_welcome(message: telebot.types.Message):
    logger.info(f'Caught start command from user {message.from_user.username}')
    _bot.send_message(message.chat.id, f'Привет!')


def handle_dices_formula(message, formula: str, set_state):
    generator = dices.DicesGenerator()
    delete_state_flag = True
    try:
        generator.parse(formula)
    except dices.EmptyFormulaError:
        if set_state:
            _bot.set_state(message.from_user.id, set_state, message.chat.id)
            _bot.send_message(message.chat.id, 'Какие кости кидать? \nПример: 2d6 + 2')
            delete_state_flag = False
    except dices.IncorrectSymbolsError:
        _bot.send_message(
            message.chat.id,
            'Не понимаю. Формула не должна содержать '
            'чего-то, кроме знаков + и -, цифр, пробелов и '
            'обозначений куба (d или к). '
            '\nПример: 2d6 + 3'
            '\nНажмите /dices, чтобы попробовать еще раз',
        )
    except dices.ParseDiceFormulaError:
        _bot.send_message(
            message.chat.id,
            'Формула не распознана.'
            'Нажмите /dices, чтобы попробовать еще раз'
            '\nПример правильной формулы:'
            '\n3к8 + 2',
        )
    except dices.ComplexityError:
        _bot.send_message(message.chat.id, 'Мне лень это считать - слишком сложно')
    except:
        _bot.send_message(message.chat.id, 'Ошибка. Нажмите /dices, чтобы попробовать еще раз')
    else:
        _bot.send_message(message.chat.id, generator.sample())
        generator_warnings = generator.get_warnings()
        if generator_warnings:
            _bot.send_message(message.chat.id, generator_warnings)
    if delete_state_flag:
        _bot.delete_state(message.from_user.id, message.chat.id)


@_bot.message_handler(commands=['dices'])
def handle_dices(message):
    formula = message.text[6:]
    handle_dices_formula(message, formula, BotStates.dices)


@_bot.message_handler(state=BotStates.dices)
def handle_dices(message):
    telebot.TeleBot
    handle_dices_formula(message, message.text, None)


@_bot.message_handler(func=(lambda x: True))
def misunderstand(message):
    _bot.send_message(message.chat.id, 'Используйте меню, чтобы выбрать команды')


_bot.add_custom_filter(custom_filters.StateFilter(_bot))


if __name__ == '__main__':
    logger.info('Starting bot polling')
    _bot.polling()
