from telegram import Bot
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from datetime import datetime
from .config import ADMINCHAT, BOTTOKEN, DATABASE
from .decorators import admin_only, patch_telegram_action
from .database import Database, Consumer

_bot = Bot(BOTTOKEN)


def send_admin_message(text, **kwargs):
    _bot.send_message(text=text, chat_id=ADMINCHAT, **kwargs)
    

@admin_only
@patch_telegram_action
def commit(respond):
    db = Database()

    unauthorized = db.get_unauthorized_chat_ids()
    id_list_string = ', '.join([str(x) for x in unauthorized])

    if not unauthorized:
        respond(
            'Es gibt keine ausstehenden Anfragen.'
        )
        return ConversationHandler.END

    respond(
        'Die folgenden Chat IDs haben keine Akaflieg ID '
        'zugeordnet.\n'
        'Schreibe für welche Chat ID du den Eintrag machen willst.\n'
        '(Suffix ist ausreichend)\n\n' + id_list_string
    )

    return 'take_chat_id'


@admin_only
@patch_telegram_action
def take_chat_id(respond, text, chat_dict):
    print('Take chat id')
    db = Database()

    chat_id_list_as_strings = [str(c) for c in db.get_unauthorized_chat_ids()]

    matches = []

    for c in chat_id_list_as_strings:
        if c.endswith(text):
            matches.append(c)

    if len(matches) == 0:
        respond(
            'Keine Chat ID hat diesen Suffix.\n'
            'Bitte gebe einen validen Suffix.'
        )
        return 'take_chat_id'

    if len(matches) > 1:
        respond(
            'Es wurden mehrere Chat IDs mit diesem '
            'Suffix gefunden: {}.\n'
            'Bitte gebe einen längeren Suffix.'.format(
                ', '.join(matches)
            )
        )
        return 'take_chat_id'

    chat_dict['current_client_chat_id'] = matches[0]

    respond(
        'Bitte setze einen Spitznamen.\n'
        'Der Klient wird mit diesem Spitznamen angesprochen.'
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


@admin_only
@patch_telegram_action
def backup(respond):
    from subprocess import Popen, PIPE
    from io import BytesIO

    respond('Backup wird generiert...')

    p = Popen(['sqlite3', DATABASE, '.dump'], stdout=PIPE)
    out, err = p.communicate()

    if err:
        respond('Fehler beim backup: ' + err.decode())
        return

    bio = BytesIO()
    bio.name = 'backup_getränkeliste_{}.sqlite3.dump'.format(
        datetime.now().strftime('%Y-%m-%d-%Hh-%Mm')
    )
    bio.write(out)
    bio.seek(0)  # reset cursor

    respond('Backup', file=bio)


commit_handler = ConversationHandler(
    entry_points=[CommandHandler('commit', commit)],
    states={
        'take_chat_id': [MessageHandler(Filters.text, take_chat_id)],
        'set_akaflieg_id': [MessageHandler(Filters.text, set_akaflieg_id)],
        'choose_name': [MessageHandler(Filters.text, choose_name)],
    },
    fallbacks=[
        MessageHandler(Filters.all, fallback),
        CommandHandler('cancel', cancel),
    ]
)