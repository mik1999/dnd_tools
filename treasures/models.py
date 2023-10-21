import dataclasses
import enum
import re
import typing

from alchemy import potion


@dataclasses.dataclass
class JewelryClass:
    cost: int
    forms: typing.List[str]
    name: str


@dataclasses.dataclass
class Jewelry:
    count: int
    cost: int
    form: str
    name: str

    def __str__(self):
        count_info = '' if self.count == 1 else f' x{self.count}'
        return f'{self.form} {self.name} стоимостью {self.cost} зм{count_info}'


@dataclasses.dataclass
class Artwork:
    cost: int
    name: str


@dataclasses.dataclass
class Scroll:
    cost: int
    level: int
    name: str
    save_throw: int
    attack_bonus: int


class Rarity(enum.Enum):
    USUAL = 'обычный'
    UNUSUAL = 'необычный'
    RARE = 'редкий'
    VARY_RARE = 'очень редкий'
    LEGENDARY = 'легендарный'
    ARTIFACT = 'артефакт'
    VARY = 'варьируется'
    MARVELOUS = 'чудесный предмет'
    UNDEFINED = 'undefined'


@dataclasses.dataclass
class MagicItem:
    name_rus: str
    name_en: str
    rarity: Rarity
    cost_str: str
    cost: typing.Optional[typing.Tuple[int, int]]
    description: str
    url: str
    image_filename: typing.Optional[str]

    def command(self):
        return '/' + re.sub(r'[`’!\-\'\":*,.\\/]', '', self.name_en.replace(' ', '_').lower())

    def explain(self):
        rarity_str = (f'{self.rarity.value} предмет'
                      if self.rarity in [Rarity.ARTIFACT, Rarity.MARVELOUS]
                      else self.rarity.value)
        return (f'{self.name_rus}, {rarity_str}, '
                f'{self.cost_str}\n{self.description}')

    def form_filename(self) -> str:
        if not self.image_filename:
            return ''
        if __debug__:
            return '../treasures/data/img/' + self.image_filename
        return '/data/magic_items_img/' + self.image_filename


@dataclasses.dataclass
class Treasury:
    gold: int = dataclasses.field(default=0)
    silver: int = dataclasses.field(default=0)
    copper: int = dataclasses.field(default=0)
    trinkets: typing.List[str] = dataclasses.field(default_factory=list)
    jewelry: typing.List[Jewelry] = dataclasses.field(default_factory=list)
    artworks: typing.List[Artwork] = dataclasses.field(default_factory=list)
    scrolls: typing.List[Scroll] = dataclasses.field(default_factory=list)
    magic_items: typing.List[MagicItem] = dataclasses.field(default_factory=list)
    potions: typing.List[potion.Potion] = dataclasses.field(default_factory=list)
