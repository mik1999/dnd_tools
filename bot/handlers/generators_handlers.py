import bestiary.bestiary as bestiary
import copy
import helpers
import telebot.types
from treasures.treasures_generator import explain_treasure

import messages as msgs
import typing
from states import BotStates

from base_handler import BaseMessageHandler
import utils.words_suggester as suggester


class GeneratorsHandler(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Что нужно сгенерировать?'
    STATE = BotStates.generators_menu
    STATE_BY_MESSAGE = {
        'Имя': {'state': BotStates.names_generator},
        'Бестиарий': {'state': BotStates.bestiary_menu},
        'Сокровища': {'state': BotStates.treasury_generator},
        'Назад': {'state': BotStates.main},
    }

    BUTTONS = [['Волна дикой магии', 'Имя', 'Бестиарий'], ['Таверна', 'Сокровища', 'Назад']]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if message.text == 'Таверна':
            return self.try_again(self.gm.gen_tavern())
        if message.text == 'Волна дикой магии':
            return self.try_again(self.gm.sample_wild_magic())
        return self.try_again(msgs.PARSE_BUTTON_ERROR)


class NamesGeneratorHandler(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Выберите расу'
    STATE = BotStates.names_generator

    BUTTONS = [
        ['Случайная раса', 'Человек'],
        ['Дварф', 'Полурослик', 'Эльф'],
        ['Гном', 'Полуорк', 'Полуэльф'],
        ['Драконорождённый', 'Сатир', 'Тифлинг'],
    ]

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if message.text == 'Случайная раса':
            return self.switch_to_state(BotStates.generators_menu, self.gm.sample_name())
        race = message.text
        if race not in self.gm.RACES:
            return self.try_again(msgs.PARSE_BUTTON_ERROR)
        self.set_user_cache(message.text)
        return self.switch_to_state(BotStates.names_generator_sex_choice)


class SexGeneratorHandler(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Кто это будет?'
    STATE = BotStates.names_generator_sex_choice

    BUTTONS = [['Мужчина', 'Женщина'], ['Ребёнок', 'Случайно']]
    SEX_MAP = {
        'Мужчина': 'male',
        'Женщина': 'female',
        'Ребёнок': 'child',
    }

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        race = self.get_user_cache()
        if message.text == 'Случайно':
            return self.switch_to_state(BotStates.generators_menu, self.gm.sample_name(race=race))
        if message.text not in self.SEX_MAP.keys():
            return self.try_again(msgs.PARSE_BUTTON_ERROR)
        sex = self.SEX_MAP[message.text]
        return self.switch_to_state(BotStates.generators_menu, self.gm.sample_name(race=race, sex=sex))


class BestiaryMenuHandler(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Здесь всё про всех монстров в ДнД.'
    STATE = BotStates.bestiary_menu

    BUTTONS = [
        ['Случайное существо', 'Найти существо'],
        ['Назад', 'В главное меню'],
    ]
    STATE_BY_MESSAGE = {
        'В главное меню': {'state': BotStates.main},
        'Назад': {'state': BotStates.generators_menu},
    }

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if message.text == 'Случайное существо':
            monster = self.bestiary.random_monster()
            self.set_user_cache(monster.name_rus)
            return self.switch_to_state(
                BotStates.bestiary_monster_info,
                monster.__str__(),
                parse_mode='HTML'
            )
        if message.text == 'Найти существо':
            return self.switch_to_state(BotStates.bestiary_enter_name)
        return self.try_again(msgs.PARSE_BUTTON_ERROR)


class BestiaryEnterNameHandler(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Наберите название существа.'
    STATE = BotStates.bestiary_enter_name
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.bestiary_menu},
    }

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        back_markup = telebot.types.ReplyKeyboardMarkup(
            resize_keyboard=True, row_width=6,
        )
        back_markup.add('Назад')
        try:
            monster = self.bestiary.get(message.text)
            self.set_user_cache(monster.name_rus)
            return self.switch_to_state(
                BotStates.bestiary_monster_info,
                monster.__str__(),
                parse_mode='HTML',
            )
        except bestiary.UnknownMonsterName:
            # then find more suggestions
            pass
        except suggester.TooManySuggestionsError:
            return self.try_again(msgs.REQUEST_TOO_BROAD, markup=back_markup)
        suggestions = self.bestiary.suggest_monsters(message.text)
        if len(suggestions) == 0:
            return self.try_again(msgs.REQUEST_NOT_FOUND, markup=back_markup)
        if len(suggestions) == 1:
            # should never happen
            monster = self.bestiary.get(suggestions[0])
            self.set_user_cache(monster.name_rus)
            return self.switch_to_state(
                BotStates.bestiary_monster_info,
                monster.__str__(),
                parse_mode='HTML',
            )
        return self.try_again(
            msgs.REQUEST_SUGGESTIONS_FOUND,
            markup=helpers.make_aligned_markup(suggestions, 3)
        )


class BestiaryMonsterInfoHandler(BaseMessageHandler):
    STATE = BotStates.bestiary_monster_info
    BUTTONS = [
        ['Прислать картинку', 'Сэмплировать атаки'],
        ['Сгенерировать лут', 'Назад'],
    ]
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.bestiary_menu},
    }

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        monster_name = self.get_user_cache()
        monster = self.bestiary.get(monster_name)
        if message.text == 'Прислать картинку':
            return self.send_photo(self.bestiary.image_filename(monster))
        if message.text == 'Сгенерировать лут':
            complexity = int(monster.challenge_number() * 4) + 6
            treasury = self.treasures.generate(complexity)
            return self.try_again(explain_treasure(treasury))
        if message.text == 'Сэмплировать атаки':
            if not monster.attacks:
                return self.try_again(msgs.BESTIARY_NO_ACTIONS)
            buttons = [a.name for a in monster.attacks]
            return self.switch_to_state(
                BotStates.bestiary_monster_attacks,
                markup=helpers.make_aligned_markup(buttons, 1)
            )


class BestiaryMonsterAttackHandler(BaseMessageHandler):
    DEFAULT_MESSAGE = 'Какую атаку сэмплировать?'
    STATE = BotStates.bestiary_monster_attacks

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        monster_name = self.get_user_cache()
        monster = self.bestiary.get(monster_name)
        attack = monster.find_attack(message.text)
        if not attack:
            return self.try_again(msgs.PARSE_BUTTON_ERROR)
        return self.switch_to_state(
            BotStates.bestiary_monster_info,
            attack.to_str(sample=True),
            parse_mode='HTML',
        )


class TreasuryHandler(BaseMessageHandler):
    STATE = BotStates.treasury_generator
    DEFAULT_MESSAGE = 'Выберите один из предложенных вариантов или введите сложность сокрощищницы числом от 1 до 100'
    BUTTONS = [
        ['Карманы прохожего', 'Склад гоблинов'],
        ['Сундук чудовища', 'Сокровищница драконов'],
        ['Легендарный клад', 'Имущество бога'],
        ['Назад'],
    ]
    COMPLEXITY_BY_NAME = {
        'Карманы прохожего': 7,
        'Склад гоблинов': 18,
        'Сундук чудовища': 30,
        'Сокровищница драконов': 50,
        'Легендарный клад': 75,
        'Имущество бога': 90,
    }
    STATE_BY_MESSAGE = {
        'Назад': {'state': BotStates.generators_menu},
    }

    def handle_message(self, message: telebot.types.Message) -> telebot.types.Message:
        if message.text.startswith('/'):
            try:
                magic_item = self.treasures.find_magic_item_by_command(message.text)
                if magic_item.image_filename is not None:
                    self.send_message(magic_item.explain())
                    return self.send_photo(magic_item.form_filename())
                else:
                    return self.try_again(magic_item.explain())
            except KeyError:
                return self.try_again(msgs.PARSE_BUTTON_ERROR)
        if message.text.isdigit():
            complexity = int(message.text)
        else:
            complexity = self.COMPLEXITY_BY_NAME.get(message.text)
            if not complexity:
                return self.try_again(msgs.PARSE_BUTTON_ERROR)
        return self.try_again(explain_treasure(self.treasures.generate(complexity)))
