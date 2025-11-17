from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_tasks_keyboard():
    """Основная клавиатура задач"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📝 Новая задача"),
                KeyboardButton(text="📋 Список задач"),
            ],
            [
                KeyboardButton(text="✅ Завершить задачу"),
                KeyboardButton(text="✏️ Редактировать задачу"),
            ],
            [
                KeyboardButton(text="🗑️ Удалить задачу"),
                KeyboardButton(text="🔄 Восстановить задачу"),
            ],
            [
                KeyboardButton(text="🏷️ Управление тегами"),
                KeyboardButton(text="🎯 Фильтры задач"),
            ],
            [
                KeyboardButton(text="📊 Группировка задач"),
                KeyboardButton(text="⏰ Ближайшие задачи"),
            ],
            [
                KeyboardButton(text="⚠️ Просроченные"),
                KeyboardButton(text="📅 Задачи на сегодня"),
            ],
            [
                KeyboardButton(text="🧹 Очистка хранилища"),
                KeyboardButton(text="🔙 Назад в меню"),
            ],
        ],
        resize_keyboard=True,
    )


def get_task_creation_keyboard():
    """Создание задачи"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏳ Без срока"), KeyboardButton(text="📅 Сегодня")],
            [KeyboardButton(text="📅 Завтра")],
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def get_priority_keyboard():
    """Приоритеты"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔴 Высокий"), KeyboardButton(text="🟡 Средний")],
            [
                KeyboardButton(text="🟢 Низкий"),
                KeyboardButton(text="📋 Все приоритеты"),
            ],
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def get_status_keyboard():
    """Статусы"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Выполненные"), KeyboardButton(text="📝 Активные")],
            [KeyboardButton(text="🗑️ Удаленные"), KeyboardButton(text="📋 Все статусы")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )


def get_filter_keyboard():
    """Фильтры задач"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎯 По приоритету"),
                KeyboardButton(text="📊 По статусу"),
            ],
            [KeyboardButton(text="🏷️ По тегу"), KeyboardButton(text="📅 По дате")],
            [
                KeyboardButton(text="🔄 Комбинированный"),
                KeyboardButton(text="📋 Все активные"),
            ],
            [KeyboardButton(text="🔙 Назад к задачам")],
        ],
        resize_keyboard=True,
    )


def get_edit_keyboard():
    """Редактирование задачи"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📝 Текст задачи"),
                KeyboardButton(text="📅 Дата и время"),
            ],
            [KeyboardButton(text="🎯 Приоритет")],
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def get_tags_keyboard():
    """Теги"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🏷️ Создать тег"),
                KeyboardButton(text="➕ Добавить к задаче"),
            ],
            [
                KeyboardButton(text="➖ Удалить с задачи"),
                KeyboardButton(text="🗑️ Удалить тег полностью"),
            ],
            [KeyboardButton(text="📋 Список тегов")],
            [KeyboardButton(text="🔙 Назад к задачам")],
        ],
        resize_keyboard=True,
    )


def get_moods_keyboard():
    """Управление настроениями"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="😊 Записать настроение"),
                KeyboardButton(text="📊 Сегодняшнее настроение"),
            ],
            [
                KeyboardButton(text="📝 Добавить заметку"),
                KeyboardButton(text="🗑️ Удалить заметку"),
            ],
            [
                KeyboardButton(text="✏️ Изменить заметку"),
                KeyboardButton(text="🔙 Назад в меню"),
            ],
        ],
        resize_keyboard=True,
    )


def get_mood_selection_keyboard():
    """Выбор настроения"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="😊 Отлично"), KeyboardButton(text="🙂 Хорошо")],
            [KeyboardButton(text="😐 Нормально"), KeyboardButton(text="😔 Плохо")],
            [KeyboardButton(text="😢 Ужасно")],
            [
                KeyboardButton(text="🔙 Назад к настроениям"),
                KeyboardButton(text="❌ Отмена"),
            ],
        ],
        resize_keyboard=True,
    )


def get_mood_period_keyboard():
    """Периоды для статистики настроений"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 7 дней"), KeyboardButton(text="📅 14 дней")],
            [KeyboardButton(text="📅 30 дней"), KeyboardButton(text="📅 90 дней")],
            [KeyboardButton(text="🔙 Назад к настроениям")],
        ],
        resize_keyboard=True,
    )


