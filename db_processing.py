import logging
import os
from datetime import date, timedelta
from textwrap import dedent

from dateutil.relativedelta import relativedelta
from redis.exceptions import ResponseError
from rejson import Client, Path

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


def get_storages():
    db = get_database_connection()
    return db.jsonget('storages', Path.rootPath())


def get_prices_by_category(category):
    db = get_database_connection()
    return db.jsonget('prices', Path(f'.{category}'))


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
        
        Размер скидки: {promo_code}%
        Сумма к оплате: {discounted_price} руб.
        
        Если у вас есть промокод, вы можете ввести его,
        нажав на кнопку "Ввести промокод".
        
        Для бронирования нажмите кнопку "Забронировать"
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
        discounted_price=booking['discounted_price'],
        promo_code=booking['promo_code'],
    )
    return dedent(message_text)


def get_discounted_price(booking_id):   
    db = get_database_connection()
    return db.jsonget('bookings', Path(f'.{booking_id}.discounted_price'))


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
    current_booking['promo_code'] = 0
    current_booking['total_cost'] = total_cost
    current_booking['discounted_price'] = total_cost
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


def get_free_cells_count(storage_id, category, item_id):
    db = get_database_connection()
    try:
        free_cells_count = db.jsonget(
            'free_cells',
            Path(f'.storage_{storage_id}.{category}.item_{item_id}.free'),
        )
        return free_cells_count
    except ResponseError:
        return 0


def update_free_cells_count(storage_id, category, item_id, count_reserved):
    previous_count = get_free_cells_count(storage_id, category, item_id)
    db = get_database_connection()       
    db.jsonset(
        'free_cells',
        Path(f'.storage_{storage_id}.{category}.item_{item_id}.free'),
        previous_count - count_reserved,
    )


def is_client_exists(client_id):
    db = get_database_connection()
    try:
        db.jsonget(
            'clients',
            Path(f'.{client_id}'),
        )  
        return True      
    except ResponseError:
        return None


def copy_client_to_current(client_id):
    db = get_database_connection()       
    client = db.jsonget(
        'clients',
        Path(f'.{client_id}'),
    ) 
    db.jsonset(
        f'c{client_id}',
        Path.rootPath(),
        client
    )
    logger.info(f'Load client {client_id} data to current client to verify')


def get_client_bookings(client_id):
    db = get_database_connection()
    if db.jsonget('clients', Path(f'.{client_id}')):
        bookings = db.jsonget('bookings', Path.rootPath())
        client_bookings = dict()
        for booking_id, booking in bookings.items():
            if booking['client_id'] == str(client_id):
                client_bookings[booking_id] = booking
        return client_bookings
    return None


def create_bookings_message(client_bookings):
    db = get_database_connection()
    prices = db.jsonget('prices', Path.rootPath())
    message_text = 'Список ваших бронирований:'
    for booking_id, booking in client_bookings.items():
        storage = db.jsonget('storages', Path(f'.{booking["storage_id"]}'))
        if booking['category'] == 'other':
            message = (
                f'\n\nИдентификационный номер заказа: {booking_id}\nПо адресу'
                f' {storage["address"]} с {booking["start_date"]} '
                f'по {booking["end_date"]} хранятся '
                f'ваши вещи на площади в {booking["count"]} кв.м.'
            )
        if booking['category'] == 'season':
            message = (
                f'\n\nИдентификационный номер заказа: {booking_id}\nПо адресу'
                f' {storage["address"]} с {booking["start_date"]} '
                f'по {booking["end_date"]} хранится '
                f'позиция "{prices["season"][booking["item_id"]]["name"]}" в'
                f' количестве {booking["count"]} штук(и).'
            )
        message_text += message
    return message_text
