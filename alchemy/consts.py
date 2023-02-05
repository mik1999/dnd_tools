import enum


class PotionForm(enum.Enum):
    POTION = 'potion'
    SALVE = 'salve'
    EXPLOSIVE_POTION = 'explosive_potion'
    POWDER = 'powder'
    INCENSE = 'incense'


ALL_FORMS = {PotionForm.POTION, PotionForm.SALVE, PotionForm.EXPLOSIVE_POTION, PotionForm.POWDER, PotionForm.INCENSE}


POTION_FORMS_RUS = {
    PotionForm.POTION: 'зелье',
    PotionForm.SALVE: 'мазь',
    PotionForm.EXPLOSIVE_POTION: 'взрывное зелье',
    PotionForm.POWDER: 'порошок',
    PotionForm.INCENSE: 'благовония',
}

COMPLEXITY_MAP = {
    1: 4,
    2: 10,
    3: 13,
    4: 16,
    5: 21,
    6: 25,
    7: 28
}

DEFAULT_MODS = {
            'days': 5,
            'hours': 6,
            'rounds': 5,
            'best_before': 12,
        }
