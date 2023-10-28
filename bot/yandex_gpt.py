import dataclasses
import enum

import requests
import resources_manager as rm
import typing


class MessageRole(enum.Enum):
    SYSTEM = 'Система'
    USER = 'Пользователь'
    SERVER = 'Ассистент'


@dataclasses.dataclass
class YandexGPTMessage:
    text: str
    role: MessageRole


def get_token():
    with open('./oauth_token.txt') as file:
        return file.read().strip()


class YandexGptHelper:
    OAUTH_TOKEN = get_token()
    INSTRUCT_HOST = 'https://llm.api.cloud.yandex.net/llm/v1alpha/instruct'
    CHAT_HOST = 'https://llm.api.cloud.yandex.net/llm/v1alpha/chat'

    def __init__(self, resources_manager: rm.ResourcesManager):
        self.resources_manager = resources_manager
        self.iam_token = self._get_iam_token()

    def _get_iam_token(self):
        response = requests.post(
            url='https://iam.api.cloud.yandex.net/iam/v1/tokens',
            json={'yandexPassportOauthToken': self.OAUTH_TOKEN}
        )
        return response.json()['iamToken']

    def generate(self, instruction_text: str, request_text: str, account: rm.Account):
        self.resources_manager.acquire(rm.Resource.YANDEX_GPT, account)
        body = {
            'model': 'general',
            'generation_options': {
                'partial_results': True,
                'temperature': 0.7,
                'max_tokens': 1000,
            },
            'request_text': request_text,
            'instruction_text': instruction_text,
        }
        headers = {
            'Authorization': f'Bearer {self.iam_token}',
            'x-folder-id': 'b1g6tu9asaapckafplet',
        }
        response = requests.post(url=self.INSTRUCT_HOST, headers=headers, json=body)
        if response.status_code != 200:
            raise rm.YandexGPTNetworkError
        return response.json()['result']['alternatives'][0]['text']

    def chat(self, instruction_text: str, messages: typing.List[YandexGPTMessage], account: rm.Account):
        self.resources_manager.acquire(rm.Resource.YANDEX_GPT, account)
        body = {
            'model': 'general',
            'generation_options': {
                'partial_results': False,
                'temperature': 0.6,
                'max_tokens': 5000,
            },
            'messages': [
                {
                    'text': message.text,
                    'role': message.role.value,
                }
                for message in messages
            ],
            'instruction_text': instruction_text,
        }
        headers = {
            'Authorization': f'Bearer {self.iam_token}',
            'x-folder-id': 'b1g6tu9asaapckafplet',
        }
        response = requests.post(url=self.CHAT_HOST, headers=headers, json=body)
        if response.status_code != 200:
            raise rm.YandexGPTNetworkError
        response_message = response.json()['result']['message']
        return YandexGPTMessage(
            text=response_message['text'],
            role=MessageRole(response_message['role']),
        )
