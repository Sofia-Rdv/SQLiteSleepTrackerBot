import sqlite3
from datetime import datetime, timedelta
# Импортируем threading для отлдочных принтов, чтобы видеть какой поток работает
import threading


class DatabaseManager:
    def __init__(self, db_name: str = 'sleep_tracker.db'):
        self.db_name: str = db_name
        self._create_tables()

    def _create_tables(self):
        """Создает таблицы, если они не существуют. Использует собственное соединение для этой операции."""
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

        try:
            # Открываем соединение внутри метода
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                # Создает таблицу users
                cursor.execute(sql_users)
                # Создает таблицу sleep_records
                cursor.execute(sql_sleep_records)
                # Создает таблицу notes
                cursor.execute(sql_notes)
            # Изменения в БД сохранятся автоматически с помощью with
            print(f'[{threading.current_thread().name}] Таблицы успешно созданы или уже существуют')
        except sqlite3.Error as e:
            print(f'[{threading.current_thread().name}] Ошибка при создании таблиц: {e}')

    def add_user(self, user_id: int, user_name: str):
        """
        Добавляет нового пользователя, если его нет в базе данных. Использует собственное соединение.
        :param user_id: int: ID пользователя в телеграмме.
        :param user_name: str: Имя пользователя в телеграмме, если указано, иначе указывается "Пользователь".
        """
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (user_id, user_name))
            print(
                f'[{threading.current_thread().name}] Пользователь {user_name} ({user_id}) добавлен или уже существует в БД')
        except sqlite3.Error as e:
            print(f'[{threading.current_thread().name}] Ошибка при добавлении пользователя в БД: {e}')

    def start_sleep_session(self, user_id: int, sleep_time: datetime) -> int | None:
        """
        Начинает новую сессию сна для пользователя. Использует собственное соединение.
        :param user_id: int: ID пользователя в телеграмме.
        :param sleep_time: datetime: Время начала сна
        :return: int: Возвращает ID новой записи сна
        """
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                # Добавляем время начала сна(преобразованное для SQLite) для указанного пользователя в таблицу с сессиями сна
                cursor.execute("INSERT INTO sleep_records (user_id, sleep_time) VALUES (?, ?)",
                               (user_id, sleep_time.isoformat()))
                # Возвращаем ID новой записи сна
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f'[{threading.current_thread().name}] Ошибка при начале сессии сна: {e}')
            return None

    def end_sleep_session(self, sleep_record_id: int, wake_time: datetime):
        """
        Завершает сессию сна, обновляя время пробуждения. Использует собственное соединение.
        :param sleep_record_id: int: ID сессии сна
        :param wake_time: datetime: Время пробуждения
        """
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                # Добавляем время пробуждение преобразованное для SQLite
                cursor.execute("UPDATE sleep_records SET wake_time = ? WHERE id = ?",
                               (wake_time.isoformat(), sleep_record_id))
            print(f'[{threading.current_thread().name}] Сессия сна {sleep_record_id} завершена.')
        except sqlite3.Error as e:
            print(f'[{threading.current_thread().name}] Ошибка при завершении сессии сна: {e}')

    def update_sleep_quality(self, sleep_record_id: int, quality: int):
        """
        Добавляет оценку качества сна для конкретной записи(сессии сна), обновляя поле sleep_quality.
        Использует собственное соединение.
        :param sleep_record_id: int: ID сессии сна.
        :param quality: int: Оценка качества сна.
        """
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE sleep_records SET sleep_quality = ? WHERE id = ?",
                               (quality, sleep_record_id))
            print(
                f'[{threading.current_thread().name}] Оценка качества сна для сессии {sleep_record_id} обновлена на {quality}')
        except sqlite3.Error as e:
            print(f'[{threading.current_thread().name}] Ошибка при обновлении оценки качества сна: {e}')

    def add_note(self, sleep_record_id: int, notes_text: str):
        """
        Добавляет заметку к записи сна. Использует собственное соединение.
        Проверяет, существует ли уже заметка для указанной сессии сна. Если да, обновляет ее, иначе создает новую.
        Это соответствует логике один к одному (одна запись о сне может иметь одну заметку)
        :param sleep_record_id: int: ID сессии сна.
        :param notes_text: str: Текст заметки
        :return:
        """
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO notes (sleep_record_id, notes_text) VALUES (?, ?)",
                               (sleep_record_id, notes_text))
            print(f'[{threading.current_thread().name}] Заметка к сессии сна {sleep_record_id} добавлена/обновлена')
        except sqlite3.Error as e:
            print(f'[{threading.current_thread().name}] Ошибка при добавлении заметки к сессии сна: {e}')

    def get_latest_unfinished_sleep_session(self, user_id: int) -> tuple[int, datetime] | tuple[None, None]:
        """
        Находит последнюю незавершенную сессию сна и извлекает нужные данные
        (ID и время начала последней незавершенной сессии сна). Использует собственное соединение.
        :param user_id: int: ID пользователя в телеграмме.
        :return: int | datetime | None: ID и время начала последней незавершенной сессии сна пользователя,
                                        None в случае ошибки или отсутствия незавершенной сессии сна.
        """
        try:
            sql_select = '''
            SELECT id, sleep_time
            FROM sleep_records
            WHERE user_id = ? AND wake_time IS NULL
            ORDER BY sleep_time
            DESC LIMIT 1
            ;'''
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(sql_select, (user_id,))
                result = cursor.fetchone()
            if result:
                print(f'[{threading.current_thread().name}] Найдена незавершенная сессия сна для {user_id}: {result}')
                # sleep_record_id, sleep_time(преобразованное в формат для Python)
                return result[0], datetime.fromisoformat(result[1])
            return None, None
        except sqlite3.Error as e:
            print(f'[{threading.current_thread().name}] Ошибка при получении последней незавершенной сессии сна: {e}')
            return None, None

    def get_latest_finished_sleep_session_without_quality(
            self, user_id: int, date: datetime.date = None
    ) -> tuple[int, datetime, datetime] | tuple[None, None, None]:
        """
        Ищет последнюю завершенную сессию без оценки качества сна. Использует собственное соединение.
        Если date задано, ищет среди сессий завершенных в эту дату.
        :param user_id: int: ID пользователя в телеграмме.
        :param date: datetime.date | None: Дата для поиска завершенной сессии сна в эту дату.
        :return: int | datetime | None: Возвращает ID последней завершенной сессии без оценки качества сна,
                                        ее время начало сна и пробуждение, None в случае ошибки или отсутствия такой записи.
        """
        try:
            query = "SELECT id, sleep_time, wake_time FROM sleep_records WHERE user_id = ? AND wake_time IS NOT NULL AND sleep_quality IS NULL"
            params = [user_id]
            # Если дата указана, добавляем в запрос сравнение этой даты с датой завершенной сессии сна
            if date:
                query += " AND DATE(wake_time) = ?"
                # добавляем в список параметров дату, преобразовав в формат для SQLite
                params.append(date.isoformat())
            # добавляем в запрос сортировку полученных данных и лимит на 1 запись
            query += " ORDER BY wake_time DESC LIMIT 1"
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
            if result:
                print(
                    f'[{threading.current_thread().name}] Найдена завершенная сессия без оценки качества сна для {user_id}: {result}')
                # sleep_record_id, sleep_time, wake_time (преобразованные в формат для Python)
                return result[0], datetime.fromisoformat(result[1]), datetime.fromisoformat(result[2])
            return None, None, None
        except sqlite3.Error as e:
            print(
                f'[{threading.current_thread().name}] Ошибка при получении завершенной сессии без оценки качества сна: {e}')
            return None, None, None

    def get_latest_finished_sleep_session_with_quality_without_note(
            self, user_id: int, date: datetime.date = None
    ) -> tuple[int, datetime, datetime] | tuple[None, None, None]:
        """
        Ищет последнюю завершенную сессию с оценкой качества сна и без заметки. Использует собственное соединение.
        Если date задано, ищет среди сессий завершенных в эту дату.
        :param user_id: int: ID пользователя в телеграмме.
        :param date: datetime.date | None: Дата для поиска завершенной сессии сна в эту дату.
        :return: int | datetime | None: Возвращает ID последней завершенной сессии с оценкой качества сна и без заметки,
                                        ее время начало сна и пробуждение, None в случае ошибки или отсутствия такой записи.
        """
        try:
            query = """
            SELECT sr.id, sr.sleep_time, sr.wake_time
            FROM sleep_records sr
            LEFT JOIN notes n ON sr.id = n.sleep_record_id
            WHERE sr.user_id = ? AND sr.wake_time IS NOT NULL AND sr.sleep_quality IS NOT NULL AND n.id IS NULL
            """
            params = [user_id]
            # Если дата указана, добавляем в запрос сравнение этой даты с датой завершенной сессии сна
            if date:
                query += " AND DATE(sr.wake_time) = ?"
                # добавляем в список параметров дату, преобразовав в формат для SQLite
                params.append(date.isoformat())
            # добавляем в запрос сортировку полученных данных и лимит на 1 запись
            query += " ORDER BY sr.wake_time DESC LIMIT 1"
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
            if result:
                print(f'[{threading.current_thread().name}]'
                      f' Найдена завершенная сессия с оценкой качества сна и без заметки для {user_id}: {result}')
                # sleep_record_id, sleep_time, wake_time (преобразованные в формат для Python)
                return result[0], datetime.fromisoformat(result[1]), datetime.fromisoformat(result[2])
            return None, None, None
        except sqlite3.Error as e:
            print(f'[{threading.current_thread().name}]'
                  f' Ошибка при получении последней завершенной сессии с оценкой качества сна и без заметки: {e}')
            return None, None, None

    def get_sleep_statistic(self, user_id: int) -> tuple[int, int, int]:
        """
        Рассчитывает статистику сна для пользователя. Использует собственное соединение.
        :param user_id: int: ID пользователя в телеграмме.
        :return: int : Возвращает общее количество сессий сна, общее и среднее количество сна в секундах,
                       0 в случае ошибки или отсутствия завершенных сессий сна.
        """
        try:
            with sqlite3.connect(self.db_name) as conn:
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
                return 0, 0, 0

            average_sleep_duration_seconds = (total_sleep_duration_seconds / total_session) if total_session > 0 else 0
            return total_session, total_sleep_duration_seconds, average_sleep_duration_seconds
        except sqlite3.Error as e:
            print(f'[{threading.current_thread().name}] Ошибка при получении статистики сна для пользователя: {e}')
            return 0, 0, 0


