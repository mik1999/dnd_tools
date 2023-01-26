import requests.exceptions

from alchemy import components_manager
from alchemy import parameters_manager
import base_handler
from bestiary import bestiary
import generators
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
HOST = '172.20.56.2'


class HandlersController:
    def __init__(self):
        logger.info('Start HandlersController initializing')
        with open('token') as file:
            token = file.read()
        state_storage = StateMemoryStorage()
        self.bot = telebot.TeleBot(token, state_storage=state_storage)
        self.bot.last_suggestions = {}
        self.bot.add_custom_filter(custom_filters.StateFilter(self.bot))

        self.pm = parameters_manager.ParametersManager('../alchemy/parameters.json')
        self.cm = components_manager.ComponentsManager('../alchemy/')
        self.gm = generators.GeneratorsManager()
        self.bestiary = bestiary.Bestiary('../bestiary/')

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
        self.user_info = db.get_collection('user_info')
        self.mongo_context = MongoContext(self.user_potions, self.user_info)

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
        while True:
            try:
                self.bot.polling()
                break
            except requests.exceptions.ReadTimeout as ex:
                logger.error(f'Caught ReadTimeout error {ex}, restarting polling')

    def init_commands(self):

        @self.bot.message_handler(commands=['start'])
        def start_handler(message: telebot.types.Message):
            self.switch_to_state(states.STATE_BY_COMMAND['/start'], message)

        @self.bot.message_handler(commands=['dices'])
        def dices_handler(message: telebot.types.Message):
            self.switch_to_state(states.STATE_BY_COMMAND['/dices'], message)

        @self.bot.message_handler(commands=['cook'])
        def cook_handler(message: telebot.types.Message):
            self.switch_to_state(states.STATE_BY_COMMAND['/cook'], message)

        @self.bot.message_handler(commands=['name'])
        def name_handler(message: telebot.types.Message):
            self.bot.send_message(message.chat.id, self.gm.sample_name())

        @self.bot.message_handler(commands=['bestiary'])
        def bestiary_handler(message: telebot.types.Message):
            self.switch_to_state(states.STATE_BY_COMMAND['/bestiary'], message)

        self.bot.set_my_commands([
                telebot.types.BotCommand('/start', 'Главное меню'),
                telebot.types.BotCommand('/dices', 'Кинуть кости'),
                telebot.types.BotCommand('/cook', 'Готовить зелье'),
                telebot.types.BotCommand('/name', 'Случайное имя'),
                telebot.types.BotCommand('/bestiary', 'Бестиарий'),
        ])

    def init_handlers(self):
        for subclass in all_subclasses(base_handler.BaseMessageHandler):
            handler = subclass(
                self.bot, self.pm, self.cm, self.gm, self.bestiary, self.mongo_context,
            )
            if handler.STATE is not None:
                self.handler_by_state[handler.STATE] = handler
                handler.set_handler_by_state(self.handler_by_state)
