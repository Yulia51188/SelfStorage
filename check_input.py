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
