import collections
import bisect
import json
import numpy.random
import typing
import random

import treasures.models as models
from numpy import random as numpy_random


def gen_poisson(mean: float) -> int:
    return numpy_random.poisson(lam=mean)


def sample(sequence):
    index = random.randint(0, len(sequence) - 1)
    return sequence[index]


def generate_gold(complexity: int):
    if complexity < 13:
        return 0
    if complexity < 27:
        return gen_poisson(2 * complexity - 24)
    return 20 * gen_poisson((10 ** (complexity / 25 - 1)))


class TreasuresGenerator:
    def __init__(self, base_path='./data'):
        self.treasury: typing.Optional[models.Treasury] = None
        self.trinkets_generator = TrinketsGenerator(base_path)
        self.jewelry_generator = JewelryGenerator(base_path)
        self.artworks_generator = ArtworksGenerator(base_path)
        self.magic_items_generator = MagicItemsGenerator(base_path)

    def explain_magic_item(self, command: str) -> str:
        return self.magic_items_generator.find_and_explain(command)

    def generate(self, complexity: int) -> models.Treasury:
        complexity = min(100, max(1, complexity))
        self.treasury = models.Treasury()
        self._generate_coins(complexity)

        self.trinkets_generator.generate(self.treasury, complexity)

        generate_both = random.randint(13, 50) <= complexity
        if generate_both:
            self.jewelry_generator.generate(self.treasury, complexity)
            self.artworks_generator.generate(self.treasury, complexity)
        else:
            if random.randint(1, 2) == 1:
                self.jewelry_generator.generate(self.treasury, complexity)
            else:
                self.artworks_generator.generate(self.treasury, complexity)
        self.magic_items_generator.generate(self.treasury, complexity)
        return self.treasury

    def _generate_coins(self, complexity: int):
        generators = [CopperCoinsGenerator, SilverCoinsGenerator, GoldenCoinsGenerator]
        generators = [generator for generator in generators if generator.available(complexity)]
        random.shuffle(generators)
        generators[0].generate(self.treasury, complexity)
        if len(generators) > 1 and random.randint(1, 2) == 1:
            generators[1].generate(self.treasury, complexity)
            if len(generators) > 2 and random.randint(1, 3) == 1:
                generators[2].generate(self.treasury, complexity)


class CoinsGenerator:
    LOWER_BOUND: int = 1
    UPPER_BOUND: int = 100

    @classmethod
    def available(cls, complexity: int):
        return cls.LOWER_BOUND <= complexity <= cls.UPPER_BOUND

    @classmethod
    def generate(cls, treasury: models.Treasury, complexity: int):
        raise NotImplementedError


class CopperCoinsGenerator(CoinsGenerator):
    UPPER_BOUND = 50

    @classmethod
    def generate(cls, treasury: models.Treasury, complexity: int):
        treasury.copper = gen_poisson(complexity ** 2)


class SilverCoinsGenerator(CoinsGenerator):
    LOWER_BOUND = 5
    UPPER_BOUND = 75

    @classmethod
    def generate(cls, treasury: models.Treasury, complexity: int):
        treasury.silver = gen_poisson(complexity ** 2 / 2.25)


class GoldenCoinsGenerator(CoinsGenerator):
    LOWER_BOUND = 13

    @classmethod
    def generate(cls, treasury: models.Treasury, complexity: int):
        treasury.gold = generate_gold(complexity)


class TrinketsGenerator:

    PROBABILITY_POINTS = 1  # prob = 1 / SAMPLE_NUMBER
    SAMPLE_NUMBER = 6

    def __init__(self, base_path='./data/'):
        with open(base_path + 'trinkets.json', encoding='utf-8') as file:
            self.trinkets = json.load(file)

    def generate(self, treasury: models.Treasury, complexity: int):
        if complexity > 30:
            return

        for _ in range(self.SAMPLE_NUMBER):
            if random.randint(1, self.SAMPLE_NUMBER) <= self.PROBABILITY_POINTS:
                treasury.trinkets.append(sample(self.trinkets))


