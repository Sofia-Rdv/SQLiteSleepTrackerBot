import os
import telebot
from telebot import types
from datetime import datetime
# Импортируем DatabaseManager, в нем вся логика работы с БД
from db_manager import DatabaseManager

# --- Инициализация бота и базы данных ---
# Токен в переменной окружения
MY_TOKEN_BOT = os.getenv("API_TOKEN")
bot = telebot.TeleBot(MY_TOKEN_BOT)
# Инициализируем менеджер базы данных
db = DatabaseManager()


# --- Обработчики команд ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    Обрабатывает команду start, обновлено для работы с БД
    :param message:
    :return:
    """
    # ID пользователя из чата с ботом в телеграмме
    user_id = message.chat.id
    # Имя пользователя в профиле телеграмма
    user_name = message.from_user.first_name if message.from_user.first_name else 'Пользователь'
    # Добавляем пользователя в базу данных при старте
    db.add_user(user_id, user_name)

    # создаем inline клавиатуру
    markup = types.InlineKeyboardMarkup()
    # создаем кнопки с callback_data - командами
    sleep_button = types.InlineKeyboardButton("Сладких снов 😴", callback_data='/sleep')
    wake_button = types.InlineKeyboardButton("Я проснулся ☀", callback_data='/wake')
    quality_button = types.InlineKeyboardButton("Качество сна 💫", callback_data='/quality')
    notes_button = types.InlineKeyboardButton("Заметки 📝", callback_data='/notes')
    recom_button = types.InlineKeyboardButton("Общие рекомендации 🧘🏼‍♀️", callback_data='/recom')
    statis_inl_button = types.InlineKeyboardButton("Статистика сна 📊💤", callback_data='/statis')
    # Добавляем кнопки на клавиатуру
    markup.add(sleep_button, wake_button)
    markup.add(quality_button, notes_button)
    markup.add(recom_button)
    markup.add(statis_inl_button)

    # создаем Reply клавиатуру
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # создаем кнопки
    start_button = types.KeyboardButton("/start")
    help_button = types.KeyboardButton("/help")
    recom_button_reply = types.KeyboardButton("/recom")
    statis_button = types.KeyboardButton("/statis")
    # добавляем кнопки на клавиатуру
    keyboard.add(help_button, recom_button_reply)
    keyboard.add(start_button, statis_button)

    # отправляем приветственное сообщение с клавиатурой
    bot.send_message(message.chat.id, """Привет!
    Я бот, который помогает отслеживать количество и качество сна💤.
    Используйте кнопки или команды:
    /sleep - начало сна. Выбирайте эту команду, когда ложитесь спать!(или кнопка 'Сладких снов 😴')
    /wake - конец сна. Выбирайте эту команду, когда проснулись!(или кнопка 'Я проснулся ☀')
    /quality - оценка качества сна по 5-бальной шкале. Выбирайте эту команду, когда хотите поставить оценку качества своему сну!(или кнопка 'Качество сна 💫')
    /notes - Ваш дневник для заметок. Выбирайте эту команду, когда хотите добавить комментарий к оценке качества Вашего сна!(или кнопка 'Заметки 📝')
    /recom - общие рекомендации для улучшения качества сна (или кнопка 'Общие рекомендации 🧘🏼‍♀️')
    /statis - cтатистика Вашего сна. Выбирайте эту команду, когда хотите получить статистику Вашего сна, в нее входят:
    общее количество сессий сна, общая и средняя продолжительность сна (или кнопка 'Статистика сна 📊💤')
    /help - пришлю список доступных команд
    /start - перезапуск бота
    Важно! Поставить оценку качества сна и комментарий к ней Вы можете только в день завершения сессии сна💫""",
                     reply_markup=markup)
    bot.send_message(message.chat.id, """Кнопки с этими командами будут всегда доступны:
    /help - пришлю список доступных команд
    /recom - общие рекомендации для улучшения качества сна
    /statis - статистика сна
    /start - перезапуск бота
    Они находятся под строкой ввода сообщения, или рядом со значком микрофона""", reply_markup=keyboard)


@bot.message_handler(commands=['help'])
def handle_help(message):
    """
    Обрабатывает команду help
    :param message:
    :return:
    """
    # создаем inline клавиатуру
    markup = types.InlineKeyboardMarkup()
    # создаем кнопки с callback_data - командами
    sleep_button = types.InlineKeyboardButton("Сладких снов 😴", callback_data='/sleep')
    wake_button = types.InlineKeyboardButton("Я проснулся ☀", callback_data='/wake')
    quality_button = types.InlineKeyboardButton("Качество сна 💫", callback_data='/quality')
    notes_button = types.InlineKeyboardButton("Заметки 📝", callback_data='/notes')
    recom_button = types.InlineKeyboardButton("Общие рекомендации 🧘🏼‍♀️", callback_data='/recom')
    statis_inl_button = types.InlineKeyboardButton("Статистика сна 📊💤", callback_data='/statis')
    # добавляем кнопки на клавиатуру
    markup.add(sleep_button, wake_button)
    markup.add(quality_button, notes_button)
    markup.add(recom_button)
    markup.add(statis_inl_button)

    # отправляем сообщение с доступными командами и клавиатурой
    bot.send_message(message.chat.id, """Список доступных команд:
    /sleep - начало сна. Выбирайте эту команду, когда ложитесь спать!(или кнопка 'Сладких снов 😴')
    /wake - конец сна. Выбирайте эту команду, когда проснулись!(или кнопка 'Я проснулся ☀')
    /quality - оценка качества сна по 5-бальной шкале. Выбирайте эту команду, когда хотите поставить оценку качества своему сну!(или кнопка 'Качество сна 💫')
    /notes - Ваш дневник для заметок. Выбирайте эту команду, когда хотите добавить комментарий к оценке качества Вашего сна!(или кнопка 'Заметки 📝')
    /recom - общие рекомендации для улучшения качества сна (или кнопка 'Общие рекомендации 🧘🏼‍♀️')
    /statis - cтатистика Вашего сна. Выбирайте эту команду, когда хотите получить статистику Вашего сна, в нее входят:
    общее количество сессий сна, общая и средняя продолжительность сна (или кнопка 'Статистика сна 📊💤')
    /help - пришлю список доступных команд 📃
    /start - перезапуск бота 🔁
    Важно! Поставить оценку качества сна и комментарий к ней Вы можете только в день завершения сессии сна💫
    Также Вы можете использовать кнопки ниже :""", reply_markup=markup)


@bot.message_handler(commands=['recom'])
def handle_recom(message):
    """
    Обрабатывает команду recom
    :param message:
    :return:
    """
    # отправляем пользователю сообщение с общими рекомендациями
    bot.send_message(message.chat.id, """✨Общие рекомендации для улучшения качества сна:

