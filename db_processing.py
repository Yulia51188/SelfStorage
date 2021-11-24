from rejson import Client, Path
import logging
import os

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
    for storage in storages:
        keyboard.append(
            [
                KeyboardButton(
                    text=(f'{storage["storage_id"]}. {storage["name"]}'
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
    prices = db.jsonget('prices', Path.rootPath())
    category_stuffs = prices[0]['other']
    
    keyboard = []
    for stuff in category_stuffs:
        keyboard.append(
            [
                KeyboardButton(
                    text=(f'{stuff["name"]} - {stuff["base_price"]} руб. '
                          f'(добавить еще + {stuff["add_one_price"]} руб.)')
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
    prices = db.jsonget('prices', Path.rootPath())
    category_stuffs = prices[0]['season']
    
    keyboard = []
    for stuff in category_stuffs:
        if stuff["price"]["week"]:
            keyboard.append(
                [
                    KeyboardButton(
                        text=(
                            f'{stuff["item_id"]}. {stuff["name"]} ( '
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
                            f'{stuff["item_id"]}. {stuff["name"]} ( '
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


def get_bookings_count():
    db = get_database_connection()
    return db.jsonarrlen('bookings', Path.rootPath())
