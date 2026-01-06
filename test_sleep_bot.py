import sqlite3
import pytest
from unittest.mock import MagicMock, patch

# Мокаем TeleBot до импорта основного файла
with patch('telebot.TeleBot') as mocked_bot_class:
    # Создаем фейковый объект бота
    mock_bot_instance = MagicMock()
    # КРИТИЧЕСКИ ВАЖНО
    # Когда функция является декоратором, возвращай эту функцию в целости и сохранности, без изменений
    mock_bot_instance.message_handler.return_value = lambda func: func
    mock_bot_instance.callback_query_handler.return_value = lambda func: func

    # При вызове telebot.TeleBot() будет возвращаться фейковый объект бота
    mocked_bot_class.return_value = mock_bot_instance
    # Импортируем файл с ботом. Внутри файла sleep_bot.py переменная bot станет нашей пустышкой
    import sleep_bot

from telebot import types
from datetime import datetime
from typing import Callable
from pytest_mock import MockFixture


# Фикстура БД ПРОВЕРЕНО
@pytest.fixture
def test_db(tmp_path):
    """
    Обеспечивает базу данных для интеграционных тестов Telegram-бота.

    Выполняет следующие задачи:
    1. Инициализирует изолированный экземпляр DatabaseManager в директории 'tmp_path'.
    2. Создает необходимую структуру таблиц.
    3. Подменяет (патчит) реальный объект 'db' в модуле 'sleep_bot' на тестовый экземпляр.

    Это позволяет проводить 'сквозное' тестирование функций:
    от сохранения данных в БД до формирования ботом корректных ответов пользователю
    (текста, кнопок и разметки), не затрагивая основной файл БД.
    
    :param tmp_path: Встроенная фикстура pytest для создания временных путей.
    :yield: Экземпляр DatabaseManager, интегрированный в модуль бота.
    """
    from database_manager import DatabaseManager
    db_file = str(tmp_path/'test_sleep_bot.db')
    manager = DatabaseManager(db_name=db_file)
    manager._create_tables()

    # Подмениваем глобальный объект db в модуле бота на наш тестовый
    with patch('sleep_bot.db', manager):
        yield manager


# -- Тесты команд /start, /help, /recom -- ПРОВЕРЕНО
def test_send_welcome(test_db) -> None:
    """
    Тест обработчика команды /start.
    :param test_db: Фикстура тестовой базы данных.
    """
    user_id = 222
    user_name = 'TestUser222'
    # Мокаем сообщение
    message = MagicMock()
    message.chat.id = user_id
    message.from_user.id = user_id
    message.from_user.first_name = user_name
    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()

    sleep_bot.send_welcome(message)

    # Проверяем добавлен ли пользователь
    user_data = test_db.get_user_by_id(user_id)
    assert user_data is not None
    assert user_data[1] == user_name

    # Проверка сколько сообщений отправлено пользователю
    assert sleep_bot.bot.send_message.call_count == 2
    # Проверка первого сообщения
    args_1, kwargs_1 = sleep_bot.bot.send_message.call_args_list[0]
    assert args_1[0] == user_id
    assert 'Привет!' in args_1[1]
    assert 'Используйте кнопки или команды' in args_1[1]
    # Проверяем прикрепленную клавиатуру
    assert isinstance(kwargs_1['reply_markup'], types.InlineKeyboardMarkup)
    assert len(kwargs_1['reply_markup'].keyboard) >= 3
    # Проверка второго сообщения
    args_2, kwargs_2 = sleep_bot.bot.send_message.call_args_list[1]
    assert 'Кнопки с этими командами будут всегда доступны' in args_2[1]
    # Проверяем прикрепленную клавиатуру
    assert isinstance(kwargs_2['reply_markup'], types.ReplyKeyboardMarkup)
    assert len(kwargs_2['reply_markup'].keyboard) >= 2


def test_send_welcome_no_name(test_db) -> None:
    """
    Тест обработчика команды /start, если у пользователя не указано имя в Telegram.
    :param test_db: Фикстура тестовой базы данных.
    """
    user_id = 222
    # Имитируем отсутствие имени
    user_name = None
    # Мокаем сообщение
    message = MagicMock()
    message.chat.id = user_id
    message.from_user.id = user_id
    message.from_user.first_name = user_name

    sleep_bot.send_welcome(message)

    user_data = test_db.get_user_by_id(user_id)
    assert user_data is not None
    assert user_data[1] == 'Пользователь'


