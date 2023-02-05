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


class StaticCachePool:
    def __init__(self):
        self.cache = StateMemoryCache()

    def __enter__(self) -> StateMemoryCache:
        return self.cache

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class CachePool:
    def __init__(self, pool: redis.ConnectionPool):
        self.pool = pool
        self.connection: typing.Optional[redis.Redis] = None

    def __enter__(self) -> redis.Redis:
        self.connection = redis.Redis(connection_pool=self.pool)
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()


@dataclasses.dataclass
class CachesContext:
    def __init__(self, cache: typing.Union[redis.ConnectionPool, StaticCachePool]):
        self.cache: typing.Union[
            CachePool, StaticCachePool
        ] = CachePool(cache) if isinstance(cache, redis.ConnectionPool) else cache