class JewelryGenerator:
    def __init__(self, base_path='./data/'):
        with open(base_path + 'jewelry.json', encoding='utf-8') as file:
            self.jewelry = json.load(file)
            self.jewelry = [models.JewelryClass(**item) for item in self.jewelry]
            self.jewelry_by_cost: typing.Dict[
                int, typing.List[models.JewelryClass]
            ] = {cost: [] for cost in [10, 50, 100, 500, 1000, 5000]}
            for item in self.jewelry:
                self.jewelry_by_cost[item.cost].append(item)

    def generate(self, treasury: models.Treasury, complexity: int):
        approximated_cost = generate_gold(complexity)
        if approximated_cost < 10:
            return
        available_costs = [key for key in self.jewelry_by_cost if key <= approximated_cost]
        available_costs = available_costs[::-1]
        if len(available_costs) == 1:
            _ = self._take_by_cost(
                treasury, available_costs[0], approximated_cost,
            )
            return
        if len(available_costs) > 2 and random.randint(1, 20) == 1:
            _ = self._take_by_cost(
                treasury, available_costs[2], approximated_cost,
            )
            return
        if random.randint(1, 7) != 1:
            approximated_cost = self._take_by_cost(
                treasury, available_costs[0], approximated_cost,
            )
        self._take_by_cost(treasury, available_costs[1], approximated_cost)

    def _take_by_cost(
            self, treasury: models.Treasury,
            cost: int, total_cost: int,
    ) -> int:
        items_number = total_cost // cost
        taken_classes = []
        classes_count = random.randint(1, 4)
        for i in range(classes_count):
            if items_number == 0:
                break
            item_class: typing.Optional[models.JewelryClass] = None
            while True:
                item_class = sample(self.jewelry_by_cost[cost])
                if item_class in taken_classes:
                    continue
                taken_classes.append(item_class)
                break
            item_class: models.JewelryClass
            count = items_number if i + 1 == classes_count else random.randint(1, items_number)
            items_number -= count
            item_form = sample(item_class.forms)
            treasury.jewelry.append(models.Jewelry(count, cost, item_form, item_class.name))
        return total_cost % cost


