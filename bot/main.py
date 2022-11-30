import telebot.types

from telebot import custom_filters
from telebot.storage import StateMemoryStorage

from alchemy import components_manager
from alchemy import parameters_manager
import helpers
import logging
import menu
import messages as msgs


logger = logging.getLogger()


def read_token():
    with open('token') as file:
        return file.read()


BOT_TOKEN = read_token()
menu.ParametersStateSwitcher.calculate_row_texts()


state_storage = StateMemoryStorage()
_bot = telebot.TeleBot(BOT_TOKEN, state_storage=state_storage)
_bot.last_suggestions = {}

_bot.set_my_commands([
    telebot.types.BotCommand("/start", "Главное меню"),
    telebot.types.BotCommand("/dices", "Кинуть кости"),
])


@_bot.message_handler(commands=['start'])
def send_welcome(message: telebot.types.Message):
    menu.switch_to_state(
        _bot, menu.BotStates.main,
        message, msgs.MAIN_MENU,
    )


@_bot.message_handler(state=menu.BotStates.main)
def handle_main(message: telebot.types.Message):
    STATE_BY_MESSAGE = {
        'Кинуть кости': {
            'state': menu.BotStates.dices,
            'message': msgs.DICES_CHOICE,
        },
        'Алхимия': {
            'state': menu.BotStates.alchemy,
            # 'message': msgs.ALCHEMY_SWITCH,
        }
    }
    helpers.process_state_by_message(
        message, _bot, STATE_BY_MESSAGE,
    )


@_bot.message_handler(state=menu.BotStates.dices)
def handle_dices(message: telebot.types.Message):
    if helpers.check_and_switch_by_command(message, _bot):
        return
    if message.text == 'Назад':
        menu.switch_to_state(
            _bot, menu.BotStates.main,
            message, msgs.MAIN_MENU,
        )
        return
    helpers.handle_dices_formula(message, message.text, menu.BotStates.dices, _bot)


@_bot.message_handler(state=menu.BotStates.alchemy)
def handle_alchemy(message: telebot.types.Message):
    STATE_BY_MESSAGE = {
        'Параметры': {
            'state': menu.BotStates.parameters,
            'message': msgs.PARAMETER_CHOICE,
        },
        'Ингредиенты': {'state': menu.BotStates.components_menu},
        'Зелья': {
            'state': menu.BotStates.dummy,
            'message': msgs.DUMMY,
        },
        'Что это такое?': {
            'state': menu.BotStates.dummy,
            'message': msgs.DUMMY,
        },
        'Назад': {
            'state': menu.BotStates.main,
            'message': msgs.MAIN_MENU,
        },
    }
    helpers.process_state_by_message(
        message, _bot, STATE_BY_MESSAGE,
    )


@_bot.message_handler(state=menu.BotStates.dummy)
def handle_dummy(message: telebot.types.Message):
    if helpers.check_and_switch_by_command(message, _bot):
        return
    menu.switch_to_state(
        _bot, menu.BotStates.main, message, msgs.MAIN_MENU,
    )


pm = parameters_manager.ParametersManager('../parameters.json')


@_bot.message_handler(state=menu.BotStates.parameters)
def handle_parameters(message: telebot.types.Message):
    if helpers.check_and_switch_by_command(message, _bot):
        return
    if message.text == 'Назад':
        menu.switch_to_state(
            _bot, menu.BotStates.alchemy, message, msgs.ALCHEMY_SWITCH,
        )
        return
    if message.text == 'В главное меню':
        menu.switch_to_state(
            _bot, menu.BotStates.main, message, msgs.MAIN_MENU,
        )
        return
    try:
        text = pm.parameter_brief(message.text)
    except parameters_manager.NoSuchParameter:
        text = msgs.NO_SUCH_PARAMETER
    menu.switch_to_state(_bot, menu.BotStates.parameters, message, text)


cm = components_manager.ComponentsManager('../components.json')


@_bot.message_handler(state=menu.BotStates.components_menu)
def handle_component_menu(message: telebot.types.Message):
    if helpers.check_and_switch_by_command(message, _bot):
        return
    STATE_BY_MESSAGE = {
        'Список ингредиентов': {
            'state': menu.BotStates.components_enter_name,
            'message': cm.components_list(show_telegram_links=True),
        },
        'Об ингредиенте': {
            'state': menu.BotStates.components_enter_name,
            # 'message': None, show default message
        },
        'Назад': {'state': menu.BotStates.alchemy},
    }
    helpers.process_state_by_message(
        message, _bot, STATE_BY_MESSAGE,
    )


@_bot.message_handler(state=menu.BotStates.components_enter_name)
def handle_component_enter(message: telebot.types.Message):
    if message.text.startswith('/'):
        component_name = message.text[1:].split()[0]
        try:
            bot_message = cm.info(component_name, pm)
            menu.switch_to_state(
                _bot, menu.BotStates.components_component_show,
                message, bot_message,
            )
            return
        except components_manager.UnrecognizedComponent:
            menu.switch_to_state(
                _bot, menu.BotStates.components_enter_name,
                message, msgs.UNRECOGNIZED_COMPONENT,
            )
            return
    # if command does not encode component
    if helpers.check_and_switch_by_command(message, _bot):
        return
    if message.text == 'Назад':
        menu.switch_to_state(
            _bot, menu.BotStates.components_menu, message,
        )
        return
    try:
        bot_message = cm.info(message.text, pm)
        menu.switch_to_state(
            _bot, menu.BotStates.components_component_show,
            message, bot_message,
        )
        return
    except components_manager.UnrecognizedComponent:
        _bot.set_state(
            message.from_user.id,
            menu.BotStates.components_enter_name,
            message.chat.id,
        )
        suggestions = cm.suggest_components(message.text)
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=6)
        if not suggestions:
            markup.add('Назад')
            _bot.send_message(message.chat.id, msgs.COMPONENT_NO_SUGGESTIONS, reply_markup=markup)
            return

        buttons = suggestions + ['Назад']
        for i in range(len(buttons) // 2):
            markup.add(buttons[2 * i], buttons[2 * i + 1])
        if len(buttons) % 2 == 1:
            markup.add(buttons[-1])
        _bot.send_message(message.chat.id, msgs.COMPONENTS_SUGGESTIONS_FOUND, reply_markup=markup)


@_bot.message_handler(state=menu.BotStates.components_component_show)
def handle_component_show(message: telebot.types.Message):
    if helpers.check_and_switch_by_command(message, _bot):
        return
    STATE_BY_MESSAGE = {
        'Назад': {'state': menu.BotStates.components_menu},
    }
    helpers.process_state_by_message(
        message, _bot, STATE_BY_MESSAGE,
    )


@_bot.message_handler(commands=['dices'])
def handle_dices(message: telebot.types.Message):
    formula = message.text[6:]
    helpers.handle_dices_formula(message, formula, menu.BotStates.dices, _bot)


@_bot.message_handler(func=(lambda x: True))
def misunderstand(message: telebot.types.Message):
    # ToDo: if message contains button text process like the button
    _bot.send_message(
        message.chat.id,
        msgs.MISUNDERSTAND,
        reply_markup=message.reply_markup,
    )


_bot.add_custom_filter(custom_filters.StateFilter(_bot))


if __name__ == '__main__':
    logger.info('Starting bot polling')
    _bot.polling()
