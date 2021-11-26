import logging
import os
from datetime import date
from enum import Enum
from textwrap import dedent

from dotenv import load_dotenv

from telegram import LabeledPrice
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater, PreCheckoutQueryHandler)

import access_qrcode as qr
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
    INPUT_PERIOD_LENGTH = 6
    INVITE_TO_BOOKING = 7
    INPUT_SERNAME = 8
    INPUT_SECOND_NAME = 9
    INPUT_PASSPORT = 10
    INPUT_BIRTH_DATE = 11
    INPUT_PHONE = 12
    ADD_CLIENT_TO_DB = 13
    PAYMENT_PART_1 = 14
    PAYMENT_PART_2 = 15
    CREATE_QR = 16


def start(update, context):
    global _booking
    _booking = None

    update.message.reply_text(
        dedent('''\
        Привет!
        Я помогу вам арендовать личную ячейку для хранения вещей.
        Давайте посмотрим адреса складов в Москве, чтобы выбрать ближайший!
        '''),
        reply_markup=db_processing.create_storages_keyboard()
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
        reply_markup=db_processing.create_storages_keyboard()
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
        'Выберите, какую вещи какого типа будете хранить',
        reply_markup=db_processing.create_season_keyboard()
    ) 
    return States.CHOOSE_STUFF


def handle_other_choice(update, context):
    add_category_to_booking('other')
    update.message.reply_text(
        'Выберите тип ячейки для хранения',
        reply_markup=db_processing.create_other_keyboard()
    )     
    return States.CHOOSE_STUFF


def handle_choose_stuff(update, context):
    add_stuff_to_booking(update.message.text)
    
    if _booking['category'] == 'other':
        message_text = 'Введите необходимую площадь ячейки от 1 кв.м.'
    else:
        message_text = 'Введите количество вещей для хранения'   
    
    update.message.reply_text(message_text)      
    return States.INPUT_COUNT


def handle_input_count(update, context):
    global _booking

    add_count_to_booking(update.message.text)
    is_week = db_processing.is_week_price_available(_booking)

    if is_week:
        update.message.reply_text(
            'Выберите, в чем будет измерятся период хранения: недели или месяцы?',
            reply_markup=db_processing.create_period_keyboard()
        )      
        return States.INPUT_PERIOD_TYPE
    
    add_period_type_to_booking(is_week=False)            
    period_type = is_week and 'недель' or 'месяцев'
    update.message.reply_text(
        f'Введите на сколько {period_type} понадобится хранение'
    ) 
    return States.INPUT_PERIOD_LENGTH


def handle_period_type(update, context):
    is_week = update.message.text == 'Неделя'
    add_period_type_to_booking(is_week)
    period_type = is_week and 'недель' or 'месяцев'
    update.message.reply_text(
        f'Введите на сколько {period_type} понадобится хранение'
    ) 
    return States.INPUT_PERIOD_LENGTH


def handle_period_length(update, context):
    global _booking
    
    input_period = int(update.message.text)
    max_period = MAX_PERIOD[_booking['category']]
    if (_booking['period_type'] == 'month' and input_period > max_period):
        update.message.reply_text(
            f'Максимальный период хранения {max_period} месяцев. '
            'Введите период еще раз')
        return States.INPUT_PERIOD_LENGTH
    
    add_period_length_to_booking(input_period)
    add_booking_cost()
    _booking['end_date'] = db_processing.get_end_date(
        _booking['start_date'],
        _booking['period_type'],
        _booking['period_length'],
    )

    # TO DO: create pretty message with booking info
    update.message.reply_text(
        db_processing.create_booking_message(_booking),
        reply_markup=db_processing.create_booking_keyboard()
    )
    return States.INVITE_TO_BOOKING


def handle_confirm_booking(update, context):
    global _booking
    
    _booking['status'] = 'created'
    booking_id = db_processing.add_booking(_booking)
    _booking['booking_id'] = booking_id

    update.message.reply_text(
        dedent(f'''\
            Бронирование подтверждено.
            Номер заказа: {booking_id}.
            
            Для оплаты вам нужно указать свои личные данные
            
            Введите ваше Имя'''),
    )
    create_new_client()
    
    return States.INPUT_SERNAME


def handle_input_sername(update, context):
    global _client
    _client['name'] = update.message.text
    
    update.message.reply_text(
        f'Введите вашу Фамилию'
    )
    return States.INPUT_SECOND_NAME


def handle_input_second_name(update, context):
    global _client
    _client['sername'] = update.message.text
     
    update.message.reply_text(
        f'Введите ваше Отчество'
    )
    return States.INPUT_PASSPORT


def handle_input_passport(update, context):
    global _client
    _client['second_name'] = update.message.text
    
    update.message.reply_text(
        f'Введите серию и номер паспорта слитно'
    )
    return States.INPUT_BIRTH_DATE


def handle_input_birth_date(update, context):
    global _client
    _client['passport'] = update.message.text
    
    update.message.reply_text(
        dedent(f'''\
            Введите свою дату рождения в формате
            ДД/ММ/ГГГГ'''))
    
    return States.INPUT_PHONE


def handle_input_phone(update, context):
    global _client
    _client['birth_date'] = update.message.text
    
    update.message.reply_text(
        dedent(f'''\
            Введите свой номер телефона в формате:
            891144442233'''))
    
    return States.ADD_CLIENT_TO_DB


def handle_add_client_to_db(update, context):
    global _client, _booking
    client_id = _booking["client_id"]
    booking_id = _booking['booking_id']
    _client['phone'] = update.message.text
    db_processing.add_client_to_booking(_client, client_id)
    _client = None
    
    update.message.reply_text(
        dedent('''\
            Ваши контактные данные записаны.
            Для начала оплаты нажмите кнопку "Оплата"'''),
        reply_markup=db_processing.create_payment_keyboard(booking_id)
    )
 
    return States.PAYMENT_PART_1


