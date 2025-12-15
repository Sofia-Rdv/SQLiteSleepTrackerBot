import pytest
import sqlite3
import logging
from datetime import datetime, date
from pytest import LogCaptureFixture
from unittest import mock
# Импортируем DatabaseManager
from database_manager import DatabaseManager


@pytest.fixture
def db_manager() -> DatabaseManager:
    """
    Предоставляет чистый DatabaseManager с постоянной базой данных в памяти для каждого теста,
    используя мокироваие sqlite3.connect.
    """
    # Создаем одно постоянное соединение в памяти для всей фикстуры
    in_memory_conn = sqlite3.connect(':memory:')
    # Используем это соединение для создания таблиц напрямую
    # Это гарантирует, что таблицы будут созданы в этом конкретном экземпляре базы данных в памяти
    with in_memory_conn as conn_setup:
        cursor_setup = conn_setup.cursor()
        cursor_setup.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY UNIQUE, name TEXT NOT NULL)""")
        cursor_setup.execute("""
        CREATE TABLE IF NOT EXISTS sleep_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sleep_time DATETIME,
            wake_time DATETIME,
            sleep_quality INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )""")
        cursor_setup.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notes_text TEXT,
            sleep_record_id INTEGER NOT NULL UNIQUE,
            FOREIGN KEY (sleep_record_id) REFERENCES sleep_records(id)
        )""")

    # Определяем функцию `side_effect`, которая будет возвращать наше постоянное соединение
    with mock.patch('database_manager.sqlite3.connect') as mock_connect:
        def side_effect_func(db_name_arg):
            if db_name_arg == ':memory:':
                return in_memory_conn
            else:
                return sqlite3.connect(db_name_arg)

        mock_connect.side_effect = side_effect_func

        manager = DatabaseManager(db_name=':memory:')
        yield manager
    in_memory_conn.close()


@pytest.fixture(autouse=True)
def configure_caplog_level(caplog: pytest.LogCaptureFixture):
    """
    Автоматически настраивает уровень логирования для тестов,
    гарантируя захват логов из 'my_app.database_manager'.
    :param caplog: pytest.LogCaptureFixture: Фикстура pytest для перехвата сообщений логгера.
    """
    # Агрессивный сброс всех логгеров
    for logger_name in list(logging.root.manager.loggerDict.keys()):
        if isinstance(logging.root.manager.loggerDict[logger_name], logging.Logger):
            temp_logger = logging.getLogger(logger_name)
            for handler in list(temp_logger.handlers):
                temp_logger.removeHandler(handler)
            temp_logger.propagate = True
            temp_logger.setLevel(logging.NOTSET)

    for handler in list(logging.root.handlers):
        logging.root.removeHandler(handler)
    logging.root.setLevel(logging.NOTSET)

    # Мокируем logging.config.dictConfig
    with mock.patch('logging.config.dictConfig') as mock_dictConfig:

        # Устанавливаем уровень для корневого логгера(по умолчанию)
        caplog.set_level(logging.INFO)
        # Явно указываем caplog захватывать логи для конкретного логгера
        # Это добавит внутренний хендлер caplog непосредственно к 'my_app.database_manager'
        caplog.set_level(logging.INFO, logger='my_app.database_manager')

        # Получаем целевой логгер, который мы хотим отслеживать
        target_logger = logging.getLogger('my_app.database_manager')

        # Сохраняем оригинальные настройки propagate и level для восстановления
        original_propagate = target_logger.propagate
        original_level = target_logger.level

        # Принудительно устанавливаем propagate в True и уровень, чтобы логи гарантированно дошли до caplog
        # Это переопределяет 'propagate: False' из YAML-файла на время теста
        target_logger.propagate = True
        target_logger.setLevel(logging.INFO)

        # Выполнение теста
        yield

        # Проверяем, что mock_dictConfig НЕ был вызван
        mock_dictConfig.assert_not_called()

        # Восстанавливаем оригинальные настройки логгера после теста
        target_logger.propagate = original_propagate
        target_logger.setLevel(original_level)


# -- Тесты "Успешного пути" --
def test_add_user_successfully(db_manager: DatabaseManager, caplog: pytest.LogCaptureFixture):
    """
    Проверяет успешное добавление пользователя и соответствующее логирование.
    :param db_manager: DatabaseManager: Менеджер базы данных, предоставляемый фикстурой.
    :param caplog: pytest.LogCaptureFixture: Фикстура pytest для перехвата сообщений логгера.
    """
    user_id = 1
    user_name = 'TestUser'
    db_manager.add_user(user_id, user_name)

    # Проверка состояния базы данных
    with sqlite3.connect(db_manager.db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
    assert user == (user_id, user_name)

    # Проверка информационного лога
    expected_log_message = f'Пользователь {user_name} ({user_id}) добавлен или уже существует в БД {db_manager.db_name}.'
    assert expected_log_message in caplog.text


def test_start_sleep_session_successfully(db_manager: DatabaseManager, caplog: pytest.LogCaptureFixture):
    """
    Проверяет успешное начало сессии сна.
    :param db_manager: DatabaseManager: Менеджер базы данных, предоставляемый фикстурой.
    :param caplog: pytest.LogCaptureFixture: Фикстура pytest для перехвата сообщений логгера.
    """
    # Добавляем пользователя
    user_id = 1
    user_name = 'TestUser'
    db_manager.add_user(user_id, user_name)
    sleep_time = datetime(2025, 12, 12, 23, 0, 0)
    session_id = db_manager.start_sleep_session(user_id, sleep_time)

    assert session_id is not None
    assert isinstance(session_id, int)

    expected_log_message = f'Начата новая сессия сна с ID {session_id}.'
    assert expected_log_message in caplog.text

    retrieved_session_id, retrieved_sleep_time = db_manager.get_latest_unfinished_sleep_session(user_id)
    assert retrieved_session_id == session_id
    assert retrieved_sleep_time == sleep_time


# -- Тесты обработки ошибок (Error Handling Tests) --
def test_add_user_error_handling(db_manager: DatabaseManager, caplog: pytest.LogCaptureFixture):
    """
    Проверяет обработку ошибок при добавлении пользователя.
    :param db_manager: DatabaseManager: Менеджер базы данных, предоставляемый фикстурой.
    :param caplog: pytest.LogCaptureFixture: Фикстура pytest для перехвата сообщений логгера.
    """
    # Изменяем уровень логирования для этого теста
    caplog.set_level(logging.ERROR)

    # В этом тесте мы мокируем sqlite3.connect еще раз, но уже так,
    # чтобы он выбрасывал ошибку, а не возвращал постоянное соединение
    # Это переопределяет мок из фикстуры специально для этого теста
    with mock.patch('sqlite3.connect') as mock_connect:
        mock_connect.side_effect = sqlite3.Error('Simulated DB connection error for add_user')

        db_manager.add_user(1, 'TestUser')
        expected_error_log_message = f'Ошибка при добавлении пользователя в БД {db_manager.db_name}: Simulated DB connection error for add_user'
        assert expected_error_log_message in caplog.text
        assert caplog.records[0].exc_info is not None

