import logging
import os
from enum import Enum
from textwrap import dedent

from dotenv import load_dotenv

from telegram import LabeledPrice
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater, PreCheckoutQueryHandler)

import access_qrcode as qr
import db_processing
import check_input


logger = logging.getLogger(__name__)

MAX_PERIOD = {'season': 6, 'other': 12}
BOT_PAYLOAD = 'StuffStorageBot'


class States(Enum):
    CHOOSE_STORAGE = 1
    CHOOSE_CATEGORY = 2
    CHOOSE_STUFF = 3
    INPUT_COUNT = 4
    INPUT_PERIOD_TYPE = 5
    INPUT_PERIOD_LENGTH = 6
    INVITE_TO_BOOKING = 7
    INPUT_SURNAME = 8
    INPUT_NAME = 9
    INPUT_SECOND_NAME = 10
    INPUT_PASSPORT = 11
    INPUT_BIRTH_DATE = 12
    INPUT_PHONE = 13
    PAYMENT = 14
    CLIENT_VERIFY = 15
    REMOVE_CLIENT_INFO = 16
    
    
def start(update, context):
    
    db_processing.clear_client_booking(update.message.chat_id)
    db_processing.clear_current_client(update.message.chat_id)

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
    db_processing.clear_client_booking(update.message.chat_id)
    db_processing.clear_current_client(update.message.chat_id)

    update.message.reply_text(
        'Давайте посмотрим адреса складов в Москве, чтобы выбрать ближайший!',
        reply_markup=db_processing.create_storages_keyboard()
    )
    return States.CHOOSE_STORAGE


def handle_storage_choice(update, context):
    db_processing.create_new_booking(
        update.message.chat_id,
        update.message.text,
    )
    update.message.reply_text(
        'Что хотите хранить?',
        reply_markup=db_processing.create_categories_keyboard()
    )    
    return States.CHOOSE_CATEGORY


def handle_season_choice(update, context):
    db_processing.add_category_to_booking(
        update.message.chat_id,
        'season',
    )
    update.message.reply_text(
        'Выберите, вещи какого типа будете хранить',
        reply_markup=db_processing.create_season_keyboard()
    ) 
    return States.CHOOSE_STUFF


def handle_other_choice(update, context):
    db_processing.add_category_to_booking(
        update.message.chat_id,
        'other',
    )
    update.message.reply_text(
        'Выберите тип ячейки для хранения',
        reply_markup=db_processing.create_other_keyboard()
    )     
    return States.CHOOSE_STUFF


def handle_choose_stuff(update, context):
    current_booking = db_processing.add_stuff_to_booking(
        update.message.chat_id,
        update.message.text,
    )

    if current_booking['category'] == 'other':
        message_text = 'Введите необходимую площадь ячейки от 1 до 10 кв.м.'
    else:
        message_text = 'Введите количество вещей для хранения'   
    
    update.message.reply_text(message_text)      
    return States.INPUT_COUNT


def handle_input_count(update, context):
    current_booking = db_processing.add_count_to_booking(
        update.message.chat_id,
        update.message.text,
    )

    input_count = int(update.message.text)
    if input_count < 1 or input_count > 10:
        if current_booking['category'] == 'other':
            message_begin = 'Доступная площадь ячейки от 1 до 10 кв.м.'
        else:
            message_begin = 'Доступное количество вещей от 1 до 10.'   
    
        update.message.reply_text(f'{message_begin} Введите еще раз')      
        return States.INPUT_COUNT       

    is_week = db_processing.is_week_price_available(current_booking)

    if is_week:
        update.message.reply_text(
            'Выберите, в чем будет измерятся период хранения: недели или месяцы?',
            reply_markup=db_processing.create_period_keyboard()
        )      
        return States.INPUT_PERIOD_TYPE
    
    db_processing.add_period_type_to_booking(
        update.message.chat_id,
        is_week=False
    )            
    period_type = is_week and 'недель' or 'месяцев'
    update.message.reply_text(
        f'Введите на сколько {period_type} понадобится хранение'
    ) 
    return States.INPUT_PERIOD_LENGTH


def handle_period_type(update, context):
    is_week = update.message.text == 'Неделя'
    db_processing.add_period_type_to_booking(
        update.message.chat_id,
        is_week,
    )
    period_type = is_week and 'недель' or 'месяцев'
    update.message.reply_text(
        f'Введите на сколько {period_type} понадобится хранение'
    ) 
    return States.INPUT_PERIOD_LENGTH


