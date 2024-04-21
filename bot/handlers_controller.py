import requests.exceptions

from alchemy import components_manager
from alchemy import parameters_manager
import base_handler
from bestiary import bestiary
import caches_context
import common_potions
import generators
import resources_manager
import logging
import messages as msgs
from mongo_context import MongoContext
import pymongo
import pymongo.collection
import redis
import states
import telebot
from telebot import custom_filters
import telebot.handler_backends as telebot_backends
import telebot.storage as storage
from treasures import treasures_generator
import typing


logger = logging.getLogger()


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])


MONGO_LOGIN = 'dnd_telegram_bot'
MONGO_PASSWORD = 'f249f9Gty2793f20nD2330ry8432'
MONGO_HOST = '172.20.56.2'

REDIS_HOST = '172.20.56.4'
REDIS_PASSWORD = 'mutvi5ey3nMtvi3qcYy47658rvFi4tvnjv3w5Ptc3'
REDIS_PORT = 6379


class HandlersController:
    def __init__(self):
        logger.info('Start HandlersController initializing')
        with open('token') as file:
            token = file.read()
        self.current_redis_db = 0
        state_storage = self.make_state_storage()
        self.bot = telebot.TeleBot(token, state_storage=state_storage)
        self.bot.last_suggestions = {}
        self.bot.add_custom_filter(custom_filters.StateFilter(self.bot))

        self.pm = parameters_manager.ParametersManager('../alchemy/parameters.json')
        self.cm = components_manager.ComponentsManager('../alchemy/')
        self.bestiary = bestiary.Bestiary('../bestiary/')
        self.treasures = treasures_generator.TreasuresGenerator('../treasures/data/')

        if __debug__:
            logger.warning('Using degub environment')
            client = pymongo.MongoClient(f'mongodb://{MONGO_LOGIN}:{MONGO_PASSWORD}@localhost:27017/dnd')
        else:
            logger.info('Using production environment')
            client = pymongo.MongoClient(
                host=[f'{MONGO_HOST}:27017'],
                serverSelectionTimeoutMS=2000,
                username=MONGO_LOGIN,
                password=MONGO_PASSWORD,
            )
        db = client.get_database('dnd')
        self.user_potions = db.get_collection('user_potions')
        self.user_info = db.get_collection('user_info')
        self.user_npcs = db.get_collection('user_npcs')
        self.user_npc_notes = db.get_collection('user_npc_notes')
        self.resources_usage = db.get_collection('resources_usage')
        self.games_collection = db.get_collection('games')
        self.mongo_context = MongoContext(
            self.user_potions, self.user_info, self.user_npcs, self.user_npc_notes, self.games_collection,
        )
        self.resources_manager = resources_manager.ResourcesManager(self.resources_usage)
        self.gm = generators.GeneratorsManager(self.resources_manager)

        self.common_potions = common_potions.CommonPotions(self.mongo_context, self.pm, self.cm)

        if __debug__:
            self.caches = caches_context.CachesContext(
                caches_context.StaticCachePool(),
            )
        else:
            self.caches = caches_context.CachesContext(
                self.make_redis_pool(),
            )

        self.handler_by_state = dict()
        self.init_handlers()
        self.init_commands()

        @self.bot.message_handler(func=(lambda x: True))
        def misunderstand(message: telebot.types.Message):
            # ToDo: if message contains button text process like the button
            self.switch_to_state(states.BotStates.main, message, msgs.MISUNDERSTAND)

        logger.info('Finished HandlersController initializing successfully')

    def make_state_storage(self):
        if __debug__:
            return storage.StateMemoryStorage()
        try:
            db = self.current_redis_db
            # self.current_redis_db += 1
            return storage.StateRedisStorage(host=REDIS_HOST, port=REDIS_PORT, db=db, password=REDIS_PASSWORD)
        except Exception as ex:
            logger.error(f'Error while initiating redis storage {ex}')
            raise ex

    def make_redis_pool(self) -> redis.ConnectionPool:
        pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=self.current_redis_db, password=REDIS_PASSWORD)
        self.current_redis_db += 1
        return pool


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
                self.bot.infinity_polling(timeout=10, long_polling_timeout=5)
                # self.bot.polling()
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
                self.bot,
                self.pm,
                self.cm,
                self.gm,
                self.bestiary,
                self.mongo_context,
                self.caches,
                self.common_potions,
                self.treasures,
            )
            if handler.STATE is not None:
                self.handler_by_state[handler.STATE] = handler
                handler.set_handler_by_state(self.handler_by_state)
