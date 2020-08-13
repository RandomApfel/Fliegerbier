from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from time import time
from datetime import datetime
from typing import List, Dict, Tuple
from collections import namedtuple
from asyncio import run, get_event_loop
import sqlalchemy
from .config import DATABASE
from .items import Item


User = namedtuple('User', ['nickname', 'akaflieg_id', 'chat_id'])

if DATABASE.startswith('sqlite'):
    _db = sqlalchemy.create_engine(DATABASE)
else:
    _db = sqlalchemy.create_engine(
        DATABASE,
        pool_size=4, max_overflow=40,
        client_encoding='utf8'
    )

metadata = sqlalchemy.MetaData()
metadata.bind = _db

consumptions = sqlalchemy.Table(
    'consumptions',
    metadata,
    sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column('akaflieg_id', sqlalchemy.Integer),
    sqlalchemy.Column('timestamp', sqlalchemy.Integer),
    sqlalchemy.Column('item_name', sqlalchemy.String),
    sqlalchemy.Column('item_price_at_this_time', sqlalchemy.Float),
    sqlalchemy.Column('gram_alcohol', sqlalchemy.Integer),
)

users = sqlalchemy.Table(
    'users',
    metadata,
    sqlalchemy.Column('chat_id', sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column('nickname', sqlalchemy.String),
    sqlalchemy.Column('akaflieg_id', sqlalchemy.Integer, unique=True),
    sqlalchemy.Column('full_name', sqlalchemy.String),
    sqlalchemy.Column('telegram_names', sqlalchemy.String),
    sqlalchemy.Column('weight', sqlalchemy.Integer)
)

metadata.create_all(_db)


class ConsumptionEntry:
    def __init__(self, timestamp: int, item_name: str, price_at_time: float, gram_alcohol: int = 0):
        self.timestamp = timestamp
        self.item_name = item_name
        self.price_at_time= price_at_time
        self.gram_alcohol = gram_alcohol

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)


class Database:
    def __init__(self):
        pass

    def enter_consumption(self, akaflieg_id: int, item: Item, consumption_time: int = None) -> int:
        if consumption_time is None:
            consumption_time = time()

        query = consumptions.insert().values(
            akaflieg_id=akaflieg_id,
            timestamp=consumption_time,
            item_name=item.name,
            item_price_at_this_time=item.price,
            gram_alcohol=item.alcohol,
        )

        id_query = consumptions.select(consumptions.c.id).where(
            consumptions.c.akaflieg_id == akaflieg_id
        ).order_by(
            consumptions.c.timestamp.desc()
        ).limit(1)

        with _db.connect() as con:
            with con.begin():
                con.execute(query)
                res = con.execute(id_query)
                for line in res:
                    return line['id']

    def remove_consumption(self, rowid: int):
        query = consumptions.delete().where(
            consumptions.c.id == rowid
        )
        with _db.connect() as con:
            con.execute(query)

    def create_user(self, chat_id):
        query = users.insert().values(
            chat_id=chat_id
        )
        with _db.connect() as con:
            con.execute(query)
    
    def get_unauthorized_chat_ids(self) -> List[int]:
        query = users.select(user.c.chat_id).where(
            users.c.akaflieg_id == None
        )
        with _db.connect() as con:
            with con.begin():
                res = con.execute(query)

                res = [
                    r[0] for r in rr
                ]
                return res

    def get_consumer_list(self) -> List['Consumer']:
        query = sqlalchemy.select([users.c.chat_id])

        with _db.connect() as con:
            with con.begin():
                rr = con.execute(query)

                res = [
                    Consumer(r['chat_id']) for r in rr
                ]
                res = sorted(res, key=lambda x: x.nickname)
                return res
    
    def get_consumption_dictionary(
        self,
        from_timestamp: int = 0,
        to_timestamp: int = None
    ) -> Dict[int, Dict[str, Dict[str, int]]]:

        if to_timestamp is None:
            to_timestamp = int(time() + 10000)

        query = sqlalchemy.select([
            consumptions.c.akaflieg_id,
            consumptions.c.item_name,
            consumptions.c.item_price_at_this_time,
        ]).where(
            sqlalchemy.and_(
                consumptions.c.timestamp >= from_timestamp,
                consumptions.c.timestamp < to_timestamp
            )
        )
        with _db.connect() as con:
            with con.begin():
                rr = con.execute(query)

                res = {}
                # res= {2203: {'Bier 0,33L': {'count': 5, 'sum': 5.0}, 'Stilles Wasser': {'count': 2, 'sum': 0.8}}}
                for row in rr:
                    akaflieg_id, item_identifier, item_price_at_this_time = row['akaflieg_id'], row['item_name'], row['item_price_at_this_time']
                    res[akaflieg_id] = res.get(akaflieg_id, {})
                    res[akaflieg_id][item_identifier] = res[akaflieg_id].get(
                        item_identifier, {'count': 0, 'sum': 0}
                    )
                    res[akaflieg_id][item_identifier]['count'] += 1
                    res[akaflieg_id][item_identifier]['sum'] += item_price_at_this_time
                return res


