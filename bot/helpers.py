import re

import telebot.types
import typing


def make_aligned_markup(
        buttons: typing.List[str], width: int,
) -> telebot.types.ReplyKeyboardMarkup:
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, row_width=width,
    )
    full_rows = len(buttons) // width
    for i in range(full_rows):
        markup.add(*buttons[width * i: width * (i + 1)])
    if len(buttons) % width != 0:
        markup.add(*buttons[full_rows * width:])
    return markup


def inflect_years(years: int) -> str:
    if years % 10 == 1:
        return 'год'
    if 1 < years % 10 < 5:
        return 'года'
    return 'лет'


def prepare_for_markdown(text: str):
    return re.sub(r'([!#\.])', '\\\1', text)
