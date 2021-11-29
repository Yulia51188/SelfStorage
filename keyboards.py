from textwrap import dedent

from telegram import KeyboardButton, ReplyKeyboardMarkup

import db_processing


def make_reply_markup(keyboard):
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )    


def create_storages_keyboard():
    storages = db_processing.get_storages()

    keyboard = []
    for storage_id, storage in storages.items():
        keyboard.append(
            [
                KeyboardButton(
                    text=(f'{storage_id}. {storage["name"]}'
                          f'({storage["address"]})')
                ),
            ],
        )
    return make_reply_markup(keyboard)


def create_categories_keyboard():
    keyboard = [
        [KeyboardButton(text='Сезонные вещи')],
        [KeyboardButton(text='Другое')],
    ]
    return make_reply_markup(keyboard)


def create_other_keyboard(storage_id):
    category_stuffs = db_processing.get_prices_by_category('other')

    keyboard = []
    text_template = '''\
        {id}. {name} - {base_price} руб.
        (за каждый доп. кв. м. + {add_price} руб.)
        Мест на складе: {free_cells_count} кв.м.
        '''
    for stuff_id, stuff in category_stuffs.items():
        free_cells_count = db_processing.get_free_cells_count(
            storage_id,
            'other',
            stuff_id
        )
        button_caption = text_template.format(
            id=stuff_id,
            name=stuff['name'],
            base_price=stuff['base_price'],
            add_price=stuff['add_one_price'],
            free_cells_count=free_cells_count,
        )
        keyboard.append(
            [KeyboardButton(text=dedent(button_caption))],
        )
    return make_reply_markup(keyboard)


def create_season_keyboard(storage_id):
    category_stuffs = category_stuffs = db_processing.get_prices_by_category(
        'season')

    keyboard = []
    week_template = '''\
        {id}. {name} 
        {week_price} руб. в неделю или {month_price} руб. в месяц
        Мест на складе: {free_cells_count}
        '''
    month_template = '''\
        {id}. {name} 
        {month_price} руб. в месяц
        Мест на складе: {free_cells_count}
        '''
    for stuff_id, stuff in category_stuffs.items():
        free_cells_count = db_processing.get_free_cells_count(
            storage_id,
            'season',
            stuff_id
        )
        if stuff["price"]["week"]:
            button_caption = week_template.format(
                id=stuff_id,
                name=stuff["name"],
                week_price=stuff["price"]["week"],
                month_price=stuff["price"]["month"],
                free_cells_count=free_cells_count,
            )
        else:
            button_caption = month_template.format(
                id=stuff_id,
                name=stuff["name"],
                month_price=stuff["price"]["month"],
                free_cells_count=free_cells_count,
            )
        keyboard.append([KeyboardButton(text=dedent(button_caption))])

    return make_reply_markup(keyboard)


def create_other_storage_keyboard():
    keyboard = [[
        KeyboardButton(text='Выбрать другой склад'),
    ]]
    return make_reply_markup(keyboard)


def create_period_keyboard():
    keyboard = [[
        KeyboardButton(text='Неделя'),
        KeyboardButton(text='Месяц'),
    ]]
    return make_reply_markup(keyboard)


def create_booking_keyboard():
    keyboard = [
        [KeyboardButton(text='Ввести промокод')],
        [KeyboardButton(text='Забронировать')],
        [KeyboardButton(text='Отмена')],
    ]
    return make_reply_markup(keyboard)


def create_payment_keyboard(booking_id):
    discounted_price = db_processing.get_discounted_price(booking_id)

    keyboard = [
        [KeyboardButton(text=f'Оплатить {discounted_price} руб.')],
        [KeyboardButton(text='Сменить фамилию')],
        [KeyboardButton(text='Сменить имя')],
        [KeyboardButton(text='Сменить отчество')],
        [KeyboardButton(text='Сменить паспорт')],
        [KeyboardButton(text='Сменить дату рождения')],
        [KeyboardButton(text='Сменить номер телефона')],
        [KeyboardButton(text='Отмена')],
    ]
    return make_reply_markup(keyboard)
