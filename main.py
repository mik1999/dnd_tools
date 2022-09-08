import json
import typing
import dataclasses
import string
import copy
import os


class UnrecognizedComponent(Exception):
    pass


class NoSuchParameter(Exception):
    pass


class ParsingFormulaError(Exception):
    def __init__(self, message: str = 'Error while parsing potion formula'):
        self.message = message
        super().__init__(self.message)


def cost_str(cost: float):
    gold = int(cost)
    gold_str = (str(gold) + ' зм' if gold else '')
    silver = int(10 * cost) % 10
    silver_str = (str(silver) + ' см' if silver else '')
    copper = int(100 * cost) % 10
    copper_str = (str(copper) + ' мм' if copper else '')
    return gold_str + (' ' if silver_str else '') + silver_str + (' ' if copper_str else '') + copper_str


def double_average_to_dices(number: int) -> str:
    # todo: d6, d8, d10, d12, ...
    if number == 0:
        return '0'
    dices = 0
    bonus = 0
    if number % 2 == 1:
        number -= 5
        dices += 1
    dices += 2 * (number // 10)
    number %= 10
    if number <= 4:
        bonus += number // 2
    else:
        dices += 2
        bonus -= (10 - number) // 2
    if dices == 0:
        return str(bonus)
    if bonus == 0:
        return str(dices) + 'к4'
    return str(dices) + 'к4' + ('+' if bonus > 0 else '') + str(bonus)


def update_dict(d: dict, delta: dict):
    for key in delta:
        value = d.get(key, 0)
        value += delta[key]
        d[key] = value


def multiply_dict(d: dict, value: float):
    for key in d:
        d[key] *= value


COMPLEXITY_MAP = {
    1: 4,
    2: 10,
    3: 13,
    4: 16,
    5: 21,
    6: 25,
    7: 28
}


class ParameterProcessor:
    pass


# Более ранние применяются раньше
class EncapsulationProcessor(ParameterProcessor):
    parameter_symbol = 'Enc'

    @staticmethod
    def description(value: int, mods: dict):
        if value > 0:
            diff = int(mods['best_before'] * (value + 1) ** 0.5) - mods['best_before']
            mods['best_before'] += diff
            return (f'Эффект зелья начинает действовать через {value} часов после применения.'
                    f'Кроме того, срок годности увеличен на {diff} дней.')
        value *= -1
        diff = mods['best_before'] - int(mods['best_before'] * (value + 1) ** -0.5)
        mods['best_before'] -= diff
        return f'Зелье быстро выветривается: срок годности снижен на {diff} дней.'


class DurationProcessor(ParameterProcessor):
    parameter_symbol = 'Dur'

    @staticmethod
    def description(value: int, mods: dict):
        coef = (1 + value / 10) if value > 0 else 1 / (1 - value / 2)
        mods['rounds'] = int(mods['rounds'] * coef)
        mods['days'] = int(mods['days'] * coef)
        mods['hours'] = int(mods['hours'] * coef)
        if value > 0:
            return 'Увеличена длительность эффектов.'
        return 'Снижена длительность эффектов.'


class HealingProcessor(ParameterProcessor):
    parameter_symbol = 'H'

    @staticmethod
    def description(value: int, mods: dict):
        hits = double_average_to_dices(abs(value))
        if value > 0:
            return 'Живительная сила наполняет ваше тело. Вы восстанавливаете {} хитов.'.format(hits)
        return (f'Ваш организм отравлен токсинами. Каждый ход, '
                f'вплоть до {mods["rounds"]} раундов, вы делаете спасбросок телосложения СЛ 13, '
                f'и в случае провала остаетесь отравленным и теряете {hits} хитов.')


class DigestionProcessor(ParameterProcessor):
    parameter_symbol = 'D'

    @staticmethod
    def description(value: int, _: dict):
        if value > 0:
            lunches = min(3, int(((value + 2) // 3) ** 0.5))
            return 'Вы чувствуете насыщение, как будто пообедали {} раз(а).'.format(lunches)
        charm = abs(value) // 2 + 1
        return ('Кажется, у вас несварение. Повышенный метеоризм '
                'проявляется постоянно и неконтролируемо. На 1к6 часов у вас помеха к спасброскам '
                'телосложения и -{} к харизме, так как с вами никто не хочет даже рядом стоять.'.format(charm)
                )


class PressureProcessor(ParameterProcessor):
    parameter_symbol = 'P'

    @staticmethod
    def description(value: int, _: dict):
        result = ''
        if value > 0:
            result += 'Ваша голова начинает сильно болеть: вены пульсируют, черепушка словно вот-вот расколется.'
        else:
            result += 'Ваше лицо заметно побледнело, вы наблюдаете сильное головокружение.'
        value = abs(value)
        wisdom = value // 3 + 1
        result += f' На 1к4 часов значение вашей мудрости снижено на {wisdom}.'
        if value >= 7:
            result += f' Кроме того, вы получаете психический уров, равный {double_average_to_dices(value - 5)} хитов.'
        if value >= 10:
            result += f' Наконец, сильное нарушение давления добавляет вам 1 степень истощения.'
        return result


class AddictiveProcessor(ParameterProcessor):
    parameter_symbol = 'Add'

    @staticmethod
    def description(value: int, mods: dict):
        if value > 0:
            return (f'Принимая это вещество, вы чувствуете кратковременную эйфорию, но каждый день без приема '
                    f'такого же вещества вы будете испытывать ломки. У вас помеха к проверкам характеристик: '
                    f'ловкость, мудрость и харизма, если сегодня вы еще не принимали это вещество. Каждое утро, '
                    f'следующее за днем без приема дозы, приносит {double_average_to_dices(value)} психического '
                    f'урона. Кроме того, каждый день вы можете сделать проверку Харизмы Сл {8 + value}, и в '
                    f'случае успеха вы избавляетесь от зависимости.')
        return (f'От этой смеси исходить жуткая фонь на {-value * 10} футов, прием ее внутрь заставляет вас '
                f'передергиваться от отвращения. Кроме того, данная субстанция выпитая или разбитая рядом '
                f'дает вам проверку на любые броски, связанные с обонянием, на {mods["rounds"]} раундов.')


class AgilityProcessor(ParameterProcessor):
    parameter_symbol = 'Ag'

    @staticmethod
    def description(value: int, mods: dict):
        if value > 0:
            agility = (value + 1) // 2
            speed = ((value + 2) // 3) * 5
            return (f'Скорость ваших движений возрастает. Вы получаете +{agility} к ловкости и'
                    f'+{speed} футов к скорости передвижения на {mods["rounds"]} раундов.')

        return (f'Ваша скорость заметно снижается, в голове словно туман. У вас -{-value // 3 + 1} '
                f'к ловкости, -{(-value // 3 + 1) * 5} футов скорости и -{(-value + 1) // 2 } '
                f'к мудрости на {mods["rounds"]} раундов.')


class InvisibilityProcessor(ParameterProcessor):
    parameter_symbol = 'Inv'

    @staticmethod
    def description(value: int, mods: dict):
        if value > 0:
            return f'Вы становитесь невидимым на {value * 10} минут.'
        return (f'На {mods["rounds"]} раундов от вас исходит свет: яркий в радиусе {value * 10} футов '
                f'и тусклый в радиусе {value * 20} футов. У врагов преимущество на броски атаки по вам,'
                f'так как им прекрасно видны ваши движения и местоположение.')


class AllergyProcessor(ParameterProcessor):
    parameter_symbol = 'All'

    @staticmethod
    def description(value: int, mods: dict):
        if value > 0:
            result = f'У вас начинает чесаться тело: помеха к ловкости на {mods["hours"]} часов.'
            if value >= 3:
                result += f'Из-за насморка вы теряете обоняние: у вас помеха на все боски, связанные с этим чувством.'
            if value >= 5:
                result += (f'Сильная аллергическая реакция вызывает анафилактический шок. Вы теряете '
                           f'{double_average_to_dices(10 * value)} хитов, вплоть до вашего текущего значения хитов,'
                           f'и получаете 2 степени истощения.')
        return (f'Иммунитет к аллергическим реакциям, не вызванным приемом зелий, на {-value} часов. '
                f'Теперь вы можете гладить котиков, не чихая :)')


class StrengthProcessor(ParameterProcessor):
    parameter_symbol = 'S'

    @staticmethod
    def description(value: int, mods: dict):
        if value > 0:
            return (f'Ваше тело наполняется силой и жизненной энергией на {mods["rounds"]} часов: вы получаете'
                    f'+{value // 2 + 1} к силе и {double_average_to_dices(value)} временных хитов, но от непривычки'
                    f'у вас -{value // 3 + 1} к ловкости. ')
        return f'Силы покидают ваше тело. Вы получаете {int((-value) ** 0.5)} уровней истощения.'


class GlitchesProcessor(ParameterProcessor):
    parameter_symbol = 'G'

    @staticmethod
    def description(value: int, mods: dict):
        if value > 0:
            int_bonus = value // 2 + 1
            wisdom = value
            rounds = mods['rounds']
            hours = mods['hours']
            return (
                'Ваши мысли улетают в волшебные дали, полные невообразимых существ и невозможных пейзажей. '
                'На {} раундов у вас +{} и интеллекту, но на {} часов вы получаете -{} к мудрости из-за потери связи с'
                ' реальным миром, а также помехи к атаке и спасброскам силы и '
                'ловкости.'.format(rounds, int_bonus, hours, wisdom)
            )
        return (f'У вас внезапно получается отлично сконцентрироваться. На {-value} '
                f'раундов у вас сопротивление психическому урону и преимущество к '
                f'спасброскам телосложения, которыми вы проверяете сохранение концентрации на заклинаниях.'
                )


@dataclasses.dataclass
class OneSideParameter:
    name_rus: str
    cost_coefficient: str

    reverse_benefit: bool = False


@dataclasses.dataclass
class Parameter:
    name: str
    symbol: str
    positive: OneSideParameter
    negative: OneSideParameter


class ParametersManager(object):
    def __init__(self):
        parameters_json = json.load(open('parameters.json', encoding="utf-8"))
        self.parameters = dict()
        for parameter in parameters_json:
            symbol = parameter['symbol']
            param_new = Parameter(
                name=parameter['name'],
                symbol=symbol,
                positive=OneSideParameter(**parameter['positive']),
                negative=OneSideParameter(**parameter['negative']),
            )
            self.parameters.update({symbol: param_new})

    def get_param(self, symbol: str):
        result = self.parameters.get(symbol, None)
        if result:
            return result
        raise NoSuchParameter

    def param_name(self, symbol: str, value: float):
        parameter = self.parameters[symbol]
        if parameter:
            if value > 0:
                return parameter.positive.name_rus
            return parameter.negative.name_rus
        return 'error-parameter'

    def parameters_list(self):
        processors = []
        for subclass in ParameterProcessor.__subclasses__():
            symbol = subclass.parameter_symbol
            processors.append(symbol)
            if not self.parameters.get(symbol):
                print(f'Внимание! Установлен процессор для ({symbol}), но такого параметра нет в parameters.json.')
        result = ''
        for i, parameter_symbol in enumerate(self.parameters):
            parameter = self.parameters[parameter_symbol]
            result += (f' {str(i + 1)}) {parameter.name} ({parameter_symbol}): {parameter.positive.name_rus} / '
                       f'{parameter.negative.name_rus};')
            if parameter_symbol not in processors:
                result += '[ Не выставлен процессор! ]'
            result += '\n'
        return result


POTION_FORMS = {'зелье', 'мазь', 'взрывное зелье', 'порошок', 'благовония'}


@dataclasses.dataclass
class Component(object):
    name: str
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
    def __init__(self):
        components_json = json.load(open('components.json', encoding="utf-8"))
        self.components = [Component(**component) for component in components_json]
        self.synonyms_map = dict()
        for i in range(len(self.components)):
            self.synonyms_map[self.components[i].name.lower()] = i
            for word in self.components[i].synonyms:
                self.synonyms_map[word.lower()] = i

    def recognize_component(self, word: string):
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

    def components_list(self):
        result = ''
        for i, component in enumerate(self.components):
            result += f' {str(i + 1)}) {component.name} {str(component.synonyms)};\n'
        return result


class Potion(object):
    def __init__(self, cm: ComponentsManager, pm: ParametersManager):
        self.parameters_vector = dict()
        self.formula = dict()
        self.possible_forms = POTION_FORMS
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

    def write(self, force_flag: bool):
        if not self.name:
            raise RuntimeError('Для сохранения зелья нужно сначала задать его название')
        filename = 'potions/' + self.name + '.json'
        if (not force_flag) and os.path.exists(filename):
            raise FileExistsError(f'Файл с названием {filename} уже существует')
        dict_repr = copy.deepcopy(self.formula)
        dict_repr.update({'__name': self.name})
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(str(dict_repr))

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
        for fnt in os.walk('potions/'):
            for i, fn in enumerate(fnt[2]):
                path = 'potion/' + fn
                potion = Potion(cm, pm)
                potion.read(fn[:-5])
                result += f'  {i + 1}) {potion.name}\n'
        return result

    def mix_from(self, formula: str):
        self.parse_formula(formula)
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
            multiply_dict(component_param, coefficient)
            update_dict(sum_vector, component_param)
            total_number += coefficient
        for parameter_symbol in sum_vector:
            param_value = int(sum_vector[parameter_symbol] / total_number)
            if param_value != 0:
                self.parameters_vector[parameter_symbol] = param_value

    def calculate_characteristics(self):
        self.complexity = COMPLEXITY_MAP[len(self.formula)]
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
        for parameter_symbol in self.parameters_vector:
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

    def parse_formula(self, formula: str):
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
            try:
                component = self.cm.recognize_component(fragment)
            except UnrecognizedComponent:
                raise ParsingFormulaError(f'Не получается распознать компонент \'{fragment}\' - '
                                          f'это не название какого-либо компонента и не синоним.')
            if self.formula.get(component.name):
                raise ParsingFormulaError(f'Компонент \'{component.name}\' использован дважды, второй раз в \'{fragment}\'.')
            self.formula[component.name] = coefficient

    def parameters_description(self):
        if self.empty:
            return 'Empty potion'
        if not self.parameters_vector:
            return 'Компоненты данного зелья нейтрализовали друг друга, поэтому никакого эффекта оно не дает.'
        description = 'Похоже, что получившаясся субстанция обладает следующими свойствами:\n'
        mods = {
            'days': 5,
            'hours': 6,
            'rounds': 4,
            'best_before': self.best_before
        }
        counter = 1
        for subclass in ParameterProcessor.__subclasses__():
            if subclass.parameter_symbol in self.parameters_vector.keys():
                coefficient = self.parameters_vector[subclass.parameter_symbol]
                rus_name = self.pm.param_name(subclass.parameter_symbol, coefficient)
                description += ' ' + str(counter) + f') {rus_name}. ' + subclass.description(coefficient, mods) + '\n'
                counter += 1
        self.best_before = mods['best_before']
        return description

    def overall_description(self):
        if self.empty:
            return 'Empty potion'
        result = f'У вас получилось: {self.market_type} {str(self.name) if self.name else ""}.\n'
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
        result += self.parameters_description()
        if self.portions > 0:
            if self.cost == 0:
                result += (f'Эта бурда ничего не стоит, хотя приготовление одной порции тратит ингридиентов '
                           f'на {cost_str(self.components_cost)}.\n')
            elif self.cost > self.components_cost:
                result += (f'Примерная цена порции равна {cost_str(self.cost)}. '
                           f'Суммарная цена компонент на одну порцию: {cost_str(self.components_cost)} '
                           f'(прибыль {cost_str(self.cost - self.components_cost)}). \n')
            else:
                result += (f'Рыночная стоимость пользы (или токсичности) порции равна {cost_str(self.cost)}, '
                           f'что меньше стоимости компонент на одну порцию ({cost_str(self.components_cost)}), '
                           f'поэтому такую субстанцию можно только продать, но не купить.\n')
        result += 'Рецепт: ' + ', '.join([str(self.formula[i]) + ' ' + i for i in self.formula]) + '\n'
        result += f'Срок годности составляет {self.best_before} дней.'
        return result


HELLO_MSG = '\nДобро пожаловать в зельеварку! Что будем готовить?'
HELP_MSG = '''Доступные команды:
помощь (h, help) - выводит это сообщение.
помощь (h, help) <название команды> - подробнее о команде.
компоненты (комп, c, components) список (l, list) [-s -e - todo] - перечислить все компоненты.
компоненты (комп, c, components) описание (d, description) <название компоненты> - 
  описание компоненты.
параметры (парам, parameters) список (l, list) - перечислить все параметры.
готовить (mix, cook) <формула = список компонент> - приготовить зелье из введенных компонент.
  Для подробностей напишите "помощь готовить".
зелья (p, potion) сохранить (s, save) [-f] <название> - сохранить последнее приготовленное зелье.
зелья (p, potion) описание (d, description) <название зелья> - описание ранее созданного и сохраненного зелья.
зелья (p, potion) список (l, list) - перечислить все сохраненные зелья.
выход (exit) - выйти из программы'''
HELP_COMP_LIST_MSG = '''Перечислить все компоненты
Использование: компоненты (комп, c, components) список (l, list)'''
HELP_COMP_DESCR_MSG = '''Описание компоненты
Использование: компоненты (комп, c, components) описание (d, description) <название компоненты>
Пример: комп описание ястребинка шепчущая
Кстати, компоненты перечислены в файле components.json, и добавление новой не требует написания кода'''
HELP_PARAM_LIST_MSG = '''Перечислить все параметры
Использование: параметры (парам, parameters) список (l, list) '''
HELP_MIX_MSG = '''Приготовление зелья
Использование: готовить (mix, cook) <формула>
Примеры формул: 8 Ястребинка Шепчушая, 4 Зверобой, Растение Харрады
То же самое: 8 * Ястребинка Шепчушая + 4 * Зверобой + 1 * Растение Харрады
Можно использовать короткие названия компонент: 8 ястребинка, 4 зверобой, харрада'''
HELP_POT_SAVE_MSG = '''Сохранение последнего приготовленного зелья
Использование: зелья (p, potion) сохранить (s, save) [-f] <название>
Опциональный флаг -f перезаписывает уже существующее зелье с таким названием
Примеры: зелья сохранить Тиравин
Перезапись: зелья сохранить -f Тиравин'''
HELP_POT_DESCR_MSG = '''Описание ранее созданного и сохраненного зелья
Использование: зелья (p, potion) описание (s, save) <название зелья>
Пример: зелья описание Тиравин'''
HELP_POT_LIST_MSG = '''Перечислить все сохраненные зелья
Использование: зелья (p, potion)  список (l, list) '''
HELP_EXIT_MSG = 'Выход из программы: написать "выход" (или exit)'

def run():
    cm = ComponentsManager()
    pm = ParametersManager()
    last_potion = None
    print(HELP_MSG)
    while True:
        print(HELLO_MSG)
        command = input()
        words_w_e = command.strip().split()
        words = []
        for word in words_w_e:
            if word != '':
                words.append(word)
        if not words:
            continue
        if words[0] in {'h', 'help', 'помощь'}:
            if len(words) > 1:
                if words[1] in ['компоненты', 'комп', 'c', 'components', 'компонента', 'component']:
                    if len(words) > 2:
                        if words[2] in ['список', 'l', 'list']:
                            print(HELP_COMP_LIST_MSG)
                        elif words[2] in ['описание', 'd', 'description']:
                            print(HELP_COMP_DESCR_MSG)
                        else:
                            print(HELP_COMP_LIST_MSG + '\n' + HELP_COMP_DESCR_MSG)
                    else:
                        print(HELP_COMP_LIST_MSG + '\n' + HELP_COMP_DESCR_MSG)
                elif words[1] in ['параметры', 'парам', 'parameters', 'parameter', 'параметр', 'param']:
                    print(HELP_PARAM_LIST_MSG)
                elif words[1] in ['готовить', 'mix', 'cook']:
                    print(HELP_MIX_MSG)
                elif words[1] in ['exit', 'выход']:
                    print(HELP_EXIT_MSG)
                elif words[1] in ['зелье', 'potion', 'p']:
                    if len(words) > 2 and words[2] in ['сохранить', 's', 'save']:
                        print(HELP_POT_SAVE_MSG)
                    elif len(words) > 2 and words[2] in ['описание', 'd', 'description', 'read', 'load']:
                        print(HELP_POT_DESCR_MSG)
                    elif len(words) > 2 and words[2] in ['list', 'l', 'список']:
                        print(HELP_POT_DESCR_MSG)
                    else:
                        print(HELP_POT_SAVE_MSG + '\n' + HELP_POT_DESCR_MSG)
                else:
                    print(HELP_MSG)
            else:
                print(HELP_MSG)
        elif words[0] in {'компоненты', 'компонента', 'component',  'комп', 'c', 'components'}:
            if len(words) <= 1:
                print(f'команда {words[0]} требует подкоманды (список или описание)')
                continue
            if words[1] in {'список', 'l', 'list'}:
                print(cm.components_list())
            elif words[1] in {'описание', 'd', 'description'}:
                if len(words) < 3:
                    print('Для использования этой команды также надо вводить название компоненты.')
                    continue
                component_name = ' '.join(words[2:])
                try:
                    print(cm.info(component_name, pm))
                except UnrecognizedComponent:
                    print(f'Компонента {component_name} не найдена. Проверьте правильность введенного названия.')
                    continue
            else:
                print(f'Не удается распознать подкоманду {words[1]}.')
                continue
        elif words[0] in ['параметры', 'парам', 'parameters', 'parameter', 'параметр', 'param']:
            if len(words) < 2 or words[1] not in ['список', 'l', 'list']:
                print(f'Не удается распознать подкоманду {" ".join(words[1:])}')
                continue
            else:
                print(pm.parameters_list())
        elif words[0] in {'готовить', 'mix', 'cook', 'готовка'}:
            formula = ' '.join(words[1:])
            if not formula:
                print('Формула зелья не может быть пустой.')
                continue
            potion = Potion(cm, pm)
            try:
                potion.mix_from(formula)
                last_potion = potion
                print(potion.overall_description())
            except ParsingFormulaError as ex:
                print('Ошибка чтения введенного рецепта: ' + ex.message)
        elif words[0] in {'зелья', 'potion', 'зелье', 'p'}:
            if len(words) > 1 and words[1] in {'сохранить', 'save'}:
                force_flag = False
                if last_potion is None:
                    print('Сначала сварите какое-то зелье')
                    continue
                if len(words) < 3 or (words[2] == '-f' and len(words) < 4):
                    print('Не введено название зелья. Попробуйте еще раз.')
                    continue
                if words[2] == '-f':
                    force_flag = True
                    potion_name = ' '.join(words[3:])
                else:
                    potion_name = ' '.join(words[2:])
                try:
                    last_potion.name = potion_name
                    last_potion.write(force_flag)
                    print('Зелье успешно сохранено')
                except FileExistsError:
                    print('Зелье с таким названием уже существует. Используйте флаг -f чтобы перезаписать')
            elif len(words) > 1 and words[1] in {'описание', 'd', 'description', 'load', 'read'}:
                if len(words) < 3:
                    print('Название зелья не введено')
                    continue
                potion_name = ' '.join(words[2:])
                try:
                    potion = Potion(cm, pm)
                    potion.read(potion_name)
                    print(potion.overall_description())
                except FileNotFoundError:
                    print(f'Зелья с названием "{potion_name}" не существует. Проверьте правильность написания.')
            elif len(words) > 1 and words[1] in {'список', 'l', 'list'}:
                print(Potion.potions_list(cm, pm))
            else:
                print(f'Подкомада {words[1]} не распознана.')
        elif words[0] in {'выход', 'exit'}:
            print('До свидания!')
            break
        else:
            print('Команда не распознана. Введите "помощь" для просмотра списка команд.')


if __name__ == '__main__':
    run()
