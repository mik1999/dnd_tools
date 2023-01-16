import json


with open('taverns_old.json', encoding='utf-8') as file:
    taverns = json.load(file)

adjs = []
for adj in taverns['adjs']:
    adjs.append({
        'plural': adj,
        'male': adj,
        'female': adj,
    })
nouns = []
for noun in taverns['nouns']:
    nouns.append({
        'word': noun,
        'gender': 'male',
    })
total = {
    'adjs': adjs,
    'nouns': nouns,
}
with open('taverns.json', 'w', encoding='utf-8') as file:
    json.dump(total, file, indent=4, ensure_ascii=False)

