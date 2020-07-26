from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from datetime import datetime
from sqlite3 import IntegrityError
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
    chat_dict['consumer_to_be_edited'] = consumer

    respond(
        'Möchtest du den Spitznamen ändern?',
        reply_markup=ReplyKeyboardMarkup([['Ja', 'Nein']])
    )
    return 'yes_no_change_nickname'
    

@admin_only
@patch_telegram_action
def yes_no_change_nickname(respond, text, chat_dict):
    if text.lower() == 'ja':
        respond(
            'Okay. Wie soll der neue Nickname sein?',
            reply_markup=ReplyKeyboardRemove()
        )
        return 'choose_nickname'
    elif text.lower() == 'nein':
        respond('Okay. Möchtest du den vollen Namen ändern?')
        return 'yes_no_full_name'
    else:
        respond('Bitte nutze die Buttons.')
        return 'yes_no_change_nickname'


@admin_only
@patch_telegram_action
def choose_nickname(respond, text, chat_dict):
    if not text.isalpha():
        respond(
            'Der Name darf keine Sonderzeichen oder Leerzeichen enthalten.\n'
            'Bitte gebe einen validen Namen an.'
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

    respond(
        'Okay. Möchtest du den vollen Namen ändern?',
        reply_markup=ReplyKeyboardMarkup([['Ja', 'Nein']])
    )
    return 'yes_no_full_name'


@admin_only
@patch_telegram_action
def yes_no_full_name(respond, text):
    if text.lower() == 'ja':
        respond(
            'Okay. Wie soll der neue Name sein?',
            reply_markup=ReplyKeyboardRemove()
        )
        return 'choose_full_name'
    elif text.lower() == 'nein':
        respond('Okay. Möchtest du die Akaflieg ID ändern?')
        return 'yes_no_change_akaflieg_id'


@admin_only
@patch_telegram_action
def choose_full_name(respond, text, chat_dict):
    chat_dict['consumer_to_be_edited'].full_name = text

    respond(
        'Der Name wurde gesetzt. Möchtest du die Akaflieg ID ändern?',
        reply_markup=ReplyKeyboardMarkup([['Ja', 'Nein']])
    )
    return 'yes_no_change_akaflieg_id'

@admin_only
@patch_telegram_action
def yes_no_change_akaflieg_id(respond, text):
    if text.lower() == 'ja':
        respond(
            'Okay. Wie soll die neue Akaflieg ID sein?',
            reply_markup=ReplyKeyboardRemove()
        )
        return 'choose_akaflieg_id'
    elif text.lower() == 'nein':
        respond(
            'Okay. Die Nutzerdaten wurden geändert.',
            reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    else:
        respond('Bitte nutze die Buttons.')
        return 'yes_no_change_akaflieg_id'


@admin_only
@patch_telegram_action
def choose_akaflieg_id(respond, text, chat_dict):
    if not text.isdigit():
        respond(
            'Die Akaflieg Nutzer ID sollte eine Ganzzahl sein.\n'
            'Bitte gebe einen validen Wert.'
        )
        return 'choose_akaflieg_id'

    try:
        chat_dict['consumer_to_be_edited'].akaflieg_id = int(text)
    except IntegrityError:
        respond(
            'Diese Akaflieg ID wurde bereits vergeben.'
            'Bitte lösche den alten Nutzer vorher (/delete).\n'
            '/cancel dafür die aktuelle Operation oder '
            'vergebe eine andere Akaflieg ID.'
        )
        return 'choose_akaflieg_id'

    respond('Okay. Die Daten wurden gesetzt.')
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
    entry_points=[CommandHandler('edit', edit)],
    states={
        'select_user': [MessageHandler(Filters.text, select_user)],
        'yes_no_change_nickname': [MessageHandler(Filters.text, yes_no_change_nickname)],
        'choose_nickname': [MessageHandler(Filters.text, choose_nickname)],
        'yes_no_full_name': [MessageHandler(Filters.text, yes_no_full_name)],
        'choose_full_name': [MessageHandler(Filters.text, choose_full_name)],
        'yes_no_change_akaflieg_id': [MessageHandler(Filters.text, yes_no_change_akaflieg_id)],
        'choose_akaflieg_id': [MessageHandler(Filters.text, choose_akaflieg_id)],
    },
    fallbacks=[
        MessageHandler(Filters.all, fallback),
        CommandHandler('cancel', cancel),
    ]
)


