import copy
import random
import re
import requests
import json
import time
import typing

import tqdm

from translate import Translator


BATCH_SIZE = 25


translator = Translator()


def _get_first_digits(line: str):
    index = 0
    for char in line:
        if not char.isdigit() and char not in './,':
            break
        index += 1
    return line[:index]


def _handle_batch(names, translations):
    translated_names = translator.translate_many(names)

    translations += [
        {
            'name': names[i],
            'name_rus': translated_names[i]
        } for i in range(len(names))
    ]
    time.sleep(1)


def create_names():
    with open('srd_5e_monsters.json') as file:
        monsters_data = json.loads(file.read())
    batch = []
    translations = []
    for monster in tqdm.tqdm(monsters_data):
        batch.append(monster['name'])
        if len(batch) >= BATCH_SIZE:
            _handle_batch(batch, translations)
            batch.clear()

    if batch:
        _handle_batch(batch, translations)
    with open('bestiary.json', 'w', encoding='utf-8') as file:
        json.dump(translations, file, indent=4, ensure_ascii=False)


class BestiaryParser:
    CHARACTERISTICS = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']

    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        raise NotImplementedError

    @classmethod
    def process_all(cls, max_count: typing.Optional[int] = None):
        with open('srd_5e_monsters.json', encoding='utf-8') as source_file:
            source = json.load(source_file)
        with open('bestiary.json', encoding='utf-8') as bestiary_file:
            bestiary = json.load(bestiary_file)
        result = []
        count = 0
        for source_monster, bestiary_monster in tqdm.tqdm(zip(source, bestiary)):
            try:
                if max_count is not None and count >= max_count:
                    result.append(bestiary_monster)
                else:
                    processed = cls.process_one(bestiary_monster, source_monster)
                    if processed is not None:
                        result.append(processed)
                    else:
                        result.append(bestiary_monster)
                count += 1
            except Exception as ex:
                name = source_monster['name']
                print(f'Failed to proceed {name} doc with exception {ex}. Skipping')
                result.append(bestiary_monster)
        with open('bestiary.json', 'w', encoding='utf-8') as file:
            json.dump(result, file, indent=4, ensure_ascii=False)


class CharacteristicsParser(BestiaryParser):
    CHARACTERISTICS = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        result = copy.deepcopy(monster_dict)
        result['characteristics'] = dict()
        for char in cls.CHARACTERISTICS:
            if result.get(char):
                result.pop(char)  # исправляем ошибки
            result['characteristics'][char] = int(source_dict[char])
        return result


class ParamsParser(BestiaryParser):
    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        result = copy.deepcopy(monster_dict)
        result['armor'] = int(_get_first_digits(source_dict['Armor Class']))
        result['challenge'] = _get_first_digits(source_dict['Challenge'])
        result['image_url'] = source_dict.get('img_url', '')
        if not source_dict.get('img_url'):
            print('No image for', source_dict['name'])
        return result


class SpeedParser(BestiaryParser):
    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        result = copy.deepcopy(monster_dict)
        speeds = source_dict['Speed']
        result['speed'] = max(map(int, re.findall(r'\d+', speeds)))
        return result


class HitsParser(BestiaryParser):
    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        result = copy.deepcopy(monster_dict)
        hits = source_dict['Hit Points']
        hit_dices = re.findall(r'\((.*)\)', hits)[0]
        result['hits'] = hit_dices
        return result


class SavingThrowsParser(BestiaryParser):
    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        result = copy.deepcopy(monster_dict)
        saving_throws = source_dict.get('Saving Throws', '')
        monster_throws = dict()
        for chr in cls.CHARACTERISTICS:
            search_result = re.findall(chr + r' .(\d+)', saving_throws)
            if search_result:
                monster_throws[chr] = int(search_result[0])
            else:
                monster_throws[chr] = monster_dict[chr] // 2 - 5
        result['saving_throws'] = monster_throws
        return result


