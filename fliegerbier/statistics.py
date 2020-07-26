from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .decorators import patch_telegram_action, requires_authorization
from .database import Consumer
from .items import item_list, Item
from .datecalculation import get_month
from re import compile


def _itemlookup(identifier: str) -> Item:
    for it in item_list:
        if it.identifier == identifier:
            return it

    assert False


def statistics_to_message(stats: dict) -> str:
    msg = ''
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
    return msg


def get_markup(around_month: int = 0):
    prev_month = get_month(around_month + 1)
    prev_text = '« {} {}'.format(
        prev_month.month_name, prev_month.year
    )

    prev_next = [
        InlineKeyboardButton(prev_text, callback_data='user_view_month_back_{}'.format(around_month + 1))
    ]

    if around_month > 0:
        next_month = get_month(around_month - 1)
        next_text = '{} {} »'.format(
            next_month.month_name, next_month.year
        )
        prev_next.append(
            InlineKeyboardButton(next_text, callback_data='user_view_month_back_{}'.format(around_month - 1))
        )

    markup = InlineKeyboardMarkup([
        prev_next,
        [InlineKeyboardButton('Gesamtverbrauch einsehen', callback_data='user_view_all')],
        [InlineKeyboardButton('Verbrauchsliste erhalten (CSV)', callback_data='user_send_csv')]
    ])
    return markup


@requires_authorization
@patch_telegram_action
def get_user_statistics(respond, chat_id):
    c = Consumer(chat_id)
    msg = 'Diesen Monat erworben:\n\n'
    month = get_month(n_backwards=0)
    stats = c.get_stats(
        from_timestamp=month.start_ts,
        to_timestamp=month.end_ts,
    )

    msg += statistics_to_message(stats)
    respond(msg, reply_markup=get_markup(around_month=0))


rematch = compile(r'user_view_month_back_(?P<month>[0-9]+)$')


@patch_telegram_action
def update_user_statistics(edit, chat_id, original_message_id, callback_data, commit_callback):
    commit_callback()
    c = Consumer(chat_id)
    previous_month_regex = rematch.match(callback_data)

    if previous_month_regex:
        # Show previous month
        desired_month_n = int(previous_month_regex.groupdict()['month'])
        desired_month = get_month(desired_month_n)

        msg = '{} {}\n\n'.format(desired_month.year, desired_month.month_name)
        stats = c.get_stats(
            from_timestamp=desired_month.start_ts,
            to_timestamp=desired_month.end_ts,
        )
        msg += statistics_to_message(stats)

        edit(message_id=original_message_id, new_text=msg, reply_markup=get_markup(around_month=desired_month_n))

        return

    if callback_data == 'user_view_all':
        # Show all

        stats = c.get_stats()  # globally
        msg = 'Insgesamt erworben:\n\n'
        msg += statistics_to_message(stats)
        edit(message_id=original_message_id, new_text=msg, reply_markup=get_markup(around_month=0))

        return

    # Error
    edit(
        message_id=original_message_id,
        new_text='Fehler. Bitte leite diese Nachricht an Info weiter. LKO53.'
    )


@patch_telegram_action
def get_user_csv(chat_id, commit_callback, respond):
    from io import BytesIO
    commit_callback()
    c = Consumer(chat_id)

    history = c.get_consumption_history()
    
    bio = BytesIO()
    bio.write('Datum und Uhrzeit;Getränk;Preis des Getränks\n'.encode('utf-8'))

    sum_ = 0
    for entry in history:
        sum_ += entry.price_at_time
        bio.write(
            '{};{};{}€\n'
            .format(
                entry.datetime,
                entry.item.name,
                entry.price_at_time
            ).encode('utf-8')
        )

    bio.write(
        'In der Summe;;{}€'.format(sum_).encode('utf-8')
    )

    bio.name = 'Gesamtliste.csv'
    bio.seek(0)

    respond(
        'Gesamtliste.csv',
        file=bio
    )

    
