import os

from dotenv import load_dotenv
from rejson import Client, Path

_database = None
storages = [
    {
        'storage_id': 1,
        'city': 'Moscow',
        'name': 'Склад Сокольники',
        'address': '1-я Сокольническая ул., 4',
    },
    {
        'storage_id': 2,
        'city': 'Moscow',
        'name': 'Склад Центральный',
        'address': 'Кремлёвская наб., 1, стр. 3',        
    },
    {
        'storage_id': 3,
        'city': 'Moscow',
        'name': 'Склад Химки',
        'address': 'ул. Кирова, 24, Химки',
    },
    {
        'storage_id': 4,
        'city': 'Moscow',
        'name': 'Склад Киевская',
        'address': 'площадь Киевского Вокзала, 1',
    },
]

prices = [{
    'season': [
        {
            'item_id': 1,
            'name': 'Лыжи',
            'price': {
                'week': 100,
                'month': 300,
            }
        },
        {
            'item_id': 2,
            'name': 'Сноуборд',
            'price': {
                'week': 100,
                'month': 300,
            }
        },
        {
            'item_id': 3,
            'name': 'Колёса 4 шт.',
            'price': {
                'week': None,
                'month': 200,
            }
        },
        {
            'item_id': 4,
            'name': 'Велосипед',
            'price': {
                'week': 150,
                'month': 400,
            }
        }
    ],
    'other': [
        {
            'item_id': 1,
            'name': 'Ячейка 1 кв. м.',
            'base_price': 599,
            'add_one_price': 150,
        },

    ],
}]


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


def main():
    load_dotenv()
    db = get_database_connection()
    db.jsonset('storages', Path.rootPath(), storages)    
    print(db.jsonget('prices', Path.rootPath()))
    db.jsonset('prices', Path.rootPath(), prices)
    print(db.jsonget('storages', Path.rootPath()))
    db.jsonset('bookings', Path.rootPath(), [])
    print(db.jsonget('bookings', Path.rootPath()))


if __name__ == '__main__':
    main()
