import dataclasses
import datetime
import enum
import typing

from pymongo import collection


class Resource(enum.Enum):
    YANDEX_GPT = 'YandexGPT'


class AccountType(enum.Enum):
    ADMIN = 'admin'
    USER = 'user'


@dataclasses.dataclass
class Account:
    type: AccountType
    id: str


@dataclasses.dataclass
class Limits:
    day_limit: typing.Optional[int] = None
    month_limit: typing.Optional[int] = None


@dataclasses.dataclass
class ResourceConfig:
    total: Limits
    by_account_type: typing.Dict[AccountType, Limits]


class LimitIsOver(Exception):
    def __init__(self, period: str, is_total: bool):
        self.period = period
        self.is_total = is_total


class ResourcesManager:
    resource_limits = {
        Resource.YANDEX_GPT: ResourceConfig(
            total=Limits(month_limit=1000000),
            by_account_type={
                AccountType.ADMIN: Limits(),
                AccountType.USER: Limits(day_limit=250, month_limit=5000),
            },
        ),
    }

    def __init__(self, resources_collection: collection.Collection):
        self.resources_collection = resources_collection

    def _common_aggregate(
            self,
            resource: Resource,
            from_datetime: datetime.datetime,
            account_id: typing.Optional[str] = None,
    ):
        match_query = {'datetime': {'$gte': from_datetime}, 'resource': resource.value}
        if account_id:
            match_query['account_id'] = account_id
        pipeline = [
            {'$match': match_query},
            {'$group': {'_id': None, 'count': {'$sum': '$weight'}}}
        ]
        result = list(self.resources_collection.aggregate(pipeline))
        if not result:
            return 0
        return result[0]['count']

    def _by_day_count(self, resource: Resource, account_id: str, current_time: datetime.datetime):
        day_start = datetime.datetime(year=current_time.year, month=current_time.month, day=current_time.day)
        return self._common_aggregate(resource, day_start, account_id)

    def _by_month_count(self, resource: Resource, account_id: str, current_time: datetime.datetime):
        month_start = datetime.datetime(year=current_time.year, month=current_time.month, day=1)
        return self._common_aggregate(resource, month_start, account_id)

    def _by_day_count_total(self, resource: Resource, current_time: datetime.datetime):
        day_start = datetime.datetime(year=current_time.year, month=current_time.month, day=current_time.day)
        return self._common_aggregate(resource, day_start)

    def _by_month_count_total(self, resource: Resource, current_time: datetime.datetime):
        month_start = datetime.datetime(year=current_time.year, month=current_time.month, day=1)
        return self._common_aggregate(resource, month_start)

    def _insert_resource_usage(
            self,
            resource: Resource,
            account_id: str,
            current_time: datetime.datetime,
            weight: int,
    ):
        self.resources_collection.insert_one(
            {
                'account_id': account_id,
                'resource': resource.value,
                'datetime': current_time,
                'weight': weight,
            }
        )

    def acquire(self, resource: Resource, account: Account, weight: int = 1):
        current_time = datetime.datetime.utcnow()
        total_limits = self.resource_limits[resource].total
        limits = self.resource_limits[resource].by_account_type[account.type]
        if limits.month_limit:
            if self._by_month_count(resource, account.id, current_time) + weight > limits.month_limit:
                raise LimitIsOver(period='month', is_total=False)
        if limits.day_limit:
            if self._by_day_count(resource, account.id, current_time) + weight > limits.day_limit:
                raise LimitIsOver(period='day', is_total=False)
        if total_limits.month_limit:
            if self._by_month_count_total(resource, current_time) + weight > total_limits.month_limit:
                raise LimitIsOver(period='month', is_total=True)
        if total_limits.day_limit:
            if self._by_day_count_total(resource, current_time) + weight > total_limits.day_limit:
                raise LimitIsOver(period='day', is_total=True)
        self._insert_resource_usage(resource, account.id, current_time, weight)
