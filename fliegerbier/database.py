from sqlite3 import connect
from time import time
from datetime import datetime
from typing import List, Dict, Tuple
from collections import namedtuple
from .config import DATABASE
from .items import Item, item_list, item_lookup


User = namedtuple('User', ['nickname', 'akaflieg_id', 'chat_id'])


class ConsumptionEntry:
    def __init__(self, timestamp: int, item_identifier: str, price_at_time: float):
        self.timestamp = timestamp
        self.item_identifier = item_identifier
        self.price_at_time= price_at_time

    @property
    def item(self) -> Item:
        return item_lookup(self.item_identifier)

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)


class Database:
    def __init__(self):
        self.con = connect(DATABASE)
        self.cur = self.con.cursor()

        self.cur.execute(
            'CREATE TABLE IF NOT EXISTS users '
            '(chat_id INT UNIQUE, nickname TEXT UNIQUE, akaflieg_id TEXT UNIQUE, full_name TEXT)'
        )
        self.cur.execute(
            'CREATE TABLE IF NOT EXISTS item_consumption '
            '(akaflieg_id INT, item_identifier TEXT, item_price_at_this_time FLOAT, timestamp INT)'
        )
        self.con.commit()

    def enter_consumption(self, akaflieg_id: int, item: Item, consumption_time: int = None) -> int:
        if consumption_time is None:
            consumption_time = time()
        self.cur.execute(
            'INSERT INTO item_consumption (akaflieg_id, item_identifier, item_price_at_this_time, timestamp) '
            'VALUES (?, ?, ?, ?)',
            (akaflieg_id, item.identifier, item.price, int(consumption_time))
        )
        self.con.commit()
        return self.cur.lastrowid

    def remove_consumption(self, rowid: int):
        self.cur.execute(
            'DELETE FROM item_consumption WHERE rowid = ?', (rowid, )
        )
        self.con.commit()

    def create_user(self, chat_id):
        self.cur.execute(
            'INSERT INTO users (chat_id) VALUES (?)', (chat_id, )
        )
        self.con.commit()

    def get_unauthorized_chat_ids(self) -> List[int]:
        self.cur.execute(
            'SELECT chat_id FROM users WHERE akaflieg_id IS NULL'
        )
        res = [
            r[0] for r in self.cur.fetchall()
        ]
        return res

    def get_consumer_list(self) -> List['Consumer']:
        self.cur.execute(
            'SELECT chat_id FROM users'
        )
        res = [
            Consumer(r[0]) for r in self.cur.fetchall()
        ]
        res = sorted(res, key=lambda x: x.nickname)
        return res

class Consumer:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.db = Database()

    def _get(self, key):
        cur = self.db.con.cursor()
        cur.execute(
            'SELECT {} FROM users WHERE chat_id = ?'.format(key),
            (self.chat_id, )
        )
        res = cur.fetchone()[0]
        cur.close()
        return res

    def _set(self, key, value):
        cur = self.db.con.cursor()
        cur.execute(
            'UPDATE users SET {} = ? WHERE chat_id = ?'.format(key),
            (value, self.chat_id)
        )
        self.db.con.commit()
        cur.close()

    @property
    def nickname(self) -> str:
        return self._get('nickname')

    @property
    def akaflieg_id(self) -> str:
        return self._get('akaflieg_id')

    @property
    def full_name(self) -> str:
        return self._get('full_name')

    @nickname.setter
    def nickname(self, value):
        self._set('nickname', value)

    @akaflieg_id.setter
    def akaflieg_id(self, value):
        self._set('akaflieg_id', value)
    
    @full_name.setter
    def full_name(self, value):
        self._set('full_name', value)

    def consume(self, item: Item) -> int:
        return self.db.enter_consumption(self.akaflieg_id, item)

    def unconsume(self, rowid: int):
        return self.db.remove_consumption(rowid)
    
    def user_exists(self) -> bool:
        self.db.cur.execute(
            'SELECT count(*) FROM users WHERE chat_id = ?', (self.chat_id, )
        )
        count = self.db.cur.fetchone()[0]
        return (count >= 1)

    def is_authorized(self) -> bool:
        value = self._get('akaflieg_id')
        return bool(value)

    def create(self):
        self.db.create_user(self.chat_id)

    def delete(self):
        self.db.cur.execute(
            'DELETE FROM users WHERE chat_id = ?',
            (self.chat_id, )
        )
        self.db.con.commit()

    def get_stats(self, from_timestamp: int = 0, to_timestamp: int = None) -> Dict[str, Tuple[int, float]]:
        if to_timestamp is None:
            to_timestamp = int(time() + 10000)
        
        res = {}
        #chat_id INT, item_identifier TEXT, item_price_at_this_time FLOAT, timestamp INT
        self.db.cur.execute(
            'SELECT item_identifier, item_price_at_this_time '
            'FROM item_consumption WHERE akaflieg_id = ? '
            'AND timestamp >= ? AND timestamp < ? '
            'ORDER BY timestamp ASC',
            (self.akaflieg_id, from_timestamp, to_timestamp)
        )

        for item_identifier, item_price_at_this_time in self.db.cur.fetchall():
            t = res.get(item_identifier, (0, 0))
            t = (t[0] + 1, t[1] + item_price_at_this_time)
            res[item_identifier] = t

        return res

    def get_consumption_history(self, from_timestamp: int = 0, to_timestamp: int = None) -> List[ConsumptionEntry]:
        if to_timestamp is None:
            to_timestamp = int(time() + 10000)
        self.db.cur.execute(
            'SELECT timestamp, item_identifier, item_price_at_this_time '
            'FROM item_consumption WHERE akaflieg_id = ? '
            'AND timestamp >= ? AND timestamp < ? '
            'ORDER BY timestamp ASC',
            (self.akaflieg_id, from_timestamp, to_timestamp)
        )

        res = self.db.cur.fetchall()
        result = []
        for r in res:
            result.append(
                ConsumptionEntry(r[0], r[1], r[2])
            )
        return result


# must be decorated manually
def is_authorized(respond, chat_id, username, first_name, last_name):
    client = Consumer(chat_id)

    def none_str(t):
        if t is None:
            return '[nicht gesetzt]'
        return str(t)

    if not client.user_exists():
        from .administration import send_admin_message
        send_admin_message(
            'Ein neuer Nutzer hat sich gemeldet.\n'
            'Nutzername: {}, Vorname: {}, Nachname: {}.\n'
            'Die Chat ID lautet {}.\n'
            'Bestätige den Nutzer durch hinzufügen einer Akaflieg ID '
            'mit dem Befehl /commit.'
            .format(
                none_str(username),
                none_str(first_name),
                none_str(last_name),
                chat_id,
            )
        )
        client.create()
        respond(
            'Du bist noch nicht in der Datenbank.\n'
            'Der Kassenwart wurde über deine Anfrage benachrichtigt.\n'
            'Du wirst benachrichtigt sobald er dich bestätigt.'
        )
        return False

    if not client.is_authorized():
        respond(
            'Der Kassenwart weiß bescheid, du kannst ihn '
            'aber auch nochmal kontaktieren.\n'
            'Hierbei könnte deine Chat ID  helfen: {}.'
            .format(chat_id)
        )
        return False

    return True

