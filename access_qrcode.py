import json
import os
from datetime import datetime
from pathlib import Path

import qrcode
import redis
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext


def create_access_code(personal_data: json) -> str:
    """Return access code."""
    personal_data = json.loads(personal_data)
    access_code = (
        f'{personal_data["passport_series"]}'
        f'{personal_data["passport_number"]}'
        f'{int(datetime.now().timestamp())}'
    )
    return access_code


def save_access_code(code: str, database: json, booking_id: str) -> None:
    """Save access code to redis database."""
    booking_data = database.get(booking_id)
    serialized_booking_data = json.loads(booking_data)
    serialized_booking_data["access_code"] = code
    booking_data = json.dumps(serialized_booking_data)
    database.set(booking_id, booking_data)


def create_qrcode(code:str) -> str:
    """Create QR-code image and return it's path."""
    qrcode_image = qrcode.make(code)
    qrcodes_directory = './qrcodes/'
    Path(qrcodes_directory).mkdir(exist_ok=True)
    qrcode_image_path = f'{qrcodes_directory}/qr{int(datetime.now().timestamp())}.jpg'
    qrcode_image.save(qrcode_image_path)
    return qrcode_image_path


def post_validity_period(update: Update, context: CallbackContext) -> None:
    """Send message with validity period."""
    booking_data = redis_db.get(booking_id)
    serialized_booking_data = json.loads(booking_data)
    message_text = (
        f'Вот ваш электронный ключ для доступа к вашему личному складу. '
        f'Вы сможете попасть на склад в любое время в период '
        f'с {serialized_booking_data["start_date"]} по {serialized_booking_data["end_date"]}'
    )
    chat_id = update.callback_query.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=message_text)


def start(update: Update, context: CallbackContext) -> None:
    """Send a message with inline button attached."""
    keyboard = [
        [InlineKeyboardButton("QR-code", callback_data='qr')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Press button:', reply_markup=reply_markup)


def button(update: Update, context: CallbackContext) -> None:
    """Send QR-code to client."""
    access_code = create_access_code(redis_db.get(booking_id))
    save_access_code(access_code, redis_db, booking_id)
    post_validity_period(update, context)

    chat_id = update.callback_query.message.chat_id
    with open(create_qrcode(access_code), 'rb') as qrcode_image:
        context.bot.send_photo(chat_id=chat_id, photo=qrcode_image)


def help_command(update: Update, context: CallbackContext) -> None:
    """Displays info on how to use the bot."""
    update.message.reply_text("Use /qrcode to test this bot.")


def main() -> None:
    """Run the bot."""

    global redis_db
    global booking_id

    load_dotenv()
    token = os.getenv('TELEGRAM_TOKEN')
    updater = Updater(token)
    db_host = os.getenv("DB_HOST", default='localhost')
    db_port = os.getenv("DB_PORT", default=6379)
    db_password = os.getenv("DB_PASSWORD", default=None)
    redis_db = redis.Redis(host=db_host, port=db_port, db=0,
        password=db_password, decode_responses=True)

    # JSON-data for testing on local redis database.
    # booking_data= {
    #   "1":{
    #       "passport_series": "5400",
    #       "passport_number": "777888",
    #       "start_date": "25.11.2021",
    #       "end_date": "29.11.2021"
    #   }
    # }
    
    booking_id = '1'

    updater.dispatcher.add_handler(CommandHandler('qrcode', start))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()