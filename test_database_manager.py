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
    Предоставляет полностью изолированный экземпляр DatabaseManager для каждого теста.

    Эта фикстура создает и управляет временной, In-Memory SQLite базой данных для каждого запускаемого теста,
    обеспечивая их полную изоляцию и чистое состояние.
    Ключевой особенностью является мокирование функции 'sqlite3.connect',
    чтобы все обращения 'DatabaseManager' к базе данных в памяти ':memory:' направлялись к одному и тому же,
    специально подготовленному тестовому соединению.

    Процесс выполнения фикстуры:
    1. Инициализация соединения: Создается одно постоянное соединение 'sqlite3.Connection'
       к базе данных в оперативной памяти (':memory:'), которое будет использоваться на протяжении всего теста.
    2. Создание схемы: В этом соединении создаются все необходимые таблицы ('users', 'sleep_records', 'notes'),
       гарантируя, что каждый тест начинается с пустой и корректно структурированной схемы базы данных.
    3. Мокирование 'sqlite3.connect': Применяется 'mock.patch' к 'sqlite3.connect' в модуле 'database_manager'.
       Настраивается 'side_effect', который перехватывает вызовы 'sqlite3.connect(':memory:')'
       и возвращает ранее созданное In-Memory соединение.
       Это гарантирует, что 'DatabaseManager' работает именно с этой временной базой данных.
    4. Создание DatabaseManager: Инстанцируется 'DatabaseManager', используя мокированное соединение.
    5. Выполнение теста: Экземпляр 'DatabaseManager' передается в тестовую функцию.
    6. Очистка: После завершения теста (или при возникновении ошибки), In-Memory соединение с базой данных закрывается,
       уничтожая все временные данные и освобождая ресурсы.

    Преимущества данной настройки:
    - Изоляция тестов: Каждый тест работает с совершенно чистой и независимой базой данных,
      исключая влияние одного теста на другой.
    - Высокая производительность: Операции с базой данных выполняются исключительно в оперативной памяти,
      значительно ускоряя выполнение тестового набора.
    - Надежность: Устраняются проблемы, связанные с доступом к файловой системе,
      разрешениями или состоянием реальных файлов базы данных.

    :return: DatabaseManager: Готовый к использованию экземпляр DatabaseManager,
                              подключенный к временной In-Memory базе данных.
    """

    in_memory_conn = sqlite3.connect(':memory:')

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
    Автоматически настраивает уровень логирования для тестов, гарантируя захват логов из 'my_app.database_manager'.
    В связи с ранней загрузкой конфигурации логирования с 'propagate: false' из YAML-файла,
    необходим 'агрессивный сброс' всех логгеров, чтобы caplog мог корректно работать в тестовых функциях.
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


# -- Тесты "Успешного пути" (Happy path) --
def test_add_user_successfully(db_manager: DatabaseManager, caplog: pytest.LogCaptureFixture):
    """
    Тестирует, что метод add_user успешно добавляет пользователя с указанными ID и именем.
    Ожидается, что add_user запишет сообщение об успешном выполнении метода в лог.
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

    expected_log_message = f'Пользователь {user_name} ({user_id}) добавлен или уже существует в БД {db_manager.db_name}.'
    assert expected_log_message in caplog.text


def test_start_sleep_session_successfully(db_manager: DatabaseManager, caplog: pytest.LogCaptureFixture):
    """
    Тестирует, что метод start_sleep_session успешно начинает новую сессию сна для указанного пользователя.
    Ожидается, что start_sleep_session вернет ID новой сессии сна и запишет сообщение об успешном выполнении метода в лог.
    :param db_manager: DatabaseManager: Менеджер базы данных, предоставляемый фикстурой.
    :param caplog: pytest.LogCaptureFixture: Фикстура pytest для перехвата сообщений логгера.
    """
    # Предварительно добавляем пользователя
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
    Тестирует поведение функции add_user при невозможности установить соединение с базой данных.
    Имитирует сбой соединения с базой данных и изменяет уровень логирования на 'ERROR' для этого теста.
    Ожидается, что add_user корректно обработает эту ситуацию и запишет сообщение об исключении в лог.
    :param db_manager: DatabaseManager: Менеджер базы данных, предоставляемый фикстурой.
    :param caplog: pytest.LogCaptureFixture: Фикстура pytest для перехвата сообщений логгера.
    """
    caplog.set_level(logging.ERROR)
    with mock.patch('database_manager.sqlite3.connect') as mock_connect:
        mock_connect.side_effect = sqlite3.Error('Simulated DB connection error for add_user')

        db_manager.add_user(1, 'TestUser')
        expected_error_log_message = (f'Ошибка при добавлении пользователя в БД {db_manager.db_name}: '
                                      f'Simulated DB connection error for add_user')
        assert expected_error_log_message in caplog.text
        assert caplog.records[0].exc_info is not None


def test_start_sleep_session_error_handling(db_manager: DatabaseManager, caplog: pytest.LogCaptureFixture):
    """
    Тестирует поведение функции start_sleep_session при невозможности установить соединение с базой данных.
    Имитирует сбой соединения с базой данных и изменяет уровень логирования на 'ERROR' для этого теста.
    Ожидается, что start_sleep_session корректно обработает эту ситуацию, вернет None
    и запишет сообщение об исключении в лог.
    :param db_manager: DatabaseManager: Менеджер базы данных, предоставляемый фикстурой.
    :param caplog: pytest.LogCaptureFixture: Фикстура pytest для перехвата сообщений логгера.
    """
    caplog.set_level(logging.ERROR)
    with mock.patch('database_manager.sqlite3.connect') as mock_connect:
        mock_connect.side_effect = sqlite3.Error('Simulated DB connection error for start_sleep_session')

        result = db_manager.start_sleep_session(1, datetime.now())
        expected_error_log_message = 'Ошибка при начале сессии сна: Simulated DB connection error for start_sleep_session'

        assert expected_error_log_message in caplog.text
        assert caplog.records[0].exc_info is not None

        assert result is None


def test_get_sleep_statistic_error_handling(db_manager: DatabaseManager, caplog: pytest.LogCaptureFixture):
    """
    Тестирует поведение функции get_sleep_statistic при невозможности установить соединение с базой данных.
    Имитирует сбой соединения с базой данных и изменяет уровень логирования на 'ERROR' для этого теста.
    Ожидается, что get_sleep_statistic корректно обработает эту ситуацию, вернет нулевые значения для статистики
    и запишет сообщение об исключении в лог.
    :param db_manager: DatabaseManager: Менеджер базы данных, предоставляемый фикстурой.
    :param caplog: pytest.LogCaptureFixture: Фикстура pytest для перехвата сообщений логгера.
    """
    caplog.set_level(logging.ERROR)
    with mock.patch('database_manager.sqlite3.connect') as mock_connect:
        mock_connect.side_effect = sqlite3.Error('Simulated DB connection error for get_sleep_statistic')

        total_s, total_d, avg_d = db_manager.get_sleep_statistic(1)
        expected_error_log_message = ('Ошибка при получении статистики сна для пользователя: '
                                      'Simulated DB connection error for get_sleep_statistic')

        assert expected_error_log_message in caplog.text
        assert caplog.records[0].exc_info is not None

        assert (total_s, total_d, avg_d) == (0, 0, 0)

