import logging
from textwrap import dedent
from enum import Enum
import os
from dotenv import load_dotenv
from rejson import Client, Path

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, KeyboardButton
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    # CallbackContext,
)

logger = logging.getLogger(__name__)
_database = None
_booking = None


class States(Enum):
    CHOOSE_STORAGE = 1
    CHOOSE_CATEGORY = 2
    CHOOSE_STUFF = 3


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
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_categories_keyboard():
    keyboard = [
        [KeyboardButton(text='Сезонные вещи')],
        [KeyboardButton(text='Другое')],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


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
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


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
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def start(update, context):
    
    update.message.reply_text(
        dedent('''\
        Привет!
        Я помогу вам арендовать личную ячейку для хранения вещей.
        Давайте посмотрим адреса складов в Москве, чтобы выбрать ближайший!
        '''),
        reply_markup=create_stogares_keyboard()
    )

    return States.CHOOSE_STORAGE


def echo(update, context):
    update.message.reply_text(update.message.text)


def handle_unknown(update, context):
    update.message.reply_text(
        text='Извините, но я вас не понял :(',
    )


def handle_storage_choice(update, context):
    create_new_booking(update.message)
    update.message.reply_text(
        'Что хотите хранить?',
        reply_markup=create_categories_keyboard()
    )    
    return States.CHOOSE_CATEGORY


def handle_season_choice(update, context):
    add_category_to_booking('season')
    update.message.reply_text(
        'Выберите, какую вещь будете хранить',
        reply_markup=create_season_keyboard()
    ) 
    return States.CHOOSE_STUFF


def handle_other_choice(update, context):
    add_category_to_booking('other')
    update.message.reply_text(
        'Выберите, какую вещь будете хранить',
        reply_markup=create_other_keyboard()
    )     
    return States.CHOOSE_STUFF


def create_new_booking(tg_message):
    global _booking

    storage_id, *_ = tg_message.text.split('.')
    logger.info(f'Storage ID is {storage_id}, client ID is {tg_message.chat_id}')
    _booking = {
        'storage_id': storage_id,
        'tg_chat_id': tg_message.chat_id,
    }

    db = get_database_connection()
    _booking['booking_id'] = db.jsonarrlen('bookings', Path.rootPath())
    logger.info(f'New booking is {_booking}')


def add_category_to_booking(category_name):
    global _booking

    _booking['category'] = category_name
    logger.info(f'Update booking: {_booking}')    


def run_bot(tg_token):
    updater = Updater(tg_token)

    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            States.CHOOSE_STORAGE: [
                MessageHandler(
                    Filters.text & ~Filters.command,
                    handle_storage_choice
                )
            ],
            States.CHOOSE_CATEGORY: [
                MessageHandler(
                    Filters.regex('^Сезонные вещи$'),
                    handle_season_choice
                ),
                MessageHandler(
                    Filters.regex('^Другое$'),
                    handle_other_choice
                )
            ],
            States.CHOOSE_STUFF: [
                MessageHandler(
                    Filters.text & ~Filters.command,
                    echo
                )
            ]
        },
        fallbacks=[
            MessageHandler(Filters.text & ~Filters.command, handle_unknown)
        ],
    )
    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    load_dotenv()
    tg_token = os.getenv('TG_TOKEN')

    run_bot(tg_token)


if __name__ == '__main__':
    main()
