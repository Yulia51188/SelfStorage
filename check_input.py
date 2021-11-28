import time

import phonenumbers


def check_passport(passport):
    passport = passport.strip()
    passport = passport.replace(' ', '')

    if (8 < len(passport) < 11
            and len(passport) != passport.count('0')):
        return passport.isdigit()
    return False


def check_phone(phone):
    try:
        all_info_about_phone = phonenumbers.parse(phone)
        country_code = phonenumbers.region_code_for_number(all_info_about_phone)
        if country_code != 'RU':
            return False
        return phonenumbers.is_possible_number(all_info_about_phone)

    except phonenumbers.phonenumberutil.NumberParseException:
        return False


def check_ru_letters(user_input):
    ru_alphabet = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    only_ru_letters = [letter for letter in user_input.lower()
                       if letter in ru_alphabet]
    return only_ru_letters == list(user_input.lower())


def check_birth_date(birth_date):
    try:
        valid_date = time.strptime(birth_date, '%d %m %Y')
        return True
    except ValueError:
        return False
