import logging
import logging.config  # Нужен для dictConfig
import yaml  # Нужен для работы с YAML
import os  # Нужен для os.getenv и os.exists
from pathlib import Path  # Нужен для создания директорий

YamlPathType = str


def setup_logging(
        default_path: YamlPathType = 'my_logging_config.yaml',
        env_key: str = 'LOG_CFG') -> None:
    """
     Настраивает систему логирования приложения.
     Пытается загрузить конфигурацию из YAML-файла, указанного в default_path или через переменную окружения env_key.
     При возникновении ошибки загрузки или если файл не найден,
     используется базовая конфигурация логирования (вывод в stderr, уровень DEBUG).
     :param default_path: YamlPathType: Путь к файлу конфигурации YAML по умолчанию.
     :param env_key: str: Ключ переменной окружения, которая может переопределить default_path.
     :return: None: Конфигурация логирования применяется глобально.
    """
    path: YamlPathType = os.getenv(env_key, default_path)  # 1. Определяем путь к конфигурации
    if os.path.exists(path):  # 2. Проверяем существование файла
        try:
            with open(path, 'rt', encoding='utf-8') as f:  # 3. Открываем и читаем YAML
                config: dict = yaml.safe_load(f)  # 4. Парсим YAML

            # 5. Создаем директорию для логов если ее нет
            log_dir: Path = Path('logs')
            log_dir.mkdir(exist_ok=True)  # отключаем возникновение ошибки в случае, если директория уже существует

            # 6. Применяем конфигурацию
            logging.config.dictConfig(config)
            print(f'Конфигурация логирования загружена из файла: {path}')
        except Exception as e:
            # 7. Если файл найден, но произошла ошибка при его чтении/парсинге
            print(f'Ошибка при чтении или парсинге файла конфигурации "{path}": {e}.'
                  f' Используются базовые настройки (уровень DEGUG).')
            logging.basicConfig(level=logging.DEBUG)  # Fallback на DEBUG
    else:
        # 8. Если файл не найден, используем базовую программную настройку
        print(f'Файл конфигурации логирования "{path}" не найден. Используются базовые настройки (уровень DEGUG).')
        logging.basicConfig(level=logging.DEBUG)  # Fallback на DEBUG