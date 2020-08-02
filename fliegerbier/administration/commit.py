from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from datetime import datetime
from ..config import ADMINCHAT, BOTTOKEN, DATABASE
from ..decorators import admin_only, patch_telegram_action
from ..database import Database, Consumer
from re import match


@patch_telegram_action
def commit_callback(callback_data, respond, chat_dict):
    p = match(r'commit_(?P<chat_id>[0-9]+)$', callback_data)
    if not p:
        respond('Massiver bug, Code MBCPDM! Bitte an Info weitergeben!')
        return

    chat_id = p.groupdict()['chat_id']
    chat_dict['current_client_chat_id'] = chat_id
    c = Consumer(chat_id)
    if not c.user_exists():
        respond('Massiver bug, Code MBUDEC! Bitte an Info weitergeben!')
        return

    respond(
        'Commiten von {} ({}).\n'
        'Bitte gebe jetzt den vollen Namen an.\n'
        'Dieser Name wird auf der Rechnung verwendet.'
        .format(c.telegram_names, chat_id),
        reply_markup=ReplyKeyboardRemove()
    )

    return 'choose_full_name'


@admin_only
@patch_telegram_action
def commit(respond):
    db = Database()

    unauthorized = db.get_unauthorized_chat_ids()
    buttons = []
    for u in unauthorized:
        c = Consumer(u)
        buttons.append([
            '{} - {}'.format(c.chat_id, c.telegram_names)
        ])

    if not unauthorized:
        respond('Es gibt keine ausstehenden Anfragen.')
        return ConversationHandler.END

    respond(
        'Die folgenden Chat IDs haben keine Akaflieg ID '
        'zugeordnet.',
        reply_markup=ReplyKeyboardMarkup(buttons)
    )

    return 'take_chat_id'


@admin_only
@patch_telegram_action
def take_chat_id(respond, text, chat_dict):
    print('Take chat id')
    db = Database()

    chat_id_list_as_strings = [str(c) for c in db.get_unauthorized_chat_ids()]

    chat_id_from_text = text.split(' - ')[0]

    if chat_id_from_text not in chat_id_list_as_strings:
        respond(
            'Bitte nutze nur die Buttons.'
        )
        return 'take_chat_id'

    chat_dict['current_client_chat_id'] = chat_id_from_text

    respond(
        'Bitte gebe jetzt den vollen Namen an.\n'
        'Dieser Name wird auf der Rechnung verwendet.',
        reply_markup=ReplyKeyboardRemove()
    )

    return 'choose_full_name'


@patch_telegram_action
def choose_full_name(respond, text, chat_dict):
    c = Consumer(chat_dict['current_client_chat_id'])
    c.full_name = text

    respond(
        'Der Name wurde gesetzt.\n'
        'Bitte gebe jetzt einen Spitznamen an.\n'
        'Der Nutzer wird mit diesem Spitzname angesprochen.'
    )
    return 'choose_name'


@patch_telegram_action
def choose_name(respond, chat_dict, text):
    if not text.isalpha():
        respond(
            'Der Name darf keine Sonderzeichen oder Leerzeichen enthalten.\n'
            'Bitte gebe einen validen Namen an.'
        )
        return 'choose_name'
    
    chat_dict['current_client_nickname'] = text

    respond(
        'Okay. Bitte gebe jetzt die Akaflieg Nutzer ID ein.'
    )

    return 'set_akaflieg_id'


@patch_telegram_action
def set_akaflieg_id(respond, chat_dict, text, bot):
    if not text.isdigit():
        respond(
            'Die Akaflieg Nutzer ID sollte eine Ganzzahl sein.\n'
            'Bitte gebe einen validen Wert.'
        )
        return 'set_akaflieg_id'

    consumer = Consumer(chat_dict['current_client_chat_id'])
    consumer.nickname = chat_dict['current_client_nickname']
    consumer.akaflieg_id = int(text)

    respond(
        '{} mit der Akaflieg ID {} und der Chat ID {} '
        'ist jetzt in der Datenbank und wird darüber jetzt informiert.'
        .format(consumer.nickname, consumer.akaflieg_id, consumer.chat_id)
    )

    bot.send_message(
        chat_id=consumer.chat_id,
        text=(
            'Hi {}.\nDer Kassenwart hat dich freigegeben, '
            'du kannst jetzt hier Getränkekäufe eintragen.'
        ).format(
            consumer.nickname
        )
    )

    return ConversationHandler.END


@patch_telegram_action
def fallback(respond):
    respond(
        'Irgendentwas lief schief. Das ist ein bug.\n'
        'Bitte versuche es erneut.'
    )
    return ConversationHandler.END


@patch_telegram_action
def cancel(respond):
    respond(
        'Okay. Aktion abgebrochen.'
    )
    return ConversationHandler.END


commit_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(commit_callback, pattern='commit_'),
        CommandHandler('commit', commit)
    ],
    states={
        'take_chat_id': [MessageHandler(Filters.text, take_chat_id)],
        'choose_full_name': [MessageHandler(Filters.text, choose_full_name)],
        'set_akaflieg_id': [MessageHandler(Filters.text, set_akaflieg_id)],
        'choose_name': [MessageHandler(Filters.text, choose_name)],
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        MessageHandler(Filters.all, fallback),
    ]
)

