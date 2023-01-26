def cost_str(cost: float):
    gold = int(cost)
    gold_str = (str(gold) + ' зм' if gold else '')
    silver = int(10 * cost) % 10
    silver_str = (str(silver) + ' см' if silver else '')
    copper = int(100 * cost) % 10
    copper_str = (str(copper) + ' мм' if copper else '')
    return gold_str + (' ' if silver_str else '') + silver_str + (' ' if copper_str else '') + copper_str


def update_dict(d: dict, delta: dict):
    for key in delta:
        value = d.get(key, 0)
        value += delta[key]
        d[key] = value


def multiply_dict(d: dict, value: float):
    for key in d:
        d[key] *= value
