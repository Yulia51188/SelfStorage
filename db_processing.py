from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
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
        _database = Client(
            host=database_host,
            port=database_port,
            password=database_password,
            decode_responses=True
        )
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
    text_template = '''\
        {id}. {name} - {base_price} руб. 
        (за каждый доп. кв. м. + {add_price} руб.)
        '''
    for stuff_id, stuff in category_stuffs.items():
        button_caption = text_template.format(
            id=stuff_id,
            name=stuff['name'],
            base_price=stuff['base_price'],
            add_price=stuff['add_one_price'],
        )
        keyboard.append(
            [KeyboardButton(text=dedent(button_caption))],
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
    week_template = '''\
        {id}. {name} 
        {week_price} руб. в неделю или {month_price} руб. в месяц
        '''
    month_template = '''\
        {id}. {name} 
        {month_price} руб. в месяц
        '''
    for stuff_id, stuff in category_stuffs.items():
        if stuff["price"]["week"]:
            button_caption = week_template.format(
                id=stuff_id,
                name=stuff["name"],
                week_price=stuff["price"]["week"],
                month_price=stuff["price"]["month"],
            )
        else:
            button_caption = month_template.format(
                id=stuff_id,
                name=stuff["name"],
                month_price=stuff["price"]["month"],
            )
        keyboard.append([KeyboardButton(text=dedent(button_caption))])

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
        [KeyboardButton(text='Сменить фамилию')],
        [KeyboardButton(text='Сменить имя')],
        [KeyboardButton(text='Сменить отчетство')],
        [KeyboardButton(text='Сменить паспорт')],
        [KeyboardButton(text='Сменить дату рождения')],
        [KeyboardButton(text='Сменить номер телефона')],
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
        end_date = start_date + relativedelta(months=+period)

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


def get_passport(client_id):
    db = get_database_connection() 
    passport_series_and_number = db.jsonget(
        'clients',
        Path(f'.{client_id}.passport')
    )
    return passport_series_and_number


def set_booking_access_code(booking_id, access_code):
    db = get_database_connection()    
    db.jsonset(
        'bookings',
        Path(f'.{booking_id}.access_code'),
        access_code
    )


def change_of_payment_status(booking_id):
    db = get_database_connection()    
    db.jsonset('bookings', Path(f'.{booking_id}.status'), 'payed')


def add_client_personal_data_to_database(client_id, client_data):
    db = get_database_connection()
    db.jsonset('clients', Path(f'.{client_id}'), client_data)
    new_client = db.jsonget('clients', Path(f'.{client_id}'))
    logger.info(f'Add client to database: {new_client}')
    return new_client


def clear_client_booking(client_id):
    db = get_database_connection()
    db.jsondel(f'b{client_id}', Path.rootPath())
    logger.info(f'Clear {client_id} current booking')


def get_client_current_booking(client_id):
    db = get_database_connection()
    current_booking = db.jsonget(f'b{client_id}', Path.rootPath())
    return current_booking


def set_client_current_booking(client_id, booking):
    db = get_database_connection()
    current_booking = db.jsonset(f'b{client_id}', Path.rootPath(), booking)
    logger.info(f'Update client {client_id} current booking to {booking}')
    return current_booking


def add_stuff_to_booking(client_id, button_text):
    current_booking = get_client_current_booking(client_id)
    stuff_id, *_ = button_text.split('.')
    current_booking['item_id'] = stuff_id
    set_client_current_booking(client_id, current_booking)
    return current_booking


def add_count_to_booking(client_id, count):
    current_booking = get_client_current_booking(client_id)
    current_booking['count'] = int(count)
    set_client_current_booking(client_id, current_booking)
    return current_booking


def create_new_booking(client_id, button_text):
    current_booking = get_client_current_booking(client_id)
    storage_id, *_ = button_text.split('.')
    current_booking = {
        'storage_id': storage_id,
        'client_id': str(client_id),
    }
    set_client_current_booking(client_id, current_booking)
    return current_booking


def add_category_to_booking(client_id, category_name):
    current_booking = get_client_current_booking(client_id)
    current_booking['category'] = category_name
    set_client_current_booking(client_id, current_booking)
    return current_booking


def add_period_type_to_booking(client_id, is_week=False):
    current_booking = get_client_current_booking(client_id)
    current_booking['period_type'] = is_week and 'week' or 'month'
    set_client_current_booking(client_id, current_booking)
    return current_booking


def add_period_length_to_booking(client_id, period_length, start_date=None):
    current_booking = get_client_current_booking(client_id)
    
    current_booking['period_length'] = period_length
    if not start_date:
        current_booking['start_date'] = date.today().isoformat()
    else:
        current_booking['start_date'] = start_date
    set_client_current_booking(client_id, current_booking)
    return current_booking


def add_booking_cost(client_id):
    current_booking = get_client_current_booking(client_id)
    total_cost = calculate_total_cost(current_booking)

    current_booking['total_cost'] = total_cost
    set_client_current_booking(client_id, current_booking)
    return current_booking


def create_new_client(client_id):
    db = get_database_connection()
    new_client = {
        'name': '',
        'surname': '',
        'second_name': '',
        'passport': '',
        'birth_date': '',
        'phone': '',
    }
    db.jsonset(f'c{client_id}', Path.rootPath(), new_client)
    return new_client


def add_booking_id_to_current_booking(client_id, booking_id):
    current_booking = get_client_current_booking(client_id)
    current_booking['booking_id'] = booking_id
    set_client_current_booking(client_id, current_booking)
    return current_booking


def get_current_client(client_id):
    db = get_database_connection()
    current_client = db.jsonget(f'c{client_id}', Path.rootPath())
    return current_client


def update_current_client(client_id, key, new_value):
    db = get_database_connection()
    db.jsonset(f'c{client_id}', Path(f'.{key}'), new_value)
    client = get_current_client(client_id)
    logger.info(f'Update current client {client_id} personal data to {client}')
    return client


def clear_current_client(client_id):
    db = get_database_connection()
    db.jsondel(f'c{client_id}', Path.rootPath())
    logger.info(f'Clear {client_id} current personal data')


def update_current_booking(booking_id, key, new_value):
    db = get_database_connection()
    db.jsonset(f'b{booking_id}', Path(f'.{key}'), new_value)
    booking = get_client_current_booking(booking_id)
    logger.info(f'Update current client {booking_id} personal data to {booking}')
    return booking


def client_param_type(client_id):
    db = get_database_connection()
    current_client = db.jsonget(f'c{client_id}', Path.rootPath())
    for param, value in current_client.items():
        if not value:
            return param
