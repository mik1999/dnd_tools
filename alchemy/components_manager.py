import dataclasses
import json
import typing

from alchemy.calculation_helper import cost_str
from alchemy.consts import POTION_FORMS
from alchemy.parameters_manager import ParametersManager
from utils.words_suggester import WordsSuggester


class UnrecognizedComponent(Exception):
    pass


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
    only_forms: typing.Tuple[str] = tuple(POTION_FORMS)


RARITY_NAME_MAP = {
    0: 'обычный',
    1: 'необычный',
    2: 'редкий',
    3: 'очень редкий',
}


class ComponentsManager(object):
    def __init__(self, parameters_json_path='components.json'):
        components_json = json.load(open(parameters_json_path, encoding="utf-8"))
        self.components = [Component(**component) for component in components_json]
        self.synonyms_map = dict()
        for i in range(len(self.components)):
            self.synonyms_map[self.components[i].name.lower()] = i
            self.synonyms_map[self.components[i].name_en] = i
            for word in self.components[i].synonyms:
                self.synonyms_map[word.lower()] = i
        self.suggester = WordsSuggester(
            [component.name for component in self.components] +
            [component.name_en for component in self.components]
        )

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
        forms = ', '.join([str(form) for form in component.only_forms])
        result += f'Возможные формы зелий, которые можно приготовить с этим компонентом: {forms}' \
                  f'{"(все)" if component.only_forms == POTION_FORMS else ""}\n'

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