1. Старайтесь ложиться спать до 22:00 🌌

2. Спите не менее 8 часов в день ⏰

3. Добавляйте дополнительно дневной сон,
если плохо или мало спали ночью 🛌

4. Не кушайте тяжелую пищу перед сном и в целом не стоит есть за 1,5-2 часа до сна 🍽️

5. Убирайте гаджеты как минимум за 30 минут до сна 📱💻

6. Пользуйтесь берушами, если Вы чутко спите 🙉

7. Полезно пить чай с мелиссой, он обладает мягким успокаивающим и расслабляющим эффектом 🍵""")


def calculate_sleep_statistics(user_id):
    """
    Рассчитывает статистику сна для пользователя, обновлено для работы с БД
    :param user_id: ID пользователя
    :return:
    """
    try:
        total_session, total_sleep_duration_sec, average_sleep_duration_sec = db.get_sleep_statistic(user_id)
        # Проверка, есть ли у пользователя данные о сне
        if total_session == 0:
            return "У Вас пока нет данных о сне.🙃"

        # Преобразование в часы и минуты
        total_hours = int(total_sleep_duration_sec // 3600)
        total_minutes = int((total_sleep_duration_sec % 3600) // 60)
        average_hours = int(average_sleep_duration_sec // 3600)
        average_minutes = int((average_sleep_duration_sec % 3600) // 60)

        # текст для пользователя
        statistics_text = f"""💤📊Ваша статистика сна:

    😴Всего сессий сна: {total_session}

    ⏳Общая продолжительность сна: {total_hours} часов {total_minutes} минут

    🛌Средняя продолжительность сна: {average_hours} часов {average_minutes} минут"""

        return statistics_text
    except Exception as e:
        return f"Простите, произошла ошибка {e}. Попробуйте еще раз.😔"


@bot.message_handler(commands=['statis'])
def handle_statistics(message):
    """
    Обрабатывает команду statis.
    Вызывает функцию расчета статистики сна и отправляет пользователю результат выполнения.
    :param message:
    :return:
    """
    user_id = message.chat.id
    statistics = calculate_sleep_statistics(user_id)
    bot.send_message(user_id, statistics)


@bot.message_handler(commands=['sleep'])
def handle_sleep(message):
    """
    Обрабатывает команду sleep, обновлено для работы с БД.
    :param message:
    :return:
    """
    user_id = message.chat.id
    user_name = message.from_user.first_name if message.from_user.first_name else 'Пользователь'
    # Убедимся, что пользователь есть в БД
    db.add_user(user_id, user_name)

    try:
        # Проверяем наличие активной(незавершенной) сессии сна
        sleep_record_id, sleep_start_time = db.get_latest_unfinished_sleep_session(user_id)
        if sleep_record_id:
            markup = types.InlineKeyboardMarkup()
            wake_button = types.InlineKeyboardButton("Я проснулся ☀", callback_data='/wake')
            markup.add(wake_button)
            bot.send_message(user_id, "У Вас уже есть активная сессия сна😴\n"
                                      "Сначала завершите ее отметив свое пробуждение.😊", reply_markup=markup)
            return

        # Если активной сессии сна нет, начинаем новую
        # Текущая дата, для установления начала сессии сна
        current_time = datetime.now()
        new_sleep_record_id = db.start_sleep_session(user_id, current_time)
        if new_sleep_record_id:
            markup = types.InlineKeyboardMarkup()
            wake_button = types.InlineKeyboardButton("Я проснулся ☀", callback_data='/wake')
            markup.add(wake_button)
            bot.send_message(user_id, "Отмечено время начала сна.\nСладких снов!✨\nНе забудьте отметить свое пробуждение!")
            bot.send_message(user_id, "Отметить пробуждение: ", reply_markup=markup)
        else:
            bot.send_message(user_id, "Простите, не удалось начать сессию сна. . Попробуйте еще раз.😔")

    except Exception as e:
        bot.send_message(user_id, f"Простите, произошла ошибка {e}. Попробуйте еще раз.😔")


@bot.message_handler(commands=['wake'])
def handle_wake(message):
    """
    Обработчик команды wake. Обновлено для работы с БД.
    :param message:
    :return:
    """
    user_id = message.chat.id
    user_name = message.from_user.first_name if message.from_user.first_name else 'Пользователь'
    db.add_user(user_id, user_name)
    try:
        # Ищем последнюю незавершенную сессию сна
        sleep_record_id, sleep_start_time = db.get_latest_unfinished_sleep_session(user_id)
        if sleep_record_id:
            sleep_end_time = datetime.now()
            # Завершаем найденную сессию сна
            db.end_sleep_session(sleep_record_id, sleep_end_time)

            # Рассчитываем продолжительность сна за эту сессию
            duration = sleep_end_time - sleep_start_time
            duration_hours = int(duration.total_seconds() // 3600)
            duration_minutes = int((duration.total_seconds() % 3600) // 60)

            # Отправляем пользователю информативное сообщение с продолжительностью сна
            # и предложением оценить качество сна
            markup_q = types.InlineKeyboardMarkup()
            quality_button = types.InlineKeyboardButton("Качество сна 💫", callback_data='/quality')
            markup_q.add(quality_button)
            bot.send_message(user_id,
                             f"Надеюсь Вы выспались!☀ Вы спали, примерно, {duration_hours} часов {duration_minutes} минут.\n"
                             f"Не забудьте поставить оценку Вашему сну сегодня!😌")
            bot.send_message(user_id, "Поставить оценку: ", reply_markup=markup_q)
        else:
            markup_s = types.InlineKeyboardMarkup()
            sleep_button = types.InlineKeyboardButton("Сладких снов 😴", callback_data='/sleep')
            markup_s.add(sleep_button)
            bot.send_message(user_id, "Сначала отметьте, когда легли спать.😊", reply_markup=markup_s)
    except Exception as e:
        bot.send_message(user_id, f"Простите, произошла ошибка {e}. Попробуйте еще раз.😔")


@bot.message_handler(commands=['quality'])
def handle_quality(message):
    """
    Обработчик команды quality. Обновлена для работы с БД.
    :param message:
    :return:
    """
    user_id = message.chat.id
    user_name = message.from_user.first_name if message.from_user.first_name else 'Пользователь'
    db.add_user(user_id, user_name)
    try:
        # Ищем последнюю завершенную сессию сегодня без оценки качества сна
        today = datetime.now().date()
        sleep_record_id, _, _ = db.get_latest_finished_sleep_session_without_quality(user_id, date=today)
        if sleep_record_id:
            # Создаем клавиатуру и кнопки с оценками от 1 до 5
            keyboard = types.InlineKeyboardMarkup()
            for i in range(1, 6):
                button = types.InlineKeyboardButton(str(i), callback_data=f'quality_{i}_{sleep_record_id}')
                keyboard.add(button)
            bot.send_message(user_id, """Оцените, пожалуйста, качество Вашего сна сегодня!

            Оценка не обязательно должна в точности соответствовать описанию.
            Достаточно, чтобы она подходила лучше остальных, а особенности и отличия укажите в комментарии к оценке.

            1️⃣ Очень плохо спалось, хуже некуда. Чувствую себя подавленно и разбито...

            2️⃣ Спалось плохо,очень чутко. Хочется поскорее вернуться в кроватку.

            3️⃣ Долго не получалось уснуть, но в целом спалось нормально.

            4️⃣ Спалось хорошо, но не против еще поваляться в кроватке.

            5️⃣ Спалось очень хорошо, удалось выспаться, чувствую себя отлично!""", reply_markup=keyboard)
        else:
            markup = types.InlineKeyboardMarkup()
            wake_button = types.InlineKeyboardButton("Я проснулся ☀", callback_data='/wake')
            markup.add(wake_button)
            bot.send_message(user_id, "Сначала отметьте свое пробуждение,"
                                      " или Вы уже оценили свой последний сон.😊", reply_markup=markup)
    except Exception as e:
        bot.send_message(user_id, f"Простите, произошла ошибка {e}. Попробуйте еще раз.😔")


@bot.callback_query_handler(func=lambda call: call.data.startswith("quality_"))
def handle_quality_callback(call):
    """
    Обрабатывает нажатие на кнопки оценки качества сна.
    :param call:
    :return:
    """
    user_id = call.from_user.id
    try:
        # Извлекаем из callback_data необходимые данные, предварительно разделив на части
        parts = call.data.split('_')
        # Оценка качества сна
        quality = int(parts[1])
        # ID сессии сна, которой поставили оценку
        sleep_record_id = int(parts[2])

        # Добавляем оценку качества сна, для найденной ранее сессии, в базу данных
        db.update_sleep_quality(sleep_record_id, quality)

        markup = types.InlineKeyboardMarkup()
        notes_button = types.InlineKeyboardButton("Заметки 📝", callback_data='/notes')
        markup.add(notes_button)
        # изменяем сообщение, с кнопками для оценки качества сна,
        # после нажатия пользователем на какую-то из предложенных кнопок, на сообщение указанное ниже
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id,
                              text=f"Ваша оценка качества сна {quality} записана! Вы можете написать комментарий к оценке"
                                   f" после команды /notes или кнопки :", reply_markup=markup)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"Простите, произошла ошибка {e}. Попробуйте еще раз.😔")

    # подтверждение того, что запрос был получен и обработан
    bot.answer_callback_query(call.id)


@bot.message_handler(commands=['notes'])
def handle_notes(message: types.Message):
    """
    Обработчик команды notes. Позволяет добавлять или обновлять заметки к сессиям сна.
    :param message: types.Message: Объект сообщения.
    """
    user_id = message.chat.id
    user_name = message.from_user.first_name if message.from_user.first_name else 'Пользователь'
    db.add_user(user_id, user_name)

    try:
        today = datetime.now().date()
        # Ищем сессию сна с оценкой качества сна, независимо от наличия заметки
        sleep_record_data = db.get_latest_finished_sleep_session_with_quality(user_id, date=today)
        if sleep_record_data:
            sleep_record_id, _, _ = sleep_record_data

            # Проверяем есть уже заметка к найденной сессии сна
            existing_note = db.get_note_by_sleep_record_id(sleep_record_id)
            if existing_note:
                bot.send_message(user_id, f'У вас уже есть заметка к этой сессии сна: "{existing_note}".'
                                          f' Напишите новый комментарий, чтобы обновить ее.😊')
            else:
                bot.send_message(user_id, "Пожалуйста, напишите комментарий к Вашей оценке сна в одном сообщении,"
                                      " я все записываю!😊")
            # задаем следующий шаг бота, а именно,
            # вызываем функцию записи комментария пользователя к оценке качества сна и передаем sleep_record_id
            bot.register_next_step_handler(message, process_notes_step, sleep_record_id)
        else:
            markup = types.InlineKeyboardMarkup()
            quality_button = types.InlineKeyboardButton("Качество сна 💫", callback_data='/quality')
            markup.add(quality_button)
            bot.send_message(user_id, "У Вас нет завершенной сессии сна с оченкой качества, "
                                      "к которой можно добавить заметку. "
                                      "Пожалуйста, сначала оцените сон.😊", reply_markup=markup)
    except Exception as e:
        bot.send_message(user_id, f"Простите, произошла ошибка {e}. Попробуйте еще раз.😔")


def process_notes_step(message: types.Message, sleep_record_id: int):
    """
    Записывает или обновляет комментарий к оценке сна.
    :param message: types.Message: Объект сообщения.
    :param sleep_record_id: int: ID сессии сна.
    """
    try:
        # Получаем текст заметки к оценке качества сна
        notes = message.text
        user_id = message.chat.id
        # add_note() самостоятельно поймет, обновить или добавить комментарий
        db.add_note(sleep_record_id, notes)
        bot.send_message(user_id, "Спасибо, Ваш комментарий записан!✅")
    except Exception as e:
        user_id = message.chat.id
        bot.send_message(user_id, f"Простите, произошла ошибка {e}. Попробуйте еще раз.😔")


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """
    Обрабатывает нажатия на inline кнопки.
    Каждой кнопке соответствует определенная команда, для этой команды вызывается ее функция-обработчик.
    :param call:
    :return:
    """
    try:
        if call.data == '/sleep':
            handle_sleep(call.message)

        elif call.data == '/wake':
            handle_wake(call.message)

        elif call.data == '/quality':
            handle_quality(call.message)

        elif call.data == '/notes':
            handle_notes(call.message)

        elif call.data == '/recom':
            handle_recom(call.message)

        elif call.data == '/statis':
            handle_statistics(call.message)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"Простите, произошла ошибка {e}. Попробуйте еще раз.😔")

    # подтверждение того, что запрос был получен и обработан
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message: True)
def all_other_message(message):
    """
    Обрабатывает все иные сообщения от пользователя.
    Просто текстовые сообщения вне комментария к оценке, фото, видео и тд.
    :param message:
    :return:
    """
    bot.reply_to(message, "Простите, я Вас не понимаю.😔\nПожалуйста, используйте кнопки или команды.😊")


# Запускаем бота
if __name__ == '__main__':
        bot.polling(non_stop=True, interval=0)




