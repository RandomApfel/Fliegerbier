from json import loads
import telegram
from .items import item_list
from .decorators import patch_telegram_action, requires_authorization
from .config import BOTTOKEN, ADMINCHAT
from .emoji import emojis
from .enter_item_consumption import enter_item_consumption, undo_consumption
from .administration import commit_handler, backup
from .statistics import get_user_statistics
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
    CallbackQueryHandler,
)


_button_item_texts = [
    item.button_text for item in item_list
]
_button_texts = _button_item_texts + [
    'Status ausgeben'
]


def _reblock(block, width=2):
    new_block = []
    for i in range(0, len(block), width):
        new_block.append(block[i:min(i+width, len(block))])
    return new_block

getreanke_markup = ReplyKeyboardMarkup(
    _reblock(_button_texts)
)


@patch_telegram_action
def start_message(respond):
    text = ('Hi!\n'
        'Dieser Bot hilft dir bei deinem '
        'sicheren und geheimen Getränkekonsum.\n'
        'Der Abrechnungszuständige kann alles einsehen.'
    )

    respond(text, reply_markup=getreanke_markup)

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
            'Nachricht ignoriert, du befindest dich in keinem Programm.',
            reply_markup=ReplyKeyboardRemove()
        )
        return

    if text not in _button_texts:
        respond('Bitte nutze nur die Buttons.', reply_markup=getreanke_markup)
        return

    if text in _button_item_texts:
        f = enter_item_consumption(text)
    else:
        get_user_statistics(update, context)
        return
    
    f(update, context)


def build_updater():
    updater = Updater(
        token=BOTTOKEN,
        use_context=True,
        workers=4,
        persistence=None
    )

    updater.dispatcher.add_handler(
        CommandHandler('start', start_message)
    )

    updater.dispatcher.add_handler(
        CommandHandler('chatid', get_chat_id)
    )

    updater.dispatcher.add_handler(
        CommandHandler('backup', backup)
    )

    updater.dispatcher.add_handler(commit_handler)
    updater.dispatcher.add_handler(MessageHandler(Filters.text, handle_text))

    updater.dispatcher.add_handler(
        MessageHandler(Filters.all, telegram_unexpecte_text)
    )

    updater.dispatcher.add_handler(
        CallbackQueryHandler(undo_consumption, pattern='revert_')
    )

    updater.dispatcher.add_error_handler(error_handler)

    return updater
