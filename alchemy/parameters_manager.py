import copy
import dataclasses
import json

from .consts import DEFAULT_MODS
from .parameter_processors import ParameterProcessor


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
    def __init__(self):
        parameters_json = json.load(open('parameters.json', encoding="utf-8"))
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

    def param_description(self, param_symbol, coefficient, mods=None):
        if mods is None:
            mods = copy.deepcopy(DEFAULT_MODS)
        return self.culc_functions[param_symbol](coefficient, mods)

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