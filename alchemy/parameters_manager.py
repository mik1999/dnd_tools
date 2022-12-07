import copy
import dataclasses
import json

from alchemy.consts import DEFAULT_MODS
from alchemy.parameter_processors import ParameterProcessor


class NoSuchParameter(Exception):
    pass


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
    def __init__(self, parameters_json_path='parameters.json'):
        parameters_json = json.load(open(parameters_json_path, encoding="utf-8"))
        self.parameters = dict()
        self.culc_functions = dict()
        self._prepare_param_culc()
        for parameter in parameters_json:
            symbol = parameter['symbol']
            param_new = Parameter(
                name=parameter['name'],
                symbol=symbol,
                positive=OneSideParameter(**parameter['positive']),
                negative=OneSideParameter(**parameter['negative']),
            )
            self.parameters.update({symbol: param_new})

    def _prepare_param_culc(self):
        for subclass in ParameterProcessor.__subclasses__():
            self.culc_functions.update(
                {subclass.parameter_symbol: subclass.description}
            )

    def param_description(self, param_symbol, coefficient, mods=None, sample=False):
        if mods is None:
            mods = copy.deepcopy(DEFAULT_MODS)
        return self.culc_functions[param_symbol](coefficient, mods, sample=sample)

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

    def parameter_symbols(self):
        return [
            subclass.parameter_symbol
            for subclass in ParameterProcessor.__subclasses__()
        ]

    def parameter_brief(self, symbol: str):
        parameter = self.get_param(symbol)
        return (f'{parameter.name} ({parameter.symbol})\n'
                f'Эффект параметра с положительным коэффициентом: {parameter.positive.name_rus}\n'
                f'Эффект параметра с отрицательным коэффициентом: {parameter.negative.name_rus}')

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