def get_mood_calendar_keyboard():
    """Календарь настроений"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 7 дней"), KeyboardButton(text="📅 14 дней")],
            [KeyboardButton(text="📅 30 дней"), KeyboardButton(text="📅 60 дней")],
            [KeyboardButton(text="🔙 Назад к настроениям")],
        ],
        resize_keyboard=True,
    )


def get_analytics_keyboard():
    """Аналитика"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📈 Общая статистика"),
                KeyboardButton(text="🎯 Анализ по приоритетам"),
            ],
            [
                KeyboardButton(text="📅 Динамика выполнения"),
                KeyboardButton(text="🏷️ Анализ по тегам"),
            ],
            [
                KeyboardButton(text="⚡ Продуктивность"),
                KeyboardButton(text="📋 Сводный отчет"),
            ],
            [
                KeyboardButton(text="😊 Анализ настроений"),
                KeyboardButton(text="📊 Статистика хранилища"),
            ],
            [KeyboardButton(text="🔙 Назад в меню")],
        ],
        resize_keyboard=True,
    )


def get_period_keyboard():
    """Периоды аналитики"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 7 дней"), KeyboardButton(text="📅 30 дней")],
            [
                KeyboardButton(text="📅 90 дней"),
                KeyboardButton(text="📅 Произвольный период"),
            ],
            [KeyboardButton(text="🔙 Назад к аналитике")],
        ],
        resize_keyboard=True,
    )


def get_notifications_keyboard():
    """Уведомления"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔔 Настройка напоминаний"),
                KeyboardButton(text="⏰ Время уведомлений"),
            ],
            [
                KeyboardButton(text="📱 Типы уведомлений"),
                KeyboardButton(text="🔕 Отключить все"),
            ],
            [
                KeyboardButton(text="🔔 Включить все"),
                KeyboardButton(text="📊 Статус уведомлений"),
            ],
            [KeyboardButton(text="🔙 Назад в меню")],
        ],
        resize_keyboard=True,
    )


def get_reminder_settings_keyboard():
    """Настройки напоминаний"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✅ Напоминания ВКЛ"),
                KeyboardButton(text="🔇 Напоминания ВЫКЛ"),
            ],
            [
                KeyboardButton(text="⏰ Изменить время"),
                KeyboardButton(text="⚠️ Просрочка ВКЛ"),
            ],
            [KeyboardButton(text="🔕 Просрочка ВЫКЛ")],
            [KeyboardButton(text="🔙 Назад к уведомлениям")],
        ],
        resize_keyboard=True,
    )


def get_start_keyboard():
    """Клавиатура старта"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🚀 Начать работу"),
                KeyboardButton(text="📚 Обучение"),
            ],
            [KeyboardButton(text="🎯 Быстрый старт")],
            [KeyboardButton(text="🔙 Назад в меню")],
        ],
        resize_keyboard=True,
    )


def get_help_keyboard():
    """Клавиатура помощи"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="❓ Работа с задачами"),
                KeyboardButton(text="❓ Работа тегами"),
            ],
            [
                KeyboardButton(text="❓ Использование аналитики"),
                KeyboardButton(text="❓ Настройка уведомлений"),
            ],
            [
                KeyboardButton(text="❓ Работа с настроениями"),
                KeyboardButton(text="❓ Чистка хранилища"),
            ],
            [KeyboardButton(text="🔙 Назад в меню")],
        ],
        resize_keyboard=True,
    )


def get_quick_actions_keyboard():
    """Быстрые действия"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📝 Быстрая задача"),
                KeyboardButton(text="😊 Мое настроение"),
            ],
            [
                KeyboardButton(text="📋 Список задач"),
                KeyboardButton(text="📊 Статистика"),
            ],
            [KeyboardButton(text="🔙 Главное меню")],
        ],
        resize_keyboard=True,
    )


def get_navigation_only_keyboard():
    """Только навигация"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад в меню"), KeyboardButton(text="📋 Задачи")],
            [KeyboardButton(text="😊 Настроения"), KeyboardButton(text="📊 Аналитика")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def get_back_to_main_keyboard():
    """Клавиатура для возврата в главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад в меню")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def get_back_cancel_keyboard():
    """Универсальная клавиатура с назад и отмена"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def get_analytics_keyboard():
    """Клавиатура раздела аналитики"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📈 Общая статистика"),
                KeyboardButton(text="🎯 Анализ по приоритетам"),
            ],
            [
                KeyboardButton(text="📅 Динамика выполнения"),
                KeyboardButton(text="🏷️ Анализ по тегам"),
            ],
            [
                KeyboardButton(text="⚡ Продуктивность"),
                KeyboardButton(text="📋 Сводный отчет"),
            ],
            [
                KeyboardButton(text="😊 Анализ настроений"),
                KeyboardButton(text="📊 Статистика хранилища"),
            ],
            [KeyboardButton(text="🔙 Назад в меню")],
        ],
        resize_keyboard=True,
    )


