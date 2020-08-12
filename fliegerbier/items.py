from typing import List
from .config import ITEMCSV
from .emoji import emojis


class Item:
    def __init__(self, name: str, price: float, emoji: str = None, alcohol: float = 0.0):
        self.name = name
        self.price = price
        self.emoji = emoji
        self.alcohol = alcohol

    @property
    def button_text(self) -> str:
        return '{emoji} {name} +1'.format(
            emoji=self.emoji, name=self.name
        )

    def __str__(self) -> str:
        return '{} for {}€'.format(
            self.name,  self.price
        )

    def __repr__(self) -> str:
        return '<Item {}>'.format(self.name)


def get_item_list():
    item_list: List[Item] = []
    for line in open(ITEMCSV).readlines():
        line = line.replace('\n', '')
        if not line:
            continue
        cells = line.split(';')
        alcohol = '0.0'
        emoji = ''
        if len(cells) == 2:
            name, price = cells
        elif len(cells) == 3:
            name, price, emoji = cells
        elif len(cells) == 4:
            name, price, emoji, alcohol = cells
        else:
            print(cells)
            raise ValueError('CSV format invalid')

        item_list.append(Item(
            name=name.strip(),
            price=float(price.strip().replace(',', '.')),
            emoji=emoji.strip(),
            alcohol=float(alcohol.strip().replace(',', '.'))
        ))

        print(item_list[-1])
    return item_list


item_list: List[Item] = get_item_list()

def reload_item_list():
    global item_list
    item_list = get_item_list()


