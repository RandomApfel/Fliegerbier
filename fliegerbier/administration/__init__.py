from telegram import Bot
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from datetime import datetime
from ..config import ADMINCHAT, BOTTOKEN, DATABASE
from ..decorators import admin_only, patch_telegram_action
from ..database import Database, Consumer
from .commit import commit_handler
from .edit import edit_handler
from .delete import delete_handler
from .rechnung import rechnung, admin_rechnung, admin_rechnung_out


_bot = Bot(BOTTOKEN)


def send_admin_message(text, **kwargs):
    _bot.send_message(text=text, chat_id=ADMINCHAT, **kwargs)
    

@admin_only
@patch_telegram_action
def help_response(respond):
    respond(
        'Hallo Admin.\n'
        '/commit - Ausstehende Eintragungsanträge '
        'annehmen und Akaflieg ID vergeben.\n\n'
        '/backup - Lass dir ein Backup der aktuellen '
        'Datenbank schicken.\n\n'
        '/list - Liste eingetragene Nutzer auf. \n\n'
        '/edit - Ändere den Spitznamen oder die Akaflieg ID '
        'eines eingetragenen Nutzers.\n\n'
        '/delete - Lösche einen Nutzer (Seine Verbrauchs'
        'historie bleibt erhalten).\n\n'
        '/rechnung - Erstelle eine Rechnung für einen Monat.\n\n'
        '/chatid - Bekomme die Chat ID. Nützlich für Nutzer.'
    )


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


@admin_only
@patch_telegram_action
def list_users(respond):
    d = Database()

    user_list = d.get_consumer_list()

    msg = 'Die folgenden Nutzer sind in der Datenbank:\n\n'

    for user in user_list:
        msg += '{}, Aka {}, Chat {}\n'.format(
            user.nickname, user.akaflieg_id, user.chat_id
        )

    respond(msg)

