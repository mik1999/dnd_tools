def cost_str(cost: float):
    gold = int(cost)
    gold_str = (str(gold) + ' зм' if gold else '')
    silver = int(10 * cost) % 10
    silver_str = (str(silver) + ' см' if silver else '')
    copper = int(100 * cost) % 10
    copper_str = (str(copper) + ' мм' if copper else '')
    return gold_str + (' ' if silver_str else '') + silver_str + (' ' if copper_str else '') + copper_str


def double_average_to_dices(number: int, sample=False) -> str:
    # todo: d6, d8, d10, d12, ...
    if number == 0:
        return '0'
    if sample:
        # ToDo fix this dummy
        return str(int(number // 2))
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
