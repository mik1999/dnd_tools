import dataclasses
import random
import string
import typing
import re


class ParseDiceFormulaError(Exception):
    pass


class EmptyFormulaError(Exception):
    pass


class IncorrectSymbolsError(Exception):
    pass


class ComplexityError(Exception):
    pass


@dataclasses.dataclass
class DiceEvent:
    dice_type: int = 0
    dices_number: int = 0
    sign: int = 1
    bies: int = 0


class DicesGenerator:
    SYMBOLS_ALLOWED = set('dDкК-+' + string.digits)
    USUAL_DICES = [4, 6, 8, 10, 12, 20, 100]

    def __init__(self):
        self.events: typing.List[DiceEvent] = []
        self.warning_dices = []
        self.parent_string: typing.Optional[str] = None

    @staticmethod
    def check_symbols(formula):
        return not (set(formula) - DicesGenerator.SYMBOLS_ALLOWED)

    def parse(self, formula: str):
        self.parent_string = formula
        if len(formula) > 300:
            raise ComplexityError()
        self.warning_dices = []
        formula = ''.join(formula.split())
        if formula == '':
            raise EmptyFormulaError()

        if not self.check_symbols(formula):
            raise IncorrectSymbolsError()

        def handle_fragment(term, sign):
            parts = re.split('к|К|d|D', term)
            if len(parts) == 1:
                if not parts[0].isdigit():
                    raise ParseDiceFormulaError
                self.events.append(DiceEvent(bies=int(parts[0]), sign=sign))
            elif len(parts) == 2:
                if not parts[0]:
                    parts[0] = '1'
                if not parts[0].isdigit() or not parts[1].isdigit():
                    raise ParseDiceFormulaError
                dices_number = int(parts[0])
                if dices_number > 2000:
                    raise ComplexityError()
                dice_type = int(parts[1])
                if dice_type == 0:
                    raise ParseDiceFormulaError
                if dice_type not in self.USUAL_DICES:
                    self.warning_dices.append(dice_type)
                self.events.append(DiceEvent(
                    dices_number=dices_number,
                    dice_type=dice_type,
                    sign=sign,
                ))
        fragments = formula.split('+')
        for fragment in fragments:
            minus_on_right = fragment.split('-')
            handle_fragment(minus_on_right[0], 1)
            for term in minus_on_right[1:]:
                handle_fragment(term, -1)
        return self

    def sample(self) -> str:
        result = ''
        total_sum = 0
        for i, event in enumerate(self.events):
            if i > 0:
                result += ' '
            if event.sign == -1:
                result += '- '
            elif i > 0:
                result += '+ '
            if event.dice_type != 0:
                samples = [
                    random.randint(1, event.dice_type)
                    for _ in range(event.dices_number)
                ]
                if self.short_comments():
                    result += ' + '.join(map(str, samples))
                else:
                    comments = ''
                    if len(samples) > 1:
                        comments = '(' + '+'.join(map(str, samples)) + ')'
                    result += f'{sum(samples)}{comments}'
                total_sum += sum(samples) * event.sign
            else:
                # bies
                result += str(event.bies)
                total_sum += event.bies * event.sign
        if len(result) > 150:
            return f'{total_sum} \nРеализации кубиков скрыты, так как костей слишком много'
        if self.show_only_result():
            return f'{total_sum}'
        return f'{total_sum} = {result}'

    def short_comments(self) -> bool:
        return len(self.events) == 1 and self.events[0].dices_number > 1

    def show_only_result(self) -> bool:
        return len(self.events) == 1 and self.events[0].dices_number <= 1

    def get_warnings(self) -> str:
        if not self.warning_dices:
            return ''
        if len(self.warning_dices) == 1:
            return f'Обратите внимение, вы выбрали необычную кость d{self.warning_dices[0]}'
        return (
                'Обратите внимание, вы выбрали необычные кости: ' +
                ', '.join(map(lambda x: 'd' + str(x), self.warning_dices))
        )

    def __str__(self):
        return self.parent_string

    def mean(self) -> int:
        result = 0.0
        for event in self.events:
            if event.dice_type != 0:
                result += event.sign * event.dices_number * (event.dice_type / 2)
            else:
                result += event.sign * event.bies
        return int(result)