# Пример использования
if __name__ == '__main__':
    db = DatabaseManager()
    user_id = 123
    user_name = 'TestUser'
    db.add_user(user_id, user_name)

    # Проверка незавершенной сессии сна (должно быть None)
    sr_id, st = db.get_latest_unfinished_sleep_session(user_id)
    print(f'Незавершенная сессия сна: {sr_id}, {st}')

    # Начало сессии сна
    sleep_start = datetime.now() - timedelta(hours=8, minutes=30)
    sleep_record_id = db.start_sleep_session(user_id, sleep_start)
    print(f'Начата сессия сна с ID: {sleep_record_id}')

    # Проверка незавершенной сессии сна (должно найти)
    sr_id_check, st_check = db.get_latest_unfinished_sleep_session(user_id)
    print(f'Незавершенная сессия сна: {sr_id_check}, {st_check}')

    # Завершение сессии сна
    sleep_end = datetime.now()
    db.end_sleep_session(sleep_record_id, sleep_end)

    # Добавляем оценку качества сна к завершенной сессии
    db.update_sleep_quality(sleep_record_id, 5)

    # Добавляем заметку к оценке качества сессии сна
    db.add_note(sleep_record_id, 'В целом хорошо спалось, но сначала долго засыпала')

    # Получение статистики
    session, total_duration, avg_duration = db.get_sleep_statistic(user_id)
    print(
        f'Статистика для {user_id}: Сессий сна={session}, Общая длительность={total_duration} сек, Средняя длительность={avg_duration}')

    # Проверка завершенной сессии сна без оценки (должно быть None)
    sr_id_no_q, st_no_q, wt_no_q = db.get_latest_finished_sleep_session_without_quality(user_id, date=sleep_end.date())
    print(f'Завершенная сессия сна без оценки: {sr_id_no_q}, {st_no_q}, {wt_no_q}')

    # Проверка завершенной сессии сна с оценкой, но без заметки (должно быть None)
    sr_id_q_no_n, st_q_no_n, wt_q_no_n = db.get_latest_finished_sleep_session_with_quality_without_note(user_id,
                                                                                                        date=sleep_end.date())
    print(f'Завершенная сессия сна с оценкой, но без заметки: {sr_id_q_no_n}, {st_q_no_n}, {wt_q_no_n}')
