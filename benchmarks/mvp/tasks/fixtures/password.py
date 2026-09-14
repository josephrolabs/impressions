def is_valid(password):
    return (
        len(password) >= 8 and any(char.isupper() for char in password)
        and any(char.islower() for char in password) and any(char.isdigit() for char in password)
        and any(not char.isalnum() for char in password)
    )
