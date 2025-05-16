class AuthError(Exception):
    """Базовая ошибка авторизации"""

    pass


class UserAlreadyExists(AuthError):
    """Пользователь уже зарегистрирован"""

    pass


class WeakPassword(AuthError):
    """Пароль не удовлетворяет требованиям"""

    pass
