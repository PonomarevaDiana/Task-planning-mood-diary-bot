from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from datetime import datetime, timedelta
from collections import Counter
import statistics
import aiosqlite
from handlers.common import handle_navigation
from aiogram.filters import Command, StateFilter


from keyboards import (
    get_analytics_keyboard,
    get_period_keyboard,
    get_back_to_analytics_keyboard,
    get_cancel_keyboard,
    get_tasks_keyboard,
    get_confirm_keyboard,
)


class CleanupStates(StatesGroup):
    waiting_for_days = State()
    waiting_for_confirmation = State()


router = Router()

MOOD_EMOJIS = {
    "отлично": "🟢",
    "хорошо": "🟡",
    "нормально": "🟠",
    "плохо": "🔴",
    "ужасно": "💔",
}

PRIORITY_EMOJIS = {"high": "🔴", "medium": "🟡", "low": "🟢"}

VISUAL_ELEMENTS = {
    "header": "✨",
    "divider": "▬▬▬▬▬▬▬▬▬▬▬▬▬",
    "sub_divider": "────────────",
    "bullet": "•",
    "star": "⭐",
    "fire": "🔥",
    "rocket": "🚀",
    "trophy": "🏆",
    "medal": "🎖️",
    "chart": "📈",
    "target": "🎯",
    "lightning": "⚡",
    "heart": "💖",
    "mind": "💭",
    "clock": "⏰",
    "calendar": "📅",
    "check": "✅",
    "warning": "⚠️",
    "idea": "💡",
    "growth": "📊",
    "balance": "⚖️",
    "energy": "🔋",
    "link": "🔗",
    "hash": "#️⃣",
    "label": "🏷️",
}

PROGRESS_BARS = {
    "excellent": ["🟢", "🟩", "💚"],
    "good": ["🟡", "🟨", "💛"],
    "average": ["🟠", "🟧", "🧡"],
    "poor": ["🔴", "🟥", "❤️"],
    "neutral": ["⚪", "⬜", "🔘"],
}


class AnalyticsStates(StatesGroup):
    waiting_for_period = State()
    waiting_for_analytics_type = State()
    waiting_for_custom_start = State()
    waiting_for_custom_end = State()


@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext):
    """Главное меню статистики с выбором периода"""
    await show_period_selection(message, state)


@router.message(Command("analytics"))
async def cmd_analytics(message: Message, state: FSMContext):
    """Альтернативная команда для аналитики"""
    await show_period_selection(message, state)


async def show_period_selection(message: Message, state: FSMContext):
    """Показывает выбор периода для статистики"""
    await state.set_state(AnalyticsStates.waiting_for_period)

    text = """
📊 Аналитика и статистика

Выберите период для анализа:
    """

    await message.answer(text, reply_markup=get_period_keyboard())


@router.message(
    AnalyticsStates.waiting_for_period,
    F.text.in_(
        [
            "📅 7 дней",
            "📅 14 дней",
            "📅 30 дней",
            "📅 90 дней",
            "📅 Произвольный период",
        ]
    ),
)
async def handle_period_selection(message: Message, state: FSMContext):
    """Обработчик выбора периода"""
    period_mapping = {
        "📅 7 дней": 7,
        "📅 14 дней": 14,
        "📅 30 дней": 30,
        "📅 90 дней": 90,
    }

    if message.text == "📅 Произвольный период":
        await handle_custom_period_start(message, state)
        return

    days = period_mapping[message.text]

    data = await state.get_data()
    analytics_type = data.get("analytics_type")

    if analytics_type:
        await show_selected_analytics(message, state, analytics_type, days)
    else:
        await state.update_data(days=days)
        await state.set_state(None)
        await show_analytics_menu(message, days)


async def handle_custom_period_start(message: Message, state: FSMContext):
    """Начинает процесс выбора произвольного периода"""
    await state.set_state(AnalyticsStates.waiting_for_custom_start)

    text = """
📅 <b>ВЫБОР ПРОИЗВОЛЬНОГО ПЕРИОДА</b>

Введите начальную дату периода в формате:
ГГГГ-ММ-ДД

Или используйте быстрые варианты:
"""
    await message.answer(text, reply_mup=get_analytics_keyboard(), parse_mode="HTML")


