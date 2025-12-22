import sqlite3
import logging
from datetime import datetime, timedelta
# Нужно для закрытия соединения с БД
from contextlib import closing
# Импортируем функцию настройки логирования из файла с конфигурацией
from my_logger_config import setup_logging
# Вызов функции настройки логирования (ОДИН РАЗ) при запуске программы
setup_logging()

# Получение экземпляра логгера
logger = logging.getLogger(f'my_app.{__name__}')


class DatabaseManager:
    """
    Менеджер для взаимодействия с базой данных SQLite.

    Этот класс представляет централизованный интерфейс для управления подключением к файловой базе данных SQLite,
    выполнения SQL-запросов (INSERT, SELECT, UPDATE) и обработки транзакций.
    Он инкапсулирует операции с БД и обеспечивает безопасное управление соединениями.

    Использует стандартную библиотеку Python `sqlite3`.

    Каждый метод этого класса устанавливает собственное соединение с базой данных,
    используя контекстный менеджер (`with sqlite3.connect(...)`). Такой подход гарантирует, что соединение корректно
    открывается и закрывается для каждой операции, что критически важно для многопоточных приложений
    (например, Telegram-ботов) при работе с SQLite.
    Это повышает надежность и предотвращает проблемы с блокировками или совместным использованием соединений
    между различными потоками.

    Attributes:
        db_name (str): Путь к файлу базы данных SQLite (например, 'sleep_tracker.db').
    """
    def __init__(self, db_name: str = 'sleep_tracker.db'):
        self.db_name: str = db_name
        self._create_tables()

    def _create_tables(self):
        """Создает таблицы, если они не существуют."""
        sql_users = '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY UNIQUE,
            name TEXT NOT NULL
        );
        '''
        sql_sleep_records = '''
        CREATE TABLE IF NOT EXISTS sleep_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sleep_time DATETIME,
            wake_time DATETIME,
            sleep_quality INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        '''
        sql_notes = '''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notes_text TEXT,
            sleep_record_id INTEGER NOT NULL UNIQUE,
            FOREIGN KEY (sleep_record_id) REFERENCES sleep_records(id)
        );
        '''
        conn = None
        try:
            # Открываем соединение внутри метода
            conn = sqlite3.connect(self.db_name)
            # with сделает commit и rollback при необходимости
            with conn:
                cursor = conn.cursor()
                # Создает таблицу users
                cursor.execute(sql_users)
                # Создает таблицу sleep_records
                cursor.execute(sql_sleep_records)
                # Создает таблицу notes
                cursor.execute(sql_notes)
            # Изменения в БД сохранятся автоматически с помощью with
            logger.info(f'Таблицы успешно созданы или уже существуют.')
        except sqlite3.Error as e:
            logger.error(f'Ошибка при создании таблиц: {e}', exc_info=True)
        finally:
            if conn:
                conn.close()

    def add_user(self, user_id: int, user_name: str):
        """
        Добавляет нового пользователя, если его нет в базе данных.
        :param user_id: int: ID пользователя в телеграмме.
        :param user_name: str: Имя пользователя в телеграмме, если указано, иначе указывается "Пользователь".
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            with conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (user_id, user_name))
            logger.info(f'Пользователь {user_name} ({user_id}) добавлен или уже существует в БД {self.db_name}.')
        except sqlite3.Error as e:
            logger.error(f'Ошибка при добавлении пользователя в БД {self.db_name}: {e}', exc_info=True)
        finally:
            if conn:
                conn.close()

    def start_sleep_session(self, user_id: int, sleep_time: datetime) -> int | None:
        """
        Начинает новую сессию сна для указанного пользователя.
        :param user_id: int: ID пользователя в телеграмме.
        :param sleep_time: datetime: Время начала сна.
        :return: int | None: ID новой записи сна, если операция успешна, иначе None.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            with conn:
                cursor = conn.cursor()
                # Добавляем время начала сна(преобразованное для SQLite) в таблицу с сессиями сна
                cursor.execute("INSERT INTO sleep_records (user_id, sleep_time) VALUES (?, ?)",
                               (user_id, sleep_time.isoformat()))
                logger.info(f'Начата новая сессия сна с ID {cursor.lastrowid}.')
                # Возвращаем ID новой записи сна
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f'Ошибка при начале сессии сна: {e}', exc_info=True)
            return None
        finally:
            if conn:
                conn.close()

    def end_sleep_session(self, sleep_record_id: int, wake_time: datetime):
        """
        Завершает сессию сна, обновляя время пробуждения.
        :param sleep_record_id: int: ID сессии сна.
        :param wake_time: datetime: Время пробуждения.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            with conn:
                cursor = conn.cursor()
                # Добавляем время пробуждение преобразованное для SQLite
                cursor.execute("UPDATE sleep_records SET wake_time = ? WHERE id = ?",
                               (wake_time.isoformat(), sleep_record_id))
            logger.info(f'Сессия сна {sleep_record_id} завершена.')
        except sqlite3.Error as e:
            logger.error(f'Ошибка при завершении сессии сна: {e}', exc_info=True)
        finally:
            if conn:
                conn.close()

    def update_sleep_quality(self, sleep_record_id: int, quality: int):
        """
        Добавляет оценку качества сна для конкретной сессии, обновляя поле sleep_quality.
        :param sleep_record_id: int: ID сессии сна.
        :param quality: int: Оценка качества сна.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            with conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE sleep_records SET sleep_quality = ? WHERE id = ?",
                               (quality, sleep_record_id))
            logger.info(f'Оценка качества сна для сессии {sleep_record_id} обновлена на {quality}.')
        except sqlite3.Error as e:
            logger.error(f'Ошибка при обновлении оценки качества сна: {e}', exc_info=True)
        finally:
            if conn:
                conn.close()

    def add_note(self, sleep_record_id: int, note_text: str):
        """
        Добавляет или обновляет заметку к сессии сна с оценкой качества.
        Если заметка для указанной сессии сна уже существует, она будет обновлена,
        в противном случае будет создана новая.
        Это соответствует логике один-к-одному (одна запись о сне может иметь одну заметку).
        :param sleep_record_id: int: ID сессии сна.
        :param note_text: str: Текст заметки.
        """
        if not note_text or not isinstance(note_text, str):
            logger.warning(f'Попытка записать пустую или нетекстовую заметку для сессии {sleep_record_id}')
            return False
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            with conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO notes (sleep_record_id, notes_text) VALUES (?, ?)",
                               (sleep_record_id, note_text))
            logger.info(f'Заметка к сессии сна {sleep_record_id} добавлена/обновлена.')
        except sqlite3.Error as e:
            logger.error(f'Ошибка при добавлении заметки к сессии сна: {e}', exc_info=True)
        finally:
            if conn:
                conn.close()

    def get_latest_unfinished_sleep_session(self, user_id: int) -> tuple[int, datetime] | tuple[None, None]:
        """
        Находит последнюю незавершенную сессию сна для пользователя.
        :param user_id: int: ID пользователя в телеграмме.
        :return: tuple[int, datetime] | tuple[None, None]: ID и время начала последней незавершенной сессии сна,
                                                           если найдено, иначе (None, None).
        """
        conn = None
        try:
            sql_select = '''
            SELECT id, sleep_time
            FROM sleep_records
            WHERE user_id = ? AND wake_time IS NULL
            ORDER BY sleep_time
            DESC LIMIT 1
            ;'''
            conn = sqlite3.connect(self.db_name)
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql_select, (user_id,))
                result = cursor.fetchone()
            if result:
                sleep_record_id, sleep_time = result
                logger.info(f'Найдена незавершенная сессия сна для {user_id}: {result}.')
                # sleep_time(преобразован в формат для Python)
                return sleep_record_id, datetime.fromisoformat(sleep_time)
            return None, None
        except sqlite3.Error as e:
            logger.error(f'Ошибка при получении последней незавершенной сессии сна: {e}', exc_info=True)
            return None, None
        finally:
            if conn:
                conn.close()

    def get_latest_finished_sleep_session_without_quality(
            self, user_id: int, date: datetime.date = None
    ) -> tuple[int, datetime, datetime] | tuple[None, None, None]:
        """
        Ищет последнюю завершенную сессию сна без оценки качества.
        Если дата указана, поиск ограничивается сессиями завершенными в эту дату.
        :param user_id: int: ID пользователя в телеграмме.
        :param date: datetime.date | None: Дата для фильтрации сессий сна.
        :return: tuple[int, datetime, datetime] | tuple[None, None, None]:
                                ID сессии, время начала сна и время пробуждения, если найдено, иначе (None, None, None).
        """
        conn = None
        try:
            query = """
            SELECT id, sleep_time, wake_time
            FROM sleep_records
            WHERE user_id = ? AND wake_time IS NOT NULL AND sleep_quality IS NULL
            """
            params = [user_id]
            # Если дата указана, добавляем в запрос сравнение этой даты с датой завершенной сессии сна
            if date:
                query += " AND DATE(wake_time) = ?"
                # добавляем в список параметров дату, преобразовав в формат для SQLite
                params.append(date.isoformat())
            # добавляем в запрос сортировку полученных данных и лимит на 1 запись
            query += " ORDER BY wake_time DESC LIMIT 1"
            conn = sqlite3.connect(self.db_name)
            with conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
            if result:
                sleep_record_id, sleep_time, wake_time = result
                logger.info(f'Найдена завершенная сессия без оценки качества сна для {user_id}: {result}.')
                # sleep_time, wake_time (преобразованные в формат для Python)
                return sleep_record_id, datetime.fromisoformat(sleep_time), datetime.fromisoformat(wake_time)
            return None, None, None
        except sqlite3.Error as e:
            logger.error(f'Ошибка при получении завершенной сессии без оценки качества сна: {e}', exc_info=True)
            return None, None, None
        finally:
            if conn:
                conn.close()

    def get_latest_finished_sleep_session_with_quality(
            self, user_id: int, date: datetime.date = None
    ) -> tuple[int, datetime, datetime] | None:
        """
        Ищет последнюю завершенную сессию сна с оценкой качества.
        Если дата указана, поиск ограничивается сессиями завершенными в эту дату.
        :param user_id: int: ID пользователя в телеграмме.
        :param date: datetime.date | None: Дата для фильтрации сессий сна.
        :return: tuple[int, datetime, datetime] | None: ID сессии, время начала сна и время пробуждения, если найдено, иначе None.
        """
        conn = None
        try:
            query = """
            SELECT id, sleep_time, wake_time
            FROM sleep_records 
            WHERE user_id = ? AND wake_time IS NOT NULL AND sleep_quality IS NOT NULL
            """
            params = [user_id]
            # Если дата указана, добавляем в запрос сравнение этой даты с датой завершенной сессии сна
            if date:
                query += " AND DATE(wake_time) = ?"
                # добавляем в список параметров дату, преобразовав в формат для SQLite
                params.append(date.isoformat())
            # добавляем в запрос сортировку полученных данных и лимит на 1 запись
            query += " ORDER BY wake_time DESC LIMIT 1"
            conn = sqlite3.connect(self.db_name)
            with conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
            if result:
                sleep_record_id, sleep_time, wake_time = result
                logger.info(f'Найдена завершенная сессия с оценкой качества сна {user_id}: {result}.')
                # sleep_time, wake_time (преобразованные в формат для Python)
                return sleep_record_id, datetime.fromisoformat(sleep_time), datetime.fromisoformat(wake_time)
            return None
        except sqlite3.Error as e:
            logger.error(f'Ошибка при получении последней завершенной сессии с оценкой качества: {e}', exc_info=True)
            return None
        finally:
            if conn:
                conn.close()

    def get_note_by_sleep_record_id(self, sleep_record_id: int) -> str | None:
        """
        Возвращает текст заметки для указанной сессии сна.
        :param sleep_record_id: int: ID сессии сна.
        :return: str | None: Текст заметки, если она существует, иначе None.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT notes_text FROM notes WHERE sleep_record_id = ?", (sleep_record_id,))
                result = cursor.fetchone()
            if result:
                logger.info(f'Текст заметки {result[0]} для сессии {sleep_record_id} получен.')
                return result[0]
            return None
        except sqlite3.Error as e:
            logger.error(f'Ошибка при получении текста заметки: {e}', exc_info=True)
            return None
        finally:
            if conn:
                conn.close()

    def get_sleep_statistic(self, user_id: int) -> tuple[int, int, float]:
        """
        Рассчитывает статистику сна для пользователя.
        :param user_id: int: ID пользователя в телеграмме.
        :return: tuple[int, int, float] : Возвращает кортеж из: общего количества сессий сна,
                                    общего и среднего количества сна в секундах. Если завершенных сессий нет (0, 0, 0).
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT
                            COUNT(id),
                            SUM(strftime('%s', wake_time) - strftime('%s', sleep_time))
                            FROM sleep_records
                            WHERE user_id = ? AND wake_time IS NOT NULL
                        """,(user_id,))
                total_session, total_sleep_duration_seconds = cursor.fetchone()

            if total_session is None or total_session == 0:
                return 0, 0, 0.0

            average_sleep_duration_seconds = (total_sleep_duration_seconds / total_session) if total_session > 0 else 0.0
            logger.info(f'Статистики сна для пользователя ({user_id}) рассчитана.')
            return total_session, total_sleep_duration_seconds, average_sleep_duration_seconds
        except sqlite3.Error as e:
            logger.error(f'Ошибка при получении статистики сна для пользователя: {e}', exc_info=True)
            return 0, 0, 0.0
        finally:
            if conn:
                conn.close()

