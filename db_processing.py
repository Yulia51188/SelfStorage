from datetime import timedelta, date
from rejson import Client, Path
import logging
import os
from textwrap import dedent

from telegram import ReplyKeyboardMarkup, KeyboardButton

logger = logging.getLogger(__name__)
_database = None

DAYS_IN_MONTH = 30


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


def create_storages_keyboard():
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
                        {stuff_id}. {stuff["name"]} - {stuff["base_price"]} руб. 
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


def create_payment_keyboard(booking_id):
    db = get_database_connection()    
    total_cost = db.jsonget('bookings', Path(f'.{booking_id}.total_cost'))

    keyboard = [
        [KeyboardButton(text=f'Оплатить {total_cost} руб.')],
        [KeyboardButton(text='Отмена')],
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return reply_markup    


def create_qr_code_keyboard(booking_id):

    keyboard = [
        [KeyboardButton(text='Показать QR-код')],
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


def calculate_total_cost(booking):
    db = get_database_connection()
    stuff = db.jsonget(
        'prices',
        Path(f'.{booking["category"]}.{booking["item_id"]}')
    )
    logger.info(f'Calculate total_cost for {stuff}')
    
    if booking['category'] == 'other':
        base_price = stuff['base_price']
        additional_price = stuff['add_one_price']
        additional_count = booking['count'] - 1
        month_price = base_price + additional_price * additional_count
        return month_price * booking['period_length']

    price = stuff['price'][booking['period_type']]
    return price * booking['period_length'] * booking['count']


def get_end_date(start_date_iso, unit, period, correct_day=False):
    start_date = date.fromisoformat(start_date_iso)

    if unit == 'week':
        end_date = start_date + timedelta(weeks=period)
    else:
        end_date = start_date + timedelta(days=period * DAYS_IN_MONTH)

    if correct_day:
        end_date = end_date - timedelta(days=1)
    return end_date.isoformat()


def add_booking(booking):
    db = get_database_connection()   
    booking_id = get_bookings_max_id() + 1
    db.jsonset('bookings', Path(f'.{booking_id}'), booking)
    logger.info(f'Set booking {booking_id} to db: {booking}')
    return booking_id


def convert_to_ruformat(date_iso):
    input_date = date.fromisoformat(date_iso)
    return input_date.strftime('%d.%m.%y')


def create_booking_message(booking):
    message_template = '''\
        Проверьте выбранные параметры бронирования:
        
        Склад: {storage_name} в г. {city}
        Адрес склада: {address}
        
        Категория хранения: {item_name}
        {count_name}: {count}
        
        Период: {period} {period_units}
        Доступ к ячейке с {start_date} по {end_date}
        
        Сумма к оплате: {total_cost} руб. 
        '''

    db = get_database_connection()
    
    storage = db.jsonget('storages', Path(f'.{booking["storage_id"]}'))
    stuff = db.jsonget(
        'prices',
        Path(f'.{booking["category"]}.{booking["item_id"]}')
    )
    
    if booking['category'] == 'other':
        count_name = 'Площадь ячейки для хранения, кв.м.'
    else:
        count_name = 'Количество вещей для хранения'

    if booking['period_type'] == 'week':
        period_units = 'нед.'
    else:
        period_units = 'мес.'

    message_text = message_template.format(
        storage_name=storage['name'],
        city=storage['city'],
        address=storage['address'],
        item_name=stuff['name'],
        count_name=count_name,
        count=booking['count'],
        period=booking['period_length'],
        period_units=period_units,
        start_date=convert_to_ruformat(booking['start_date']),
        end_date=convert_to_ruformat(booking['end_date']),
        total_cost=booking['total_cost'],
    )
    return dedent(message_text)


def get_passport_series_and_number(database, client_id):
    passport_series_and_number = database.jsonget(
                'clients',
                Path(f'.{client_id}.passport')
            )
    return passport_series_and_number


def set_booking_access_code(database, booking_id, access_code):
    database.jsonset(
        'bookings',
        Path(f'.{booking_id}.access_code'),
        access_code
    )


def change_of_payment_status(booking_id):
    db = get_database_connection()    
    
    db.jsonset('bookings', Path(f'.{booking_id}.status'), 'payed')
    booking = db.jsonget('bookings', Path(f'.{booking_id}'))