@router.message(AnalyticsStates.waiting_for_custom_start)
async def handle_custom_start_date(message: Message, state: FSMContext):
    """Обрабатывает начальную дату произвольного периода"""
    if await handle_navigation(message, state):
        return
    start_date = await parse_date_input(message.text)

    if not start_date:
        await message.answer(
            "❌ Неверный формат даты. Пожалуйста, введите дату в формате ГГГГ-ММ-ДД\n\n"
            "Пример: 2024-12-25",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(custom_start_date=start_date)
    await state.set_state(AnalyticsStates.waiting_for_custom_end)

    await message.answer(
        f"📅 Начальная дата: {start_date.strftime('%Y-%m-%d')}\n\n"
        "Теперь введите конечную дату периода в формате ГГГГ-ММ-ДД:",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AnalyticsStates.waiting_for_custom_end)
async def handle_custom_end_date(message: Message, state: FSMContext):
    """Обрабатывает конечную дату произвольного периода"""
    if await handle_navigation(message, state):
        return
    end_date = await parse_date_input(message.text)

    if not end_date:
        await message.answer(
            "❌ Неверный формат даты. Пожалуйста, введите дату в формате ГГГГ-ММ-ДД\n\n"
            "Пример: 2024-12-31",
            reply_markup=get_cancel_keyboard(),
        )
        return

    data = await state.get_data()
    start_date = data.get("custom_start_date")

    if end_date <= start_date:
        await message.answer(
            "❌ Конечная дата должна быть после начальной даты.\n\n"
            f"Начальная дата: {start_date.strftime('%Y-%m-%d')}\n"
            "Пожалуйста, введите корректную конечную дату:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    days = (end_date - start_date).days + 1

    if days > 365:
        await message.answer(
            "❌ Период не может превышать 365 дней.\n\n"
            "Пожалуйста, выберите меньший период:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    if days < 1:
        await message.answer(
            "❌ Период должен быть хотя бы 1 день.\n\n"
            "Пожалуйста, выберите корректный период:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    analytics_type = data.get("analytics_type")

    if analytics_type:
        await show_selected_analytics_custom(
            message, state, analytics_type, start_date, end_date, days
        )
    else:
        await state.update_data(days=days)
        await state.set_state(None)
        await show_analytics_menu_custom(message, start_date, end_date, days)


async def parse_date_input(date_str: str) -> datetime:
    """Парсит ввод даты от пользователя"""
    date_str = date_str.strip().lower()

    quick_dates = {
        "неделя": datetime.now() - timedelta(days=7),
        "месяц": datetime.now() - timedelta(days=30),
        "3 месяца": datetime.now() - timedelta(days=90),
        "сегодня": datetime.now(),
        "вчера": datetime.now() - timedelta(days=1),
    }

    if date_str in quick_dates:
        return quick_dates[date_str]

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass

    try:
        return datetime.strptime(date_str, "%y-%m-%d")
    except ValueError:
        pass

    return None


async def show_analytics_menu(message: Message, days: int):
    """Показывает меню аналитики для выбранного периода"""
    period_names = {7: "неделю", 14: "14 дней", 30: "месяц", 90: "90 дней"}
    period_name = period_names.get(days, f"{days} дней")

    text = f"""
📊 Аналитика за {period_name}

Выберите тип отчета:
    """

    await message.answer(text, reply_markup=get_analytics_keyboard())


async def show_analytics_menu_custom(
    message: Message, start_date: datetime, end_date: datetime, days: int
):
    """Показывает меню аналитики для произвольного периода"""
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    text = f"""
📊 Аналитика за произвольный период
{start_str} - {end_str} ({days} дней)

Выберите тип отчета:
"""

    await message.answer(text, reply_markup=get_analytics_keyboard())


@router.message(F.text == "📈 Общая статистика")
async def handle_general_stats(message: Message, state: FSMContext):
    """Общая статистика"""
    await show_period_selection_with_type(message, state, "overview")


@router.message(F.text == "🎯 Анализ по приоритетам")
async def handle_priority_stats(message: Message, state: FSMContext):
    """Анализ по приоритетам"""
    await show_period_selection_with_type(message, state, "priority")


@router.message(F.text == "📅 Динамика выполнения")
async def handle_dynamics_stats(message: Message, state: FSMContext):
    """Динамика выполнения"""
    await show_period_selection_with_type(message, state, "dynamics")


@router.message(F.text == "🏷️ Анализ по тегам")
async def handle_tags_stats(message: Message, state: FSMContext):
    """Анализ по тегам"""
    await show_period_selection_with_type(message, state, "tags")


@router.message(F.text == "⚡ Продуктивность")
async def handle_productivity_stats(message: Message, state: FSMContext):
    """Анализ продуктивности"""
    await show_period_selection_with_type(message, state, "productivity")


@router.message(F.text == "📋 Сводный отчет")
async def handle_summary_stats(message: Message, state: FSMContext):
    """Сводный отчет"""
    await show_period_selection_with_type(message, state, "summary")


@router.message(F.text == "😊 Анализ настроений")
async def handle_mood_stats(message: Message, state: FSMContext):
    """Анализ настроений"""
    await show_period_selection_with_type(message, state, "mood")


async def show_period_selection_with_type(
    message: Message, state: FSMContext, analytics_type: str
):
    """Показывает выбор периода для конкретного типа аналитики"""
    await state.update_data(analytics_type=analytics_type)
    await state.set_state(AnalyticsStates.waiting_for_period)

    text = f"""
📊 <b>ВЫБОР ПЕРИОДА АНАЛИТИКИ</b>

• 📅 7 дней - краткосрочная аналитика
• 📅 30 дней - среднесрочная аналитика  
• 📅 90 дней - долгосрочные тенденции
• 📅 Произвольный период - гибкие настройки
"""
    await message.answer(text, reply_markup=get_period_keyboard(), parse_mode="HTML")


async def show_selected_analytics(
    message: Message, state: FSMContext, analytics_type: str, days: int
):
    """Показывает выбранный тип аналитики"""
    user_id = message.from_user.id

    try:
        if analytics_type == "overview":
            await show_overview_analytics_universal(message, user_id, days=days)
        elif analytics_type == "priority":
            await show_priority_analytics_universal(message, user_id, days=days)
        elif analytics_type == "dynamics":
            await show_dynamics_analytics_universal(message, user_id, days=days)
        elif analytics_type == "tags":
            await show_tags_analytics_universal(message, user_id, days=days)
        elif analytics_type == "productivity":
            await show_productivity_analytics_universal(message, user_id, days=days)
        elif analytics_type == "summary":
            await show_summary_analytics_universal(message, user_id, days=days)
        elif analytics_type == "mood":
            await show_mood_analytics_universal(message, user_id, days=days)

        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении статистики: {str(e)}",
            reply_markup=get_back_to_analytics_keyboard(),
        )
        await state.clear()


async def show_selected_analytics_custom(
    message: Message,
    state: FSMContext,
    analytics_type: str,
    start_date: datetime,
    end_date: datetime,
    days: int,
):
    """Показывает выбранный тип аналитики для произвольного периода"""
    user_id = message.from_user.id

    try:
        if analytics_type == "overview":
            await show_overview_analytics_universal(
                message, user_id, start_date=start_date, end_date=end_date, days=days
            )
        elif analytics_type == "priority":
            await show_priority_analytics_universal(
                message, user_id, start_date=start_date, end_date=end_date, days=days
            )
        elif analytics_type == "dynamics":
            await show_dynamics_analytics_universal(
                message, user_id, start_date=start_date, end_date=end_date, days=days
            )
        elif analytics_type == "tags":
            await show_tags_analytics_universal(
                message, user_id, start_date=start_date, end_date=end_date, days=days
            )
        elif analytics_type == "productivity":
            await show_productivity_analytics_universal(
                message, user_id, start_date=start_date, end_date=end_date, days=days
            )
        elif analytics_type == "summary":
            await show_summary_analytics_universal(
                message, user_id, start_date=start_date, end_date=end_date, days=days
            )
        elif analytics_type == "mood":
            await show_mood_analytics_universal(
                message, user_id, start_date=start_date, end_date=end_date, days=days
            )

        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении статистики: {str(e)}",
            reply_markup=get_back_to_analytics_keyboard(),
        )
        await state.clear()


async def show_overview_analytics_universal(
    message: Message,
    user_id: int,
    days: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальная общая статистика"""
    if start_date and end_date:
        all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
        filtered_tasks = filter_tasks_by_date(all_tasks, start_date, end_date)
        all_moods = await db.get_mood_statistics(user_id, 365)
        filtered_moods = (
            filter_moods_by_date(all_moods, start_date, end_date) if all_moods else []
        )
        task_analysis = analyze_tasks_for_custom_period(filtered_tasks, days)
        mood_analysis = analyze_moods(filtered_moods, days) if filtered_moods else None
    else:
        task_stats = await db.get_task_statistics(user_id, days)
        mood_stats = await db.get_mood_statistics(user_id, days)
        all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
        task_analysis = (
            analyze_tasks(task_stats, all_tasks, days) if task_stats else None
        )
        mood_analysis = analyze_moods(mood_stats, days) if mood_stats else None

    text = format_overview_analytics_universal(
        task_analysis, mood_analysis, days, start_date, end_date
    )
    await message.answer(
        text, reply_markup=get_back_to_analytics_keyboard(), parse_mode="HTML"
    )


async def show_priority_analytics_universal(
    message: Message,
    user_id: int,
    days: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальный анализ по приоритетам"""
    if start_date and end_date:
        all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
        filtered_tasks = filter_tasks_by_date(all_tasks, start_date, end_date)
        task_stats = []
        if filtered_tasks:
            status_count = {}
            for task in filtered_tasks:
                if len(task) > 5:
                    status = task[5]
                    status_count[status] = status_count.get(status, 0) + 1
            for status, count in status_count.items():
                task_stats.append((status, count))
    else:
        task_stats = await db.get_task_statistics(user_id, days)
        all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
        filtered_tasks = all_tasks

    text = format_priority_analytics_universal(
        filtered_tasks, task_stats, days, start_date, end_date
    )
    await message.answer(
        text, reply_markup=get_back_to_analytics_keyboard(), parse_mode="HTML"
    )


async def show_dynamics_analytics_universal(
    message: Message,
    user_id: int,
    days: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальная динамика выполнения"""
    task_stats, all_tasks, actual_days = await get_dynamics_data(
        user_id, days=days, start_date=start_date, end_date=end_date
    )
    text = format_dynamics_analytics_universal(
        task_stats, all_tasks, actual_days, start_date, end_date
    )
    await message.answer(
        text, reply_markup=get_back_to_analytics_keyboard(), parse_mode="HTML"
    )


async def show_tags_analytics_universal(
    message: Message,
    user_id: int,
    days: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальный анализ по тегам"""
    try:

        if start_date and end_date:
            all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
            filtered_tasks = filter_tasks_by_date(all_tasks, start_date, end_date)
            actual_days = days
        else:
            tag_stats = await db.get_tasks_grouped_by_tags(user_id)
            all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            filtered_tasks = filter_tasks_by_date(all_tasks, start_date, end_date)
            actual_days = days

        tag_analysis = await analyze_tags_for_period_db(
            user_id, filtered_tasks, actual_days
        )

        text = format_tags_analytics_universal(
            tag_analysis, actual_days, start_date, end_date
        )
        await message.answer(
            text, reply_markup=get_back_to_analytics_keyboard(), parse_mode="HTML"
        )

    except Exception as e:
        print(f"❌ Ошибка в анализе тегов: {e}")
        import traceback

        traceback.print_exc()
        await message.answer(
            f"❌ Ошибка при анализе тегов: {str(e)}",
            reply_markup=get_back_to_analytics_keyboard(),
        )


async def analyze_tags_for_period_db(user_id: int, tasks: list, days: int) -> dict:
    """Анализирует теги для периода через запросы к БД"""
    if not tasks:
        return {
            "total_tasks_with_tags": 0,
            "unique_tags": 0,
            "total_tag_uses": 0,
            "tags_distribution": {},
            "most_used_tags": [],
            "completion_by_tags": {},
            "avg_tags_per_task": 0,
        }

    all_tags = await db.get_user_tags(user_id)

    tags_stats = {}
    tasks_with_tags = 0
    total_tag_uses = 0

    for task in tasks:
        task_id = task[0]
        task_status = task[5] if len(task) > 5 else "pending"

        task_tags = await db.get_task_tags(task_id)

        if task_tags:
            tasks_with_tags += 1
            total_tag_uses += len(task_tags)

            for tag in task_tags:
                tag_id, tag_name, tag_color = tag

                if tag_name not in tags_stats:
                    tags_stats[tag_name] = {
                        "total": 0,
                        "completed": 0,
                        "pending": 0,
                        "color": tag_color,
                    }

                tags_stats[tag_name]["total"] += 1
                if task_status == "completed":
                    tags_stats[tag_name]["completed"] += 1
                else:
                    tags_stats[tag_name]["pending"] += 1

    most_used_tags = sorted(
        [(tag, stats["total"]) for tag, stats in tags_stats.items()],
        key=lambda x: x[1],
        reverse=True,
    )

    return {
        "total_tasks_with_tags": tasks_with_tags,
        "unique_tags": len(tags_stats),
        "total_tag_uses": total_tag_uses,
        "tags_distribution": tags_stats,
        "most_used_tags": most_used_tags,
        "completion_by_tags": {
            tag: stats["completed"] for tag, stats in tags_stats.items()
        },
        "avg_tags_per_task": (
            total_tag_uses / tasks_with_tags if tasks_with_tags > 0 else 0
        ),
    }


async def show_productivity_analytics_universal(
    message: Message,
    user_id: int,
    days: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальный анализ продуктивности"""
    if start_date and end_date:
        all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
        filtered_tasks = filter_tasks_by_date(all_tasks, start_date, end_date)
        all_moods = await db.get_mood_statistics(user_id, 365)
        filtered_moods = (
            filter_moods_by_date(all_moods, start_date, end_date) if all_moods else []
        )
        task_stats = []
        if filtered_tasks:
            status_count = {}
            for task in filtered_tasks:
                if len(task) > 5:
                    status = task[5]
                    status_count[status] = status_count.get(status, 0) + 1
            for status, count in status_count.items():
                task_stats.append((status, count))
    else:
        task_stats = await db.get_task_statistics(user_id, days)
        mood_stats = await db.get_mood_statistics(user_id, days)
        filtered_moods = mood_stats

    analysis = analyze_productivity(task_stats, filtered_moods, days)
    text = format_productivity_analytics_universal(analysis, days, start_date, end_date)
    await message.answer(
        text, reply_markup=get_back_to_analytics_keyboard(), parse_mode="HTML"
    )


async def show_summary_analytics_universal(
    message: Message,
    user_id: int,
    days: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальный сводный отчет"""
    if start_date and end_date:
        all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
        filtered_tasks = filter_tasks_by_date(all_tasks, start_date, end_date)
        all_moods = await db.get_mood_statistics(user_id, 365)
        filtered_moods = (
            filter_moods_by_date(all_moods, start_date, end_date) if all_moods else []
        )
        task_stats = []
        if filtered_tasks:
            status_count = {}
            for task in filtered_tasks:
                if len(task) > 5:
                    status = task[5]
                    status_count[status] = status_count.get(status, 0) + 1
            for status, count in status_count.items():
                task_stats.append((status, count))
        task_analysis = (
            analyze_tasks(task_stats, filtered_tasks, days) if task_stats else None
        )
        mood_analysis = analyze_moods(filtered_moods, days) if filtered_moods else None
    else:
        task_stats = await db.get_task_statistics(user_id, days)
        mood_stats = await db.get_mood_statistics(user_id, days)
        all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
        task_analysis = (
            analyze_tasks(task_stats, all_tasks, days) if task_stats else None
        )
        mood_analysis = analyze_moods(mood_stats, days) if mood_stats else None

    text = format_summary_analytics_universal(
        task_analysis, mood_analysis, days, start_date, end_date
    )
    await message.answer(
        text, reply_markup=get_back_to_analytics_keyboard(), parse_mode="HTML"
    )


async def show_mood_analytics_universal(
    message: Message,
    user_id: int,
    days: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальный анализ настроений"""
    if start_date and end_date:
        all_moods = await db.get_mood_statistics(user_id, 365)
        filtered_moods = (
            filter_moods_by_date(all_moods, start_date, end_date) if all_moods else []
        )
        mood_analysis = analyze_moods(filtered_moods, days) if filtered_moods else None
    else:
        mood_stats = await db.get_mood_statistics(user_id, days)
        mood_analysis = analyze_moods(mood_stats, days) if mood_stats else None

    text = format_mood_analytics_universal(mood_analysis, days, start_date, end_date)
    await message.answer(
        text, reply_markup=get_back_to_analytics_keyboard(), parse_mode="HTML"
    )


async def show_storage_statistics(message: Message):
    """Статистика хранилища"""
    user_id = message.from_user.id

    all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
    mood_stats = await db.get_mood_statistics(user_id, 365)

    active_tasks = len([t for t in all_tasks if len(t) > 4 and t[4] == "pending"])
    completed_tasks = len([t for t in all_tasks if len(t) > 4 and t[4] == "completed"])
    total_mood_records = len(mood_stats) if mood_stats else 0

    text = f"""
📊 СТАТИСТИКА ХРАНИЛИЩА

💾 Ваши данные:

📝 Задачи:
• Всего задач: {len(all_tasks)}
• Активных: {active_tasks}
• Выполненных: {completed_tasks}

😊 Настроения:
• Всего записей: {total_mood_records}

📈 Рекомендации:
• Регулярно завершайте выполненные задачи
• Отслеживайте настроение для полной статистики
• Используйте теги для организации задач

💡 Совет: Все ваши данные хранятся безопасно и доступны в любое время.
"""
    await message.answer(text, reply_markup=get_back_to_analytics_keyboard())


def format_overview_analytics_universal(
    task_analysis,
    mood_analysis,
    days: int,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальная общая статистика"""
    period_header = create_period_header("universal", days, start_date, end_date)

    html = f"""
{VISUAL_ELEMENTS['header']} <b>ОБЗОР СТАТИСТИКИ</b> {VISUAL_ELEMENTS['header']}
{period_header}
{VISUAL_ELEMENTS['divider']}
"""

    if task_analysis:
        completion_quality = get_quality_level(task_analysis["completion_rate"])
        productivity_quality = get_quality_level(task_analysis["productivity"] * 10)

        html += f"""
{VISUAL_ELEMENTS['target']} <b>ЗАДАЧИ И ПРОДУКТИВНОСТЬ</b>

{VISUAL_ELEMENTS['bullet']} <b>Всего задач:</b> <code>{task_analysis['total']}</code>
{VISUAL_ELEMENTS['check']} <b>Выполнено:</b> <code>{task_analysis['completed']}</code> ({task_analysis['completion_rate']}%)
{create_fancy_progress_bar(task_analysis['completion_rate'], completion_quality)}

{VISUAL_ELEMENTS['clock']} <b>В работе:</b> <code>{task_analysis['pending']}</code>
"""

        if task_analysis["overdue"] > 0:
            html += f"{VISUAL_ELEMENTS['warning']} <b>Просрочено:</b> <code>{task_analysis['overdue']}</code>\n"

        if days > 1:
            html += f"{VISUAL_ELEMENTS['growth']} <b>В день:</b> <code>{task_analysis['daily_avg']}</code> задач\n"

        html += f"""
{VISUAL_ELEMENTS['lightning']} <b>Продуктивность:</b> <code>{task_analysis['productivity']}/10</code>
{create_fancy_progress_bar(task_analysis['productivity'] * 10, productivity_quality)}
"""
    else:
        html += (
            f"{VISUAL_ELEMENTS['warning']} <i>Нет данных о задачах за этот период</i>\n"
        )

    html += f"\n{VISUAL_ELEMENTS['sub_divider']}\n"

    if mood_analysis:
        mood_quality = get_quality_level(mood_analysis["avg_score"] * 20)

        html += f"""
{VISUAL_ELEMENTS['heart']} <b>ЭМОЦИОНАЛЬНОЕ СОСТОЯНИЕ</b>

{VISUAL_ELEMENTS['bullet']} <b>Всего записей:</b> <code>{mood_analysis['total']}</code>
"""

        if days >= 7:
            html += f"{VISUAL_ELEMENTS['chart']} <b>В неделю:</b> <code>{mood_analysis['frequency']}</code> записей\n"

        html += f"""
{VISUAL_ELEMENTS['star']} <b>Средняя оценка:</b> <code>{mood_analysis['avg_score']}/5</code>
{create_fancy_progress_bar(mood_analysis['avg_score'] * 20, mood_quality)}

{VISUAL_ELEMENTS['balance']} <b>Стабильность:</b> {get_stability_emoji(mood_analysis['stability'])} {mood_analysis['stability']}
"""

        if mood_analysis["distribution"]:
            html += f"\n{VISUAL_ELEMENTS['mind']} <b>РАСПРЕДЕЛЕНИЕ НАСТРОЕНИЙ</b>\n"
            html += create_mood_distribution_table(
                mood_analysis["distribution"], mood_analysis["total"]
            )
    else:
        html += f"{VISUAL_ELEMENTS['idea']} <i>Начните отслеживать настроение для полной статистики</i>\n"

    return html


def format_priority_analytics_universal(
    all_tasks,
    task_stats,
    days: int,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальный анализ по приоритетам"""
    period_header = create_period_header("universal", days, start_date, end_date)

    if not all_tasks:
        return f"""
{VISUAL_ELEMENTS['header']} <b>АНАЛИЗ ПО ПРИОРИТЕТАМ</b> {VISUAL_ELEMENTS['header']}
{period_header}
{VISUAL_ELEMENTS['divider']}

{VISUAL_ELEMENTS['warning']} <i>Нет задач за этот период</i>
"""

    priority_stats = {}
    for task in all_tasks:
        if len(task) > 4:
            priority = task[4] or "medium"
            status = task[5] if len(task) > 5 else "pending"
            if priority not in priority_stats:
                priority_stats[priority] = {"total": 0, "completed": 0, "pending": 0}
            priority_stats[priority]["total"] += 1
            if status == "completed":
                priority_stats[priority]["completed"] += 1
            else:
                priority_stats[priority]["pending"] += 1

    html = f"""
{VISUAL_ELEMENTS['header']} <b>АНАЛИЗ ПО ПРИОРИТЕТАМ</b> {VISUAL_ELEMENTS['header']}
{period_header}
{VISUAL_ELEMENTS['divider']}
"""

    if priority_stats:
        html += f"{VISUAL_ELEMENTS['target']} <b>Распределение по приоритетам</b>\n\n"

        for priority in ["high", "medium", "low"]:
            if priority in priority_stats:
                stats = priority_stats[priority]
                emoji = PRIORITY_EMOJIS.get(priority, "⚪")
                completion_rate = (
                    (stats["completed"] / stats["total"] * 100)
                    if stats["total"] > 0
                    else 0
                )
                quality = get_quality_level(completion_rate)

                priority_name = {
                    "high": "Высокий",
                    "medium": "Средний",
                    "low": "Низкий",
                }[priority]

                html += f"""
{emoji} <b>{priority_name}</b>
{VISUAL_ELEMENTS['bullet']} Всего: <code>{stats['total']}</code>
{VISUAL_ELEMENTS['check']} Выполнено: <code>{stats['completed']}</code> ({completion_rate:.1f}%)
{create_fancy_progress_bar(completion_rate, quality)}
{VISUAL_ELEMENTS['clock']} В работе: <code>{stats['pending']}</code>
{VISUAL_ELEMENTS['sub_divider']}
"""

        total_tasks = len(all_tasks)
        completed_tasks = len(
            [t for t in all_tasks if len(t) > 5 and t[5] == "completed"]
        )
        completion_rate = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )
        quality = get_quality_level(completion_rate)

        html += f"""
{VISUAL_ELEMENTS['chart']} <b>Общая статистика</b>

{VISUAL_ELEMENTS['bullet']} <b>Всего задач:</b> <code>{total_tasks}</code>
{VISUAL_ELEMENTS['check']} <b>Выполнено:</b> <code>{completed_tasks}</code> ({completion_rate:.1f}%)
{create_fancy_progress_bar(completion_rate, quality)}
"""
    else:
        html += f"{VISUAL_ELEMENTS['warning']} <i>Нет задач с приоритетами за этот период</i>"

    return html


def format_dynamics_analytics_universal(
    task_stats,
    all_tasks,
    days: int,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальная динамика выполнения"""
    period_header = create_period_header("universal", days, start_date, end_date)

    html = f"""
{VISUAL_ELEMENTS['header']} <b>ДИНАМИКА ВЫПОЛНЕНИЯ</b> {VISUAL_ELEMENTS['header']}
{period_header}
{VISUAL_ELEMENTS['divider']}
"""

    if task_stats and all_tasks:
        status_data = {status: count for status, count in task_stats}
        total = sum(status_data.values())
        completed = status_data.get("completed", 0)
        pending = status_data.get("pending", 0)
        completion_rate = (completed / total * 100) if total > 0 else 0
        quality = get_quality_level(completion_rate)

        html += f"""
{VISUAL_ELEMENTS['growth']} <b>ОСНОВНЫЕ ПОКАЗАТЕЛИ</b>

{VISUAL_ELEMENTS['bullet']} <b>Всего задач:</b> <code>{total}</code>
{VISUAL_ELEMENTS['check']} <b>Выполнено:</b> <code>{completed}</code>
{VISUAL_ELEMENTS['clock']} <b>В работе:</b> <code>{pending}</code>

{VISUAL_ELEMENTS['chart']} <b>ПРОГРЕСС ВЫПОЛНЕНИЯ</b>
{create_fancy_progress_bar(completion_rate, quality, show_percentage=True)}
"""

        html += f"\n{VISUAL_ELEMENTS['medal']} <b>ОЦЕНКА РЕЗУЛЬТАТОВ</b>\n"
        if completion_rate >= 80:
            html += f"{VISUAL_ELEMENTS['trophy']} <b>Отличные результаты!</b>\n<i>Вы эффективно справляетесь с задачами</i>"
        elif completion_rate >= 60:
            html += f"{VISUAL_ELEMENTS['fire']} <b>Хорошая динамика!</b>\n<i>Продолжайте в том же духе</i>"
        elif completion_rate >= 40:
            html += f"{VISUAL_ELEMENTS['target']} <b>Есть над чем работать</b>\n<i>Попробуйте планировать задачи лучше</i>"
        else:
            html += f"{VISUAL_ELEMENTS['rocket']} <b>Время для изменений</b>\n<i>Рассмотрите новые подходы к планированию</i>"
    else:
        html += f"{VISUAL_ELEMENTS['warning']} <i>Нет данных для анализа динамики</i>"

    return html


def format_tags_analytics_universal(
    tag_analysis: dict,
    days: int,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальный формат анализа по тегам"""
    period_header = create_period_header("universal", days, start_date, end_date)

    html = f"""
{VISUAL_ELEMENTS['header']} <b>АНАЛИТИКА ПО ТЕГАМ</b> {VISUAL_ELEMENTS['header']}
{period_header}
{VISUAL_ELEMENTS['divider']}
"""

    if not tag_analysis or tag_analysis["unique_tags"] == 0:
        html += f"""
{VISUAL_ELEMENTS['warning']} <i>Нет задач с тегами за этот период</i>

{VISUAL_ELEMENTS['idea']} <i>Добавляйте теги к задачам для лучшей организации и аналитики.</i>
"""
        return html

    html += f"""
{VISUAL_ELEMENTS['chart']} <b>ОБЩАЯ СТАТИСТИКА</b>

{VISUAL_ELEMENTS['bullet']} <b>Задач с тегами:</b> <code>{tag_analysis['total_tasks_with_tags']}</code>
{VISUAL_ELEMENTS['target']} <b>Уникальных тегов:</b> <code>{tag_analysis['unique_tags']}</code>
{VISUAL_ELEMENTS['growth']} <b>Всего использований:</b> <code>{tag_analysis['total_tag_uses']}</code>
{VISUAL_ELEMENTS['link']} <b>В среднем на задачу:</b> <code>{tag_analysis['avg_tags_per_task']:.1f}</code> тегов
"""

    if tag_analysis["most_used_tags"]:
        html += f"\n{VISUAL_ELEMENTS['fire']} <b>ПОПУЛЯРНЫЕ ТЕГИ</b>\n\n"

        for i, (tag, count) in enumerate(tag_analysis["most_used_tags"][:10], 1):
            stats = tag_analysis["tags_distribution"][tag]
            completion_rate = (
                (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            quality = get_quality_level(completion_rate)

            rank_emoji = get_rank_emoji(i)

            html += f"""
{rank_emoji} <b>#{tag}</b>
{VISUAL_ELEMENTS['bullet']} Использован: <code>{count}</code> раз
{VISUAL_ELEMENTS['check']} Выполнено: <code>{stats['completed']}</code> ({completion_rate:.1f}%)
{create_fancy_progress_bar(completion_rate, quality)}
{VISUAL_ELEMENTS['sub_divider']}
"""

    html += f"\n{VISUAL_ELEMENTS['idea']} <b>РЕКОМЕНДАЦИИ</b>\n"

    if tag_analysis["avg_tags_per_task"] < 1.5:
        html += "• Добавляйте несколько тегов к одной задаче\n"

    if tag_analysis["unique_tags"] < 5:
        html += "• Используйте больше разнообразных тегов\n"
    else:
        html += "• Продолжайте использовать теги для организации задач\n"

    return html


def get_rank_emoji(rank: int) -> str:
    """Возвращает эмодзи для ранга"""
    rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣"}
    return rank_emojis.get(rank, "🔹")


def format_productivity_analytics_universal(
    analysis, days: int, start_date: datetime = None, end_date: datetime = None
):
    """Универсальный анализ продуктивности"""
    period_header = create_period_header("universal", days, start_date, end_date)

    html = f"""
{VISUAL_ELEMENTS['header']} <b>АНАЛИТИКА ПРОДУКТИВНОСТИ</b> {VISUAL_ELEMENTS['header']}
{period_header}
{VISUAL_ELEMENTS['divider']}
"""

    if analysis["task_analysis"]:
        task = analysis["task_analysis"]
        html += f"""
{VISUAL_ELEMENTS['target']} <b>ЗАДАЧИ:</b>

{VISUAL_ELEMENTS['bullet']} <b>Создано:</b> <code>{task['total']}</code> задач
{VISUAL_ELEMENTS['check']} <b>Выполнено:</b> <code>{task['completed']}</code> ({task['completion_rate']}%)
{VISUAL_ELEMENTS['clock']} <b>В работе:</b> <code>{task['pending']}</code> задач
"""

        if task["overdue"] > 0:
            html += f"{VISUAL_ELEMENTS['warning']} <b>Просрочено:</b> <code>{task['overdue']}</code> задач\n"

        html += f"{VISUAL_ELEMENTS['lightning']} <b>Оценка продуктивности:</b> <code>{task['productivity']}/10</code>\n"

    if analysis["mood_analysis"]:
        mood = analysis["mood_analysis"]
        html += f"""
{VISUAL_ELEMENTS['heart']} <b>НАСТРОЕНИЕ:</b>

{VISUAL_ELEMENTS['bullet']} <b>Записей:</b> <code>{mood['total']}</code>
{VISUAL_ELEMENTS['star']} <b>Средняя оценка:</b> <code>{mood['avg_score']}/5</code>
{VISUAL_ELEMENTS['balance']} <b>Стабильность:</b> {mood['stability']}
"""

    html += f"\n{VISUAL_ELEMENTS['idea']} <b>РЕКОМЕНДАЦИИ:</b>\n"
    for insight in analysis["insights"]:
        html += f"• {insight}\n"

    return html


def format_summary_analytics_universal(
    task_analysis,
    mood_analysis,
    days: int,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Универсальный сводный отчет"""
    period_header = create_period_header("universal", days, start_date, end_date)

    html = f"""
{VISUAL_ELEMENTS['header']} <b>СВОДНЫЙ ОТЧЕТ</b> {VISUAL_ELEMENTS['header']}
{period_header}
{VISUAL_ELEMENTS['divider']}
"""

    overall_score = 0
    factors = []

    if task_analysis:
        task_score = min(task_analysis["productivity"] * 10, 100)
        overall_score += task_score * 0.7
        factors.append(f"Задачи: {task_score:.1f}%")

    if mood_analysis:
        mood_score = mood_analysis["avg_score"] * 20
        overall_score += mood_score * 0.3
        factors.append(f"Настроение: {mood_score:.1f}%")

    if overall_score > 0:
        quality = get_quality_level(overall_score)
        html += f"""
{VISUAL_ELEMENTS['trophy']} <b>ОБЩАЯ ОЦЕНКА: {overall_score:.1f}%</b>
{create_fancy_progress_bar(overall_score, quality, show_percentage=True)}

{VISUAL_ELEMENTS['chart']} <b>Составляющие:</b>
"""
        for factor in factors:
            html += f"{VISUAL_ELEMENTS['bullet']} {factor}\n"

        html += f"\n{VISUAL_ELEMENTS['sub_divider']}\n"

    if task_analysis:
        completion_quality = get_quality_level(task_analysis["completion_rate"])
        productivity_quality = get_quality_level(task_analysis["productivity"] * 10)

        html += f"""
{VISUAL_ELEMENTS['target']} <b>ЭФФЕКТИВНОСТЬ ЗАДАЧ</b>

{VISUAL_ELEMENTS['check']} <b>Выполнение:</b> {task_analysis['completion_rate']}%
{create_fancy_progress_bar(task_analysis['completion_rate'], completion_quality)}

{VISUAL_ELEMENTS['lightning']} <b>Продуктивность:</b> {task_analysis['productivity']}/10
{create_fancy_progress_bar(task_analysis['productivity'] * 10, productivity_quality)}
"""

        if task_analysis["overdue"] > 0:
            html += f"{VISUAL_ELEMENTS['warning']} <b>Внимание:</b> {task_analysis['overdue']} просроченных задач\n"

    if mood_analysis:
        mood_quality = get_quality_level(mood_analysis["avg_score"] * 20)
        html += f"""
{VISUAL_ELEMENTS['heart']} <b>СОСТОЯНИЕ НАСТРОЕНИЯ</b>

{VISUAL_ELEMENTS['star']} <b>Средняя оценка:</b> {mood_analysis['avg_score']}/5
{create_fancy_progress_bar(mood_analysis['avg_score'] * 20, mood_quality)}

{VISUAL_ELEMENTS['balance']} <b>Стабильность:</b> {get_stability_emoji(mood_analysis['stability'])} {mood_analysis['stability']}
"""

        if mood_analysis["most_common"]:
            common_emoji = MOOD_EMOJIS.get(mood_analysis["most_common"], "⚪")
            html += f"{VISUAL_ELEMENTS['target']} <b>Преобладает:</b> {common_emoji} {mood_analysis['most_common']}\n"

    html += f"\n{VISUAL_ELEMENTS['medal']} <b>ИТОГОВАЯ ОЦЕНКА</b>\n"
    if overall_score >= 80:
        html += f"{VISUAL_ELEMENTS['trophy']} <b>ОТЛИЧНЫЕ РЕЗУЛЬТАТЫ!</b>\n<i>Вы прекрасно справляетесь!</i>"
    elif overall_score >= 60:
        html += f"{VISUAL_ELEMENTS['fire']} <b>ХОРОШАЯ РАБОТА!</b>\n<i>Продолжайте в том же духе!</i>"
    elif overall_score >= 40:
        html += f"{VISUAL_ELEMENTS['target']} <b>НЕПЛОХО!</b>\n<i>Есть возможности для улучшения.</i>"
    else:
        html += f"{VISUAL_ELEMENTS['rocket']} <b>НАЧАЛО ПУТИ!</b>\n<i>Каждый день - новая возможность!</i>"

    return html


def format_mood_analytics_universal(
    analysis, days: int, start_date: datetime = None, end_date: datetime = None
):
    """Универсальный анализ настроений"""
    period_header = create_period_header("universal", days, start_date, end_date)

    if not analysis:
        return f"""
{VISUAL_ELEMENTS['header']} <b>АНАЛИЗ НАСТРОЕНИЙ</b> {VISUAL_ELEMENTS['header']}
{period_header}
{VISUAL_ELEMENTS['divider']}

{VISUAL_ELEMENTS['warning']} <i>У вас пока нет записей о настроении за этот период</i>

{VISUAL_ELEMENTS['idea']} <i>Начните отслеживать настроение регулярно для получения полезной статистики</i>
"""

    html = f"""
{VISUAL_ELEMENTS['header']} <b>АНАЛИЗ НАСТРОЕНИЙ</b> {VISUAL_ELEMENTS['header']}
{period_header}
{VISUAL_ELEMENTS['divider']}

{VISUAL_ELEMENTS['heart']} <b>ОСНОВНЫЕ МЕТРИКИ</b>

{VISUAL_ELEMENTS['bullet']} <b>Всего записей:</b> <code>{analysis['total']}</code>
"""

    if days >= 7:
        html += f"{VISUAL_ELEMENTS['chart']} <b>В неделю:</b> <code>{analysis['frequency']}</code> записей\n"

    mood_quality = get_quality_level(analysis["avg_score"] * 20)
    html += f"""
{VISUAL_ELEMENTS['star']} <b>Средняя оценка:</b> <code>{analysis['avg_score']}/5</code>
{create_fancy_progress_bar(analysis['avg_score'] * 20, mood_quality, show_percentage=True)}

{VISUAL_ELEMENTS['balance']} <b>Стабильность:</b> {get_stability_emoji(analysis['stability'])} {analysis['stability']}
"""

    if analysis["distribution"]:
        html += f"\n{VISUAL_ELEMENTS['mind']} <b>РАСПРЕДЕЛЕНИЕ НАСТРОЕНИЙ</b>\n"
        html += create_mood_distribution_table(
            analysis["distribution"], analysis["total"]
        )

    if analysis["most_common"]:
        common_emoji = MOOD_EMOJIS.get(analysis["most_common"], "⚪")
        html += f"\n{VISUAL_ELEMENTS['target']} <b>Преобладающее настроение:</b> {common_emoji} {analysis['most_common']}"

    return html


def create_period_header(
    period_type: str,
    days: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
) -> str:
    """Создает заголовок периода"""
    if start_date and end_date:
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        return f"{VISUAL_ELEMENTS['calendar']} <i>Период: {start_str} - {end_str} ({days} дней)</i>"
    else:
        period_names = {7: "неделю", 14: "14 дней", 30: "месяц", 90: "90 дней"}
        period_name = period_names.get(days, f"{days} дней")
        return f"{VISUAL_ELEMENTS['calendar']} <i>Период: {period_name}</i>"


def get_quality_level(percentage: float) -> str:
    """Определяет уровень качества"""
    if percentage >= 80:
        return "excellent"
    elif percentage >= 60:
        return "good"
    elif percentage >= 40:
        return "average"
    else:
        return "poor"


def get_stability_emoji(stability: str) -> str:
    """Возвращает эмодзи для стабильности"""
    stability_emojis = {
        "высокая": "🟢",
        "средняя": "🟡",
        "низкая": "🔴",
        "недостаточно данных": "⚪",
    }
    return stability_emojis.get(stability, "⚪")


def create_fancy_progress_bar(
    percentage: float, quality: str, width: int = 12, show_percentage: bool = False
) -> str:
    """Создает красивый прогресс-бар"""
    filled = max(1, int((percentage / 100) * width))
    empty = width - filled

    bars = PROGRESS_BARS.get(quality, PROGRESS_BARS["neutral"])
    filled_char = bars[1]
    empty_char = "⬜"

    bar = filled_char * filled + empty_char * empty

    if show_percentage:
        return f"<code>{bar}</code> <b>{percentage:.1f}%</b>"
    else:
        return f"<code>{bar}</code>"


def create_mood_distribution_table(distribution: dict, total: int) -> str:
    """Создает таблицу распределения настроений"""
    table = ""
    for mood in ["отлично", "хорошо", "нормально", "плохо", "ужасно"]:
        if mood in distribution:
            count = distribution[mood]
            percentage = (count / total) * 100
            emoji = MOOD_EMOJIS.get(mood, "⚪")
            quality = get_quality_level(percentage)
            bar = create_fancy_progress_bar(percentage, quality, 8)
            table += f"{emoji} {bar} <code>{percentage:5.1f}%</code> ({count})\n"
    return table


def mood_to_score(mood: str) -> int:
    """Конвертирует настроение в числовую оценку"""
    scores = {"отлично": 5, "хорошо": 4, "нормально": 3, "плохо": 2, "ужасно": 1}
    return scores.get(mood.lower(), 3)


def count_overdue_tasks(tasks: list) -> int:
    """Считает просроченные задачи"""
    if not tasks:
        return 0

    overdue = 0
    now = datetime.now()

    for task in tasks:
        if len(task) > 3 and task[3] and task[5] == "pending":
            try:
                due_date_str = str(task[3]).strip()
                if "." in due_date_str:
                    due_date_str = due_date_str.split(".")[0]
                due_date_str = due_date_str.replace("Z", "+00:00")
                due_date = datetime.fromisoformat(due_date_str)
                if due_date < now:
                    overdue += 1
            except (ValueError, TypeError):
                continue

    return overdue


def calculate_productivity_score(
    completion_rate: float, pending_tasks: int, overdue_tasks: int
) -> float:
    """Рассчитывает оценку продуктивности"""
    completion_score = (completion_rate / 100) * 6

    pending_bonus = 0
    if pending_tasks == 0:
        pending_bonus = 2.0
    elif pending_tasks <= 3:
        pending_bonus = 1.0
    elif pending_tasks <= 5:
        pending_bonus = 0.5

    overdue_penalty = min(overdue_tasks * 0.3, 2.0)

    activity_bonus = 1.0 if (completion_rate > 0 or pending_tasks > 0) else 0

    productivity = completion_score + pending_bonus - overdue_penalty + activity_bonus

    return max(0, min(10, round(productivity, 1)))


def filter_moods_by_date(
    mood_stats: list, start_date: datetime, end_date: datetime
) -> list:
    """Фильтрует настроения по дате"""
    filtered = []
    for mood in mood_stats:
        if len(mood) > 1 and mood[1]:
            try:
                mood_date = datetime.strptime(mood[1], "%Y-%m-%d").date()
                if start_date.date() <= mood_date <= end_date.date():
                    filtered.append(mood)
            except (ValueError, TypeError):
                continue
    return filtered


def filter_tasks_by_date(tasks: list, start_date: datetime, end_date: datetime) -> list:
    """Фильтрует задачи по дате создания"""
    filtered = []
    for task in tasks:
        if len(task) < 7:
            continue

        task_id = task[0]
        created_at = task[6]

        if not created_at:
            continue

        try:
            created_str = str(created_at).strip()
            if "." in created_str:
                created_str = created_str.split(".")[0]
            created_str = created_str.replace("Z", "+00:00")
            task_date = datetime.fromisoformat(created_str)
            task_date_date = task_date.date()
            start_date_date = start_date.date()
            end_date_date = end_date.date()

            if start_date_date <= task_date_date <= end_date_date:
                filtered.append(task)
        except (ValueError, TypeError):
            continue

    return filtered


async def get_dynamics_data(
    user_id: int,
    days: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    """Получает данные для анализа динамики"""
    if start_date and end_date:
        all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
        filtered_tasks = filter_tasks_by_date(all_tasks, start_date, end_date)
        days = (end_date - start_date).days + 1
    else:
        all_tasks = await db.get_user_tasks(user_id, include_deleted=False)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        filtered_tasks = filter_tasks_by_date(all_tasks, start_date, end_date)

    task_stats = []
    if filtered_tasks:
        status_count = {}
        for task in filtered_tasks:
            if len(task) > 5:
                status = task[5]
                status_count[status] = status_count.get(status, 0) + 1

        for status, count in status_count.items():
            task_stats.append((status, count))

    return task_stats, filtered_tasks, days


def analyze_tasks_for_custom_period(tasks: list, days: int) -> dict:
    """Анализирует задачи для произвольного периода"""
    if not tasks:
        return None

    total = len(tasks)
    completed = 0
    pending = 0

    for task in tasks:
        if len(task) > 5:
            status = task[5]
            if status == "completed":
                completed += 1
            elif status == "pending":
                pending += 1

    completion_rate = (completed / total * 100) if total > 0 else 0
    overdue = count_overdue_tasks(tasks)

    priorities = {}
    for task in tasks:
        if len(task) > 4:
            priority = task[4] if task[4] else "medium"
            priorities[priority] = priorities.get(priority, 0) + 1

    productivity = calculate_productivity_score(completion_rate, pending, overdue)
    daily_avg = round(total / days, 1) if days > 0 and total > 0 else 0

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "completion_rate": round(completion_rate, 1),
        "overdue": overdue,
        "priorities": priorities,
        "productivity": round(productivity, 1),
        "daily_avg": daily_avg,
    }


def analyze_tasks(task_stats, all_tasks, days):
    """Анализирует статистику задач"""
    if not task_stats:
        return None

    status_data = {status: count for status, count in task_stats}
    total = sum(status_data.values())
    completed = status_data.get("completed", 0)
    pending = status_data.get("pending", 0)

    completion_rate = (completed / total * 100) if total > 0 else 0
    overdue = count_overdue_tasks(all_tasks)

    priorities = {}
    for task in all_tasks:
        if len(task) > 3 and task[4] == "pending":
            priority = task[3] if task[3] else "medium"
            priorities[priority] = priorities.get(priority, 0) + 1

    productivity = calculate_productivity_score(completion_rate, pending, overdue)
    daily_avg = round(total / days, 1) if days > 0 and total > 0 else 0

    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "completion_rate": round(completion_rate, 1),
        "overdue": overdue,
        "priorities": priorities,
        "productivity": round(productivity, 1),
        "daily_avg": daily_avg,
    }


def analyze_moods(mood_stats, days):
    """Анализирует статистику настроений"""
    if not mood_stats:
        return None

    moods = [mood[0] for mood in mood_stats]
    distribution = dict(Counter(moods))
    total = len(moods)

    most_common = (
        max(distribution.items(), key=lambda x: x[1])[0] if distribution else None
    )

    stability = "недостаточно данных"
    if len(moods) >= 3:
        changes = sum(1 for i in range(1, len(moods)) if moods[i] != moods[i - 1])
        change_rate = changes / (len(moods) - 1)
        if change_rate < 0.3:
            stability = "высокая"
        elif change_rate < 0.6:
            stability = "средняя"
        else:
            stability = "низкая"

    scores = [mood_to_score(mood) for mood in moods]
    avg_score = statistics.mean(scores) if scores else 0

    weeks = days / 7
    frequency = round(total / weeks, 1) if weeks > 0 else total

    return {
        "total": total,
        "distribution": distribution,
        "most_common": most_common,
        "stability": stability,
        "avg_score": round(avg_score, 1),
        "frequency": frequency,
    }


def analyze_productivity(task_stats, mood_stats, days):
    """Анализирует продуктивность"""
    task_analysis = analyze_tasks(task_stats, [], days) if task_stats else None
    mood_analysis = analyze_moods(mood_stats, days) if mood_stats else None

    insights = []

    if task_analysis:
        if task_analysis["completion_rate"] > 80:
            insights.append("🎯 Отличный уровень выполнения задач")
        elif task_analysis["completion_rate"] < 50:
            insights.append("💪 Есть возможность улучшить выполнение задач")

        if task_analysis["overdue"] > 3:
            insights.append(
                f"⏰ Обратите внимание на {task_analysis['overdue']} просроченных задач"
            )
        elif task_analysis["overdue"] > 0:
            insights.append(f"⏰ Есть {task_analysis['overdue']} просроченная задача")

    if mood_analysis:
        if mood_analysis["stability"] == "низкая":
            insights.append(
                "💭 Настроение нестабильно - это может влиять на продуктивность"
            )
        elif mood_analysis["stability"] == "высокая":
            insights.append("😊 Стабильное настроение способствует продуктивности")

    if not insights:
        if task_analysis and task_analysis["total"] > 0:
            insights.append("📈 Продолжайте в том же духе!")
        else:
            insights.append("🌟 Начните с создания первых задач!")

    return {
        "task_analysis": task_analysis,
        "mood_analysis": mood_analysis,
        "insights": insights,
    }


@router.message(F.text == "📊 Аналитика")
@router.message(Command("stats", "analytics"))
async def cmd_analytics(message: Message, state: FSMContext):
    """Переход в раздел аналитики"""
    await state.clear()
    await message.answer(
        "📊 РАЗДЕЛ АНАЛИТИКИ\n\n" "Выберите тип аналитики для просмотра статистики:",
        reply_markup=get_analytics_keyboard(),
    )


@router.message(F.text == "📊 Статистика хранилища")
async def handle_storage_analytics(message: Message):
    """Обработка кнопки статистики хранилища в разделе аналитики"""
    await cmd_storage_info(message)


async def get_storage_stats(user_id: int) -> str:
    """Получить статистику хранилища"""
    async with aiosqlite.connect(db.db_path) as conn:
        cursor = await conn.execute(
            "SELECT status, COUNT(*) FROM tasks WHERE user_id = ? AND is_deleted = 0 GROUP BY status",
            (user_id,),
        )
        task_stats = await cursor.fetchall()

        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'completed' AND completed_at <= ? AND user_id = ?",
            (month_ago, user_id),
        )
        old_completed = (await cursor.fetchone())[0]

        three_months_ago = (datetime.now() - timedelta(days=90)).date().isoformat()
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM moods WHERE date < ? AND user_id = ?",
            (three_months_ago, user_id),
        )
        old_moods = (await cursor.fetchone())[0]

    stats_text = "📊 <b>Текущая статистика хранилища</b>\n\n"

    for status, count in task_stats:
        icon = "✅" if status == "completed" else "📝"
        status_name = "выполненные" if status == "completed" else "активные"
        stats_text += f"{icon} {status_name}: {count}\n"

    stats_text += f"\n🗑️ <b>Готово к очистке:</b>\n"
    stats_text += f"• Выполненные задачи (>30 дней): {old_completed}\n"
    stats_text += f"• Записи настроения (>90 дней): {old_moods}\n"

    return stats_text


async def perform_manual_cleanup(user_id: int, days: int) -> dict:
    """Выполняет ручную очистку и возвращает статистику"""
    results = {}

    try:
        results["completed_tasks"] = await db.cleanup_old_completed_tasks(days)

        results["deleted_tasks"] = await db.cleanup_old_deleted_tasks(days)

        results["moods"] = await db.cleanup_old_moods(days * 3)

        results["reminders"] = await db.cleanup_old_reminders(7)

        return results

    except Exception as e:
        print(f"❌ Ошибка при ручной очистке: {e}")
        return {}


@router.message(F.text == "📊 Статистика хранилища")
@router.message(Command("storage_info"))
async def cmd_storage_info(message: Message):
    """Показать статистику хранилища"""
    try:
        stats = await get_storage_stats(message.from_user.id)

        settings_info = (
            "\n\n⚙️ <b>Настройки хранения:</b>\n"
            "✅ Активные задачи: бессрочно\n"
            "✅ Выполненные задачи: 30 дней\n"
            "🗑️ Удаленные задачи: 30 дней\n"
            "😊 Записи настроения: 90 дней\n"
            "🔔 Напоминания: 7 дней\n\n"
            "💡 Автоочистка каждый день в 3:00\n"
        )

        await message.answer(
            stats + settings_info, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении статистики: {e}",
            reply_markup=get_tasks_keyboard(),
        )


@router.message(Command("cleanup"))
async def cmd_cleanup(message: Message, state: FSMContext):
    """Начать процесс очистки старых данных"""
    try:
        stats = await get_storage_stats(message.from_user.id)

        cleanup_info = (
            "🧹 <b>Очистка старых данных</b>\n\n"
            f"{stats}\n\n"
            "Введите количество дней для очистки (по умолчанию 30):\n"
        )

        await message.answer(
            cleanup_info, parse_mode="HTML", reply_markup=get_cancel_keyboard()
        )
        await state.set_state(CleanupStates.waiting_for_days)

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении статистики: {e}",
            reply_markup=get_tasks_keyboard(),
        )


@router.message(StateFilter(CleanupStates.waiting_for_days))
async def process_cleanup_days(message: Message, state: FSMContext):
    """Обработка ввода количества дней для очистки"""
    if await handle_navigation(message, state):
        return

    try:
        days = int(message.text) if message.text.isdigit() else 30

        if days < 1:
            await message.answer(
                "❌ Количество дней должно быть больше 0! Попробуйте снова:"
            )
            return

        if days > 365:
            await message.answer(
                "❌ Слишком большой период! Максимум 365 дней. Попробуйте снова:"
            )
            return

        await state.update_data(cleanup_days=days)

        confirm_text = (
            f"🧹 <b>Подтверждение очистки</b>\n\n"
            f"📅 <b>Период очистки:</b> старше {days} дней\n\n"
            f"🗑️ <b>Будут удалены:</b>\n"
            f"• Выполненные задачи (> {days} дней)\n"
            f"• Удаленные задачи (> {days} дней)\n"
            f"• Записи настроения (> {days * 3} дней)\n"
            f"• Старые напоминания (> 7 дней)\n\n"
            f"⚠️ <b>Внимание:</b> Это действие нельзя отменить!\n\n"
            f"Подтверждаете очистку?"
        )

        await message.answer(
            confirm_text, parse_mode="HTML", reply_markup=get_confirm_keyboard()
        )
        await state.set_state(CleanupStates.waiting_for_confirmation)

    except ValueError:
        await message.answer("❌ Неверный формат! Введите число дней:")


@router.message(StateFilter(CleanupStates.waiting_for_confirmation))
async def process_cleanup_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения очистки"""
    if await handle_navigation(message, state):
        return

    answer = message.text.lower().strip()

    if answer in ["✅ подтвердить", "да", "yes", "y", "д"]:
        data = await state.get_data()
        days = data.get("cleanup_days", 30)

        try:
            wait_msg = await message.answer("🔄 Выполняется очистка...")

            results = await perform_manual_cleanup(message.from_user.id, days)

            total_deleted = sum(results.values())

            if total_deleted > 0:
                result_text = (
                    f"✅ <b>Очистка завершена успешно!</b>\n\n"
                    f"🗑️ <b>Удалено записей:</b> {total_deleted}\n"
                    f"• ✅ Выполненные задачи: {results.get('completed_tasks', 0)}\n"
                    f"• 🗑️ Удаленные задачи: {results.get('deleted_tasks', 0)}\n"
                    f"• 😊 Записи настроения: {results.get('moods', 0)}\n"
                    f"• 🔔 Старые напоминания: {results.get('reminders', 0)}\n\n"
                    f"📅 <b>Период:</b> старше {days} дней\n\n"
                    f"💾 <b>Освобождено место в хранилище</b>"
                )
            else:
                result_text = (
                    "✅ <b>Очистка завершена</b>\n\n"
                    "🗑️ Не найдено данных для очистки\n"
                    "Все данные актуальны и соответствуют настройкам хранения"
                )

            await wait_msg.delete()
            await message.answer(
                result_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
            )

        except Exception as e:
            await message.answer(
                f"❌ Ошибка при очистке: {str(e)}", reply_markup=get_tasks_keyboard()
            )

        await state.clear()

    elif answer in ["❌ отменить", "нет", "no", "n", "н"]:
        await message.answer("❌ Очистка отменена", reply_markup=get_tasks_keyboard())
        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, используйте кнопки для подтверждения:")


@router.message(Command("storage"))
async def cmd_storage(message: Message):
    """Информация о настройках хранения данных"""
    storage_info = (
        "📊 <b>Настройки хранения данных</b>\n\n"
        "🕒 <b>Периоды хранения:</b>\n"
        "✅ Активные задачи: бессрочно\n"
        "✅ Выполненные задачи: 30 дней\n"
        "🗑️ Удаленные задачи: 30 дней\n"
        "😊 Записи настроения: 90 дней\n"
        "🔔 Напоминания: 7 дней после отправки\n\n"
        "⚡ <b>Автоматическая очистка:</b>\n"
        "Каждый день в 3:00 утра\n\n"
        "🛠️ <b>Команды управления:</b>\n"
        "/storage_info - текущая статистика\n"
        "/cleanup - ручная очистка\n"
        "/storage - эта справка\n\n"
        "💡 <b>Совет:</b> Регулярно проверяйте статистику \n"
        "чтобы контролировать использование хранилища"
    )
    await message.answer(
        storage_info, parse_mode="HTML", reply_markup=get_tasks_keyboard()
    )


@router.message(F.text == "🧹 Очистка хранилища")
async def handle_cleanup_button(message: Message, state: FSMContext):
    """Обработка кнопки ручной очистки хранилища"""
    await cmd_cleanup(message, state)


@router.message(F.text == "🧹 Очистка")
async def handle_main_cleanup(message: Message, state: FSMContext):
    """Обработка кнопки очистки из главного меню"""
    await cmd_cleanup(message, state)
