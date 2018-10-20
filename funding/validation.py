def val_username(value):
    if len(value) >= 20:
        raise Exception("username too long")


def val_email(value):
    if len(value) >= 50:
        raise Exception("email too long")
