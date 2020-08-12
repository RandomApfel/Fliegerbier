from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from datetime import datetime
from sqlite3 import IntegrityError
from datetime import datetime
from re import match
from io import BytesIO
from ..config import ADMINCHAT, BOTTOKEN, DATABASE
from ..decorators import admin_only, patch_telegram_action
from ..database import Database, Consumer
from ..datecalculation import get_month


def get_reply_markup(month_n):
    back_forth = [
        InlineKeyboardButton(
            '« zurück',
            callback_data='admin_rechnung_{}'.format(month_n + 1)
        )
    ]
    if month_n > 0:
        back_forth += [
            InlineKeyboardButton(
                'vor »',
                callback_data='admin_rechnung_{}'.format(month_n - 1)
        )
    ]

    return InlineKeyboardMarkup([
        back_forth,
        [InlineKeyboardButton(
            'Monatsrechnung ausgeben', callback_data='admin_rechnung_out_{}'
            .format(month_n)
        )],
        []
    ])


@admin_only
@patch_telegram_action
def rechnung(respond):
    this_month = get_month(0)

    respond(
        'Möchtest du für diesen {} '
        'eine Rechnung erstellen?\n'
        '(unvollständig)'
        .format(this_month.month_name),
        reply_markup=get_reply_markup(0)
    )


@patch_telegram_action
def admin_rechnung(original_message_id, edit, callback_data):
    x = match(r'admin_rechnung_(?P<month>[0-9]+)$', callback_data)
    month_n = int(x.groupdict()['month'])

    month = get_month(month_n)
    new_text = (
        'Möchtest du für {} {} '
        'eine Rechnung erstellen?'
        .format(month.month_name, month.year)
    )
    if month_n == 0:
        new_text += '\n(unvollständig)'
    edit(
        message_id=original_message_id,
        new_text=new_text,
        reply_markup=get_reply_markup(month_n)
    )



@patch_telegram_action
def admin_rechnung_out(respond, edit, callback_data):
    x = match(r'admin_rechnung_out_(?P<month>[0-9]+)$', callback_data)
    month_n = int(x.groupdict()['month'])
    month = get_month(month_n)

    bio = BytesIO()
    bio.name = 'Rechnung {:0>2} {}.txt'.format(month.month, month.year)

    bio.write(
        _create_csv(month_n).encode('cp1252', 'replace')
    )
    bio.seek(0)

    respond(
        'Monatsrechnung {:0>2}/{}'.format(month.month, month.year),
        file=bio
    )


def _create_csv(month_n: int):
    db = Database()

    month = get_month(month_n)
    last_day_of_month = datetime.fromtimestamp(month.end_ts - 1)

    consumption = db.get_consumption_dictionary(
        from_timestamp=month.start_ts,
        to_timestamp=month.end_ts,
    )

    keys = sorted(
        list(consumption.keys()),
        key=lambda x: Consumer(x).full_name
    )

    csv = ''
    for akaflieg_id in keys:
        drinks = []
        sum_ = 0
        for item_name in sorted(consumption[akaflieg_id].keys()):
            if consumption[akaflieg_id][item_name]['sum'] == 0:
                # Freigetränk, nicht auf die Liste
                continue
            count = consumption[akaflieg_id][item_name]['count']
            drinks.append('{} x{}'.format(item_name, count))
            sum_ += consumption[akaflieg_id][item_name]['sum']

        c = Consumer.from_akaflieg_id(akaflieg_id)
        full_name = '[nicht in Datenbank]'
        if c.is_authorized():
            full_name = c.full_name

        line = (
            '{last_day_of_month};Getränke-Abrechnung {month:0>2}/{year}, '
            '{drinks}, {full_name};{akaflieg_id};880;{sum};{year}\n'.format(
                last_day_of_month=last_day_of_month.strftime('%d.%m.%Y'),
                month=month.month,
                year=month.year,
                drinks=', '.join(drinks),
                full_name=full_name,
                akaflieg_id=akaflieg_id,
                sum=str(sum_).replace('.', ',')  # 12.1 to 12,1
            )
        )
        csv += line
    return csv
