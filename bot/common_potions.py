from alchemy import potion
from alchemy import components_manager
from alchemy import parameters_manager
from utils import words_suggester
import typing
import mongo_context


class CommonPotions:
    PAGE_SIZE = 6

    def __init__(self,
                 mongo_context: mongo_context.MongoContext,
                 pm: parameters_manager.ParametersManager,
                 cm: components_manager.ComponentsManager,
                 ):
        self.mongo = mongo_context
        self.pm = pm
        self.cm = cm
        self.potions = []
        for potion_doc in mongo_context.user_potions.find({'common': True}):
            self.potions.append(self._make_potion(potion_doc))
        self.words_suggester: typing.Optional[words_suggester.WordsSuggester] = None
        self.potion_by_name: typing.Dict[str, potion.Potion] = {}
        self.pages_count = 0
        self._refresh_structures()

    def _make_potion(self, potion_doc) -> potion.Potion:
        new_potion = potion.Potion(self.cm, self.pm)
        new_potion.from_dict(potion_doc['potion'])
        return new_potion

    def _refresh_structures(self):
        self.potions = sorted(self.potions, key=lambda p: p.name)
        self.potion_names = [p.name for p in self.potions]
        self.pages_count = len(self.potions) // self.PAGE_SIZE + int(len(self.potions) % self.PAGE_SIZE != 0)
        for p in self.potions:
            self.potion_by_name[p.name] = p
        self.words_suggester = words_suggester.WordsSuggester([p.name for p in self.potions])

    def get_page(self, page: int) -> typing.List[str]:
        if not (0 <= page < self.pages_count):
            return []
        return self.potion_names[page * self.PAGE_SIZE: (page + 1) * self.PAGE_SIZE]

    def add_potion(self, new_potion_doc: typing.Dict[str, typing.Any]):
        potion_name = new_potion_doc['potion']['__name']
        self.mongo.user_potions.update_one(
            {'user': new_potion_doc['user'], 'name': potion_name},
            {'$set': {'common': True}},
        )
        self.potions.append(self._make_potion(new_potion_doc))
        self._refresh_structures()

    def suggest_potion(self, user_query: str) -> typing.Optional[potion.Potion]:
        names = self.words_suggester.suggest(user_query)
        if not names:
            return None
        potion_found = self.potion_by_name[names[0]]
        return potion_found
