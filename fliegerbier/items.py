from typing import List
from .emoji import emojis

class Item:
    def __init__(self, name: str, identifier: str, price: float, emoji: str = None):
        self.name = name
        self.identifier = identifier
        self.price = price
        self.emoji = emoji

    @property
    def button_text(self) -> str:
        return '{emoji} {name} +1'.format(
            emoji=self.emoji, name=self.name
        )

    def __str__(self) -> str:
        return '{} ({}) für {}€'.format(
            self.name, self.identifier, self.price
        )

    def __repr__(self) -> str:
        return '<Item {}>'.format(self.identifier)


item_list: List[Item] = [
    Item('Bier', identifier='beer', price=1, emoji=emojis.beer),
    Item('Limo', identifier='limo', price=1, emoji=emojis.lemonade),
    Item('Wasser', identifier='water', price=0.4, emoji=emojis.wave),
]


def item_lookup(identifier: str) -> Item:
    for it in item_list:
        if it.identifier == identifier:
            return it
    raise ValueError('Item Lookup failed!')
