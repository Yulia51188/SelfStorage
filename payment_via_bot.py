import os
from pprint import pprint
from dotenv import load_dotenv
from rejson import Client, Path

from telegram import LabeledPrice, ShippingOption, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    PreCheckoutQueryHandler,
    ShippingQueryHandler,
    CallbackContext,
    CallbackQueryHandler,
)


_booking = {
        'booking_id': '1',
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
    }


def get_database_connection():
    database_password = '70uD9NjLBZhP7MvxKgpydqbPYyqzK4mU'
    database_host = 'redis-13524.c250.eu-central-1-1.ec2.cloud.redislabs.com'
    database_port = '13524'
    database = Client(host=database_host, port=database_port,
        password=database_password, decode_responses=True)
    return database


def start_callback(update: Update, context: CallbackContext) -> None:
    """Displays info on how to use the bot."""
    msg = (
        "Use /shipping to get an invoice for shipping-payment, or /noshipping for an "
        "invoice without shipping."
    )

    update.message.reply_text(msg)


def start_without_shipping_callback(update: Update, context: CallbackContext):
    """Sends an invoice without shipping-payment."""
    global _booking, provider_token
    db = get_database_connection()
    booking_id = _booking['booking_id']
    
    chat_id = update.callback_query.message.chat_id
    title = "Оплата бронирования"
    description = f"Оплата категории {_booking['category']}"
    # select a payload just for you to recognize its the donation from your bot
    payload = "Fuppergupper"
    # In order to get a provider_token see https://core.telegram.org/bots/payments#getting-a-token
    currency = "RUB"
    # price in dollars
    price = _booking['total_cost']
    # price * 100 so as to include 2 decimal points
    prices = [LabeledPrice("Test", price * 100)]

    # optionally pass need_name=True, need_phone_number=True,
    # need_email=True, need_shipping_address=True, is_flexible=True
    context.bot.send_invoice(
        chat_id, title, description, payload, provider_token, currency, prices
    )

# after (optional) shipping, it's the pre-checkout
def precheckout_callback(update: Update, context: CallbackContext) -> None:
    """Answers the PreQecheckoutQuery"""
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != 'Fuppergupper':
        # answer False pre_checkout_query
        query.answer(ok=False, error_message="Something went wrong...")
    else:
        query.answer(ok=True)


# finally, after contacting the payment provider...
def successful_payment_callback(update: Update, context: CallbackContext) -> None:
    global _booking
    db = get_database_connection()
    booking_id = _booking['booking_id']

    db.jsonset('bookings', Path(f'.{booking_id}.status'), 'payed')
    booking = db.jsonget('bookings', Path(f'.{booking_id}'))
    pprint(booking)

def create_button(update: Update, context: CallbackContext) -> None:
    """Sends a message with three inline buttons attached."""
    keyboard = [[InlineKeyboardButton("PAY", callback_data='1')]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Give me your money', reply_markup=reply_markup)


def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    global provider_token
    load_dotenv()
    token = os.environ['TELEGRAM_TOKEN']
    provider_token = os.environ['P_TOKEN']
    updater = Updater(token)    
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler('start', create_button))
    dispatcher.add_handler(CallbackQueryHandler(start_without_shipping_callback))
    # Pre-checkout handler to final check
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()
