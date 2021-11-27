def check_passport(passport):
    passport = passport.strip()
    passport = passport.replace(' ', '')

    if 8 < len(passport) < 11:
        return passport.isdigit()
    return False