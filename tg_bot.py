import logging
import os
from enum import Enum
from textwrap import dedent

from dotenv import load_dotenv
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

import db_processing

logger = logging.getLogger(__name__)
_booking = None


class States(Enum):
    CHOOSE_STORAGE = 1
    CHOOSE_CATEGORY = 2
    CHOOSE_STUFF = 3
    INPUT_COUNT = 4


def start(update, context):
    
    update.message.reply_text(
        dedent('''\
        Привет!
        Я помогу вам арендовать личную ячейку для хранения вещей.
        Давайте посмотрим адреса складов в Москве, чтобы выбрать ближайший!
        '''),
        reply_markup=db_processing.create_stogares_keyboard()
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
        reply_markup=db_processing.create_categories_keyboard()
    )    
    return States.CHOOSE_CATEGORY


def handle_season_choice(update, context):
    add_category_to_booking('season')
    update.message.reply_text(
        'Выберите, какую вещь будете хранить',
        reply_markup=db_processing.create_season_keyboard()
    ) 
    return States.CHOOSE_STUFF


def handle_other_choice(update, context):
    add_category_to_booking('other')
    update.message.reply_text(
        'Выберите, какую вещь будете хранить',
        reply_markup=db_processing.create_other_keyboard()
    )     
    return States.CHOOSE_STUFF


def handle_choose_stuff(update, context):
    add_stuff_to_booking(update.message.text)
    update.message.reply_text(
        'Сколько вещей выбранного типа нужно хранить?'
    )      
    return States.INPUT_COUNT


def create_new_booking(tg_message):
    global _booking

    storage_id, *_ = tg_message.text.split('.')
    logger.info(f'Storage ID is {storage_id}, client ID is {tg_message.chat_id}')
    _booking = {
        'storage_id': storage_id,
        'tg_chat_id': tg_message.chat_id,
    }

    _booking['booking_id'] = db_processing.get_bookings_count()
    logger.info(f'New booking is {_booking}')


def add_category_to_booking(category_name):
    global _booking

    _booking['category'] = category_name
    logger.info(f'Update booking: {_booking}')


def add_stuff_to_booking(button_text):
    global _booking
    
    stuff_id, *_ = button_text.split('.')
    _booking['item_id'] = stuff_id
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
                    handle_choose_stuff
                )
            ],
            States.INPUT_COUNT: [
                MessageHandler(
                    Filters.regex(r'^\d+$'),
                    echo
                ),
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
