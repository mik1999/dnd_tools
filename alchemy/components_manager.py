import collections
import dataclasses
import enum
import json
import random
import typing

from alchemy.calculation_helper import cost_str
import alchemy.consts as consts
from alchemy.parameters_manager import ParametersManager
from utils.words_suggester import WordsSuggester, WordsSuggesterV2
from utils.dices import DicesGenerator


class UnrecognizedComponent(Exception):
    pass


class Location(enum.Enum):
    FOREST = 'Лес'
    MEADOW = 'Луг'
    UNDERGROUND = 'Подземелье'


LOCATIONS_LIST = [Location.FOREST, Location.MEADOW, Location.UNDERGROUND]


@dataclasses.dataclass
class Component(object):
    name: str
    name_en: str
    synonyms: typing.List[str]
    cost: float
    mass: float
    parameters: typing.Dict[str, float]
    rarity: int
    description: str

    organ: str = None
    cooking_time_mod: float = 1
    complexity_mod: int = 0
    only_forms: typing.Tuple[consts.PotionForm] = None
    locations: typing.Tuple[str] = tuple()

    def __post_init__(self):
        if self.only_forms is None:
            self.only_forms = tuple(consts.ALL_FORMS)
        else:
            self.only_forms = tuple(consts.PotionForm(x) for x in self.only_forms)


RARITY_NAME_MAP = {
    0: 'обычный',
    1: 'необычный',
    2: 'редкий',
    3: 'очень редкий',
}


class ComponentsManager(object):
    def __init__(self, base_path='./'):
        components_json = json.load(open(base_path + 'components.json', encoding="utf-8"))
        self.components = [Component(**component) for component in components_json]
        self.synonyms_map = dict()
        for i in range(len(self.components)):
            self.synonyms_map[self.components[i].name.lower()] = i
            self.synonyms_map[self.components[i].name_en] = i
            for word in self.components[i].synonyms:
                self.synonyms_map[word.lower()] = i
        self.suggester = WordsSuggesterV2(
            [component.name for component in self.components] +
            [component.name_en for component in self.components]
        )
        self.randomizer = ComponentsRandomizer(self.components, base_path)

    def suggest_components(self, word: str) -> typing.List[str]:
        return self.suggester.suggest(word)

    def recognize_component(self, word: str):
        index = self.synonyms_map.get(word.lower(), None)
        if index is not None:
            return self.components[index]
        raise UnrecognizedComponent

    def info(self, component_name, pm: ParametersManager) -> str:
        component = self.recognize_component(component_name)
        result = '   ' + component.name
        if component.organ:
            result += ' (' + component.organ + ')'
        result += '\n'

        result += component.description + '\n'
        result += 'Алхимические параметры:\n'
        for i, parameter_symbol in enumerate(component.parameters):
            number = component.parameters[parameter_symbol]
            parameter_name = pm.param_name(parameter_symbol, number)
            number_str = ('+' if number > 0 else '') + str(number)
            result += ' ' + str(i) + ') ' + parameter_name + ': ' + str(abs(number))
            result += '.  ([' + parameter_symbol + ']: ' + number_str + ')\n'
        result += '\n'
        result += 'В алхимических книгах также упоминается как:'
        for i, synonym in enumerate(component.synonyms):
            if i:
                result += ','
            result += ' ' + synonym
        result += '.\n'

        result += 'Средний вес одной компоненты равен ' + str(component.mass) + 'г. '
        if component.organ:
            result += 'В рецептах используется ' + component.organ + '.'
        result += '\n'
        forms = ', '.join([consts.POTION_FORMS_RUS[form] for form in component.only_forms])
        result += f'Возможные формы зелий, которые можно приготовить с этим компонентом: {forms}' \
                  f'{"(все)" if component.only_forms == consts.ALL_FORMS else ""}\n'
        if component.locations:
            result += 'Встречается в: ' + ', '.join(component.locations) + '\n'
        result += 'Редкость: ' + RARITY_NAME_MAP[component.rarity]
        result += '. Примерная стоимость : ' + cost_str(component.cost) + '.'
        return result

    def components_list(self, show_alias: bool = False,
                        show_params: bool = False,
                        show_telegram_links: bool = False,
                        ):
        result = ''
        for i, component in enumerate(self.components):
            synonyms = '' if not show_alias else ' ' + str(component.synonyms)
            params = '' if not show_params else ' ' + str(component.parameters)
            telegram_link = '' if not show_telegram_links else ' (/' + component.name_en + ')'
            result += f' {str(i + 1)}) {component.name}{telegram_link} {synonyms}{params};\n'
        return result

    def sample_component(
            self, roll_value: int, location: Location,
    ) -> typing.Tuple[typing.Optional[Component], int]:
        return self.randomizer.sample(roll_value, location)


class ComponentsRandomizer:
    def __init__(self, components: typing.List[Component], base_path='./'):
        self.location_components: typing.Dict[
            Location, typing.Dict[int, typing.List[Component]],
        ] = {loc: {r: [] for r in range(4)} for loc in LOCATIONS_LIST}
        for component in components:
            for location in component.locations:
                self.location_components[Location(location)][component.rarity].append(component)
        with open(base_path + 'rarity_points_by_roll.json', 'r') as file:
            points_info = json.load(file)
        values = points_info['loot']
        self.values: typing.Dict[
            int,
            typing.List[typing.Tuple[int, DicesGenerator]]
        ] = {}
        for rarity in values.keys():
            rarity_thresholds = []
            for threshold in values[rarity].keys():
                dice_str = values[rarity][threshold]
                dice_generator = DicesGenerator(show_only_total_=True)
                dice_generator.parse(dice_str)
                rarity_thresholds.append((int(threshold), dice_generator))
            self.values[int(rarity)] = rarity_thresholds
        self.points: typing.Dict[int, typing.Dict[int, int]] = {}
        for roll_value in points_info['roll'].keys():
            roll_dict = {}
            points_by_rarity = points_info['roll'][roll_value]
            for rarity in points_by_rarity.keys():
                points = points_by_rarity[rarity]
                roll_dict[int(rarity)] = points
            self.points[int(roll_value)] = roll_dict

    def sample(
            self, roll_value: int, location: Location,
    ) -> typing.Tuple[typing.Optional[Component], int]:
        """ returns component_name, how_much """
        roll_value = min(30, max(0, roll_value))
        rarity = self._sample_rarity(roll_value)
        if rarity is None:
            return None, 0
        appropriate_components = self.location_components[location][rarity]
        if not appropriate_components:
            return None, 0
        index = random.randint(0, len(appropriate_components) - 1)
        component = appropriate_components[index]
        thresholds = self.values[rarity]
        current_generator = None
        for threshold, generator in thresholds:
            if threshold <= roll_value:
                current_generator = generator
        count = current_generator.sample() if current_generator else 0
        return component, int(count)

    def _sample_rarity(self, roll_value: int) -> typing.Optional[int]:
        points = self.points[roll_value]
        random_points = random.randint(1, 100)
        current_sum = 0
        for rarity in range(4):
            current_sum += points[rarity]
            if current_sum >= random_points:
                return rarity
        return None