def handle_period_length(update, context):    
    input_period = int(update.message.text)
    
    if input_period < 1:
        update.message.reply_text('Минимальный период хранения - 1 месяц. '
            'Введите период еще раз')
        return States.INPUT_PERIOD_LENGTH

    current_booking = db_processing.get_client_current_booking(
        update.message.chat_id
    )

    max_period = MAX_PERIOD[current_booking['category']]
    if (current_booking['period_type'] == 'month' and input_period > max_period):
        update.message.reply_text(
            f'Максимальный период хранения {max_period} месяцев. '
            'Введите период еще раз')
        return States.INPUT_PERIOD_LENGTH
    
    current_booking = db_processing.add_period_length_to_booking(
        update.message.chat_id,
        input_period,
    )
    current_booking = db_processing.add_booking_cost(update.message.chat_id)
    current_booking['end_date'] = db_processing.get_end_date(
        current_booking['start_date'],
        current_booking['period_type'],
        current_booking['period_length'],
    )
    db_processing.update_current_booking(
        update.message.chat_id,
        'end_date',
        current_booking['end_date'],
    )

    update.message.reply_text(
        db_processing.create_booking_message(current_booking),
        reply_markup=db_processing.create_booking_keyboard()
    )
    return States.INVITE_TO_BOOKING


def handle_confirm_booking(update, context):

    current_booking = db_processing.get_client_current_booking(
        update.message.chat_id
    )

    current_booking['status'] = 'created'
    booking_id = db_processing.add_booking(current_booking)
    
    db_processing.add_booking_id_to_current_booking(
        update.message.chat_id,
        booking_id,
    )

    update.message.reply_text(
        dedent(f'''\
            Бронирование подтверждено.
            Номер заказа: {booking_id}.
            
            Для оплаты вам нужно указать свои личные данные
            
            Введите вашу Фамилию'''),
    )
    db_processing.create_new_client(update.message.chat_id)
    
    return States.INPUT_SURNAME


def handle_input_surname(update, context):
    surname = update.message.text
    if not check_input.check_ru_letters(surname):
        update.message.reply_text(
            dedent(f'''\
                Вы ввели некорректную фамилию. Используйте только кирилицу.
                Вы ввели: {surname}
                Попробуйте еще раз.'''))
        return States.INPUT_SURNAME

    db_processing.update_current_client(
        update.message.chat_id,
        'surname',
        surname.title()
    )
    
    update.message.reply_text(
        'Введите ваше Имя'
    )
    return States.INPUT_NAME


def handle_input_name(update, context):
    name = update.message.text
    if not check_input.check_ru_letters(name):
        update.message.reply_text(
            dedent(f'''\
                Вы ввели некорректное имя. Используйте только кирилицу.
                Вы ввели: {name}
                Попробуйте еще раз.'''))
        return States.INPUT_NAME
    
    db_processing.update_current_client(
        update.message.chat_id,
        'name',
        name.title()
    )
     
    update.message.reply_text(
        'Введите ваше Отчество'
    )
    return States.INPUT_SECOND_NAME


def handle_input_second_name(update, context):
    second_name = update.message.text
    if not check_input.check_ru_letters(second_name):
        update.message.reply_text(
        dedent(f'''\
            Вы ввели некорректное отчество. Используйте только кирилицу.
            Вы ввели: {second_name}
            Попробуйте еще раз.'''))
        return States.INPUT_SECOND_NAME
    
    db_processing.update_current_client(
        update.message.chat_id,
        'second_name',
        second_name.title()
    )

    update.message.reply_text(
    dedent('''\
        Введите серию и номер паспорта слитно.
        Принимается только пасспорт РФ, состоящий из цифр.
        В зависимости от пасспорта в нем может быть 9 или 10 цифр.'''))
    return States.INPUT_PASSPORT


def handle_input_passport(update, context):
    passport = update.message.text
    if not check_input.check_passport(passport):
        update.message.reply_text(
        dedent(f'''\
            Вы ввели некорректный номер паспорта.
            Вы ввели: {passport}
            Попробуйте еще раз.'''))
        return States.INPUT_PASSPORT

    db_processing.update_current_client(
        update.message.chat_id,
        'passport',
        passport
    )
    
    update.message.reply_text(
        dedent('''\
            Введите свою дату рождения в формате
            ДД ММ ГГГГ
            Значения вводятся через пробел.'''))
    
    return States.INPUT_BIRTH_DATE


