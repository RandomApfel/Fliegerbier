from .decorators import patch_telegram_action, requires_authorization
from .items import Item, item_list
from .database import Consumer
from .config import REVERTTIME
from .emoji import emojis
from time import time, sleep
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from threading import Thread


def _revert_counter(
    consume_time: int,
    text: str,
    message_id: int,
    chat_dict: dict,
    key: str,
    edit
):
    for _ in range(0, 1800):  # 1800 MAXIMUM
        time_left = consume_time + REVERTTIME - time()
        if time_left < 0:
            edit(message_id=message_id, new_text=text)
            return

        sleep(time_left % 1)

        if chat_dict.get(key, None) is None:
            # expired or reverted
            return

        try:
            edit(message_id=message_id, new_text=text, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    'Rückgängig machen ({})'.format(
                        int(time_left)
                    ),
                    callback_data=key
                )]
            ]))
        except KeyboardInterrupt:
            # Message has been deleted
            return



def enter_item_consumption(drink: str):
    item: Item = None
    for it in item_list:
        if drink == it.button_text:
            item = it
    
    if not item:
        raise ValueError("Lookup of item failed: " + drink)

    @patch_telegram_action
    def f(chat_id, respond, chat_dict, edit):
        c = Consumer(chat_id)
        assert item
        rowid = c.consume(item)

        text = '{} Kauf von {} für {}€ eingetragen.'.format(
            item.emoji, item.name, item.price
        )
        r = respond(text)

        key = 'revert_{}'.format(rowid)
        consume_time = time()

        t = Thread(
            target=_revert_counter,
            kwargs=dict(
                consume_time=consume_time,
                text=text,
                message_id=r['message_id'],
                chat_dict=chat_dict,
                key=key,
                edit=edit,
            )
        )
        chat_dict[key] = {
            'thread': t,
            'message_id': r['message_id'],
            'text': text,
            'consume_time': consume_time,
            'rowid': rowid,
        }
        t.start()

    return f


@patch_telegram_action
def undo_consumption(callback_data, chat_id, edit, chat_dict, respond):
    try:
        revert_data = chat_dict[callback_data]
    except KeyError:
        respond(
            'Hi. Hier hat sich gerade ein Feher ergeben.\n'
            'Hast du Versuch eine Transaktion rückgängig zu machen '
            'die es nicht gab?'
        )
        return
    
    del chat_dict[callback_data]

    too_late = (time() - revert_data['consume_time'] > REVERTTIME)
    revert_data['thread'].join()

    if too_late:
        edit(
            message_id=revert_data['message_id'],
            new_text=revert_data['text'] + (
                '\n\n{} Zu Spät um abzubrechen!\n'
                'Die Transaktions-ID ist {}. Melde dies dem Kassenwart '
                'um die Transaktion rückgängig zu machen.\n'
                'Bitte tus aber nicht, das kostet viel zu viel Zeit, '
                'nimm dir das Getränk einfach trotzdem.'
            ).format(emojis.red_cross, revert_data['rowid'])
        )
        return

    consumer = Consumer(chat_id)
    consumer.unconsume(revert_data['rowid'])

    edit(
        message_id=revert_data['message_id'],
        new_text=revert_data['text'] + '\n{} Abgebrochen!'.format(
            emojis.red_cross
        )
    )

