from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from datetime import datetime
from sqlite3 import IntegrityError
from re import match
from ..config import ADMINCHAT, BOTTOKEN, DATABASE
from ..decorators import admin_only, patch_telegram_action
from ..database import Database, Consumer


def get_buttons_from_user(user_list):
    buttons = []
    for user in user_list:
        user_text = '{} - Aka {} - Chat {}'.format(
            user.nickname, user.akaflieg_id, user.chat_id
        )
        buttons += [user_text]
    return buttons


def get_user_from_button(user_list, button_text):
    for user in user_list:
        user_text = '{} - Aka {} - Chat {}'.format(
            user.nickname, user.akaflieg_id, user.chat_id
        )
        if user_text == button_text:
            return user
    raise ValueError('User not found. Race?')



def get_user_data_buttons(chat_id):
    consumer = Consumer(chat_id)
    text = (
        'Spitznamen: {nickname}\n'
        'Voller Name: {full_name}\n'
        'Akaflieg ID: {aka_id}\n'
        'Chat ID: {chat_id}\n'
        'Telegram Namen: {telegram_names}'
    ).format(
        nickname=consumer.nickname,
        full_name=consumer.full_name,
        aka_id=consumer.akaflieg_id,
        chat_id=consumer.chat_id,
        telegram_names=consumer.telegram_names,
    )
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('Editiere Spitzname', callback_data='edit_nickname_{}'.format(chat_id))],
        [InlineKeyboardButton('Editiere vollen Namen', callback_data='edit_fullname_{}'.format(chat_id))],
        [InlineKeyboardButton('Editiere Akaflieg ID', callback_data='edit_akaid_{}'.format(chat_id))],
    ])
    return text, reply_markup


@admin_only
@patch_telegram_action
def edit(respond):
    db = Database()
    user_list = db.get_consumer_list()

    if not user_list:
        respond('Keine Nutzer in der Datenbank.')
        return ConversationHandler.END

    buttons = [[b] for b in get_buttons_from_user(user_list)]

    respond(
        'Welchen Nutzer möchtest du editieren?',
        reply_markup=ReplyKeyboardMarkup(buttons)
    )
    return 'select_user'


@admin_only
@patch_telegram_action
def select_user(respond, text, chat_dict):
    db = Database()
    user_list = db.get_consumer_list()
    buttons = get_buttons_from_user(user_list)

    if text not in buttons:
        respond('Bitte nutze die Buttons.')
        return 'select_user'

    consumer = get_user_from_button(user_list, text)

    text, reply_markup = get_user_data_buttons(consumer.chat_id)
    print(reply_markup)
    respond(text, reply_markup=reply_markup)
    return ConversationHandler.END


@patch_telegram_action
def say_choose_nickname(respond, callback_data, original_message_id, chat_dict):
    m = match(r'edit_nickname_(?P<chat_id>[0-9]+)$', callback_data)
    chat_id = m.groupdict()['chat_id']
    c = Consumer(chat_id)
    chat_dict['consumer_to_be_edited'] = c
    chat_dict['original_message_id'] = original_message_id

    respond(
        'Gebe einen neuen Spitznamen an.\n'
        '({nickname})'
        .format(nickname=c.nickname),
        reply_markup=ReplyKeyboardRemove()
    )
    return 'choose_nickname'


@admin_only
@patch_telegram_action
def choose_nickname(respond, text, edit, chat_dict):
    if '\n' in text:
        respond(
            'Der Name darf keine Zeileumbrüche enthalten.\n'
            'Bitte gebe einen validen Spitznamen an.'
        )
        return 'choose_nickname'

    try:
        chat_dict['consumer_to_be_edited'].nickname = text
    except IntegrityError:
        respond(
            'Dieser Spitzname wurde bereits vergeben.\n'
            'Bitte /cancel die aktuelle Operation und lösche '
            'den anderen Nutzer oder sende einen anderen Spitznamen.'
        )
        return 'choose_nickname'

    consumer = chat_dict['consumer_to_be_edited']
    text, reply_markup = get_user_data_buttons(consumer.chat_id)
    
    respond('Okay. Der Wert wurde aktualisiert.')
    edit(
        message_id=chat_dict['original_message_id'],
        new_text=text,
        reply_markup=reply_markup
    )
    return ConversationHandler.END