def handle_input_birth_date(update, context):
    birth_date = update.message.text
    if not check_input.check_birth_date(birth_date):
        update.message.reply_text(
        dedent(f'''\
            Вы ввели некорректню дату рождения.
            Вы ввели: {birth_date}
            Попробуйте еще раз.'''))
        return States.INPUT_BIRTH_DATE
    
    db_processing.update_current_client(
        update.message.chat_id,
        'birth_date',
        update.message.text
    )

    update.message.reply_text(
        dedent('''\
            Введите свой номер телефона.
            Принимаются номера только Российских операторов, состоящие из 11 цифр, включая код старны.
            Номер надо вводить через +7.
            
            Пример: +7 911 111 22 33
            '''))
    
    return States.INPUT_PHONE

def handle_input_phone(update, context):
    phone = update.message.text
    client_id = update.message.chat_id

    if not check_input.check_phone(phone):
        update.message.reply_text(
        dedent(f'''\
            Вы ввели некорректный номер телефона.
            Вы ввели: {phone}
            Попробуйте еще раз.'''))
        return States.INPUT_PHONE

    db_processing.update_current_client(
        update.message.chat_id,
        'phone',
        phone
    )
    handle_client_verify(update, context)
    return States.CLIENT_VERIFY
    db_processing.add_client_personal_data_to_database(
        client_id,
        current_client
    )
    db_processing.clear_current_client(client_id)
    
    current_booking = db_processing.get_client_current_booking(client_id)
    update.message.reply_text(
        dedent('''\
            Ваши контактные данные записаны.
            Для начала оплаты нажмите кнопку "Оплата"'''),
        reply_markup=db_processing.create_payment_keyboard(
            current_booking['booking_id'])
    )
 
    return States.PAYMENT_PART_1


def handle_qrcode(update, context):
    
    current_booking = db_processing.get_client_current_booking(
        update.message.chat_id)

    if current_booking['status'] == 'payed':
        client_id = update.message.chat_id
        passport_series_and_number = db_processing.get_passport(client_id)
        
        access_code = qr.create_access_code(passport_series_and_number)
        current_booking["access_code"] = access_code

        db_processing.set_booking_access_code(
            current_booking["booking_id"],
            access_code
        )

        message_text = (
            f'Вот ваш электронный ключ для доступа к вашему личному складу. '
            f'Вы сможете попасть на склад в любое время в период '
            f'с {current_booking["start_date"]} по {current_booking["end_date"]}'
        )
        context.bot.send_message(chat_id=client_id, text=message_text)

        qrcode_image_path = qr.create_qrcode(access_code)
        with open(qrcode_image_path, 'rb') as qrcode_image:
            context.bot.send_photo(chat_id=client_id, photo=qrcode_image)
        os.remove(qrcode_image_path)

    return handle_cancel(update, context)


def start_without_shipping_callback(update, context):
    """Sends an invoice without shipping-payment."""
    global provider_token
    
    client_id = update.message.chat_id
    current_booking = db_processing.get_client_current_booking(client_id)
    
    title = "Оплата бронирования"
    description = f"Оплата категории {current_booking['category']}"
    payload = BOT_PAYLOAD
    currency = "RUB"
    price = current_booking['total_cost']
    prices = [LabeledPrice("Test", price * 100)]
    
    context.bot.send_invoice(client_id, title, description, payload,
                             provider_token, currency, prices)
    return States.PAYMENT_PART_2


def precheckout_callback(update, context):
    """Answers the PreQecheckoutQuery"""
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != BOT_PAYLOAD:
        # answer False pre_checkout_query
        query.answer(ok=False, error_message="Something went wrong...")

    else:
        query.answer(ok=True)


def successful_payment_callback(update, context):
    client_id = update.message.chat_id
    current_booking = db_processing.get_client_current_booking(client_id)
    
    db_processing.update_current_booking(
        client_id,
        'status',
        'payed'
    )
    db_processing.change_of_payment_status(current_booking['booking_id'])
    
    update.message.reply_text('Оплата прошла успешно')
    
    handle_qrcode(update, context)
    return States.CHOOSE_STORAGE


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
                    Filters.regex(r'^[0-9]+$'),
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
                    Filters.regex(r'^[0-9]+$'),
                    handle_period_length
                ),
            ],
            States.INVITE_TO_BOOKING: [
                MessageHandler(
                    Filters.regex('^Забронировать$'),
                    handle_confirm_booking
                ),
       
            ],
            States.INPUT_SURNAME: [
                MessageHandler(
                    Filters.text & ~Filters.command,
                    handle_input_surname
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
    
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    load_dotenv()
    tg_token = os.getenv('TG_TOKEN')

    global provider_token
    provider_token = os.environ['PROVIDER_TOKEN']

    run_bot(tg_token)


if __name__ == '__main__':
    main()
