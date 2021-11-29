import os
from pprint import pprint

from dotenv import load_dotenv
from rejson import Client, Path

STORAGES = {
    '1': {
        'city': 'Москва',
        'name': 'Сокольники',
        'address': '1-я Сокольническая ул., 4',
    },
    '2': {
        'city': 'Москва',
        'name': 'Центральный',
        'address': 'Кремлёвская наб., 1, стр. 3',        
    },
    '3': {
        'city': 'Москва',
        'name': 'Химки',
        'address': 'ул. Кирова, 24, Химки',
    },
    '4': {
        'city': 'Москва',
        'name': 'Киевская',
        'address': 'площадь Киевского Вокзала, 1',
    },
}

PRICES = {
    'season': {
        '1': {
            'name': 'Лыжи',
            'price': {
                'week': 100,
                'month': 300,
            }
        },
        '2': {
            'name': 'Сноуборд',
            'price': {
                'week': 100,
                'month': 300,
            }
        },
        '3': {
            'name': 'Комплект колёс из 4 шт.',
            'price': {
                'week': None,
                'month': 200,
            }
        },
        '4': {
            'name': 'Велосипед',
            'price': {
                'week': 150,
                'month': 400,
            }
        },
    },
    'other': { 
        '1': {
            'name': 'Ячейка от 1 кв. м. до 10 кв. м.',
            'base_price': 599,
            'add_one_price': 150,
        },
    }
}

FREE_CELLS = {
    'storage_1': {
        'season': {
            'item_1': {
                'total': 20,
                'free': 16,
            },
            'item_2': {
                'total': 10,
                'free': 9,
            },
            'item_3': {
                'total': 15,
                'free': 12,
            },
            'item_4': {
                'total': 10,
                'free': 10,
            },
        },
        'other': {
            'item_1': {
                'total': 100,
                'free': 92,
            },
        },
    },
    'storage_2': {
        'season': {
            'item_1': {
                'total': 20,
                'free': 16,
            },
            'item_3': {
                'total': 15,
                'free': 12,
            },
            'item_4': {
                'total': 10,
                'free': 10,
            },
        },
        'other': {
            'item_1': {
                'total': 50,
                'free': 50,
            },
        },
    },
    'storage_3': {
        'season': {
            'item_1': {
                'total': 20,
                'free': 16,
            },
            'item_2': {
                'total': 10,
                'free': 9,
            },
            'item_3': {
                'total': 15,
                'free': 12,
            },
            'item_4': {
                'total': 5,
                'free': 0,
            },
        },
        'other': {
            'item_1': {
                'total': 100,
                'free': 92,
            },
        },
    },
    'storage_4': {
        'season': {
            'item_1': {
                'total': 20,
                'free': 18,
            },
            'item_2': {
                'total': 10,
                'free': 7,
            },
            'item_3': {
                'total': 18,
                'free': 15,
            },
            'item_4': {
                'total': 15,
                'free': 7,
            },
        },
        'other': {
            'item_1': {
                'total': 150,
                'free': 89,
            },
        },
    },


}

BOOKINGS = {
    '1': {
        'storage_id': '2',
        'client_id': '1967131305',
        'category': 'season',
        'item_id': '4',
        'count': 2,
        'period_type': 'week',
        'period_lenght': 1,
        'start_date': '2021-11-25',
        'end_date': '2021-12-01',
        'total_cost': 600,
        'status': 'created',
    },
    '2': {
        'storage_id': '3',
        'client_id': '1967131305',
        'category': 'other',
        'item_id': '1',
        'count': 5,
        'period_type': 'month',
        'period_lenght': 1,
        'start_date': '2021-11-25',
        'end_date': '2021-12-24',
        'total_cost': 1199,
        'status': 'payed',
        'access_code': 'j2kjhsu7263#hgvdw',
    },   
    '3': {
        'storage_id': '1',
        'client_id': '1967131305',
        'category': 'season',
        'item_id': '1',
        'count': 3,
        'period_type': 'month',
        'period_lenght': 3,
        'start_date': '2021-11-25',
        'end_date': '2021-02-24',
        'total_cost': 1800,
        'status': 'created',
    },  
}

CLIENTS = {
    '1967131305': {
        'name': 'Юлия',
        'passport': '1234987654',
        'birth_date': '2021-01-01',
        'phone': '9117894563',
    },
    '123456789': {
        'name': 'Пушкин Александр Сергеевич',
        'passport': '2901183737',
        'birth_date': '1799-05-26',
        'phone': '9376665214',
    },
}


def get_database_connection():
    database_password = os.getenv("DB_PASSWORD", default=None)
    database_host = os.getenv("DB_HOST", default='localhost')
    database_port = os.getenv("DB_PORT", default=6379)
    database = Client(
        host=database_host,
        port=database_port,
        password=database_password,
        decode_responses=True
    )
    return database


def print_db_content(db):
    bookings = db.jsonget('bookings', Path.rootPath())
    print("\nБронирования")
    pprint(bookings)
    clients = db.jsonget('clients', Path.rootPath())
    print("\nКлиенты")
    pprint(clients)
    storages = db.jsonget('storages', Path.rootPath())
    print("\nСклады")
    pprint(storages)
    prices = db.jsonget('prices', Path.rootPath())
    print("\nЦены на хранение")
    print("--- Сезонные вещи ---")    
    pprint(prices['season'])
    print("--- Другое ---")    
    pprint(prices['other'])


def load_test_data_to_db(db):
    db.jsonset('storages', Path.rootPath(), STORAGES)    
    db.jsonset('prices', Path.rootPath(), PRICES)
    db.jsonset('bookings', Path.rootPath(), BOOKINGS)
    db.jsonset('clients', Path.rootPath(), CLIENTS)


def main():
    load_dotenv()
    db = get_database_connection()

    # TODO: add argparse to set upload or not test data
    load_test_data_to_db(db)
    print_db_content(db)    


if __name__ == '__main__':
    main()
