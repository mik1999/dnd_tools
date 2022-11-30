from alchemy.calculation_helper import double_average_to_dices


class ParameterProcessor:
    parameter_symbol = ''


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
        mods['rounds'] = max(1, mods['rounds'] + value)
        mods['days'] = max(1, mods['days'] + value)
        mods['hours'] = max(1, mods['hours'] + value)
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
            return result
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
