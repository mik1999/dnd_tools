import json
import re
import time
import typing
import tqdm

import random
import requests
import pydantic


def extract_raw_links():
    links = []
    with open('./data/raw_links.txt', encoding='utf-8') as file:
        for line in file:
            _, link = line.split('\t')
            links.append(link)
    with open('./data/links.txt', 'w') as file:
        for link in links:
            file.write(link)


RARITY_KEYWORDS = [
    ('необычн', 'необычный'),
    ('обычн', 'обычный'),
    ('легенда', 'легендарный'),
    ('артефакт', 'артефакт'),
    ('варьируется', 'варьируется'),
    ('очень редк', 'очень редкий'),
    ('редк', 'редкий'),
]


class MagicItem(pydantic.BaseModel):
    name_rus: typing.Optional[str]
    name_en: typing.Optional[str]
    rarity: typing.Optional[str]
    cost: typing.Optional[str]
    description: typing.Optional[str]
    url: str
    image_url: typing.Optional[str]


def parse_page(url):
    r = requests.get(url)
    text = r.text

    names = re.findall(r'<h2 class="card-title" itemprop="name"><span data-copy="(.+?)">', text)
    if names:
        name_rus, name_en = names[0].split('[')
        name_en = name_en[:-1]
        name_rus = name_rus.strip()
    else:
        name_rus, name_en = None, None
    rarity_texts = re.findall(r'<li class="size-type-alignment">(.+?)</li>', text)
    if rarity_texts:
        rarity_text: str = rarity_texts[0]
        rarity = 'undefined'
        for keyword, rarity_value in RARITY_KEYWORDS:
            if rarity_text.find(keyword) != -1:
                rarity = rarity_value
                break
    else:
        rarity = None
    cost_texts = re.findall(r'<strong>Рекомендованная стоимость:</strong>(.+?)</li>', text)
    if cost_texts:
        cost = cost_texts[0].replace('&thinsp;', '')
    else:
        cost = None
    descriptions = re.findall(r'<div itemprop="description">(.+?)</div>', text, re.DOTALL)
    if descriptions:
        description = descriptions[0]
        description = re.sub(r'<.+?>', '', description)
        description = re.sub(r'[\t\r]', '', description)
    else:
        description = None
    images = re.findall(r'<img src=\'(.+?\.jpeg)\'', text)
    if images:
        image_url = 'https://www.dnd.su' + images[0]
    else:
        image_url = None
    return MagicItem(
        url=url, name_en=name_en, name_rus=name_rus,
        cost=cost, rarity=rarity, description=description, image_url=image_url,
    )


with open('./data/links.txt') as links_file:
    links = [line for line in links_file]

magic_items = []

for i, link in enumerate(tqdm.tqdm(links)):
    item = parse_page(link[:-1])
    magic_items.append(item.dict())
    time.sleep(random.randint(1, 5))


with open('./data/magic_items.json', 'w', encoding='utf-8') as file:
    json.dump(magic_items, file, indent=4, ensure_ascii=False)
