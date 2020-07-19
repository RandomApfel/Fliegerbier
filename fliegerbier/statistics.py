from .decorators import patch_telegram_action, requires_authorization
from .database import Consumer
from .items import item_list, Item


def _itemlookup(identifier: str) -> Item:
    for it in item_list:
        if it.identifier == identifier:
            return it

    assert False


@requires_authorization
@patch_telegram_action
def get_user_statistics(respond, chat_id):
    c = Consumer(chat_id)

    stats = c.get_stats()

    msg = 'Deine Gesamtrechnung:\n\n'

    sum_ = 0

    for key in sorted(stats.keys()):
        item = _itemlookup(key)
        count, price_sum = stats[key]
        msg += (
            '{emoji} {count} x {name} {sum:.2f}€\n'
            .format(
                emoji=item.emoji,
                count=count,
                name=item.name,
                sum=price_sum,
            )
        )
        sum_ += price_sum

    msg += '\nIn der Summe: {:.2f}€'.format(sum_)

    respond(msg)

