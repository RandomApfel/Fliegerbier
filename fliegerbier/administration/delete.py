from .edit import get_buttons_from_user, get_user_from_button, fallback, cancel
from telegram import Bot, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from datetime import datetime
from sqlite3 import IntegrityError
from ..config import ADMINCHAT, BOTTOKEN, DATABASE
from ..decorators import admin_only, patch_telegram_action
from ..database import Database, Consumer


@admin_only
@patch_telegram_action
def delete(respond):
    db = Database()
    user_list = db.get_consumer_list()

    if not user_list:
        respond('Keine Nutzer in der Datenbank.')
        return ConversationHandler.END

    buttons = [[b] for b in get_buttons_from_user(user_list)]

    respond(
        'Welchen Nutzer möchtest du löschen?',
        reply_markup=ReplyKeyboardMarkup(buttons)
    )
    return 'delete_user'


@admin_only
@patch_telegram_action
def delete_user(respond, text, chat_dict):
    db = Database()
    user_list = db.get_consumer_list()
    buttons = get_buttons_from_user(user_list)

    if text not in buttons:
        respond('Bitte nutze die Buttons.')
        return 'delete_user'

    user = get_user_from_button(user_list, text)
    c = Consumer(user.chat_id)
    c.delete()
    respond(
        'Der Nutzer wurde gelöscht.\n'
        'Wenn er neu eingetragen wird (mit der selben '
        'Akaflieg ID), so bleibt seine gesamte Historie erhalten.',
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END



delete_handler = ConversationHandler(
    entry_points=[CommandHandler('delete', delete)],
    states={
        'delete_user': [MessageHandler(Filters.text, delete_user)],
    },
    fallbacks=[
        MessageHandler(Filters.all, fallback),
        CommandHandler('cancel', cancel),
    ]
)
