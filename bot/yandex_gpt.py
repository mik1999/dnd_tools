import dataclasses
import enum
import logging
import requests
import resources_manager as rm
import typing


logger = logging.getLogger(__name__)


class MessageRole(enum.Enum):
    SYSTEM = 'system'
    USER = 'user'
    SERVER = 'assistant'


@dataclasses.dataclass
class YandexGPTMessage:
    text: str
    role: MessageRole


def get_token():
    with open('./oauth_token.txt') as file:
        return file.read().strip()


class YandexGptHelper:
    OAUTH_TOKEN = get_token()
    INSTRUCT_HOST = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
    CHAT_HOST = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
    FOLDER_ID = 'b1g6tu9asaapckafplet'

    def __init__(self, resources_manager: rm.ResourcesManager):
        self.resources_manager = resources_manager
        self.iam_token = None
        self._renew_iam_token()

    def _renew_iam_token(self):
        response = requests.post(
            url='https://iam.api.cloud.yandex.net/iam/v1/tokens',
            json={'yandexPassportOauthToken': self.OAUTH_TOKEN}
        )
        self.iam_token = response.json()['iamToken']

    @property
    def headers(self):
        return {
            'Authorization': f'Bearer {self.iam_token}',
            'Accept': 'application/json',
        }

    def generate(self, instruction_text: str, request_text: str, account: rm.Account) -> str:
        self.resources_manager.acquire(rm.Resource.YANDEX_GPT, account)
        body = {
            'modelUri': f'gpt://{self.FOLDER_ID}/yandexgpt',
            'completionOptions': {
                'stream': False,
                'temperature': 0.7,
                'maxTokens': 5000,
            },
            'messages': [
                {'role': 'system', 'text': instruction_text},
                {'role': 'user', 'text': request_text},
            ]
        }
        response = requests.post(url=self.INSTRUCT_HOST, headers=self.headers, json=body)
        self._handle_response(response)
        return response.json()['result']['alternatives'][0]['message']['text']

    def chat(self, instruction_text: str, messages: typing.List[YandexGPTMessage], account: rm.Account):
        self.resources_manager.acquire(rm.Resource.YANDEX_GPT, account)
        messages = [
            {'role': 'system', 'text': instruction_text},
        ] + [
            {
                'text': message.text,
                'role': message.role.value,
            }
            for message in messages
        ]
        body = {
            'modelUri': f'gpt://{self.FOLDER_ID}/yandexgpt',
            'completionOptions': {
                'stream': False,
                'temperature': 0.7,
                'maxTokens': 5000,
            },
            'messages': messages,
        }
        response = requests.post(url=self.CHAT_HOST, headers=self.headers, json=body)
        self._handle_response(response)
        response_message = response.json()['result']['alternatives'][0]['message']
        return YandexGPTMessage(
            text=response_message['text'],
            role=MessageRole(response_message['role']),
        )

    def _handle_response(self, response: requests.Response):
        if response.status_code == 401:
            self._renew_iam_token()
        if response.status_code != 200:
            logger.error('YandexGPT error %s, status_code %s', response.json(), response.status_code)
            raise rm.YandexGPTNetworkError
