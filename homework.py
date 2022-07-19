import logging
from http import HTTPStatus
import telegram
import requests
import os
import time
import sys
from dotenv import load_dotenv
import exception

logger = logging.getLogger()

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message) -> None:
    """Отправляет сообщение в Telegram чат.
    Логирует уровень INFO при успешной отправке.
    """
    try:
        logger.info('Бот отправляет сообщение в Telegram')
        # bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        raise Exception(f'Сбой при отправке сообщения в Telegram {error}')
    else:
        logger.info(f'Бот отправил сообщение: "{message}"')


def get_api_answer(current_timestamp) -> list:
    """Возвращает ответ API приведенный к типу данных python."""
    timestamp = current_timestamp or int(time.time())
    params_data = {'from_date': timestamp}
    request_params = dict(url=ENDPOINT, headers=HEADERS, params=params_data)
    try:
        logger.info('Бот запрашивает ответ от эндпоинта')
        api_response = requests.get(**request_params)
        api_status = api_response.status_code
    except Exception as error:
        raise Exception(f'Ошибка получения ответа от эндпоинта {error}')
    if api_status == HTTPStatus.OK:
        return api_response.json()
    elif api_status == (HTTPStatus.FOUND or HTTPStatus.MOVED_PERMANENTLY):
        message = 'Эндпоинт пытается перенаправить на другой адрес. '
        f'Параметры запроса: эндпоинт - {ENDPOINT}, '
        f'Код ответа API: {api_status}, заголовки {api_response.headers}'
        raise exception.EndpointMoved(message)
    else:
        message = 'Эндпоинт недоступен. '
        f'Параметры запроса: эндпоинт - {ENDPOINT}, '
        f'Код ответа API: {api_status}, заголовки {api_response.headers}'
        raise exception.EndpointNotFound(message)


def check_response(response) -> list:
    """Возвращает список домашних работ."""
    try:
        homework_list = response['homeworks']
        type_hw = type(homework_list)
    except KeyError as error:
        raise KeyError(f'Отсутсвие ожидаемого ключа: {error}')
    else:
        if not isinstance(homework_list, list):
            message = f"Под ключом 'homeworks' пришел не list, а {type_hw}"
            raise TypeError(message)
        elif homework_list == []:
            raise exception.HomeWorksIsEmpty('Список домашних работ пуст')

    return homework_list


def parse_status(homework):
    """Проверяет статус домашней роботы и взвращает расшифровку статуса."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    elif homework_status is None:
        raise exception.StatusHomeWorkEmpty('Статус отсутствует')
    else:
        message = 'Статус домашней работы не соответствует ожидаемому'
        raise KeyError(message)


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Ошибка переменных окружения, работа прекращена')
        raise exception.TokenError('Ошибка переменных окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    message_error = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) != 0:
                status = parse_status(homework[0])
                send_message(bot, status)

            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except exception.HomeWorksIsEmpty:
            logger.debug('Список домашних заданий пуст')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message_error != message:
                send_message(bot, message)
            message_error = message
            time.sleep(RETRY_TIME)

        except KeyboardInterrupt:
            logger.info('Бот красиво завершает свою работу')
            exit()


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(message)s - %(funcName)s - '
        'строка %(lineno)d'
    )
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Бот красиво завершает свою работу')
        exit()
