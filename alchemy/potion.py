import json
import string
import copy
import os
import typing

from . import calculation_helper as calcs
from . import consts
from .parameters_manager import ParametersManager
from .parameter_processors import ParameterProcessor
from .components_manager import ComponentsManager, UnrecognizedComponent


class ParsingFormulaError(Exception):
    def __init__(self, message: str = 'Error while parsing potion formula'):
        self.message = message
        super().__init__(self.message)


class Potion(object):
    def __init__(self, cm: ComponentsManager, pm: ParametersManager):
        self.parameters_vector = dict()
        self.formula = dict()
        self.possible_forms = consts.POTION_FORMS
        self.name = ''
        self.cm = cm
        self.pm = pm
        self.empty = True
        self.mass = 0
        self.cost = 0
        self.components_cost = 0
        self.cooking_time = 10
        self.portions = None
        self.market_type = None
        self.complexity = None
        self.best_before = 12
        self.marks = []

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        result = copy.deepcopy(self.formula)
        result.update({'__name': self.name})
        return result

    def write(self, force_flag: bool):
        if not self.name:
            raise RuntimeError('Для сохранения зелья нужно сначала задать его название')
        filename = 'potions/' + self.name + '.json'
        if (not force_flag) and os.path.exists(filename):
            raise FileExistsError(f'Файл с названием {filename} уже существует')
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(str(self.to_dict()))

    def from_dict(self, dict_repr):
        dict_repr = copy.deepcopy(dict_repr)
        self.name = dict_repr['__name']
        dict_repr.pop('__name')
        self.formula = dict_repr

        self.calculate_parameters()
        self.calculate_characteristics()
        self.empty = False

    def read(self, potion_name):
        if not self.empty:
            raise RuntimeError('Нельзя читать из файла непустое зелье')
        filename = 'potions/' + potion_name + '.json'
        if not os.path.exists(filename):
            raise FileNotFoundError(f'Файл с названием {filename} не существует.'
                                    f' Проверьте правильно ли введено название')
        with open(filename, 'r', encoding='utf-8') as f:
            self.formula = json.loads(f.read().replace("'", "\""))
            self.name = self.formula['__name']
            self.formula.pop('__name')
        self.calculate_parameters()
        self.calculate_characteristics()
        self.empty = False

    @staticmethod
    def potions_list(cm: ComponentsManager, pm: ParametersManager):
        result = ''
        for fnt in os.walk('console/potions/'):
            for i, fn in enumerate(fnt[2]):
                potion = Potion(cm, pm)
                potion.read(fn[:-5])
                result += f'  {i + 1}) {potion.name}\n'
        return result[:-1]  # erase line end

    def mix_from(self, formula: str, use_suggestions=False):
        self.parse_formula(formula, use_suggestions)
        self.calculate_parameters()
        self.calculate_characteristics()
        self.empty = False

    def calculate_parameters(self):
        total_number = 0
        sum_vector = dict()
        for component_name in self.formula:
            component = self.cm.recognize_component(component_name)
            coefficient = self.formula[component_name]
            component_param = copy.deepcopy(component.parameters)
            calcs.multiply_dict(component_param, coefficient)
            calcs.update_dict(sum_vector, component_param)
            total_number += coefficient
        for parameter_symbol in sum_vector:
            param_value = int(sum_vector[parameter_symbol] / total_number)
            if param_value != 0:
                self.parameters_vector[parameter_symbol] = param_value

    def calculate_characteristics(self):
        self.complexity = consts.COMPLEXITY_MAP[len(self.formula)]
        for component_name in self.formula:
            component = self.cm.recognize_component(component_name)
            coef = self.formula[component_name]
            self.mass += coef * component.mass
            self.components_cost += component.cost * coef
            self.cooking_time *= component.cooking_time_mod
            self.complexity += component.complexity_mod
            self.possible_forms &= set(component.only_forms)
        self.cooking_time = int(self.cooking_time) + 20
        self.portions = self.mass // 100
        if self.portions > 0:
            self.components_cost /= self.portions

        positive_cost = 0
        negative_cost = 0
        # the right classes order
        for subclass in ParameterProcessor.__subclasses__():
            parameter_symbol = subclass.parameter_symbol
            if parameter_symbol not in self.parameters_vector:
                continue
            parameter = self.pm.get_param(parameter_symbol)
            coef = self.parameters_vector[parameter_symbol]
            if coef > 0:
                if parameter.positive.reverse_benefit:
                    negative_cost += parameter.positive.cost_coefficient * coef
                else:
                    positive_cost += parameter.positive.cost_coefficient * coef
            else:
                if parameter.negative.reverse_benefit:
                    positive_cost += parameter.negative.cost_coefficient * (-coef)
                else:
                    negative_cost += parameter.negative.cost_coefficient * (-coef)
        if positive_cost > 2 * negative_cost:
            self.cost = positive_cost - 2 * negative_cost
            self.market_type = 'эликсир'
        elif negative_cost > 2 * positive_cost:
            self.cost = 2 * negative_cost - positive_cost
            self.market_type = 'яд'
        else:
            self.market_type = 'бурда'

    def parse_formula(self, formula: str, use_suggestions=False):
        comp_set_old = {formula}
        comp_set = set()
        for delimiter in ',+':
            for fragment in comp_set_old:
                comp_set |= set(fragment.split(delimiter))
            comp_set_old = comp_set
            comp_set = set()
        for fragment in comp_set_old:
            fragment = fragment.strip()
            i = 0
            while i < len(fragment) and fragment[i] in (string.digits + ' '):
                i += 1
            coef_frag = fragment[:i].strip()
            if coef_frag == '':
                coefficient = 1
            else:
                try:
                    coefficient = int(coef_frag)
                except ValueError:
                    raise ParsingFormulaError(f'Непонятный коэффициент {coef_frag} в терме {fragment}.')
            if fragment[i] in '*-':
                i += 1
            fragment = fragment[i:].strip()
            component = self.get_component(fragment, use_suggestions)
            if self.formula.get(component.name):
                raise ParsingFormulaError(
                    f'Компонент \'{component.name}\' использован дважды, второй раз в \'{fragment}\'.',
                )
            self.formula[component.name] = coefficient

    def get_component(self, name: str, use_suggestions: bool):
        if use_suggestions:
            suggestions = self.cm.suggest_components(name)
            if not suggestions:
                raise ParsingFormulaError(
                    f'Не получается распознать компонент \'{name}\'',
                )
            suggestion = suggestions[0]
            component = self.cm.recognize_component(suggestion)
            if component.name != name and component.name_en != name:
                self.marks.append((name, suggestion))
            return component
        try:
            return self.cm.recognize_component(name)
        except UnrecognizedComponent:
            raise ParsingFormulaError(f'Не получается распознать компонент \'{name}\' - '
                                      f'это не название какого-либо компонента и не синоним.')

    def parameters_description(self, sample=False):
        if self.empty:
            return 'Empty potion'
        if not self.parameters_vector:
            return 'Компоненты данного зелья нейтрализовали друг друга, поэтому никакого эффекта оно не дает.'
        description = 'Похоже, что получившаясся субстанция обладает следующими свойствами:\n'
        mods = copy.deepcopy(consts.DEFAULT_MODS)
        mods['best_before'] = self.best_before
        counter = 1
        # the right classes order
        for subclass in ParameterProcessor.__subclasses__():
            parameter_symbol = subclass.parameter_symbol
            if parameter_symbol not in self.parameters_vector:
                continue
            coefficient = self.parameters_vector[parameter_symbol]
            rus_name = self.pm.param_name(parameter_symbol, coefficient)
            param_description = self.pm.param_description(parameter_symbol, coefficient, mods, sample=sample)
            description += ' ' + str(counter) + f') {rus_name}. ' + param_description + '\n'
            counter += 1
        self.best_before = mods['best_before']
        return description

    def overall_description(self, sample=False):
        if self.empty:
            return 'Empty potion'
        result = ''
        if self.marks:
            result += 'Интерпетирую ' + ', '.join(f'{name} как {suggestion}' for name, suggestion in self.marks) + '\n'
        result += f'У вас получилось: {self.market_type}{" " + str(self.name) if self.name else ""}.\n'
        result += 'Вектор параметров: ' + str(self.parameters_vector) + '\n'
        if self.portions == 0:
            result += (f'Общей массы компонент ({self.mass} г.) не хватает для приготавления даже одной порции. '
                       f'На одну порцию необходимо 100 г. веществ.\n'
                       )
        else:
            result += f'Кол-во порций: {self.portions} (всего {self.mass} г.)\n'
        if self.possible_forms:
            forms = ', '.join([str(form) for form in self.possible_forms])
            result += f'Возможные формы результата: {forms}.\n'
        else:
            result += (f'Невозможно приготовить это зелье, так как нет ни одной доступной формы. '
                      f'Чтобы конкретная форма была доступна, нужно, '
                      f'чтобы все компоненты содержали ее в списке возможных форм.\n')
        result += (f'Сложность приготовления: {self.complexity} (бросок к20 с инструментами алхимика). '
                   f'Время приготовления равно {self.cooking_time} мин.\n')
        result += self.parameters_description(sample=sample)
        if self.portions > 0:
            if self.cost == 0:
                result += (f'Эта бурда ничего не стоит, хотя приготовление одной порции тратит ингридиентов '
                           f'на {calcs.cost_str(self.components_cost)}.\n')
            elif self.cost > self.components_cost:
                result += (f'Примерная цена порции равна {calcs.cost_str(self.cost)}. '
                           f'Суммарная цена компонент на одну порцию: {calcs.cost_str(self.components_cost)} '
                           f'(прибыль {calcs.cost_str(self.cost - self.components_cost)}). \n')
            else:
                result += (f'Рыночная стоимость пользы (или токсичности) порции равна {calcs.cost_str(self.cost)}, '
                           f'что меньше стоимости компонент на одну порцию ({calcs.cost_str(self.components_cost)}), '
                           f'поэтому такую субстанцию можно только продать, но не купить.\n')
        result += 'Рецепт: ' + ', '.join([str(self.formula[i]) + ' ' + i for i in self.formula]) + '\n'
        result += f'Срок годности составляет {self.best_before} дней.'
        return result
