from .decorators import patch_telegram_action, requires_authorization
from .database import Consumer
from .emoji import emojis
from time import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode


FEMALE_HIGH_DECAY = 0.1  # promille per hour
FEMALE_LOW_DECAY = 0.085  # promille per hour
MALE_HIGH_DECAY = 0.2  # promille per hour
MALE_LOW_DECAY = 0.1  # promille per hour
FEMALE_WATER = 0.6  # percent water female
MALE_WATER = 0.7  # percent water male
ALC_EFFECTIVENESS = 0.9  # how much gets absorbed


def _get_promille_message(c: Consumer):
    consum_history = c.get_consumption_history(
        from_timestamp=int(time() - 3600 * 24)
    )

    decays = [FEMALE_HIGH_DECAY, FEMALE_LOW_DECAY, MALE_HIGH_DECAY, MALE_LOW_DECAY]
    last_promille = [0.0, 0.0, 0.0, 0.0]
    last_timestamp = 0

    for consumption in consum_history:
        if not consumption.gram_alcohol:
            continue
        gram_alcohol = consumption.gram_alcohol * ALC_EFFECTIVENESS

        instant_promille_female = gram_alcohol / c.weight / FEMALE_WATER
        instant_promille_male = gram_alcohol / c.weight / MALE_WATER

        hours_since_last_drink = (consumption.timestamp - last_timestamp) / 3600
        for i in range(4):
            last_promille[i] = max(0.0, last_promille[i] - decays[i] * hours_since_last_drink)

        last_promille[0] += instant_promille_female
        last_promille[1] += instant_promille_female
        last_promille[2] += instant_promille_male
        last_promille[3] += instant_promille_male
        last_timestamp = consumption.timestamp

    # Now
    hours_since_last_drink = (time() - last_timestamp) / 3600
    for i in range(4):
        last_promille[i] = max(0.0, last_promille[i] - decays[i] * hours_since_last_drink)

    male_max = last_promille[3]
    female_max = last_promille[1]

    male_hours = male_max / MALE_LOW_DECAY
    female_hours = female_max / FEMALE_LOW_DECAY

    return (
        'Dein angenommenes Körpergewicht ist {weight}kg.\n'
        'Sämtliche hier ausgeführten Berechnungen sind nicht juristisch bindend.\n\n'

        '{male} Für Männer\n'
        '{wine} Bei {male_low_decay}{promille} Abbau pro Stunde: *{male_max:.3}{promille}*\n'
        '{wine} Bei {male_high_decay}{promille} Abbau pro Stunde: {male_min:.3}{promille}\n'
        '{alarm} Du hast in {male_hours:.3}h kein Alkohol mehr im Blut.\n\n'
        
        '{female} Für Frauen\n'
        '{wine} Bei {female_low_decay}{promille} Abbau pro Stunde: *{female_max:.3}{promille}*\n'
        '{wine} Bei {female_high_decay}{promille} Abbau pro Stunde: {female_min:.3}{promille}\n'
        '{alarm} Du hast in {female_hours:.3}h kein Alkohol mehr im Blut.'

        .format(
            promille='‰',
            weight=c.weight,
            male=emojis.man,
            female=emojis.woman,
            wine=emojis.wine,
            male_min=last_promille[2],
            male_max=male_max,
            male_hours=male_hours,
            female_min=last_promille[0],
            female_max=female_max,
            female_hours=female_hours,
            alarm=emojis.alarm,
            male_high_decay=MALE_HIGH_DECAY,
            male_low_decay=MALE_LOW_DECAY,
            female_high_decay=FEMALE_HIGH_DECAY,
            female_low_decay=FEMALE_LOW_DECAY
        )
    )

_plus_minus_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton('+1kg', callback_data='promille_plus'),
    InlineKeyboardButton('-1kg', callback_data='promille_minus')]
])

_what_to_escape = '.-!()'

@requires_authorization
@patch_telegram_action
def get_promille(respond, chat_id):
    c = Consumer(chat_id)
    respond(
        _get_promille_message(c),
        reply_markup=_plus_minus_markup,
        escape_markdown=_what_to_escape,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@patch_telegram_action
def get_promille_callback(edit, original_message_id, chat_id, callback_data):
    c = Consumer(chat_id)
    if callback_data == 'promille_plus':
        c.weight = c.weight + 1
    elif callback_data == 'promille_minus':
        c.weight = c.weight - 1
    
    edit(
        message_id=original_message_id,
        new_text=_get_promille_message(c),
        reply_markup=_plus_minus_markup,
        escape_markdown=_what_to_escape,
        parse_mode=ParseMode.MARKDOWN_V2,
    )