@patch_telegram_action
def say_choose_full_name(respond, callback_data, original_message_id, chat_dict):
    m = match(r'edit_fullname_(?P<chat_id>[0-9]+)$', callback_data)
    chat_id = m.groupdict()['chat_id']
    c = Consumer(chat_id)
    chat_dict['consumer_to_be_edited'] = c
    chat_dict['original_message_id'] = original_message_id

    respond(
        'Gebe einen neuen vollen Namen an.\n'
        'Dieser wird auf der Rechnung verwendet.\n'
        '({full_name})'
        .format(full_name=c.full_name),
        reply_markup=ReplyKeyboardRemove()
    )
    return 'choose_full_name'


@admin_only
@patch_telegram_action
def choose_full_name(respond, text, chat_dict, edit):
    consumer = chat_dict['consumer_to_be_edited']
    consumer.full_name = text

    text, reply_markup = get_user_data_buttons(consumer.chat_id)
    respond('Okay. Der Wert wurde aktualisiert.')
    edit(
        message_id=chat_dict['original_message_id'],
        new_text=text,
        reply_markup=reply_markup
    )
    return ConversationHandler.END


@patch_telegram_action
def say_choose_aka_id(respond, callback_data, original_message_id, chat_dict):
    m = match(r'edit_akaid_(?P<chat_id>[0-9]+)$', callback_data)
    chat_id = m.groupdict()['chat_id']
    c = Consumer(chat_id)
    chat_dict['consumer_to_be_edited'] = c
    chat_dict['original_message_id'] = original_message_id

    respond(
        'Bitte gebe die Akaflieg ID an.\n'
        '({aka_id})'
        .format(aka_id=c.akaflieg_id),
        reply_markup=ReplyKeyboardRemove()
    )
    return 'choose_akaflieg_id'


@admin_only
@patch_telegram_action
def choose_akaflieg_id(respond, text, chat_dict, edit):
    if not text.isdigit():
        respond(
            'Die Akaflieg Nutzer ID sollte eine Ganzzahl sein.\n'
            'Bitte gebe einen validen Wert.'
        )
        return 'choose_akaflieg_id'

    consumer = chat_dict['consumer_to_be_edited']
    try:
        consumer.akaflieg_id = int(text)
    except IntegrityError:
        respond(
            'Diese Akaflieg ID wurde bereits vergeben.'
            'Bitte lösche den alten Nutzer vorher (/delete).\n'
            '/cancel dafür die aktuelle Operation oder '
            'vergebe eine andere Akaflieg ID.'
        )
        return 'choose_akaflieg_id'

    text, reply_markup = get_user_data_buttons(consumer.chat_id)
    respond('Okay. Der Wert wurde aktualisiert.')
    edit(
        message_id=chat_dict['original_message_id'],
        new_text=text,
        reply_markup=reply_markup
    )
    return ConversationHandler.END


@patch_telegram_action
def fallback(respond):
    respond(
        'Irgendentwas lief schief. Das ist ein bug.\n'
        'Bitte versuche es erneut.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


@patch_telegram_action
def cancel(respond):
    respond(
        'Okay. Aktion abgebrochen.'
    )
    return ConversationHandler.END


edit_handler = ConversationHandler(
    entry_points=[
        CommandHandler('edit', edit),
        CallbackQueryHandler(say_choose_nickname, pattern='edit_nickname_'),
        CallbackQueryHandler(say_choose_full_name, pattern='edit_fullname_'),
        CallbackQueryHandler(say_choose_aka_id, pattern='edit_akaid_'),
    ],
    states={
        'select_user': [MessageHandler(Filters.text, select_user)],
        'choose_nickname': [MessageHandler(Filters.text, choose_nickname)],
        'choose_full_name': [MessageHandler(Filters.text, choose_full_name)],
        'choose_akaflieg_id': [MessageHandler(Filters.text, choose_akaflieg_id)],
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        MessageHandler(Filters.all, fallback),
    ]
)


