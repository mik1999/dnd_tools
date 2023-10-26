import requests
import resources_manager as rm


def get_token():
    with open('./oauth_token.txt') as file:
        return file.read().strip()


class YandexGptHelper:
    OAUTH_TOKEN = get_token()
    HOST = 'https://llm.api.cloud.yandex.net/llm/v1alpha/instruct'

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
                'partial_results': False,
                'temperature': 0.5,
                'max_tokens': 1000,
            },
            'request_text': request_text,
            'instruction_text': instruction_text,
        }
        headers = {
            'Authorization': f'Bearer {self.iam_token}',
            'x-folder-id': 'b1g6tu9asaapckafplet',
        }
        response = requests.post(url=self.HOST, headers=headers, json=body)
        return response.json()['result']['alternatives'][0]['text']