class ArtworksGenerator:
    def __init__(self, base_path='./data/'):
        with open(base_path + 'artworks.json', encoding='utf-8') as file:
            self.artworks = json.load(file)
            self.artworks = [models.Artwork(**item) for item in self.artworks]
            self.artworks_by_cost: typing.Dict[
                int, typing.List[models.Artwork]
            ] = {cost: [] for cost in [25, 250, 750, 2500, 7500]}
            for item in self.artworks:
                self.artworks_by_cost[item.cost].append(item)

    def generate(self, treasury: models.Treasury, complexity: int):
        approximated_cost = generate_gold(complexity)
        if approximated_cost < 25:
            return
        cost = max([key for key in self.artworks_by_cost if key <= approximated_cost])
        items_number = min(6, approximated_cost // cost)
        appropriate_artworks = self.artworks_by_cost[cost]
        random.shuffle(appropriate_artworks)
        artworks = appropriate_artworks[:items_number]
        treasury.artworks += artworks


class MagicItemsGenerator:
    def __init__(self, base_path='./data/'):
        self.magic_items = []
        self.items_by_rarity: typing.Dict[
            models.Rarity, typing.List[models.MagicItem]
        ] = collections.defaultdict(list)
        self.items_by_command: typing.Dict[str, models.MagicItem] = {}
        with open(base_path + 'magic_items.json', encoding='utf-8') as file:
            for item_doc in json.load(file):
                rarity = models.Rarity(item_doc.get('rarity') or 'undefined')
                cost_str: typing.Optional[str] = item_doc.get('cost')
                cost_bounds = None if cost_str is None else (0, 0)
                if cost_str is not None:
                    cost = cost_str
                    if cost[-3:] == ' зм':
                        cost = cost[:-3]
                    if cost.startswith('от '):
                        cost_lower = int(cost[3:])
                        cost_bounds = cost_lower, cost_lower * 2
                    else:
                        mid = cost.find('-')
                        cost_bounds = int(cost[:mid]), int(cost[mid + 1:])
                if cost_str is None:
                    cost_str = 'бесценный'
                magic_item = models.MagicItem(
                    name_rus=item_doc['name_rus'],
                    name_en=item_doc['name_en'],
                    rarity=rarity,
                    cost_str=cost_str,
                    cost=cost_bounds,
                    description=item_doc['description'],
                    url=item_doc['url'],
                    image_url=item_doc.get('image_url')
                )
                self.magic_items.append(magic_item)
                if rarity == models.Rarity.MARVELOUS:
                    rarity = models.Rarity.UNUSUAL
                self.items_by_rarity[rarity].append(magic_item)
                self.items_by_command[magic_item.command()] = magic_item

    RARITY_BY_COMPLEXITY = {
        26: models.Rarity.USUAL,
        # 38: models.Rarity.UNUSUAL, TODO: заново распарсить правильно и вернуть два типа
        50: models.Rarity.RARE,
        # 62: models.Rarity.VARY_RARE,
        74: models.Rarity.LEGENDARY,
        86: models.Rarity.ARTIFACT,
    }
    RARITY_KEYS = list(RARITY_BY_COMPLEXITY.keys())

    def generate(self, treasury: models.Treasury, complexity: int):
        if complexity <= 25:
            return
        pos = bisect.bisect_right(self.RARITY_KEYS, complexity) - 1
        if pos > 0 and random.randint(1, 4) == 1:
            # decrease rarity, that will gain more items
            pos -= 1
        lower_bound = self.RARITY_KEYS[pos]
        rarity = self.RARITY_BY_COMPLEXITY[lower_bound]
        rarity_list = self.items_by_rarity[rarity]

        items_number = numpy.random.binomial(complexity - lower_bound + 1, 0.33, 1)[0]
        for _ in range(items_number):
            treasury.magic_items.append(sample(rarity_list))

    @staticmethod
    def explain_magic_item(magic_item: models.MagicItem) -> str:
        return (f'{magic_item.name_rus}, {magic_item.rarity.value} предмет, '
                f'{magic_item.cost_str}\n{magic_item.description}')

    def find_and_explain(self, command: str) -> str:
        item = self.items_by_command.get(command)
        if not item:
            raise KeyError
        return self.explain_magic_item(item)


def explain_treasure(treasury: models.Treasury) -> str:
    result = ''
    weight = (treasury.copper + treasury.silver + treasury.gold) // 50
    coins_info = []
    if treasury.copper:
        coins_info.append(f'{treasury.copper} медных монет')
    if treasury.silver:
        coins_info.append(f'{treasury.silver} серебряных монет')
    if treasury.gold:
        coins_info.append(f'{treasury.gold} золотых монет')
    result += f'Деньги: {", ".join(coins_info)} общим весом {weight} фунтов;\n'
    if treasury.trinkets:
        result += f'Безделушки: {", ".join(treasury.trinkets)};\n'
    if treasury.artworks:
        total_cost = 0
        artworks = []
        for artwork in treasury.artworks:
            total_cost += artwork.cost
            artworks.append(f'{artwork.name} ({artwork.cost} зм)')
        total_info = '' if len(artworks) == 1 else f' общей стоимостью {total_cost} зм'
        result += f'Произведения искусства: {", ".join(artworks)}{total_info};\n'
    if treasury.jewelry:
        total_cost = 0
        jewelry = []
        for item in treasury.jewelry:
            total_cost += item.cost * item.count
            count_info = '' if item.count == 1 else f' x{item.count}'
            jewelry.append(f'{item.form} {item.name} ({item.cost} зм){count_info}')
        total_info = '' if len(jewelry) == 1 else f' общей стоимостью {total_cost} зм'
        result += f'Драгоценности: {", ".join(jewelry)}{total_info};\n'
    if treasury.magic_items:
        magic_items = []
        for item in treasury.magic_items:
            magic_items.append(
                f'{item.name_rus}, {item.rarity.value} предмет, {item.cost_str}, подробнее: {item.command()}',
            )
        result += 'Магические предметы:\n'
        for i, item in enumerate(magic_items):
            result += f'{i + 1}. {item}\n'
    return result