class TraitsParser(BestiaryParser):
    MARKERS_TO_DELETE = [
        '<em>', '</em>',
        '<p>', '</p>',
        '<strong>', '</strong>',
    ]
    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        result = copy.deepcopy(monster_dict)
        if not source_dict.get('Traits'):
            return result
        source_traits = source_dict['Traits']
        traits = []
        for trait in source_traits.split('</p><p>'):
            for marker in cls.MARKERS_TO_DELETE:
                trait = re.sub(marker, '', trait)
            traits.append(trait)
        result['traits'] = traits
        return result


class TraitsTranslator(BestiaryParser):
    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        result = copy.deepcopy(monster_dict)
        traits = monster_dict.get('traits', [])
        if not traits:
            return result
        result['traits'] = translator.translate_many(traits)
        return result


class CommonReactionsParser(BestiaryParser):
    MARKERS_TO_DELETE = [
        '<em>', '</em>',
        '<p>', '</p>',
        '<strong>', '</strong>',
    ]
    SOURCE_FIELD = ''
    BESTIARY_FIELD = ''
    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        result = copy.deepcopy(monster_dict)
        if not source_dict.get(cls.SOURCE_FIELD):
            return result
        source_traits = source_dict[cls.SOURCE_FIELD]
        reactions = []
        for trait in source_traits.split('</p><p>'):
            for marker in cls.MARKERS_TO_DELETE:
                trait = re.sub(marker, '', trait)
            reactions.append(trait)
        result[cls.BESTIARY_FIELD] = translator.translate_many(reactions)
        return result


class ReactionsParser(CommonReactionsParser):
    SOURCE_FIELD = 'Reactions'
    BESTIARY_FIELD = 'reactions'


class LegendActionsParser(CommonReactionsParser):
    SOURCE_FIELD = 'Legendary Actions'
    BESTIARY_FIELD = 'legend_actions'


class ActionsParser(BestiaryParser):
    MARKERS_TO_DELETE = [
        '<em>', '</em>',
        '<p>', '</p>',
        '<strong>', '</strong>',
    ]
    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        result = copy.deepcopy(monster_dict)
        if not source_dict.get('Actions'):
            print(f'No actions for {source_dict["name"]}')
            return result
        actions = []
        for action in source_dict['Actions'].split('</p><p>'):
            for marker in cls.MARKERS_TO_DELETE:
                action = re.sub(marker, '', action)
            action_info = dict()
            attack_bonus = re.findall(r'[+-]\d+ to hit', action)
            if attack_bonus:
                attack_bonus = attack_bonus[0]
                action = action.replace(attack_bonus, '{}')
                action_info['attack_bonus'] = int(attack_bonus[:-7])
            damages = re.findall(r'\d+ \(\d+d\d+(?:| [+-] \d+)\)', action)
            action_info['damages'] = [
                re.findall(r'\((.*)\)', d)[0]
                for d in damages
            ]
            action = re.sub(r'\d+ \(\d+d\d+(?:| [+-] \d+)\)', '{}', action)
            action_info['description'] = action
            actions.append(action_info)
        result['actions'] = actions
        return result


class TranslateActions(BestiaryParser):
    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        result = copy.deepcopy(monster_dict)
        if not monster_dict.get('actions'):
            return result
        translated = translator.translate_many(
            [a['description'] for a in monster_dict['actions']]
        )
        for monster_action, translated_action in zip(result['actions'], translated):
            monster_action['description'] = translated_action
        return result


class ImageDownloader(BestiaryParser):
    @classmethod
    def process_one(
            cls,
            monster_dict: typing.Dict[str, typing.Any],
            source_dict: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        try:
            img_data = requests.get(monster_dict['image_url']).content
        except requests.exceptions.RequestException as ex:
            print(f'Failed to get image for {monster_dict["name"]}. Error: {ex}')
            return copy.deepcopy(monster_dict)
        with open('./img/' + monster_dict['name'] + '.jpg', 'wb') as file:
            file.write(img_data)
        time.sleep(random.randint(1, 4))
        return copy.deepcopy(monster_dict)


parser = ParamsParser()
parser.process_all()
