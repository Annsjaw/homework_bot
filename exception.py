class SendMsgError(Exception):
    """Ошибка отправки сообщения."""

    pass


class EndpointError(Exception):
    """Ошибка эндпоинта."""

    pass


class TokenError(Exception):
    """Ошибка токена."""

    pass


class EndpointNotFound(Exception):
    """Эндпоинт не найден."""

    pass


class EndpointMoved(Exception):
    """Эндпоинт редиректит."""

    pass


class HomeWorksIsEmpty(Exception):
    """Список домашних заданий пуст."""

    pass


class KeyHomeWorkEmpty(Exception):
    """Ключ homework не найден."""

    pass


class StatusHomeWorkEmpty(Exception):
    """Статус пуст."""

    pass
