from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from datetime import datetime
from sqlite3 import IntegrityError
from datetime import datetime
from re import match
from io import BytesIO
from ..items import item_lookup
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
    consumers = db.get_consumer_list()

    month = get_month(month_n)
    last_day_of_month = datetime.fromtimestamp(month.end_ts - 1)

    csv_content = ''

    for c in consumers:
        stats = c.get_stats(from_timestamp=month.start_ts, to_timestamp=month.end_ts)
        stat_msg_parts = []
        sum_ = 0
        for key in sorted(list(stats.keys())):
            count, price_sum = stats[key]
            item = item_lookup(key)
            stat_msg_parts.append(
                '{} x{}'.format(item.name, count)
            )
            sum_ += price_sum

        drinks = ''
        if stat_msg_parts:
            drinks = ', '.join(stat_msg_parts) + ', '

        line = (
            '{last_day_of_month};Getränke-Abrechnung {month:0>2}/{year}, '
            '{drinks}{full_name};{akaflieg_id};880;{sum};{year}\n'.format(
                last_day_of_month=last_day_of_month.strftime('%d.%m.%Y'),
                month=month.month,
                year=month.year,
                drinks=drinks,
                full_name=c.full_name,
                akaflieg_id=c.akaflieg_id,
                sum=str(sum_).replace('.', ',')  # 12.1 to 12,1
            )
        )
        csv_content += line
    return csv_content