def test_handle_help() -> None:
    """
    Тест обработчика команды /help.
    """
    user_id = 333
    message = MagicMock()
    message.chat.id = user_id

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()
    sleep_bot.handle_help(message)

    # Проверяем вызов
    sleep_bot.bot.send_message.assert_called_once()
    args, kwargs = sleep_bot.bot.send_message.call_args
    assert args[0] == user_id
    assert 'Список доступных команд' in args[1]

    # Проверяем клавиатуру
    markup = kwargs['reply_markup']
    assert isinstance(markup, types.InlineKeyboardMarkup)
    # Дополнительная проверка:
    # Собираем все callback_data из всех рядов кнопок
    all_callbacks = []
    for i in markup.keyboard:
        for button in i:
            all_callbacks.append(button.callback_data)

    # Проверяем, что важные команды на месте
    expected_callbacks = ['/sleep', '/wake', '/quality', '/notes', '/recom', '/statis']
    for cmd in expected_callbacks:
        assert cmd in all_callbacks


def test_handle_recom() -> None:
    """
    Тест обработчика команды /recom.
    """
    user_id = 333
    message = MagicMock()
    message.chat.id = user_id

    sleep_bot.bot.send_message.reset_mock()
    sleep_bot.handle_recom(message)

    sleep_bot.bot.send_message.assert_called_once()

    args, kwargs = sleep_bot.bot.send_message.call_args
    assert args[0] == user_id
    assert 'Общие рекомендации для улучшения качества сна' in args[1]


# -- Тесты для статистики сна -- ПРОВЕРЕНО
def test_calculate_sleep_statistics_no_data(test_db) -> None:
    """
    Тест обработки случая с отсутствием данных о сне.
    :param test_db: Фикстура тестовой базы данных.
    """
    user_id = 777

    # Вызываем функцию
    result = sleep_bot.calculate_sleep_statistics(user_id)

    assert 'У Вас пока нет данных о сне.' in result


def test_calculate_sleep_statistics_successfully(test_db) -> None:
    """
    Тест успешного расчета статистики при наличии данных.
    :param test_db: Фикстура тестовой базы данных.
    """
    user_id = 888
    # Подготавливаем данные в тестовой БД
    # 1 сессия: 8 часов (28800 сек)
    session_id_1 = test_db.start_sleep_session(user_id, datetime(2025, 12, 1, 22, 0, 0))
    test_db.end_sleep_session(session_id_1, datetime(2025, 12, 2, 6, 0, 0))
    # 2 сессия: 4 часа (14400 сек)
    session_id_2 = test_db.start_sleep_session(user_id, datetime(2025, 12, 2, 23, 0, 0))
    test_db.end_sleep_session(session_id_2, datetime(2025, 12, 3, 3, 0, 0))
    # Итого: 12 часов. Среднее: 6 часов.
    result = sleep_bot.calculate_sleep_statistics(user_id)

    # Проверяем расчеты в тексте
    assert 'Всего сессий сна: 2' in result
    assert 'Общая продолжительность сна: 12 часов 0 минут' in result
    assert 'Средняя продолжительность сна: 6 часов 0 минут' in result


def test_calculate_sleep_statistics_error(test_db, mocker: MockFixture) -> None:
    """
    Проверяет обработки исключения в блоке статистики.
    Тест имитирует разрыв соединения с БД и проверяет, что функция возвращает сообщение об ошибке.
    :param test_db: Фикстура тестовой базы данных.
    :param mocker: MockFixture: Объект для имитации ошибок (mocking)
    """
    user_id = 111
    # Имитируем ошибку при вызове метода БД
    mocker.patch('sleep_bot.db.get_sleep_statistic', side_effect=Exception('DB Error'))
    result = sleep_bot.calculate_sleep_statistics(user_id)

    assert 'произошла ошибка' in result
    assert 'DB Error' in result


def test_handle_statistics(test_db) -> None:
    """
    Тест обработчика команды /statis
    :param test_db: Фикстура тестовой базы данных.
    """
    user_id = 555
    session_id_1 = test_db.start_sleep_session(user_id, datetime(2025, 12, 1, 22, 0, 0))
    test_db.end_sleep_session(session_id_1, datetime(2025, 12, 2, 6, 0, 0))
    message = MagicMock()
    message.chat.id = user_id
    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()
    sleep_bot.handle_statistics(message)

    # Проверяем результат
    sleep_bot.bot.send_message.assert_called_once()
    args, kwargs = sleep_bot.bot.send_message.call_args
    assert args[0] == user_id
    assert 'Ваша статистика сна' in args[1]


