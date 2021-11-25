import logging
import os
from datetime import date
from enum import Enum
from textwrap import dedent

from dotenv import load_dotenv
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

import db_processing

logger = logging.getLogger(__name__)
_booking = None

MAX_PERIOD = {'season': 6, 'other': 12}


class States(Enum):
    CHOOSE_STORAGE = 1
    CHOOSE_CATEGORY = 2
    CHOOSE_STUFF = 3
    INPUT_COUNT = 4
    INPUT_PERIOD_TYPE = 5
    INPUT_PERIOD_LENGHT = 6
    INVITE_TO_BOOKING = 7


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


def handle_cancel(update, context):
    global _booking
    _booking = None

    update.message.reply_text(
        'Давайте посмотрим адреса складов в Москве, чтобы выбрать ближайший!',
        reply_markup=db_processing.create_stogares_keyboard()
    )
    return States.CHOOSE_STORAGE


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


def handle_input_count(update, context):
    add_count_to_booking(update.message.text)
    is_week = db_processing.is_week_price_available(_booking)

    if is_week:
        update.message.reply_text(
            'Выберите подходящий тариф для оплаты хранения:',
            reply_markup=db_processing.create_period_keyboard()
        )      
        return States.INPUT_PERIOD_TYPE
    
    add_period_type_to_booking(is_week=False)            
    update.message.reply_text(
        'Введите количество месяцев от 1 до 6'
    ) 
    return States.INPUT_PERIOD_LENGHT


def handle_period_type(update, context):
    is_week = update.message.text == 'Неделя'
    add_period_type_to_booking(is_week)
    period_type = is_week and 'недель' or 'месяцев'
    update.message.reply_text(
        f'Введите на сколько {period_type} понадобится хранение. '
    ) 
    return States.INPUT_PERIOD_LENGHT


def handle_period_length(update, context):
    global _booking
    
    input_period = int(update.message.text)
    max_period = MAX_PERIOD[_booking['category']]
    if (_booking['period_type'] == 'month' and input_period > max_period):
        update.message.reply_text(
            f'Максимальный период хранения {max_period} месяцев. '
            'Введите период еще раз')
        return States.INPUT_PERIOD_LENGHT
    
    add_period_length_to_booking(input_period)
    add_booking_cost()

    # TO DO: create pretty message with booking info
    update.message.reply_text(
        f'''
        Ваше бронирование:
        {_booking}
        ''',
        reply_markup=db_processing.create_booking_keyboard()
    )
    return States.INVITE_TO_BOOKING


def create_new_booking(tg_message):
    global _booking

    storage_id, *_ = tg_message.text.split('.')
    logger.info(f'Storage ID is {storage_id}, client ID is {tg_message.chat_id}')
    _booking = {
        'storage_id': storage_id,
        'tg_chat_id': tg_message.chat_id,
    }

    _booking['booking_id'] = str(db_processing.get_bookings_max_id() + 1)
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


def add_count_to_booking(count):
    global _booking

    _booking['count'] = int(count)
    logger.info(f'Update booking: {_booking}')


def add_period_type_to_booking(is_week=False):
    global _booking

    _booking['period_type'] = is_week and 'week' or 'month'
    logger.info(f'Update booking: {_booking}')


def add_period_length_to_booking(period_lenght, start_date=None):
    global _booking

    _booking['period_lenght'] = period_lenght

    if not start_date:
        _booking['start_date'] = date.today().strftime('%d.%m.%y')
    else:
        _booking['start_date'] = start_date
    logger.info(f'Update booking: {_booking}')    


def add_booking_cost():
    # TO DO: add cost calculation
    total_cost = 1000

    global _booking
    _booking['total_cost'] = total_cost
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
                    Filters.regex(r'^[1-9]+$'),
                    handle_input_count
                ),
            ],
            States.INPUT_PERIOD_TYPE: [
                MessageHandler(
                    Filters.regex('^Неделя$'),
                    handle_period_type
                ),
                MessageHandler(
                    Filters.regex('^Месяц$'),
                    handle_period_type
                ),
            ],
            States.INPUT_PERIOD_LENGHT: [
                MessageHandler(
                    Filters.regex(r'^[1-9]+$'),
                    handle_period_length
                ),
            ],
            States.INVITE_TO_BOOKING: [
                MessageHandler(
                    Filters.regex('^Забронировать$'),
                    echo
                ),
       
            ]
        },
        fallbacks=[
            MessageHandler(Filters.regex('^Отмена$'), handle_cancel), 
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
