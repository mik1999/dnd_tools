import copy
import datetime

from base_handler import BaseMessageHandler

import utils.dices as dices
import handlers_controller

# ignore unused import! It is used to bind handlers!

from handlers import common_alchemy_handlers
from handlers import component_handlers
from handlers import generators_handlers
from handlers import potion_handlers
from handlers import npc
from handlers import casino

import logging
import messages as msgs
from states import BotStates
import telebot.types


logger = logging.getLogger()


class MainStateHandler(BaseMessageHandler):
    STATE = BotStates.main
    STATE_BY_MESSAGE = {
        'Кинуть кости': {'state': BotStates.dices},
        'Генераторы': {'state': BotStates.generators_menu},
        'Алхимия': {'state': BotStates.alchemy},
        'Казино': {'state': BotStates.casino_main},
    }
    DEFAULT_MESSAGE = msgs.MAIN_MENU
    BUTTONS = [['Алхимия', 'Казино', 'NPC'], ['Генераторы', 'Кинуть кости']]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        if message.text == 'NPC':
            npcs_count = self.mongo.user_npcs.count_documents({'user': message.from_user.id})
            if npcs_count > 0:
                return self.switch_to_state(BotStates.npc_start_menu)
            return self.switch_to_state(BotStates.npc_create_race, msgs.NPCS_ONBOARDING)
        return self.try_again(msgs.PARSE_BUTTON_ERROR)


class DicesStateHandler(BaseMessageHandler):
    STATE = BotStates.dices
    STATE_BY_MESSAGE = {'Назад': {'state': BotStates.main}}
    DEFAULT_MESSAGE = msgs.DICES_CHOICE
    BUTTONS = [
        ['d4', 'd6', 'd8'],
        ['d10', 'd20', 'd100'],
        ['Назад'],
    ]

    def handle_message(
            self, message: telebot.types.Message,
    ) -> telebot.types.Message:
        formula = message.text
        generator = dices.DicesGenerator()
        try:
            generator.parse(formula)
        except dices.EmptyFormulaError:
            return self.switch_to_state(BotStates.dices, msgs.EMPTY_TEXT_ERROR)
        except dices.IncorrectSymbolsError:
            return self.switch_to_state(BotStates.dices, msgs.DICES_INCORRECT_SYMBOL)
        except dices.ParseDiceFormulaError:
            return self.switch_to_state(BotStates.dices, msgs.DICES_PARSE_ERROR)
        except dices.ComplexityError:
            return self.switch_to_state(BotStates.dices, msgs.DICES_COMPLEXITY_ERROR)
        except:
            return self.switch_to_state(BotStates.dices, msgs.DICES_PARSE_ERROR)
        else:
            generator_warnings = generator.get_warnings()
            markup = None
            if message.text not in ['d4', 'd6', 'd8', 'd10', 'd20', 'd100']:
                buttons = copy.deepcopy(self.BUTTONS)
                buttons[2].append(message.text)
                markup = self.make_markup(buttons)
            # ToDo: add dice emoji if dice == d6
            if generator_warnings:
                self.send_message(generator.sample())
                return self.switch_to_state(BotStates.dices, generator_warnings, markup=markup)
            else:
                return self.switch_to_state(BotStates.dices, generator.sample(), markup=markup)


class DummyHandler(BaseMessageHandler):
    STATE = BotStates.dummy
    STATE_BY_MESSAGE = {'В меню': {'state': BotStates.main}}
    BUTTONS = [['В меню']]
    DEFAULT_MESSAGE = msgs.DUMMY


if __name__ == '__main__':
    controller = handlers_controller.HandlersController()
    controller.run()