class Consumer:
    def __init__(self, chat_id):
        self.chat_id = int(chat_id)
        self.db = Database()

    @classmethod
    def from_akaflieg_id(cls, akaflieg_id):
        instance = cls(-1)
        query = sqlalchemy.select([users.c.chat_id]).where(
            users.c.akaflieg_id == akaflieg_id
        )
        with _db.connect() as con:
            with con.begin():
                res = con.execute(query)

                for line in res:
                    instance.chat_id = int(line['chat_id'])
                return instance

    
    def _get(self, key):
        with _db.connect() as con:
            with con.begin():
                res = con.execute(
                    sqlalchemy.select([getattr(users.c, key)]).where(
                        users.c.chat_id == self.chat_id
                    )
                )
                for line in res:
                    return line[key]
                return None

    
    def _set(self, key, value):
        with _db.connect() as con:
            con.execute(
                users.update().where(
                    users.c.chat_id == self.chat_id
                ).values(**{key: value})
            )

    @property
    def nickname(self) -> str:
        return self._get('nickname') or '[nicht gesetzt]'

    @property
    def akaflieg_id(self) -> str:
        return self._get('akaflieg_id') or '[nicht gesetzt]'

    @property
    def full_name(self) -> str:
        return self._get('full_name') or '[nicht gesetzt]'

    @property
    def telegram_names(self) -> str:
        return self._get('telegram_names') or '[nicht gesetzt]'

    @property
    def weight(self) -> int:
        return self._get('weight') or 70

    @weight.setter
    def weight(self, value):
        self._set('weight', int(value))

    @nickname.setter
    def nickname(self, value):
        self._set('nickname', value)

    
    def _async_id_change(self, value, old_akaflieg_id):
        with _database_pool.transaction():
            _database_pool.execute(
                'UPDATE item_consumption SET akaflieg_id = :new WHERE akaflieg_id = :old',
                {'new': int(value), 'old': int(old_akaflieg_id)}
            )

    @akaflieg_id.setter
    def akaflieg_id(self, value):
        old_akaflieg_id = self._get('akaflieg_id')

        query_set_new_id = users.update().values(
            akaflieg_id=int(value)
        ).where(
            users.c.chat_id == self.chat_id
        )
        query_change_ids_in_consumptions = consumptions.update().values(
            akaflieg_id=int(value)
        ).where(
            consumptions.c.akaflieg_id == old_akaflieg_id
        )

        with _db.connect() as con:
            with con.begin():
                con.execute(query_set_new_id)
                con.execute(query_change_ids_in_consumptions)
                # commits here
    
    @full_name.setter
    def full_name(self, value):
        self._set('full_name', value)

    def set_telegram_names(self, user):
        s = ''
        if user.username:
            s += '@{} '.format(user.username)
        if getattr(user, 'first_name', None):
            s += '{} '.format(getattr(user, 'first_name'))
        if getattr(user, 'last_name', None):
            s += '{}'.format(getattr(user, 'last_name'))
        self._set('telegram_names', s.strip())

    def consume(self, item: Item) -> int:
        return self.db.enter_consumption(self.akaflieg_id, item)

    def unconsume(self, rowid: int):
        return self.db.remove_consumption(rowid)
    
    
    def user_exists(self) -> bool:
        query = sqlalchemy.select([users.c.chat_id]).where(
            users.c.chat_id == int(self.chat_id)
        )
        with _db.connect() as con:
            with con.begin():
                res = con.execute(query)
                for line in res:
                    return True
                return False

        

    def is_authorized(self) -> bool:
        value = self._get('akaflieg_id')
        return bool(value)

    def create(self):
        self.db.create_user(self.chat_id)

    
    def delete(self):
        query = users.delete().where(
            chat_id=self.chat_id
        )
        with _db.connect() as con:
            con.execute(query)

    def get_consumption_history(self, from_timestamp: int = 0, to_timestamp: int = None) -> List[ConsumptionEntry]:
        if to_timestamp is None:
            to_timestamp = int(time() + 10000)
        
        query = query = sqlalchemy.select([
            consumptions.c.timestamp,
            consumptions.c.item_name,
            consumptions.c.item_price_at_this_time,
            consumptions.c.gram_alcohol,
        ]).where(
            sqlalchemy.and_(
                consumptions.c.akaflieg_id == self.akaflieg_id,
                consumptions.c.timestamp >= from_timestamp,
                consumptions.c.timestamp < to_timestamp,
            )
        )

        with _db.connect() as con:
            with con.begin():
                res = con.execute(query)

                result = []
                for r in res:
                    result.append(
                        ConsumptionEntry(r[0], r[1], r[2], r[3])
                    )
                return result


# must be decorated manually
def is_authorized(respond, chat_id, username, first_name, last_name, user):
    client = Consumer(int(chat_id))

    def none_str(t):
        if t is None:
            return '[nicht gesetzt]'
        return str(t)

    if not client.user_exists():
        from .administration import send_admin_message
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton('Diesen Nutzer commiten', callback_data='commit_{}'.format(chat_id))]
        ])
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
            ),
            reply_markup=reply_markup
        )
        client.create()
        client.set_telegram_names(user)
        respond(
            'Deine Nachricht wurde ignoriert!\n'
            'Du bist noch nicht in der Datenbank.\n'
            'Der Kassenwart wurde über deine Anfrage benachrichtigt.\n'
            'Du wirst benachrichtigt sobald er dich bestätigt.'
        )
        return False

    if not client.is_authorized():
        respond(
            'Deine Nachricht wurde ignoriert, weil du '
            'noch nicht in der Datenbank bist.\n\n'
            'Der Kassenwart weiß bescheid, du kannst ihn '
            'aber auch nochmal kontaktieren.\n'
            'Hierbei könnte deine Chat ID  helfen: {}.'
            .format(chat_id)
        )
        client.set_telegram_names(user)
        return False

    return True

