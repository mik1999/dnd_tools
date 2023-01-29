import dataclasses
import typing

import redis


class StateMemoryCache:
    def __init__(self):
        self._dict = {}

    def get(self, key: str) -> typing.Optional[str]:
        return self._dict.get(key)

    def set(self, key: str, value: str):
        self._dict[key] = value


@dataclasses.dataclass
class CachesContext:
    cache: typing.Union[redis.Redis, StateMemoryCache]
