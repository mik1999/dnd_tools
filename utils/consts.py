RANDOM_RACE = 'Случайная раса'


def races_buttons(include_random=False, include_back=False):
    first_raw = ['Человек']
    if include_random:
        first_raw += [RANDOM_RACE]
    if include_back:
        first_raw += ['Назад']
    return [
        first_raw,
        ['Дварф', 'Полурослик', 'Эльф'],
        ['Гном', 'Полуорк', 'Полуэльф'],
        ['Драконорождённый', 'Сатир', 'Тифлинг'],
    ]
