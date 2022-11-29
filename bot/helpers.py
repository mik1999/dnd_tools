import typing

import dices
import menu
import messages as msgs

import telebot
import telebot.types


def check_and_switch_by_command(
        message: telebot.types.Message,
        bot: telebot.TeleBot,
) -> bool:
    """
    If message start with command - switch to appropriate state
    and write a message
    :param message: user message
    :param bot: the bot
    :return: true if swithed using a command and false otherwise
    """
    STATE_BY_COMMAND = {
        '/start': {
            'state': menu.BotStates.main,
            'message': msgs.MAIN_MENU,
        },
        '/dices': {
            'state': menu.BotStates.dices,
            'message': msgs.DICES_CHOICE,
        },
    }
    if not message.text.startswith('/'):
        return False
    for command in STATE_BY_COMMAND.keys():
        if message.text.startswith(command):
            state_doc = STATE_BY_COMMAND[command]
            menu.switch_to_state(
                bot, state_doc['state'],
                message, state_doc['message'],
            )
            return True
    return False


def process_state_by_message(
        message: telebot.types.Message,
        bot: telebot.TeleBot,
        state_by_message_map,
):
    if check_and_switch_by_command(message, bot):
        return
    if message.text is None:
        menu.switch_to_state(
            bot, menu.BotStates.main,
            message, msgs.ON_NO_USER_TEXT,
        )
    message_text: str = message.text
    state_doc = state_by_message_map.get(message_text)
    if state_doc:
        menu.switch_to_state(
            bot, state_doc['state'],
            message, state_doc['message'],
        )


def handle_dices_formula(
        message: telebot.types.Message,
        formula: str,
        message_on_empty_formula: str,
        bot: telebot.TeleBot,
):
    generator = dices.DicesGenerator()
    try:
        generator.parse(formula)
    except dices.EmptyFormulaError:
        menu.switch_to_state(bot, menu.BotStates.dices, message, message_on_empty_formula)
    except dices.IncorrectSymbolsError:
        menu.switch_to_state(bot, menu.BotStates.dices, message, msgs.DICES_INCORRECT_SYMBOL)
    except dices.ParseDiceFormulaError:
        menu.switch_to_state(bot, menu.BotStates.dices, message, msgs.DICES_PARSE_ERROR)
    except dices.ComplexityError:
        menu.switch_to_state(bot, menu.BotStates.dices, message, msgs.DICES_COMPLEXITY_ERROR)
    except:
        menu.switch_to_state(bot, menu.BotStates.dices, message, msgs.DICES_PARSE_ERROR)
    else:
        generator_warnings = generator.get_warnings()
        if generator_warnings:
            bot.send_message(message.chat.id, generator.sample())
            menu.switch_to_state(bot, menu.BotStates.dices, message, generator_warnings)
        else:
            menu.switch_to_state(bot, menu.BotStates.dices, message, generator.sample())