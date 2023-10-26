import requests
import typing


def get_token():
    with open('../bot/oauth_token.txt') as file:
        return file.read().strip()


class Translator:
    OAUTH_TOKEN = get_token()
    HOST = 'https://translate.api.cloud.yandex.net/translate/v2/translate'

    def __init__(self):
        self.iam_token = self._get_iam_token()

    def _get_iam_token(self):
        response = requests.post(
            url='https://iam.api.cloud.yandex.net/iam/v1/tokens',
            json={'yandexPassportOauthToken': self.OAUTH_TOKEN}
        )
        return response.json()['iamToken']

    def translate_many(self, texts: typing.List[str]) -> typing.List[str]:
        body = {
            'texts': texts,
            'folderId': 'b1g6tu9asaapckafplet',
            'sourceLanguageCode': 'en',
            'targetLanguageCode': 'ru',
        }
        headers = {
            'Authorization': f'Bearer {self.iam_token}',
            'Content-Type': 'application/json',
        }
        response = requests.post(url=self.HOST, headers=headers, json=body)
        response_body = response.json()
        if not response_body.get('translations'):
            return []
        translations = response.json()['translations']
        return [t['text'] for t in translations]

    def translate(self, text: str) -> typing.Optional[str]:
        result = self.translate_many([text])
        if not result:
            return None
        return result[0]
