from json import loads
import telegram
from .items import item_list
from .decorators import patch_telegram_action, requires_authorization
from .config import BOTTOKEN, ADMINCHAT
from .emoji import emojis
from .enter_item_consumption import enter_item_consumption, undo_consumption
from .administration import (
    commit_handler,
    backup,
    admin_help_response,
    list_users,
    edit_handler,
    delete_handler,
    rechnung, admin_rechnung, admin_rechnung_out
)
from .statistics import get_user_statistics, update_user_statistics, get_user_csv
from .promille import get_promille, get_promille_callback
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
    CallbackQueryHandler,
)


def _reblock(block, width=2):
    new_block = []
    for i in range(0, len(block), width):
        new_block.append(block[i:min(i+width, len(block))])
    return new_block

_free_drinks_with_alc_text = 'Freie Getränke mit Alkohol'
_back_to_buyable_drinks = 'Zurück zur Hauptübersicht'
def get_main_reply_markup():
    costly_items = [item.button_text for item in item_list if item.price > 0]
    return ReplyKeyboardMarkup(
        _reblock(costly_items) + [
        ['/status', '/promille', _free_drinks_with_alc_text]
    ])

def get_free_alc_drinks_markup():
    free_items = [item.button_text for item in item_list if item.price == 0]
    return ReplyKeyboardMarkup(
        [[_back_to_buyable_drinks]] + _reblock(free_items)
    )


@patch_telegram_action
def start_message(respond):
    text = ('Hi!\n'
        'Dieser Bot hilft dir bei deinem '
        'sicheren und geheimen Getränkekonsum.\n'
        'Der Abrechnungszuständige kann alles einsehen.'
    )

    respond(text, reply_markup=get_main_reply_markup())

@patch_telegram_action
def telegram_unexpecte_text(respond, chat_id):
    print(chat_id, chat_id == ADMINCHAT)
    if chat_id == ADMINCHAT:
        respond('Nachricht ignoriert, du befindest dich in keinem Programm.')
        return

    respond('Bitte nutze die Buttons.')


@patch_telegram_action
def get_chat_id(respond, chat_id):
    respond(str(chat_id))


def error_handler(update, context):
    from subprocess import run
    import traceback
    from datetime import datetime

    try:
        raise context.error
    except:
        tb = traceback.format_exc()

    print(tb)
    print('ERROR')

    run(['mkdir', '-p', 'tracebacks'], check=True)
    with open('tracebacks/' + str(datetime.now().timestamp()), 'w') as f:
        f.write('Error occured at {}:\n'.format(datetime.now()))
        f.write(tb)

    context.bot.send_message(text='Der Bot ist gecrasht! Eine Fehlermeldung wurde '
        'auf dem Server gerneriert und wird bei Bemerken analysiert und '
        'eventuell demnächst gefixt!',
        chat_id=update.message.chat.id)
    return ConversationHandler.END


@requires_authorization
@patch_telegram_action
def handle_text(update, context, text, respond, chat_id):
    if chat_id == ADMINCHAT:
        respond(
            'Nachricht ignoriert, du befindest dich in keinem Programm.\n'
            'Führe /help aus für alle Adminbefehle.',
            reply_markup=ReplyKeyboardRemove()
        )
        return

    all_items = [item.button_text for item in item_list]

    if text in all_items:
        f = enter_item_consumption(text)
    elif text == _free_drinks_with_alc_text:
        respond('Okay', reply_markup=get_free_alc_drinks_markup())
        return
    elif text == _back_to_buyable_drinks:
        respond('Okay', reply_markup=get_main_reply_markup())
        return
    else:
        respond('Bitte nutze die Buttons um deine Kauf einzutragen!', reply_markup=get_main_reply_markup())
        return
    
    f(update, context)


def build_updater():
    updater = Updater(
        token=BOTTOKEN,
        use_context=True,
        workers=16,
        persistence=None
    )

    updater.dispatcher.add_handler(CommandHandler('start', start_message))
    updater.dispatcher.add_handler(CommandHandler('chatid', get_chat_id))
    updater.dispatcher.add_handler(CommandHandler('backup', backup))
    updater.dispatcher.add_handler(CommandHandler('help', admin_help_response))
    updater.dispatcher.add_handler(CommandHandler('list', list_users))
    updater.dispatcher.add_handler(CommandHandler('rechnung', rechnung))
    updater.dispatcher.add_handler(edit_handler)
    updater.dispatcher.add_handler(delete_handler)

    updater.dispatcher.add_handler(CommandHandler('promille', get_promille))
    updater.dispatcher.add_handler(CommandHandler('status', get_user_statistics))

    updater.dispatcher.add_handler(commit_handler)
    updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_text))

    updater.dispatcher.add_handler(
        MessageHandler(Filters.all, telegram_unexpecte_text)
    )

    updater.dispatcher.add_handler(
        CallbackQueryHandler(undo_consumption, pattern='revert_')
    )
    updater.dispatcher.add_handler(
        CallbackQueryHandler(update_user_statistics, pattern='user_view_')
    )
    updater.dispatcher.add_handler(
        CallbackQueryHandler(get_user_csv, pattern='user_send_csv')
    )

    updater.dispatcher.add_handler(
        CallbackQueryHandler(admin_rechnung_out, pattern='admin_rechnung_out_')
    )
    updater.dispatcher.add_handler(
        CallbackQueryHandler(admin_rechnung, pattern='admin_rechnung_')
    )

    updater.dispatcher.add_handler(
        CallbackQueryHandler(get_promille_callback, pattern='promille_')
    )

    updater.dispatcher.add_error_handler(error_handler)

    return updater
