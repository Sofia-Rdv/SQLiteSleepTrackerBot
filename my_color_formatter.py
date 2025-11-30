import logging
from colorama import Fore, Style, init


# Инициализируем colorama для поддержки цвета в консоли.
# autoreset=True гарантирует что цвета сбрасываются после каждой печати.
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """
    Кастомный форматтер для цветного вывода логов в консоль.
    Этот форматтер сопоставляет уровни логирования (DEBUG, INFO, WARNING, ...)
    с соответствующими цветами из библиотеки colorama и применяет цвет ко всей строке лог-сообщения.
    """
    # Тип: dict[str, str] - словарь, где ключ (имя уровня) - строка, значение (код цвета) - тоже строка
    COLORS: dict[str, str] = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA + Style.BRIGHT
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        Форматирует объект LogRecord, добавляя цвет в соответствии с уровнем лога.
        При возникновении ошибки во время форматирования создается стандартный форматтер для сообщения об ошибке,
         чтобы избежать рекурсии и гарантировать, что сообщение будет выведено.
        :param record: logging.LogRecord: объект LogRecord, содержащий информацию о сообщении лога.
        :return: str: Отформатированная строка лога с примененным цветом
         или строка лога отформатированная стандартным форматтером.
        """
        try:
            # Получаем стандартное сообщение, отформатированное родительским классом
            log_message = super().format(record)

            # Получаем цвет для текущего уровня
            # Если уровень не найден в COLORS, используется белый цвет по умолчанию
            color = self.COLORS.get(record.levelname, Fore.WHITE)
            # Добавляем цвет к сообщению
            # autoreset=True в init() позаботится о Style.RESET_ALL,
            # но явно его добавить не повредит и может быть полезно,
            # если init() не был вызван с autoreset=True по какой-то причине
            return color + log_message + Style.RESET_ALL
        except Exception as e:
            # Если во время форматирования произошла ошибка
            # создаем стандартный форматтер для сообщения об ошибке, чтобы избежать рекурсии
            # и гарантировать, что сообщение будет выведено
            fallback_formatter = logging.Formatter()
            # Возвращаем отформатированное сообщение об ошибке, используя стандартный форматтер
            return fallback_formatter.formatMessage(record)
