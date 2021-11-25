from rejson import Client, Path
import logging
import os
from textwrap import dedent

from telegram import ReplyKeyboardMarkup, KeyboardButton

logger = logging.getLogger(__name__)
_database = None


def get_database_connection():
    """Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан."""
    global _database
    if _database is None:
        database_password = os.getenv("DB_PASSWORD", default=None)
        database_host = os.getenv("DB_HOST", default='localhost')
        database_port = os.getenv("DB_PORT", default=6379)
        _database = Client(host=database_host, port=database_port,
            password=database_password, decode_responses=True)
    return _database


def create_stogares_keyboard():
    db = get_database_connection()
    storages = db.jsonget('storages', Path.rootPath())
    keyboard = []
    for storage_id, storage in storages.items():
        keyboard.append(
            [
                KeyboardButton(
                    text=(f'{storage_id}. {storage["name"]}'
                          f'({storage["address"]})')
                ),
            ],
        )
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return reply_markup


def create_categories_keyboard():
    keyboard = [
        [KeyboardButton(text='Сезонные вещи')],
        [KeyboardButton(text='Другое')],
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return reply_markup


def create_other_keyboard():
    db = get_database_connection()
    category_stuffs = db.jsonget('prices', Path('.other'))
    
    keyboard = []
    for stuff_id, stuff in category_stuffs.items():
        keyboard.append(
            [
                KeyboardButton(
                    text=(dedent(f'''\
                        {stuff["name"]} - {stuff["base_price"]} руб. 
                        (за каждый доп. кв. м. + {stuff["add_one_price"]} руб.)
                        '''
                    ))
                ),
            ],
        )
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return reply_markup


def create_season_keyboard():
    db = get_database_connection()
    category_stuffs = db.jsonget('prices', Path('.season'))
    
    keyboard = []
    for stuff_id, stuff in category_stuffs.items():
        if stuff["price"]["week"]:
            keyboard.append(
                [
                    KeyboardButton(
                        text=(
                            f'{stuff_id}. {stuff["name"]} ( '
                            f'{stuff["price"]["week"]} руб. в неделю или '
                            f'{stuff["price"]["month"]} руб. в месяц)'
                        )
                    )
                ],
            )
        else:
            keyboard.append(
                [
                    KeyboardButton(
                        text=(
                            f'{stuff_id}. {stuff["name"]} ( '
                            f'{stuff["price"]["month"]} руб. в месяц)'
                        )
                    )
                ],
            )  
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return reply_markup


def create_period_keyboard():
    keyboard = [[
        KeyboardButton(text='Неделя'),
        KeyboardButton(text='Месяц'),
    ]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return reply_markup


def create_booking_keyboard():
    keyboard = [
        [KeyboardButton(text='Забронировать')],
        [KeyboardButton(text='Отмена')],
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return reply_markup    


def get_bookings_max_id():
    db = get_database_connection()
    ids = [int(booking_id) for booking_id in 
           db.jsonobjkeys('bookings', Path.rootPath())]
    return max(ids)    


def is_week_price_available(booking):
    if booking["category"] == 'other':
        return False
    db = get_database_connection()
    chosen_stuff = db.jsonget('prices', Path(f'.season.{booking["item_id"]}'))
    return chosen_stuff['price']['week']
