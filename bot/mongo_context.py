import dataclasses
import pymongo.collection


@dataclasses.dataclass
class MongoContext:
    user_potions: pymongo.collection.Collection
    user_info: pymongo.collection.Collection
    user_npcs: pymongo.collection.Collection
    user_npc_notes: pymongo.collection.Collection