def get_period_keyboard():
    """Клавиатура выбора периода"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 7 дней"), KeyboardButton(text="📅 14 дней")],
            [KeyboardButton(text="📅 30 дней"), KeyboardButton(text="📅 90 дней")],
            [KeyboardButton(text="📅 Произвольный период")],
            [KeyboardButton(text="🔙 Назад к аналитике")],
        ],
        resize_keyboard=True,
    )


def get_analytics_types_keyboard():
    """Клавиатура типов аналитики"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Общий обзор"),
                KeyboardButton(text="🎯 По приоритетам"),
            ],
            [KeyboardButton(text="📈 Динамика"), KeyboardButton(text="😊 Настроения")],
            [
                KeyboardButton(text="⚡ Продуктивность"),
                KeyboardButton(text="📋 Сводка"),
            ],
            [KeyboardButton(text="🔙 Назад к периодам")],
        ],
        resize_keyboard=True,
    )


def get_back_to_analytics_keyboard():
    """Клавиатура для возврата в аналитику"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад к аналитике")],
        ],
        resize_keyboard=True,
    )


def get_filter_date():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Сегодня"), KeyboardButton(text="📅 Завтра")],
            [KeyboardButton(text="📅 Неделя"), KeyboardButton(text="⚠️ Просроченные")],
            [
                KeyboardButton(text="📋 Все даты"),
                KeyboardButton(text="🔙 Назад к задачам"),
            ],
        ],
        resize_keyboard=True,
    )


def get_main_keyboard():
    """Главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Задачи"), KeyboardButton(text="😊 Настроения")],
            [
                KeyboardButton(text="📊 Аналитика"),
                KeyboardButton(text="🔔 Уведомления"),
            ],
            [
                KeyboardButton(text="🧹 Очистка"),
                KeyboardButton(text="❓ Помощь"),
            ],
            [KeyboardButton(text="🚀 Старт")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел...",
    )


def get_grouping_keyboard():
    """Клавиатура для группировки задач"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🏷️ По тегам"),
                KeyboardButton(text="🎯 По приоритетам"),
            ],
            [
                KeyboardButton(text="📅 По датам"),
                KeyboardButton(text="📊 По статусу"),
            ],
            [
                KeyboardButton(text="🔄 Комбинированная"),
                KeyboardButton(text="📋 Все задачи"),
            ],
            [KeyboardButton(text="🔙 Назад к задачам")],
        ],
        resize_keyboard=True,
    )


def get_grouping_period_keyboard():
    """Клавиатура для выбора периода группировки"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📅 Сегодня"),
                KeyboardButton(text="📅 Завтра"),
            ],
            [
                KeyboardButton(text="📅 Неделя"),
                KeyboardButton(text="📅 Месяц"),
            ],
            [
                KeyboardButton(text="📅 Все время"),
                KeyboardButton(text="🔙 Назад к задачам"),
            ],
        ],
        resize_keyboard=True,
    )


def get_grouping_priority_keyboard():
    """Клавиатура для группировки по приоритетам"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔴 Высокий"),
                KeyboardButton(text="🟡 Средний"),
            ],
            [
                KeyboardButton(text="🟢 Низкий"),
                KeyboardButton(text="🎯 Все приоритеты"),
            ],
            [
                KeyboardButton(text="🔙 Назад к задачам"),
            ],
        ],
        resize_keyboard=True,
    )


def get_grouping_status_keyboard():
    """Клавиатура для группировки по статусам"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📝 Активные"),
                KeyboardButton(text="✅ Выполненные"),
            ],
            [
                KeyboardButton(text="🗑️ Удаленные"),
                KeyboardButton(text="📊 Все статусы"),
            ],
            [
                KeyboardButton(text="🔙 Назад к задачам"),
            ],
        ],
        resize_keyboard=True,
    )


def get_grouping_combined_keyboard():
    """Клавиатура для комбинированной группировки"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎯 Приоритет + Дата"),
                KeyboardButton(text="🏷️ Тег + Приоритет"),
            ],
            [
                KeyboardButton(text="📅 Дата + Статус"),
                KeyboardButton(text="🏷️ Тег + Статус"),
            ],
            [
                KeyboardButton(text="🔄 Тройная группировка"),
                KeyboardButton(text="🔙 Назад к задачам"),
            ],
        ],
        resize_keyboard=True,
    )


def get_navigation_keyboard():
    """Универсальная клавиатура навигации"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="❌ Отмена")],
            [KeyboardButton(text="🔙 Назад в меню")],
        ],
        resize_keyboard=True,
    )


def get_back_keyboard():
    """Только кнопка назад"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )


def get_cancel_keyboard():
    """Только кнопка отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def get_confirm_keyboard():
    """Подтверждение действий"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Подтвердить"), KeyboardButton(text="❌ Отменить")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )


def get_back_moods_keyboard():
    """Только кнопка назад"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад к настроениям")],
        ],
        resize_keyboard=True,
    )
