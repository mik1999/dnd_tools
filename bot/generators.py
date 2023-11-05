import dataclasses

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


RACES = ['Гном', 'Дварф', 'Драконорождённый', 'Полуорк', 'Полурослик', 'Полуэльф', 'Сатир', 'Тифлинг', 'Эльф', 'Человек']
SEXES = ['male', 'female', 'child']
SEX_TO_SEX_NAME = {
    'male': 'мужчина',
    'female': 'женщина',
    'child': 'ребёнок',
}
SEX_NAME_TO_SEX = dict(zip(SEX_TO_SEX_NAME.values(), SEX_TO_SEX_NAME.keys()))


@dataclasses.dataclass
class Person:
    race: str
    gender: str
    name: str
    show_race: bool = False
    show_gender: bool = False
    is_child: bool = False

    @property
    def full_name(self):
        result = self.name
        if self.show_gender or self.show_race:
            extra = []
            if self.show_race:
                extra.append(self.race)
            if self.show_gender:
                extra.append(SEX_TO_SEX_NAME[self.gender])
            result += ' (' + ', '.join(extra) + ')'
        return result


class GeneratorsManager:
    WILD_MAGIC_WAVES = 50

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

    def race_has_child_names(self, race: str):
        return self.names.get(race, {}).get('child') is not None

    def sample_name(
            self,
            race: typing.Optional[str] = None,
            gender: typing.Optional[str] = None,
    ):
        random_race = False
        if race is None or race not in RACES:
            if random.randint(0, 2) == 1:
                race = 'Человек'
            else:
                race = sample(RACES)
            random_race = True
        race_names = self.names[race]
        random_gender = False
        if race == 'Человек' and (gender is None or gender not in SEXES[:2]):
            gender = sample(SEXES[:2])
            random_gender = True
        elif race != 'Человек' and (gender is None or race_names.get(gender) is None):
            max_index = 1 if race_names.get('child') is None else 2
            gender = SEXES[random.randint(0, max_index)]
            random_gender = True
        full_name = self._sample_full_name(race_names, race, gender)
        gender_ = sample(SEXES[:1]) if gender == 'child' else gender
        return Person(
            race=race,
            gender=gender_,
            name=full_name,
            show_gender=random_gender,
            show_race=random_race,
            is_child=(gender == 'child'),
        )

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
        host_name = self.sample_name().full_name
        return f'Таверна "{tavern_name}"\nХозяин: {host_name}'

    def race_age_levels(self, race: str) -> typing.List[int]:
        if race not in RACES:
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
