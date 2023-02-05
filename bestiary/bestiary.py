import dataclasses
import json
import logging
import random
import typing
import utils.dices as dices

from utils.words_suggester import WordsSuggester, WordsSuggesterV2


logger = logging.getLogger()


class UnknownMonsterName(Exception):
    pass


@dataclasses.dataclass
class ActionInfo:
    description: str
    attack_bonus: typing.Optional[int]
    damages: typing.List[dices.DicesGenerator]


class Action(ActionInfo):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = self.action_name()

    def action_name(self):
        positions = (len(self.description), self.description.find('.'), self.description.find(':'))
        end_pos = min((p for p in positions if p != -1))
        return self.description[:end_pos]

    def to_str(self, sample: bool = False) -> str:
        attack_roll = []
        attack_bonus = self.attack_bonus
        if sample:
            d20 = 0
            if attack_bonus is not None:
                d20 = random.randint(1, 20)
                crit_info = ' <b>(Критическое попадание!)</b>' if d20 == 20 else ''
                attack_roll = [f'бросок атаки <b>{d20 + attack_bonus}</b> = {d20} + {attack_bonus} {crit_info}']
            damages = [
                f'<b>{a.sample()}</b>' + (f'(+ крит <b>{a.sample()}</b>)' if d20 == 20 else '')
                for a in self.damages
            ]
        else:
            if attack_bonus is not None:
                attack_roll = [f'{"+" if attack_bonus >= 0 else ""}{attack_bonus} к попаданию']
            damages = [a for a in self.damages]
        result = self.description.format(*attack_roll, *damages)
        return result.replace(self.action_name(), f'<b>{self.action_name()}</b>', 1)


@dataclasses.dataclass
class MonsterData:
    name: str
    name_rus: str
    characteristics: typing.Dict[str, int]
    saving_throws: typing.Dict[str, int]
    challenge: int
    armor: int
    speed: int
    hits: dices.DicesGenerator
    attacks: typing.List[Action]
    image_url: str
    traits: typing.Optional[typing.List[str]]
    reactions: typing.Optional[typing.List[str]]
    legend_actions: typing.Optional[typing.List[str]]


class Monster(MonsterData):
    CHALLENGE_MAP = {
        '0': 10,
        '1/8': 25,
        '1/4': 50,
        '1/2': 100,
        '1': 200,
        '2': 450,
        '3': 700,
        '4': 1100,
        '5': 1800,
        '6': 2300,
        '7': 2900,
        '8': 3900,
        '9': 5000,
        '10': 5900,
        '11': 7200,
        '12': 8400,
        '13': 10000,
        '14': 11500,
        '15': 13000,
        '16': 15000,
        '17': 18000,
        '18': 20000,
        '19': 22000,
        '20': 25000,
        '21': 33000,
        '22': 41000,
        '23': 50000,
        '24': 62000,
        '30': 155000,
    }

    def find_attack(self, name):
        for a in self.attacks:
            if a.name == name:
                return a
        return None

    def __str__(self):

        result = (f'       <b>{self.name_rus}</b>\n'
                  f'Опасность: {self.challenge} ({self.CHALLENGE_MAP[self.challenge]} опыта)\n'
                  f'Хиты: <b>{self.hits.mean()}</b> ({self.hits})\n'
                  f'КД: {self.armor}, скорость {self.speed} футов\n'
                  f'<pre>'
                  f'| СИЛ | ЛОВ | ТЕЛ | ИНТ | МДР | ХАР |\n'
                  f'|-----|-----|-----|-----|-----|-----|\n'
                  f'|{self.characteristics["STR"]: ^5}|{self.characteristics["DEX"]: ^5}'
                  f'|{self.characteristics["CON"]: ^5}|{self.characteristics["INT"]: ^5}'
                  f'|{self.characteristics["WIS"]: ^5}|{self.characteristics["CHA"]: ^5}|\n'
                  f'</pre>\n')
        if self.attacks:
            result += '       Действия:\n'
            for a in self.attacks:
                result += '* ' + a.to_str() + '\n'
        if self.legend_actions:
            result += '       Легендарные действия:\n'
            for trait in self.legend_actions:
                result += '* ' + trait + '\n'
        if self.traits:
            result += '       Умения:\n'
            for trait in self.traits:
                result += '* ' + trait + '\n'
        if self.reactions:
            result += '       Реакции:\n'
            for trait in self.reactions:
                result += '* ' + trait + '\n'
        return result


class Bestiary:
    def __init__(self, base_path: str = './'):
        self.base_path = base_path
        logger.info('Bestiary started opening')
        with open(self.base_path + 'bestiary.json', encoding='utf-8') as bestiary_file:
            monsters_json = json.load(bestiary_file)
            self.monsters = {
                doc['name_rus']: self._build_monster(doc)
                for doc in monsters_json
            }
            self.keys = list(self.monsters.keys())

        self.suggester = WordsSuggester([name for name in self.monsters.keys()])
        logger.info(f'Bestiary successfully loaded {len(self.monsters)} creatures')

    @staticmethod
    def _build_monster(monster_dict: typing.Dict[str, typing.Any]):
        hits = dices.DicesGenerator()
        hits.parse(monster_dict['hits'])
        actions = []
        for action in monster_dict.get('actions', []):
            actions.append(
                Action(
                    action['description'],
                    action.get('attack_bonus'),
                    [
                        dices.DicesGenerator().parse(d)
                        for d in action['damages']
                    ]
                )
            )
        return Monster(
            monster_dict['name'],
            monster_dict['name_rus'],
            monster_dict['characteristics'],
            monster_dict['saving_throws'],
            monster_dict['challenge'],
            monster_dict['armor'],
            monster_dict['speed'],
            hits,
            actions,
            monster_dict['image_url'],
            monster_dict.get('traits'),
            monster_dict.get('reactions'),
            monster_dict.get('legend_actions'),
        )

    def image_filename(self, monster: Monster):
        if __debug__:
            return self.base_path + 'img/' + monster.name + '.jpg'
        return '/data/img/' + monster.name + '.jpg'

    def suggest_monsters(self, text) -> typing.List[str]:
        return self.suggester.suggest(text, 9)

    def get(self, name) -> Monster:
        monster = self.monsters.get(name)
        if monster:
            return monster
        suggestions = self.suggester.suggest(name)
        if len(suggestions) == 1:
            return self.monsters[suggestions[0]]
        raise UnknownMonsterName

    def random_monster(self):
        index = random.randint(0, len(self.keys) - 1)
        return self.monsters[self.keys[index]]
