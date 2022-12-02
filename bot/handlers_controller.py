import copy

from alchemy import components_manager
from alchemy import parameters_manager
import base_handler
import logging
import menu
import messages as msgs
import states
import telebot
from telebot import custom_filters
from telebot.storage import StateMemoryStorage


logger = logging.getLogger()


class HandlersController:
    def __init__(self):
        logger.info('Start HandlersController initializing')
        with open('token') as file:
            token = file.read()
        state_storage = StateMemoryStorage()
        self.bot = telebot.TeleBot(token, state_storage=state_storage)
        self.bot.last_suggestions = {}
        self.bot.add_custom_filter(custom_filters.StateFilter(self.bot))

        menu.ParametersStateSwitcher.calculate_row_texts()
        self.pm = parameters_manager.ParametersManager('../parameters.json')
        self.cm = components_manager.ComponentsManager('../components.json')

        self.init_handlers()
        self.init_commands()

        @self.bot.message_handler(func=(lambda x: True))
        def misunderstand(message: telebot.types.Message):
            # ToDo: if message contains button text process like the button
            menu.switch_to_state(self.bot, states.BotStates.main,
                                 message, msgs.MISUNDERSTAND)

        logger.info('Finished HandlersController initializing successfully')

    def run(self):
        logger.info('Start polling bot')
        self.bot.polling()

    def init_commands(self):

        @self.bot.message_handler(commands=['start'])
        def start_handler(message: telebot.types.Message):
            menu.switch_to_state(
                self.bot, states.STATE_BY_COMMAND['/start'],
                message,
            )

        @self.bot.message_handler(commands=['dices'])
        def dices_handler(message: telebot.types.Message):
            menu.switch_to_state(
                self.bot, states.STATE_BY_COMMAND['/dices'],
                message,
            )

        self.bot.set_my_commands([
            telebot.types.BotCommand('/start', 'Главное меню'),
            telebot.types.BotCommand('/dices', 'Кинуть кости'),
        ])

    def init_handlers(self):
        for subclass in base_handler.BaseMessageHandler.__subclasses__():
            _ = subclass(self.bot, self.pm, self.cm)




