import logging
from http import HTTPStatus
import telegram
import requests
import os
import time
import sys
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message) -> None:
    """Отправляет сообщение в Telegram чат.
    Логирует уровень INFO при успешной отправке.
    """
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logger.error(f'Сбой при отправке сообщения в Telegram {error}')
    logger.info(f'Бот отправил сообщение: "{message}"')


def get_api_answer(current_timestamp) -> list:
    """Возвращает ответ API приведенный к типу данных python."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        api_response = requests.get(url=ENDPOINT,
                                    headers=HEADERS,
                                    params=params
                                    )
        api_status = api_response.status_code
    except Exception:
        logger.error('Ошибка получения ответа от эндпоинта')
    if api_status == HTTPStatus.OK:
        return api_response.json()
    elif api_status == (HTTPStatus.FOUND or HTTPStatus.MOVED_PERMANENTLY):
        message = f'Эндпоинт {ENDPOINT} пытается перенаправить на другой адрес'
        logger.error(message)
        raise Exception(message)
    else:
        message = f'Эндпоинт {ENDPOINT} недоступен. '
        f'Код ответа API: {api_status}'
        logger.error(message)
        raise Exception(message)


def check_response(response) -> list:
    """Возвращает список домашних работ."""
    try:
        homework_list = response['homeworks']
        type_hw = type(homework_list)
    except KeyError as error:
        logger.error(f'Отсутсвие ожидаемого ключа: {error}')
    if type(homework_list) != list:
        message = f"Под ключом 'homeworks' пришел не list, а {type_hw}"
        logger.error(message)
        raise Exception(message)
    return homework_list


def parse_status(homework):
    """Проверяет статус домашней роботы и взвращает расшифровку статуса."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status in HOMEWORK_STATUSES.keys():
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        message = 'Статус домашней работы не соответствует ожидаемому'
        logger.error(message)
        raise KeyError(message)


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Ошибка переменных окружения, работа прекращена')
        raise Exception('Ошибка переменных окружения')
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
            else:
                logger.debug('Список домашних заданий пуст')

            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message_error != message:
                send_message(bot, message)
            message_error = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
