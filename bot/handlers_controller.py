from alchemy import components_manager
from alchemy import parameters_manager
import base_handler
import logging
import messages as msgs
from mongo_context import MongoContext
import pymongo
import pymongo.collection
import states
import telebot
from telebot import custom_filters
import telebot.handler_backends as telebot_backends
from telebot.storage import StateMemoryStorage
import typing


logger = logging.getLogger()


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])


MONGO_LOGIN = 'dnd_telegram_bot'
MONGO_PASSWORD = 'f249f9Gty2793f20nD2330ry8432'
HOST = '172.21.0.2'


class HandlersController:
    def __init__(self):
        logger.info('Start HandlersController initializing')
        with open('token') as file:
            token = file.read()
        state_storage = StateMemoryStorage()
        self.bot = telebot.TeleBot(token, state_storage=state_storage)
        self.bot.last_suggestions = {}
        self.bot.add_custom_filter(custom_filters.StateFilter(self.bot))

        self.pm = parameters_manager.ParametersManager('../parameters.json')
        self.cm = components_manager.ComponentsManager('../components.json')

        if __debug__:
            logger.warning('Using degub environment')
            client = pymongo.MongoClient(f'mongodb://{MONGO_LOGIN}:{MONGO_PASSWORD}@localhost:27017/dnd')
        else:
            logger.info('Using production environment')
            client = pymongo.MongoClient(
                host=[f'{HOST}:27017'],
                serverSelectionTimeoutMS=2000,
                username=MONGO_LOGIN,
                password=MONGO_PASSWORD,
            )
        db = client.get_database('dnd')
        self.user_potions = db.get_collection('user_potions')
        self.mongo_context = MongoContext(self.user_potions)

        self.handler_by_state = dict()
        self.init_handlers()
        self.init_commands()

        @self.bot.message_handler(func=(lambda x: True))
        def misunderstand(message: telebot.types.Message):
            # ToDo: if message contains button text process like the button
            self.switch_to_state(states.BotStates.main, message, msgs.MISUNDERSTAND)

        logger.info('Finished HandlersController initializing successfully')

    def switch_to_state(
            self, state: telebot_backends.State,
            message: telebot.types.Message,
            bot_message: typing.Optional[str] = None,
    ) -> telebot.types.Message:
        handler = self.handler_by_state[state]
        handler.message = message
        return handler.switch_on_me(bot_message)

    def run(self):
        logger.info('Start polling bot')
        self.bot.polling()

    def init_commands(self):

        @self.bot.message_handler(commands=['start'])
        def start_handler(message: telebot.types.Message):
            self.switch_to_state(states.STATE_BY_COMMAND['/start'], message)

        @self.bot.message_handler(commands=['dices'])
        def dices_handler(message: telebot.types.Message):
            self.switch_to_state(states.STATE_BY_COMMAND['/dices'], message)

        self.bot.set_my_commands([
            telebot.types.BotCommand('/start', 'Главное меню'),
            telebot.types.BotCommand('/dices', 'Кинуть кости'),
        ])

    def init_handlers(self):
        for subclass in all_subclasses(base_handler.BaseMessageHandler):
            handler = subclass(self.bot, self.pm, self.cm, self.mongo_context)
            if handler.STATE is not None:
                self.handler_by_state[handler.STATE] = handler
                handler.set_handler_by_state(self.handler_by_state)
