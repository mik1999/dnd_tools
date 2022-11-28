import dices

import telebot
import telebot.types


def handle_dices_formula(
        bot: telebot.TeleBot,
        message: telebot.types.Message,
        formula: str,
        set_state,
):
    generator = dices.DicesGenerator()
    delete_state_flag = True
    try:
        generator.parse(formula)
    except dices.EmptyFormulaError:
        if set_state:
            bot.set_state(message.from_user.id, set_state, message.chat.id)
            bot.send_message(message.chat.id, 'Какие кости кидать? \nПример: 2d6 + 2')
            delete_state_flag = False
    except dices.IncorrectSymbolsError:
        bot.send_message(
            message.chat.id,
            'Не понимаю. Формула не должна содержать '
            'чего-то, кроме знаков + и -, цифр, пробелов и '
            'обозначений куба (d или к). '
            '\nПример: 2d6 + 3'
            '\nНажмите /dices, чтобы попробовать еще раз',
        )
    except dices.ParseDiceFormulaError:
        bot.send_message(
            message.chat.id,
            'Формула не распознана.'
            'Нажмите /dices, чтобы попробовать еще раз'
            '\nПример правильной формулы:'
            '\n3к8 + 2',
        )
    except dices.ComplexityError:
        bot.send_message(message.chat.id, 'Мне лень это считать - слишком сложно')
    except:
        bot.send_message(message.chat.id, 'Ошибка. Нажмите /dices, чтобы попробовать еще раз')
    else:
        bot.send_message(message.chat.id, generator.sample())
        generator_warnings = generator.get_warnings()
        if generator_warnings:
            bot.send_message(message.chat.id, generator_warnings)
    if delete_state_flag:
        bot.delete_state(message.from_user.id, message.chat.id)