def create_new_booking(tg_message):
    global _booking

    storage_id, *_ = tg_message.text.split('.')
    _booking = {
        'storage_id': storage_id,
        'client_id': str(tg_message.chat_id),
    }
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


def add_period_length_to_booking(period_length, start_date=None):
    global _booking

    _booking['period_length'] = period_length

    if not start_date:
        _booking['start_date'] = date.today().isoformat()
    else:
        _booking['start_date'] = start_date
    logger.info(f'Update booking: {_booking}')    


def add_booking_cost():
    global _booking
    total_cost = db_processing.calculate_total_cost(_booking)

    _booking['total_cost'] = total_cost
    logger.info(f'Update booking: {_booking}')   


def create_new_client():
    global _client
    
    _client = {
        'name': '',
        'sername': '',
        'second_name': '',
        'passport': '',
        'birth_date': '',
        'phone': '',
    }


def handle_qrcode(update, context):
    global _booking

    db = db_processing.get_database_connection()


    if _booking['status'] == 'payed':
        client_id = _booking["client_id"]
        passport_series_and_number = db_processing.get_passport_series_and_number(db, client_id)
        
        access_code = qr.create_access_code(passport_series_and_number)
        _booking["access_code"] = access_code

        db_processing.set_booking_access_code(
            db, _booking["booking_id"],
            access_code
        )

        message_text = (
            f'Вот ваш электронный ключ для доступа к вашему личному складу. '
            f'Вы сможете попасть на склад в любое время в период '
            f'с {_booking["start_date"]} по {_booking["end_date"]}'
        )
        context.bot.send_message(chat_id=client_id, text=message_text)

        with open(qr.create_qrcode(access_code), 'rb') as qrcode_image:
            context.bot.send_photo(chat_id=client_id, photo=qrcode_image)
        
    _booking = None
    return States.CHOOSE_STORAGE


def start_without_shipping_callback(update, context):
    """Sends an invoice without shipping-payment."""
    global _booking, provider_token
    
    chat_id = update.message.chat_id
    
    title = "Оплата бронирования"
    description = f"Оплата категории {_booking['category']}"
    payload = "Fuppergupper"
    currency = "RUB"
    price = _booking['total_cost']
    prices = [LabeledPrice("Test", price * 100)]
    
    context.bot.send_invoice(
        chat_id, title, description, payload, provider_token, currency, prices
    )
    return States.PAYMENT_PART_2

def precheckout_callback(update, context):
    """Answers the PreQecheckoutQuery"""
    global _booking
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != 'Fuppergupper':
        # answer False pre_checkout_query
        query.answer(ok=False, error_message="Something went wrong...")
        _booking['status'] = 'payed'
    else:
        query.answer(ok=True)


def successful_payment_callback(update, context):
    global _booking
    
    booking_id = _booking['booking_id']
    client_id = _booking["client_id"]
    
    _booking['status'] = 'payed'
    db_processing.change_of_payment_status(booking_id, client_id)
    update.message.reply_text(
        dedent(f'Оплата прошла успешно'),
        reply_markup=db_processing.create_qr_code_keyboard(booking_id)
    )
    return States.CREATE_QR

    

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
            States.INPUT_PERIOD_LENGTH: [
                MessageHandler(
                    Filters.regex(r'^[1-9]+$'),
                    handle_period_length
                ),
            ],
            States.INVITE_TO_BOOKING: [
                MessageHandler(
                    Filters.regex('^Забронировать$'),
                    handle_confirm_booking
                ),
       
            ],
            States.INPUT_SERNAME: [
                MessageHandler(
                    Filters.text & ~Filters.command,
                    handle_input_sername
                ),
       
            ],
            States.INPUT_SECOND_NAME: [
                MessageHandler(
                    Filters.text & ~Filters.command,
                    handle_input_second_name
                ),
       
            ],
            States.INPUT_PASSPORT: [
                MessageHandler(
                    Filters.text & ~Filters.command,
                    handle_input_passport
                ),
       
            ],
            States.INPUT_BIRTH_DATE: [
                MessageHandler(
                    Filters.text & ~Filters.command,
                    handle_input_birth_date
                ),
       
            ],
            States.INPUT_PHONE: [
                MessageHandler(
                    Filters.text & ~Filters.command,
                    handle_input_phone
                ),
       
            ],
            States.ADD_CLIENT_TO_DB: [
                MessageHandler(
                    Filters.text & ~Filters.command,
                    handle_add_client_to_db
                ),
       
            ],
            States.PAYMENT_PART_1: [
                MessageHandler(
                    Filters.regex('^Оплатить'),
                    start_without_shipping_callback
                ),
            ],
            States.PAYMENT_PART_2: [
                MessageHandler(
                    Filters.successful_payment,
                    successful_payment_callback
                ),
            ],
            
            States.CREATE_QR: [
                MessageHandler(
                    Filters.regex('^Показать QR-код'),
                    handle_qrcode
                ),               
            ]

        },
        fallbacks=[
            CommandHandler('start', start),
            MessageHandler(Filters.regex('^Отмена$'), handle_cancel), 
            MessageHandler(Filters.text & ~Filters.command, handle_unknown)
        ],
    )
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    
    updater.start_polling()
    updater.idle()


def main():
    global provider_token
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    load_dotenv()
    tg_token = os.getenv('TG_TOKEN')
    provider_token = os.environ['PROVIDER_TOKEN']

    run_bot(tg_token)


if __name__ == '__main__':
    main()
