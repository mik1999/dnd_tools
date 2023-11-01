from bot import yandex_gpt

import json
import logging
import random
import resources_manager as rm
import typing

logger = logging.getLogger()


def prepare_json():
    result = '[\n'
    with open('data/wild_magic_waves.json') as file:
        for line in file:
            result += '  \"' + line[6:-1] + '\",\n'
        result += '\n]'

    with open('data/wild_magic_waves.json', 'w') as file:
        file.write(result)


def sample(sequence):
    index = random.randint(0, len(sequence) - 1)
    return sequence[index]


class GeneratorsManager:
    WILD_MAGIC_WAVES = 50
    RACES = ['Гном', 'Дварф', 'Драконорождённый', 'Полуорк', 'Полурослик', 'Полуэльф', 'Сатир', 'Тифлинг', 'Эльф', 'Человек']
    SEXES = ['male', 'female', 'child']
    SEX_TO_SEX_NAME = {
        'male': 'мужчина',
        'female': 'женщина',
        'child': 'ребёнок',
    }
    SEX_NAME_TO_SEX = dict(zip(SEX_TO_SEX_NAME.values(), SEX_TO_SEX_NAME.keys()))

    def __init__(self, resources_manager: rm.ResourcesManager, base_path='./data'):
        with open(base_path + '/wild_magic_waves.json', encoding='utf-8') as file:
            self.wild_magic_waves = json.loads(file.read())
            if len(self.wild_magic_waves) != self.WILD_MAGIC_WAVES:
                logger.error(
                    f'Loaded unexpected number of wild magic waves: '
                    f'{self.wild_magic_waves}(got) != '
                    f'{self.WILD_MAGIC_WAVES}(expected)'
                )
        with open(base_path + '/names_by_races.json', encoding='utf-8') as file:
            self.names = json.loads(file.read())
        with open(base_path + '/taverns.json', encoding='utf-8') as file:
            self.taverns = json.loads(file.read())
            self.tavern_nouns = self.taverns["nouns"]
            self.tavern_adjs = self.taverns["adjs"]
        self.gpt = yandex_gpt.YandexGptHelper(resources_manager)

    def sample_wild_magic(self):
        return sample(self.wild_magic_waves)

    def sample_name(
            self,
            race: typing.Optional[str] = None,
            gender: typing.Optional[str] = None,
    ):
        random_race = False
        if race is None or race not in self.RACES:
            if random.randint(0, 2) == 1:
                race = 'Человек'
            else:
                race = sample(self.RACES)
            random_race = True
        race_names = self.names[race]
        random_gender = False
        if race == 'Человек' and (gender is None or gender not in self.SEXES[:2]):
            gender = sample(self.SEXES[:2])
            random_gender = True
        elif race != 'Человек' and (gender is None or race_names.get(gender) is None):
            max_index = 1 if race_names.get('child') is None else 2
            gender = self.SEXES[random.randint(0, max_index)]
            random_gender = True
        full_name = self._sample_full_name(race_names, race, gender)
        gender_rus = self.SEX_TO_SEX_NAME[gender]
        if random_race:
            return f'{full_name} ({race.lower()}, {gender_rus})'
        if random_gender:
            return f'{full_name} ({gender_rus})'
        return full_name

    def _sample_full_name(
            self,
            race_names: typing.Dict[str, typing.Any],
            race: str,
            gender: str,
    ):
        # ToDo: is_child param
        if race == 'Полуэльф':
            parent_race = 'Человек' if random.randint(0, 1) == 0 else 'Эльф'
            return self._sample_full_name(self.names[parent_race], parent_race, gender)
        if race == 'Человек':
            clan_names = sample(race_names['clans'])
            first_name = sample(clan_names[gender])
            surname = sample(clan_names['surnames'])
            return f'{first_name} {surname}, клан: {clan_names["clan"]}'
        first_name = sample(race_names[gender])
        if race == 'Гном':
            if random.randint(0, 1) == 0:
                return f'{first_name} из клана {sample(race_names["clans"])}'
            return f'{first_name} по прозвищу {sample(race_names["sobriquets"])}'
        if race == 'Дварф':
            return f'{first_name} из клана {sample(race_names["clans"])}'
        if race == 'Драконорождённый':
            clan = sample(race_names["clans"])
            if gender == 'child':
                return first_name
            return f'{clan} {first_name}'
        if race == 'Полуорк':
            return first_name
        if race == 'Полурослик':
            if random.randint(0, 2) == 2:
                surname = sample(race_names['surnames'])
                return f'{first_name} {surname}'
            return first_name
        if race == 'Сатир':
            return f'{first_name} по прозвищу {sample(race_names["sobriquets"])}'
        if race == 'Тифлинг':
            if random.randint(0, 3) == 0:
                return f'{sample(race_names["ideas"])}'
            return f'{first_name}'
        if race == 'Эльф':
            surname = sample(race_names["surnames"])
            if gender == 'child':
                return first_name
            return f'{first_name} {surname}'
        return f'{first_name}'

    def gen_tavern(self):
        adj = sample(self.tavern_adjs)
        noun = sample(self.tavern_nouns)
        adj = adj[noun['gender']]
        noun = noun['word']
        tavern_name = f'{adj} {noun}'
        host_name = self.sample_name()
        return f'Таверна "{tavern_name}"\nХозяин: {host_name}'

    def race_age_levels(self, race: str) -> typing.List[int]:
        if race not in self.RACES:
            adulthood_age = 18
            max_age = 80
        else:
            adulthood_age = self.names[race]['adulthood_age']
            max_age = self.names[race]['max_age']
        return [
            2 * adulthood_age // 3,
            adulthood_age,
            (3 * adulthood_age + max_age) // 4,
            (adulthood_age + max_age) // 2,
            (adulthood_age + max_age * 3) // 4,
            max_age,
        ]