# -- Тесты для команды /sleep -- ПРОВЕРЕНО
def test_handle_sleep_successfully(test_db) -> None:
    """
    Тест успешного начала новой сессии сна.
    :param test_db: Фикстура тестовой базы данных.
    """
    user_id = 888
    user_name = 'TestUser888'
    # Мокаем сообщение
    message = MagicMock()
    message.chat.id = user_id
    message.from_user.id = user_id
    message.from_user.first_name = user_name

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()

    sleep_bot.handle_sleep(message)

    assert sleep_bot.bot.send_message.call_count == 2

    args_1, kwargs_1 = sleep_bot.bot.send_message.call_args_list[0]
    assert args_1[0] == user_id
    assert 'Отмечено время начала сна' in args_1[1]

    args_2, kwargs_2 = sleep_bot.bot.send_message.call_args_list[1]
    markup = kwargs_2['reply_markup']
    assert 'Отметить пробуждение' in args_2[1]
    assert isinstance(markup, types.InlineKeyboardMarkup)
    assert markup.keyboard[0][0].callback_data == '/wake'
    assert markup.keyboard[0][0].text == 'Я проснулся ☀'


def test_handle_sleep_with_unfinished_sleep_session(test_db) -> None:
    """
    Тест обработки команды /sleep, когда уже есть активная сессия сна.
    :param test_db: Фикстура тестовой базы данных.
    """
    # 1. Подготавливаем данные в тестовой БД
    user_id = 12345
    user_name = 'TestUser888'
    test_db.add_user(user_id, user_name)

    sleep_time = datetime(2025, 12, 21, 23, 0, 0)
    session_id = test_db.start_sleep_session(user_id, sleep_time)

    # Мокаем сообщение
    message = MagicMock()
    message.chat.id = user_id
    message.from_user.id = user_id
    message.from_user.first_name = user_name

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()

    sleep_bot.handle_sleep(message)

    sleep_bot.bot.send_message.assert_called_once()
    args, kwargs = sleep_bot.bot.send_message.call_args
    assert args[0] == user_id
    assert 'У Вас уже есть активная сессия сна' in args[1]
    assert isinstance(kwargs['reply_markup'], types.InlineKeyboardMarkup)
    assert len(kwargs['reply_markup'].keyboard) == 1


