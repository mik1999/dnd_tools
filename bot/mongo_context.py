import dataclasses
import pymongo.collection


@dataclasses.dataclass
class MongoContext:
    user_potions: pymongo.collection.Collection