# -- Тесты для команды /wake -- ПРОВЕРЕНО
def test_handle_wake_successfully(test_db) -> None:
    """
    Тест обработки команды /wake.
    :param test_db: Фикстура тестовой базы данных.
    """
    # 1. Подготавливаем данные в тестовой БД
    user_id = 12345
    user_name = 'TestUser888'
    test_db.add_user(user_id, user_name)
    sleep_time = datetime(2025, 12, 24, 20, 0, 0)
    session_id = test_db.start_sleep_session(user_id, sleep_time)
    # Рассчитываем данные о сне
    wake_time = datetime.now()
    duration = wake_time - sleep_time
    duration_hours = int(duration.total_seconds() // 3600)
    duration_minutes = int((duration.total_seconds() % 3600) // 60)

    # Мокаем сообщение
    message = MagicMock()
    message.chat.id = user_id
    message.from_user.id = user_id
    message.from_user.first_name = user_name

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()

    sleep_bot.handle_wake(message)

    assert sleep_bot.bot.send_message.call_count == 2

    args_1, kwargs_1 = sleep_bot.bot.send_message.call_args_list[0]
    assert args_1[0] == user_id
    assert 'Надеюсь Вы выспались' in args_1[1]
    assert f'Вы спали, примерно, {duration_hours} часов {duration_minutes} минут' in args_1[1]

    args_2, kwargs_2 = sleep_bot.bot.send_message.call_args_list[1]
    markup = kwargs_2['reply_markup']
    assert 'Поставить оценку' in args_2[1]
    assert isinstance(markup, types.InlineKeyboardMarkup)
    assert markup.keyboard[0][0].callback_data == '/quality'
    assert markup.keyboard[0][0].text == 'Качество сна 💫'


def test_handle_wake_without_unfinished_sleep_session(test_db) -> None:
    """
    Тест обработки команды /wake, когда нет активных сессий сна.
    :param test_db: Фикстура тестовой базы данных.
    """
    user_id = 888
    user_name = 'TestUser888'
    # Мокаем сообщение
    message = MagicMock()
    message.chat.id = user_id
    message.from_user.id = user_id
    message.from_user.first_name = user_name

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()

    sleep_bot.handle_wake(message)

    sleep_bot.bot.send_message.assert_called_once()
    args, kwargs = sleep_bot.bot.send_message.call_args
    markup = kwargs['reply_markup']
    assert args[0] == user_id
    assert 'Сначала отметьте, когда легли спать' in args[1]
    assert isinstance(markup, types.InlineKeyboardMarkup)
    assert len(markup.keyboard) == 1
    assert markup.keyboard[0][0].callback_data == '/sleep'
    assert markup.keyboard[0][0].text == 'Сладких снов 😴'


# -- Тесты для команды /quality -- ПРОВЕРЕНО
def test_handle_quality_successfully(test_db) -> None:
    """
    Тест обработчика команды /quality.
    :param test_db: Фикстура тестовой базы данных.
    """
    # 1. Подготавливаем данные в тестовой БД
    user_id = 888
    user_name = 'TestUser888'
    test_db.add_user(user_id, user_name)

    sleep_time = datetime(2025, 12, 25, 23, 0, 0)
    session_id = test_db.start_sleep_session(user_id, sleep_time)
    test_db.end_sleep_session(session_id, datetime.now())

    # Мокаем сообщение
    message = MagicMock()
    message.chat.id = user_id
    message.from_user.id = user_id
    message.from_user.first_name = user_name

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()
    # 3. Вызываем функцию
    sleep_bot.handle_quality(message)

    # Проверка
    sleep_bot.bot.send_message.assert_called_once()
    args, kwargs = sleep_bot.bot.send_message.call_args
    assert args[0] == user_id
    assert 'Оцените, пожалуйста, качество Вашего сна' in args[1]
    assert isinstance(kwargs['reply_markup'], types.InlineKeyboardMarkup)
    assert len(kwargs['reply_markup'].keyboard) == 5


@pytest.mark.parametrize('setup_type', ['no_session', 'already_rated'])
def test_handle_quality_failure_cases(test_db, setup_type: str) -> None:
    """
    Тест негативных сценариев команды /quality (ветка else).
    Проверяет, что бот корректно реагирует, если:
    1. 'no_session' - в базе данных нет завершенных сессий сна у данного пользователя.
    2. 'already_rated' - последняя завершенная сессия сна уже имеет заполненное поле оценки качества.
    :param test_db: Фикстура тестовой базы данных.
    :param setup_type: str: Ключ сценария подготовки данных (из parametrize).
    """
    # 1. Подготавливаем данные в тестовой БД
    user_id = 888
    user_name = 'TestUser'
    test_db.add_user(user_id, user_name)

    if setup_type == 'already_rated':
        # Создаем завершенную сессию сна и ставим оценку
        now = datetime.now()
        session_id = test_db.start_sleep_session(user_id, now)
        test_db.end_sleep_session(session_id, now)
        test_db.update_sleep_quality(session_id, 4)
    # Если setup_type == 'no_session', мы ничего не делаем, кроме добавления пользователя

    # Мокаем сообщение
    message = MagicMock()
    message.chat.id = user_id
    message.from_user.id = user_id
    message.from_user.first_name = user_name

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()
    # 3. Вызываем функцию
    sleep_bot.handle_quality(message)

    # Проверяем, что попали в ветку else(одна кнопка 'Я проснулся')
    sleep_bot.bot.send_message.assert_called_once()
    args, kwargs = sleep_bot.bot.send_message.call_args
    assert args[0] == user_id
    assert 'отметьте свое пробуждение' in args[1]
    assert 'Вы уже оценили свой последний сон' in args[1]
    assert isinstance(kwargs['reply_markup'], types.InlineKeyboardMarkup)
    assert len(kwargs['reply_markup'].keyboard) == 1


@pytest.mark.parametrize('quality', ['1', '3', '5'])
def test_handle_quality_callback(test_db, quality: str) -> None:
    """
    Тест обработки нажатия кнопок (inline) оценки качества сна.
    :param test_db: Фикстура тестовой базы данных.
    :param quality: Ключ к оценке качества сна.
    """
    # Подготавливаем данные
    user_id = 888
    user_name = 'TestUser'
    message_id = 101
    test_db.add_user(user_id, user_name)
    sleep_record_id = test_db.start_sleep_session(user_id, datetime.now())
    test_db.end_sleep_session(sleep_record_id, datetime.now())

    # Создаем мок для CallbackQuery
    call = MagicMock()
    call.id = 'callback_id_777'
    call.from_user.id = user_id
    call.data = f'quality_{quality}_{sleep_record_id}'
    call.message.message_id = message_id
    call.message.chat.id = user_id

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.edit_message_text.reset_mock()
    sleep_bot.bot.answer_callback_query.reset_mock()

    # Вызываем хендлер
    sleep_bot.handle_quality_callback(call)

    # -- Проверки --

    # 1. Проверяем, что текст сообщения обновился (edit_message_text)
    sleep_bot.bot.edit_message_text.assert_called_once()
    args, kwargs = sleep_bot.bot.edit_message_text.call_args
    assert kwargs['chat_id'] == user_id
    assert kwargs['message_id'] == message_id
    assert f'Ваша оценка качества сна {quality} записана!' in kwargs['text']
    assert 'Вы можете написать комментарий к оценке' in kwargs['text']
    assert isinstance(kwargs['reply_markup'], types.InlineKeyboardMarkup)
    assert len(kwargs['reply_markup'].keyboard) == 1

    # 2. Проверяем, что callback был получен и обработан
    sleep_bot.bot.answer_callback_query.assert_called_once_with(call.id)

    # 3. Проверяем действительно ли оценка записана в БД
    with sqlite3.connect(test_db.db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT sleep_quality FROM sleep_records WHERE id = ?', (sleep_record_id,))
        row = cursor.fetchone()
    assert row is not None
    assert row[0] == int(quality)
    conn.close()


# -- Тест для handle_notes (начало процесса) -- ПРОВЕРЕНО
@pytest.mark.parametrize('setup_type', ['without_notes', 'with_notes', 'no_session'])
def test_handle_notes(test_db, setup_type: str) -> None:
    """
    Тест трех сценариев команды /notes(ветки if, else).
    Проверяет, что бот корректно реагирует, если:
    1. 'without_notes' - последняя завершенная сессия сна оценкой качества и без заметки.
    2. 'with_notes' - последняя завершенная сессия сна с оценкой уже имеет заметку.
    3. 'no_session' - в базе данных нет завершенных сессий сна у данного пользователя.
    :param test_db: Фикстура тестовой базы данных.
    :param setup_type: str: Ключ сценария подготовки данных (из parametrize).
    """
    # 1. Подготавливаем данные в тестовой БД
    user_id = 888
    user_name = 'TestUser888'
    test_db.add_user(user_id, user_name)

    # Если у завершенной сессии нет заметки
    if setup_type == 'without_notes':
        sleep_time = datetime(2025, 12, 21, 23, 0, 0)
        session_id = test_db.start_sleep_session(user_id, sleep_time)
        test_db.end_sleep_session(session_id, datetime.now())
        test_db.update_sleep_quality(session_id, 4)
        expected_text = 'напишите комментарий к Вашей оценке'

    # Если у завершенной сессии есть заметка
    elif setup_type == 'with_notes':
        sleep_time = datetime(2025, 12, 21, 23, 0, 0)
        session_id = test_db.start_sleep_session(user_id, sleep_time)
        test_db.end_sleep_session(session_id, datetime.now())
        test_db.update_sleep_quality(session_id, 4)
        test_db.add_note(session_id, 'Хорошо, выспалась')
        expected_text = 'уже есть заметка к последней оцененной сессии'

    # Если нет сессий сна, ничего не добавляем, кроме пользователя вначале
    elif setup_type == 'no_session':
        expected_text = 'У Вас нет завершенной сессии'

    # Мокаем сообщение
    message = MagicMock()
    message.chat.id = user_id
    message.from_user.id = user_id
    message.from_user.first_name = user_name

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()
    sleep_bot.bot.register_next_step_handler.reset_mock()

    sleep_bot.handle_notes(message)

    sleep_bot.bot.send_message.assert_called_once()
    args, kwargs = sleep_bot.bot.send_message.call_args
    assert args[0] == user_id
    assert expected_text in args[1]

    if setup_type == 'without_notes':
        sleep_bot.bot.register_next_step_handler.assert_called_once()
        args_step, kwargs_step = sleep_bot.bot.register_next_step_handler.call_args
        assert args_step[1] == sleep_bot.process_notes_step


# -- Тесты для handle_notes_update_callback -- ПРОВЕРЕНО
@pytest.mark.parametrize('yes_no, expected_text', [
    ('yes', 'напишите новый комментарий'),
    ('no', 'заметка останется без изменений')
])
def test_handle_notes_update_callback(yes_no: str, expected_text: str) -> None:
    """
    Тест обработки нажатия кнопок (inline) при обновлении заметки.
    Проверяет сценарии:
    1. 'Да' - редактирование сообщения с кнопками и переход к следующему шагу (запись текста заметки).
    2. 'Нет' - только редактирование сообщения с кнопками.
    :param yes_no: Ключ сценария дальнейших действий бота.
    :param expected_text: Ключ текста для редактирования сообщения с кнопками.
    """
    user_id = 888
    message_id = 1001
    sleep_record_id = 123

    # Создаем мок для CallbackQuery
    call = MagicMock()
    call.id = 'callback_id_999'
    call.from_user.id = user_id
    call.data = f'update_{yes_no}_{sleep_record_id}'
    call.message.message_id = message_id

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.edit_message_text.reset_mock()
    sleep_bot.bot.register_next_step_handler.reset_mock()
    sleep_bot.bot.answer_callback_query.reset_mock()

    # Вызываем хендлер
    sleep_bot.handle_notes_update_callback(call)

    # 1. Проверяем, что текст сообщения обновился (edit_message_text)
    sleep_bot.bot.edit_message_text.assert_called_once()
    args, kwargs = sleep_bot.bot.edit_message_text.call_args
    assert kwargs['chat_id'] == user_id
    assert kwargs['message_id'] == message_id
    assert expected_text in kwargs['text']
    # 2. Проверяем, что callback был получен и обработан
    sleep_bot.bot.answer_callback_query.assert_called_once_with(call.id)

    # 3. Проверяем регистрацию следующего шага (только для 'yes')
    if yes_no == 'yes':
        sleep_bot.bot.register_next_step_handler.assert_called_once()
        # Проверяем, что передали верный ID записи в функцию process_notes_step
        step_args, _ = sleep_bot.bot.register_next_step_handler.call_args
        assert step_args[2] == sleep_record_id
    else:
        sleep_bot.bot.register_next_step_handler.assert_not_called()


# -- Тесты для записи заметки к оценке качества сна -- ПРОВЕРЕНО
def test_process_notes_successfully(test_db) -> None:
    """
    Тест успешного сохранения заметки.
    :param test_db: Фикстура тестовой базы данных.
    """
    # 1. Подготавливаем данные в тестовой БД
    user_id = 12345
    test_db.add_user(user_id, 'TestUser')

    sleep_time = datetime(2025, 12, 21, 23, 0, 0)
    session_id = test_db.start_sleep_session(user_id, sleep_time)
    test_db.end_sleep_session(session_id, datetime.now())
    test_db.update_sleep_quality(session_id, 4)

    # 2. Имитируем сообщение от пользователя
    message = MagicMock()
    message.chat.id = user_id
    message.text = 'Спалось хорошо, но мало.'
    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()
    # 3. Вызываем функцию
    sleep_bot.process_notes_step(message, session_id)

    # 4. Проверки
    # Проверяем, что в БД действительно появилась заметка
    note_in_db = test_db.get_note_by_sleep_record_id(session_id)
    assert note_in_db == 'Спалось хорошо, но мало.'

    # Проверяем, что бот ответил пользователю об успехе
    sleep_bot.bot.send_message.assert_called_once()
    args, kwargs = sleep_bot.bot.send_message.call_args
    assert args[0] == user_id
    assert "Спасибо, Ваш комментарий записан" in args[1]


@pytest.mark.parametrize('stop_word', ['/cancel', '/stop', 'Отмена'])
def test_process_notes_cancel(test_db, stop_word: str) -> None:
    """
    Тест отмены ввода заметки.
    Проверяет три стоп-слова/команды отмены записи заметки.
    :param test_db: Фикстура тестовой базы данных.
    :param stop_word: str: Ключ к стоп слову/команде.
    """
    user_id = 12345
    message = MagicMock()
    message.chat.id = user_id
    # Стоп-слово

    if stop_word == '/cancel':
        message.text = stop_word

    elif stop_word == '/stop':
        message.text = stop_word

    elif stop_word == 'Отмена':
        message.text = stop_word

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()
    sleep_bot.process_notes_step(message, 1)

    # Проверяем результаты
    sleep_bot.bot.send_message.assert_called_once()
    args, kwargs = sleep_bot.bot.send_message.call_args
    assert args[0] == user_id
    assert 'Действие отменено' in args[1]
    # Проверяем, что в БД пусто, заметка не добавилась
    assert test_db.get_note_by_sleep_record_id(1) is None


def test_process_notes_invalid_connect(test_db) -> None:
    """
    Тест отправки некорректного типа данных (не текст, например, картинка)
    :param test_db: Фикстура тестовой базы данных.
    """
    user_id = 12345
    message = MagicMock()
    message.chat.id = user_id
    # Имитируем стикер или фото, не текстовый тип данных будет None
    message.text = None
    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()
    sleep_bot.bot.register_next_step_handler.reset_mock()

    sleep_bot.process_notes_step(message, 1)

    # Проверки
    sleep_bot.bot.send_message.assert_called_once()
    args, kwargs = sleep_bot.bot.send_message.call_args
    assert args[0] == user_id
    assert 'Пожалуйста, отправьте заметку текстом' in args[1]
    # Проверяем, что бот снова вызвал register_next_step_handler, чтобы ждать текст
    assert sleep_bot.bot.register_next_step_handler.called


# -- Тесты обработки ошибок -- ПРОВЕРЕНО
@pytest.mark.parametrize('handler_to_test, db_method_path', [
    (sleep_bot.handle_sleep, 'sleep_bot.db.start_sleep_session'),
    (sleep_bot.handle_wake, 'sleep_bot.db.end_sleep_session'),
    (sleep_bot.handle_quality, 'sleep_bot.db.get_latest_finished_sleep_session_without_quality'),
    (sleep_bot.handle_wake, 'sleep_bot.db.get_latest_unfinished_sleep_session'),
    (sleep_bot.handle_notes, 'sleep_bot.db.get_latest_finished_sleep_session_with_quality'),
    (sleep_bot.handle_notes, 'sleep_bot.db.get_note_by_sleep_record_id'),
    (sleep_bot.process_notes_step, 'sleep_bot.db.add_note')
    ])
def test_handlers_database_error(test_db, mocker: MockFixture, handler_to_test: Callable, db_method_path: str) -> None:
    """
    Универсальный тест для проверки обработки ошибок БД в хендлерах.
    Проверяет, что при возникновении Exception в методах БД, вызываемых внутри хендлеров,
    бот отправляет пользователю уведомление об ошибке.
    :param test_db: Фикстура тестовой базы данных.
    :param mocker: MockFixture: Объект для имитации ошибок (mocking).
    :param handler_to_test: str: Ключ тестируемого хендлера.
    :param db_method_path: str: Ключ пути к методу БД для тестируемого хендлера.
    """
    user_id = 888
    user_name = 'TestUser888'
    # Мокаем сообщение
    message = MagicMock()
    message.chat.id = user_id
    message.from_user.id = user_id
    message.from_user.first_name = user_name
    message.text = 'Ok'
    dummy_sleep_record_id = 1

    # Создаем активную сессию сна, чтобы первая проверка handle_wake прошла успешно
    if db_method_path == 'sleep_bot.db.end_sleep_session':
        test_db.add_user(user_id, user_name)
        _ = test_db.start_sleep_session(user_id, datetime.now())
    elif db_method_path == 'sleep_bot.db.get_note_by_sleep_record_id':
        test_db.add_user(user_id, user_name)
        session_id = test_db.start_sleep_session(user_id, datetime.now())
        test_db.end_sleep_session(session_id, datetime.now())
        test_db.update_sleep_quality(session_id, 5)

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()
    sleep_bot.bot.register_next_step_handler.reset_mock()

    # Имитируем ошибку при вызове метода БД
    mocker.patch(db_method_path, side_effect=Exception('DB Error'))
    # Вызываем хендлер
    if db_method_path == 'sleep_bot.db.add_note':
        handler_to_test(message, dummy_sleep_record_id)
    else:
        handler_to_test(message)

    sleep_bot.bot.send_message.assert_called_once()
    args, kwargs = sleep_bot.bot.send_message.call_args
    assert args[0] == user_id
    assert 'произошла ошибка' in args[1]
    assert 'DB Error' in args[1]


@pytest.mark.parametrize('handler_to_test, error_type', [
    (sleep_bot.handle_quality_callback, 'IndexError_split'),
    (sleep_bot.handle_quality_callback, 'ValueError_int'),
    (sleep_bot.handle_quality_callback, 'DatabaseError'),
    (sleep_bot.handle_notes_update_callback, 'IndexError_split'),
    (sleep_bot.handle_notes_update_callback, 'ValueError_int')
])
def test_handle_quality_and_notes_update_callback_error(
        mocker: MockFixture, handler_to_test: Callable, error_type: str) -> None:
    """
    Проверка блока except в callback-хендлере.
    Проверяет три сценария возможных ошибок:
    1. IndexError - ошибка при разделении(split) полученных данных(call.data) на части.
    2. ValueError - ошибка при преобразовании в целое число (int).
    3. DatabaseError - ошибка в методе БД (только для handle_quality_callback)
    :param mocker: MockFixture: Объект для имитации ошибок (mocking).
    :param handler_to_test: Callable: Ключ тестируемого хендлера.
    :param error_type: str: Ключ к типу ошибки.
    """
    call = MagicMock()
    user_id = 888
    call.from_user.id = user_id
    call.message.chat.id = user_id
    call.message.message_id = 101
    call.id = 'callback_id_777'

    # Специально ломаем data, чтобы вызвать ошибку при split или приведении к int
    if error_type == 'IndexError_split':
        call.data = 'non-separable'
        expected_error_text = 'list index out of range'
    elif error_type == 'ValueError_int':
        call.data = 'not_converted_to_int'
        expected_error_text = "invalid literal for int() with base 10:"
    elif error_type == 'DatabaseError':
        # Корректные данные, чтобы пройти парсинг
        call.data = 'quality_5_123'
        mocker.patch('sleep_bot.db.update_sleep_quality', side_effect=Exception('DB Error'))
        expected_error_text = 'DB Error'

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.send_message.reset_mock()
    sleep_bot.bot.answer_callback_query.reset_mock()

    handler_to_test(call)

    # Проверяем, что callback был получен и обработан
    sleep_bot.bot.answer_callback_query.assert_called_once_with(call.id)
    # Проверяем, что сработал блок except и бот отправил сообщение об ошибке
    sleep_bot.bot.send_message.assert_called_once()
    args, _ = sleep_bot.bot.send_message.call_args
    assert 'произошла ошибка' in args[1]
    assert expected_error_text in args[1]


# -- Тесты для handle_callback -- ПРОВЕРЕНО
@pytest.mark.parametrize('command_to_test, handler_name', [
    ('/sleep', 'handle_sleep'),
    ('/wake', 'handle_wake'),
    ('/quality', 'handle_quality'),
    ('/notes', 'handle_notes'),
    ('/recom', 'handle_recom'),
    ('/statis', 'handle_statistics')
])
def test_handle_callback_routing(test_db, mocker: MockFixture, command_to_test: str, handler_name: str) -> None:
    """
    Тестирует роутинг: что нажатие на inline кнопку вызывает правильную функцию-обработчик.
    :param test_db: Фикстура тестовой базы данных.
    :param mocker: MockFixture: Объект для имитации вызова функции (mocking).
    :param command_to_test: Ключ к тестируемой команде.
    :param handler_name: Ключ к имени хендлера для тестируемой команды.
    """
    # Создаем мок для CallbackQuery
    call = MagicMock()
    call.id = 'test_id'
    call.data = command_to_test
    call.message.chat.id = 123

    # Мокаем целевой хендлер, чтобы он ничего не делал, но помнил, что был вызван
    mocked_handler = mocker.patch(f'sleep_bot.{handler_name}')

    # Очищаем историю вызовов перед тестом
    sleep_bot.bot.answer_callback_query.reset_mock()

    # Вызываем функцию
    sleep_bot.handle_callback(call)
    # Проверяем, что нужный хендлер был вызван один раз
    mocked_handler.assert_called_once_with(call.message)
    # Проверяем, что callback был получен и обработан
    sleep_bot.bot.answer_callback_query.assert_called_once_with(call.id)


@pytest.mark.parametrize('command_to_test, handler_name', [
    ('/sleep', 'handle_sleep'),
    ('/wake', 'handle_wake'),
    ('/quality', 'handle_quality'),
    ('/notes', 'handle_notes'),
    ('/recom', 'handle_recom'),
    ('/statis', 'handle_statistics')
])
def test_handle_callback_error(mocker: MockFixture, command_to_test: str, handler_name: str) -> None:
    """
    Проверка блока except в функции-роутере.
    Проверяет, что если вызванный хендлер выдал ошибку, пользователь получит уведомление, а callback будет подтвержден.
    :param mocker: MockFixture: Объект для имитации ошибки (mocking).
    :param command_to_test: str: Ключ к тестируемой команде.
    :param handler_name: str: Ключ к имени хендлера для тестируемой команды.
    """
    call = MagicMock()
    call.data = command_to_test
    call.id = 'error_id'
    call.message.chat.id = 123

    # Имитируем ошибку при вызове хендлера
    mocker.patch(f'sleep_bot.{handler_name}', side_effect=Exception('Unexpected crash!'))

    # Очищаем историю вызовов
    sleep_bot.bot.send_message.reset_mock()
    sleep_bot.bot.answer_callback_query.reset_mock()

    # Вызов
    sleep_bot.handle_callback(call)

    # Проверяем, что сообщение об ошибке отправлено
    sleep_bot.bot.send_message.assert_called_once()
    args, _ = sleep_bot.bot.send_message.call_args
    assert 'Простите, произошла ошибка' in args[1]
    assert 'Unexpected crash!' in args[1]
    # Проверяем, что запрос был получен и обработан
    sleep_bot.bot.answer_callback_query.assert_called_once_with(call.id)


# -- Тесты для all_other_message --
def test_all_other_message(test_db) -> None:
    """
    Тест обработчика всех поступающих сообщений,
    которые не являются командами, или написаны вне функции записи заметки.
    :param test_db: Фикстура тестовой базы данных.
    """
    user_id = 333
    message = MagicMock()
    message.chat.id = user_id

    sleep_bot.bot.reply_to.reset_mock()
    sleep_bot.all_other_message(message)

    args, kwargs = sleep_bot.bot.reply_to.call_args
    assert args[0] == message
    assert 'Простите, я Вас не понимаю' in args[1]



