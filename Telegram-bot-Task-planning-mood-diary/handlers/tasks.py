from aiogram import Router, F
import aiosqlite
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, time, timedelta
from pathlib import Path
import sys
from reminders import reminder_manager
from aiogram.types import Message
from handlers.common import handle_navigation

current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from database import db
from keyboards import (
    get_main_keyboard,
    get_tasks_keyboard,
    get_task_creation_keyboard,
    get_priority_keyboard,
    get_filter_keyboard,
    get_edit_keyboard,
    get_tags_keyboard,
    get_confirm_keyboard,
    get_back_keyboard,
    get_cancel_keyboard,
    get_notifications_keyboard,
    get_reminder_settings_keyboard,
    get_confirm_keyboard,
    get_cancel_keyboard,
    get_back_keyboard,
    get_quick_actions_keyboard,
    get_status_keyboard,
    get_filter_date,
    get_grouping_keyboard,
    get_grouping_period_keyboard,
    get_grouping_priority_keyboard,
    get_grouping_status_keyboard,
    get_grouping_combined_keyboard,
)

router = Router()


class TaskCreation(StatesGroup):
    waiting_for_content = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_priority = State()


class TaskEdit(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_edit_choice = State()
    waiting_for_new_content = State()
    waiting_for_new_date = State()
    waiting_for_new_time = State()
    waiting_for_new_priority = State()
    waiting_for_continue_edit = State()


class TaskComplete(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_confirmation = State()


class TaskDelete(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_confirmation = State()


class TaskRestore(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_confirmation = State()


class TaskFilter(StatesGroup):
    waiting_for_filter_choice = State()
    waiting_for_priority = State()
    waiting_for_status = State()
    waiting_for_tag = State()
    waiting_for_date = State()
    waiting_for_confirmation = State()


class TagStates(StatesGroup):
    waiting_for_tag_name = State()
    waiting_for_tag_color = State()
    waiting_for_tag_selection = State()
    waiting_for_task_for_tag = State()


class NewTagStates(StatesGroup):
    waiting_for_tag_name = State()


class CleanupStates(StatesGroup):
    waiting_for_days = State()
    waiting_for_confirmation = State()


class RemoveTagStates(StatesGroup):
    waiting_for_tag_name = State()
    waiting_for_confirmation = State()


class DelTagStates(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_tag_name = State()
    waiting_for_confirmation = State()


class ReminderSettings(StatesGroup):
    waiting_for_settings_choice = State()
    waiting_for_reminders_setting = State()
    waiting_for_overdue_setting = State()
    waiting_for_reminder_hours = State()


class DailyReminderSettings(StatesGroup):
    waiting_for_daily_time = State()


class TaskFilter(StatesGroup):
    waiting_for_filter_choice = State()
    waiting_for_priority = State()
    waiting_for_status = State()
    waiting_for_tag = State()
    waiting_for_date = State()
    waiting_for_confirmation = State()
    waiting_for_combined_next = State()


class AddTagStates(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_tag_name = State()
    waiting_for_confirmation = State()
    waiting_for_tag_creation = State()


class TaskGrouping(StatesGroup):
    waiting_for_group_type = State()
    waiting_for_specific_choice = State()
    waiting_for_confirmation = State()


def extract_task_data(task):
    try:
        if not task or len(task) < 2:
            return None

        task_id = task[0]
        user_id = task[1]
        content = task[2] if len(task) > 2 else ""
        due_date = task[3] if len(task) > 3 else None
        priority = task[4] if len(task) > 4 else "medium"
        status = task[5] if len(task) > 5 else "pending"
        is_deleted = False
        if len(task) > 9:
            is_deleted = bool(task[9])

        print(
            f"DEBUG extract_task_data: id:{task_id}, priority:'{priority}', status:'{status}', is_deleted:{is_deleted}"
        )

        return task_id, content, due_date, priority, status, is_deleted

    except (IndexError, TypeError, AttributeError) as e:
        print(f"Error extracting task data: {e}")
        return None


def format_due_date(due_date):
    """Форматирование даты для отображения с учетом времени"""
    if not due_date:
        return "⏳ без срока"

    try:
        if not isinstance(due_date, str):
            return "⏳ без срока"

        invalid_keywords = [
            "high",
            "medium",
            "low",
            "сделать",
            "проект",
            "задача",
            "описание",
        ]
        if any(keyword in due_date.lower() for keyword in invalid_keywords):
            return "⏳ без срока"
        if not any(char.isdigit() for char in due_date):
            return "⏳ без срока"

        if "T" in due_date:
            due_datetime = datetime.fromisoformat(due_date)
        elif " " in due_date:
            due_datetime = datetime.fromisoformat(due_date.replace(" ", "T"))
        else:
            due_datetime = datetime.fromisoformat(due_date + "T00:00:00")

        now = datetime.now()
        is_overdue = due_datetime < now

        if due_datetime.time() == time(23, 59) or due_datetime.hour == 23:
            if is_overdue:
                return f"⚠️ ПРОСРОЧЕНА: \n📅 до {due_datetime.strftime('%d.%m.%Y')} (весь день)"
            else:
                return f"📅 до {due_datetime.strftime('%d.%m.%Y')} (весь день)"
        else:
            if is_overdue:
                return (
                    f"⚠️ ПРОСРОЧЕНА: \n📅 до {due_datetime.strftime('%d.%m.%Y %H:%M')}"
                )
            else:
                return f"📅 до {due_datetime.strftime('%d.%m.%Y %H:%M')}"

    except (ValueError, AttributeError, TypeError) as e:
        print(f"Error formatting due date '{due_date}': {e}")
        return "⏳ без срока"


async def format_and_send_tasks(
    message: Message, tasks: list, title: str = "📋 Ваши задачи"
):
    """Простой и красивый формат задач"""
    if not tasks:
        await message.answer(
            "🎉 <b>Пока нет задач!</b>\n\n"
            "<i>Используйте кнопку '📝 Новая задача' чтобы создать первую</i>",
            parse_mode="HTML",
            reply_markup=get_tasks_keyboard(),
        )
        return

    tasks_text = f"<b>{title}</b>\n\n"

    for i, task in enumerate(tasks, 1):
        task_data = extract_task_data(task)
        if not task_data:
            continue

        task_id, content, due_date, priority, status, is_deleted = task_data

        task_tags = await db.get_task_tags(task_id)
        tags_text = (
            " ".join([f"<code>#{tag[1]}</code>" for tag in task_tags])
            if task_tags
            else ""
        )

        if status == "completed":
            icon = "✅"
            content = f"{content}"
        elif is_deleted:
            icon = "🗑️"
        else:
            icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            icon = icons.get(priority, "🟡")

        tasks_text += f"{icon} <b>#{task_id}</b> - {content}\n"

        if due_date:
            due_text = format_due_date(due_date)
            tasks_text += f"{due_text}\n"

        if tags_text:
            tasks_text += f"🏷️ {tags_text}\n"

        tasks_text += "\n"

    tasks_text += f"<i>Всего: {len(tasks)} задач</i>"

    await message.answer(
        tasks_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
    )


def describe_filters(filters: dict) -> str:
    """Описание примененных фильтров на русском"""
    if not filters:
        return "все задачи"

    descriptions = []

    priority_names = {
        "high": "🔴 высокий приоритет",
        "medium": "🟡 средний приоритет",
        "low": "🟢 низкий приоритет",
    }

    status_names = {
        "pending": "активные",
        "completed": "✅ выполненные",
        "deleted": "🗑️ удаленные",
    }

    date_names = {
        "today": "📅 сегодня",
        "tomorrow": "📅 завтра",
        "week": "📅 неделя",
        "overdue": "⚠️ просроченные",
    }

    if "priority" in filters:
        descriptions.append(
            priority_names.get(filters["priority"], filters["priority"])
        )

    if "status" in filters:
        descriptions.append(status_names.get(filters["status"], filters["status"]))

    if "tag" in filters:
        descriptions.append(f"🏷️ #{filters['tag']}")

    if "date" in filters:
        descriptions.append(date_names.get(filters["date"], filters["date"]))

    return ", ".join(descriptions) if descriptions else "все задачи"


async def count_filtered_tasks(user_id: int, filters: dict) -> int:
    """Посчитать количество задач по фильтрам"""
    if filters.get("status") == "completed":
        tasks = await db.get_user_tasks(user_id, "completed")
    elif filters.get("status") == "deleted":
        tasks = await db.get_deleted_tasks(user_id)
    else:
        tasks = await db.get_user_tasks_with_priority(user_id, "pending")

    count = 0
    for task in tasks:
        task_data = extract_task_data(task)
        if not task_data:
            continue

        task_id, content, due_date, priority, status, is_deleted = task_data

        if is_deleted and filters.get("status") != "deleted":
            continue

        if "priority" in filters and priority != filters["priority"]:
            continue

        if "tag" in filters:
            task_tags = await db.get_task_tags(task_id)
            tag_names = [tag[1].lower() for tag in task_tags]
            if filters["tag"].lower() not in tag_names:
                continue

        if "date" in filters:
            if not due_date:
                if filters["date"] != "overdue":
                    continue
            else:
                due_datetime = datetime.fromisoformat(due_date)
                today = datetime.now().date()

                if filters["date"] == "today" and due_datetime.date() != today:
                    continue
                elif filters[
                    "date"
                ] == "tomorrow" and due_datetime.date() != today + timedelta(days=1):
                    continue
                elif (
                    filters["date"] == "week" and (due_datetime.date() - today).days > 7
                ):
                    continue
                elif filters["date"] == "overdue" and due_datetime.date() >= today:
                    continue

        count += 1

    return count


async def get_storage_stats(user_id: int) -> str:
    """Получить статистику хранилища - УПРОЩЕННАЯ ВЕРСИЯ"""
    storage_stats = await db.get_storage_statistics(user_id)

    task_stats = await db.get_task_statistics(user_id, days=365)

    stats_text = "📊 Текущая статистика:\n\n"

    if task_stats:
        for status, count in task_stats:
            icon = "✅" if status == "completed" else "📝"
            status_name = "выполненные" if status == "completed" else "активные"
            stats_text += f"{icon} {status_name}: {count}\n"
    else:
        active_tasks = await db.get_user_tasks(user_id, "pending")
        completed_tasks = await db.get_user_tasks(user_id, "completed")
        stats_text += f"📝 активные: {len(active_tasks)}\n"
        stats_text += f"✅ выполненные: {len(completed_tasks)}\n"

    stats_text += f"\n🗑️ Готово к очистке:\n"
    stats_text += (
        f"• Выполненные задачи (>30 дней): {storage_stats['old_completed_tasks']}\n"
    )
    stats_text += f"• Записи настроения (>90 дней): {storage_stats['old_moods']}\n"

    return stats_text


async def show_priority_options(message: Message, state: FSMContext):
    """Показать опции приоритета для фильтрации"""
    priority_menu = (
        "🎯 Фильтр по приоритету\n\n"
        "Выберите приоритет:\n\n"
        "🔴 Высокий\n"
        "🟡 Средний\n"
        "🟢 Низкий\n"
        "📋 Все приоритеты\n"
        "🔙 Назад к фильтрам"
    )

    await message.answer(priority_menu, reply_markup=get_priority_keyboard)
    await state.set_state(TaskFilter.waiting_for_priority)


async def show_status_options(message: Message, state: FSMContext):
    """Показать опции статуса для фильтрации"""
    status_menu = (
        "📊 Фильтр по статусу\n\n"
        "Выберите статус:\n\n"
        "✅ Выполненные\n"
        "📝 Активные\n"
        "🗑️ Удаленные\n"
        "📋 Все статусы\n"
        "🔙 Назад к фильтрам"
    )

    await message.answer(status_menu, reply_markup=get_status_keyboard)
    await state.set_state(TaskFilter.waiting_for_status)


async def show_date_options(message: Message, state: FSMContext):
    """Показать опции даты для фильтрации"""
    date_menu = (
        "📅 Фильтр по дате\n\n"
        "Выберите период:\n\n"
        "📅 Сегодня\n"
        "📅 Завтра\n"
        "📅 Неделя\n"
        "⚠️ Просроченные\n"
        "📋 Все даты\n"
        "🔙 Назад к фильтрам"
    )

    await message.answer(date_menu, reply_markup=get_filter_date)
    await state.set_state(TaskFilter.waiting_for_date)


@router.message(F.text == "📋 Задачи")
@router.message(Command("tasks"))
async def handle_tasks_main(message: Message):
    """Главное меню задач"""
    await message.answer(
        "📋 Управление задачами\n\n" "Выберите действие:",
        reply_markup=get_tasks_keyboard(),
    )


@router.message(F.text == "📝 Новая задача")
@router.message(Command("plan"))
async def cmd_plan(message: Message, state: FSMContext):
    """Начать создание новой задачи"""
    await message.answer("📝 Опишите вашу задачу:", reply_markup=get_cancel_keyboard())
    await state.set_state(TaskCreation.waiting_for_content)


@router.message(StateFilter(TaskCreation.waiting_for_content))
async def process_task_content(message: Message, state: FSMContext):
    """Обработка содержания задачи"""
    if await handle_navigation(message, state):
        return
    await state.update_data(content=message.text)
    await message.answer(
        "📅 Укажите дату выполнения (в формате ГГГГ-ММ-ДД)\n"
        "Или нажмите кнопку ниже:",
        reply_markup=get_task_creation_keyboard(),
    )
    await state.set_state(TaskCreation.waiting_for_date)


@router.message(StateFilter(TaskCreation.waiting_for_date))
async def process_task_date(message: Message, state: FSMContext):
    """Обработка даты задачи"""
    if await handle_navigation(message, state):
        return
    if message.text == "⏳ Без срока":
        await state.update_data(due_date=None)
        await message.answer(
            "🎯 Выберите приоритет задачи:", reply_markup=get_priority_keyboard()
        )
        await state.set_state(TaskCreation.waiting_for_priority)
        return

    if message.text == "📅 Сегодня":
        today = datetime.now().date()
        await state.update_data(due_date=today)
        await message.answer(
            "⏰ Хотите указать время для задачи?\n"
            "• Напишите время в формате ЧЧ:ММ (например, 14:30)\n"
            "• Или напишите 'нет' чтобы установить только дату",
            reply_markup=get_back_keyboard(),
        )
        await state.set_state(TaskCreation.waiting_for_time)
        return

    try:
        date_only = datetime.strptime(message.text, "%Y-%m-%d").date()
        if date_only < datetime.now().date():
            await message.answer(
                "❌ Нельзя установить прошедшую дату! Попробуйте снова:"
            )
            return

        await state.update_data(due_date=date_only)
        await message.answer(
            "⏰ Хотите указать время для задачи?\n"
            "• Напишите время в формате ЧЧ:ММ (например, 14:30)\n"
            "• Или напишите 'нет' чтобы установить только дату",
            reply_markup=get_back_keyboard(),
        )
        await state.set_state(TaskCreation.waiting_for_time)

    except ValueError:
        await message.answer(
            "❌ Неверный формат даты! Используйте: ГГГГ-ММ-ДД\nПопробуйте снова:"
        )


@router.message(StateFilter(TaskCreation.waiting_for_time))
async def process_task_time(message: Message, state: FSMContext):
    """Обработка времени задачи"""
    if await handle_navigation(message, state):
        return
    data = await state.get_data()
    content = data["content"]
    due_date = data["due_date"]
    time_text = message.text.lower()

    if time_text == "нет":
        due_datetime = datetime.combine(due_date, time(23, 59)) if due_date else None
    else:
        try:
            time_only = datetime.strptime(time_text, "%H:%M").time()
            due_datetime = datetime.combine(due_date, time_only)

            if due_datetime < datetime.now():
                await message.answer(
                    "❌ Нельзя установить прошедшее время! Попробуйте снова:"
                )
                return

        except ValueError:
            await message.answer(
                "❌ Неверный формат времени! Используйте: ЧЧ:ММ\nПопробуйте снова:"
            )
            return

    await state.update_data(due_datetime=due_datetime)
    await message.answer(
        "🎯 Выберите приоритет задачи:", reply_markup=get_priority_keyboard()
    )
    await state.set_state(TaskCreation.waiting_for_priority)


@router.message(StateFilter(TaskCreation.waiting_for_priority))
async def process_task_priority(message: Message, state: FSMContext):
    """Обработка приоритета задачи"""
    if await handle_navigation(message, state):
        return
    priority_map = {"🔴 Высокий": "high", "🟡 Средний": "medium", "🟢 Низкий": "low"}

    if message.text in priority_map:
        priority = priority_map[message.text]
    else:
        await message.answer(
            "❌ Пожалуйста, выберите приоритет из предложенных вариантов:"
        )
        return

    data = await state.get_data()
    content = data["content"]
    due_datetime = data.get("due_datetime")

    task_id = await db.add_task_with_priority(
        message.from_user.id, content, due_datetime, priority
    )

    if due_datetime and reminder_manager:
        try:
            await reminder_manager.create_reminder_for_new_task(
                user_id=message.from_user.id, task_id=task_id, due_date=due_datetime
            )
        except Exception as e:
            print(f"ERROR: Failed to create reminder for task {task_id}: {e}")

    priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    priority_texts = {"high": "высокий", "medium": "средний", "low": "низкий"}

    response_text = f"✅ Задача добавлена!\n"
    response_text += (
        f"Приоритет: {priority_icons[priority]} {priority_texts[priority]}\n"
    )

    if due_datetime:
        if due_datetime.time() == time(23, 59):
            response_text += f"Срок: {due_datetime.strftime('%d.%m.%Y')} (весь день)"
        else:
            response_text += f"Срок: {due_datetime.strftime('%d.%m.%Y %H:%M')}"

        settings = await db.get_reminder_settings(message.from_user.id)
        if settings and settings[1]:
            reminder_hours = settings[2]
            response_text += f"\n🔔 Напоминание придет за {reminder_hours} ч до срока"
    else:
        response_text += "Срок: без срока"

    response_text += f"\nНомер задачи: {task_id}"

    await message.answer(response_text, reply_markup=get_tasks_keyboard())
    await state.clear()


@router.message(F.text == "📋 Список задач")
async def handle_show_tasks(message: Message):
    """Показать все активные задачи"""
    await show_all_tasks(message)


async def show_all_tasks(message: Message):
    """Показать все активные задачи"""
    tasks = await db.get_user_tasks_with_priority(message.from_user.id, "pending")

    if not tasks:
        await message.answer(
            "🎉 У вас нет активных задач!", reply_markup=get_tasks_keyboard()
        )
        return

    await format_and_send_tasks(message, tasks, "📋 Ваши активные задачи")


@router.message(F.text == "🚨 Срочные задачи")
@router.message(Command("urgent"))
async def cmd_urgent(message: Message):
    """Показать срочные задачи"""
    await show_urgent_tasks(message)


async def show_urgent_tasks(message: Message):
    """Показать срочные задачи - УПРОЩЕННАЯ ВЕРСИЯ"""
    try:
        user_id = message.from_user.id

        urgent_tasks = await db.get_urgent_tasks(user_id)

        if not urgent_tasks:
            await message.answer(
                "🎉 Нет срочных задач!", reply_markup=get_tasks_keyboard()
            )
            return

        await format_and_send_tasks(message, urgent_tasks, "🚨 Срочные задачи")

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении срочных задач: {e}",
            reply_markup=get_tasks_keyboard(),
        )


@router.message(F.text == "⏰ Ближайшие задачи")
@router.message(Command("upcoming"))
async def cmd_upcoming(message: Message):
    """Показать ближайшие задачи"""
    await show_upcoming_tasks(message)


async def show_upcoming_tasks(message: Message):
    """Показать ближайшие задачи - УПРОЩЕННАЯ ВЕРСИЯ"""
    try:
        user_id = message.from_user.id

        tasks = await db.get_upcoming_tasks(user_id, days=7)

        if not tasks:
            await message.answer(
                "🎉 Нет ближайших задач!", reply_markup=get_tasks_keyboard()
            )
            return

        await format_and_send_tasks(message, tasks, "⏰ Ближайшие задачи")

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении ближайших задач: {e}",
            reply_markup=get_tasks_keyboard(),
        )


@router.message(F.text == "⚠️ Просроченные")
@router.message(Command("overdue"))
async def cmd_overdue(message: Message):
    """Показать просроченные задачи"""
    await show_overdue_tasks(message)


async def show_overdue_tasks(message: Message):
    """Показать просроченные задачи - УПРОЩЕННАЯ ВЕРСИЯ"""
    try:
        user_id = message.from_user.id
        overdue_tasks = await db.get_overdue_tasks(user_id)

        if not overdue_tasks:
            await message.answer(
                "🎉 У вас нет просроченных задач!", reply_markup=get_tasks_keyboard()
            )
            return

        await format_and_send_tasks(message, overdue_tasks, "⚠️ Просроченные задачи")

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении просроченных задач: {e}",
            reply_markup=get_tasks_keyboard(),
        )


@router.message(F.text == "📅 Задачи на сегодня")
async def handle_today_tasks(message: Message):
    """Показать задачи на сегодня"""
    await show_today_tasks(message)


async def show_today_tasks(message: Message):
    """Показать задачи на сегодня - УПРОЩЕННАЯ ВЕРСИЯ"""
    try:
        user_id = message.from_user.id
        tasks = await db.get_today_tasks(user_id)

        if not tasks:
            await message.answer(
                "🎉 На сегодня задач нет!", reply_markup=get_tasks_keyboard()
            )
            return

        await format_and_send_tasks(message, tasks, "📅 Задачи на сегодня")

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении задач на сегодня: {e}",
            reply_markup=get_tasks_keyboard(),
        )


@router.message(F.text == "✅ Завершить задачу")
@router.message(Command("complete"))
async def cmd_complete(message: Message, state: FSMContext):
    """Начать процесс завершения задачи"""
    await message.answer(
        "✅ Завершение задачи\n\n"
        "Введите ID задачи для завершения:\n"
        "(ID можно посмотреть в списке задач)",
        reply_markup=get_back_keyboard(),
    )
    await state.set_state(TaskComplete.waiting_for_task_id)


@router.message(StateFilter(TaskComplete.waiting_for_task_id))
async def process_complete_task_id_input(message: Message, state: FSMContext):
    """Обработка ввода ID задачи"""
    if await handle_navigation(message, state):
        return
    user_input = message.text.strip()

    if not user_input:
        await message.answer("❌ ID не может быть пустым! Введите число:")
        return

    if not user_input.isdigit():
        await message.answer("❌ Неверный формат ID! Введите число:")
        return

    try:
        task_id = int(user_input)
        await process_complete_task_id(message, state, task_id)
    except ValueError:
        await message.answer("❌ Неверный формат ID! Введите корректное число:")
    except Exception as e:
        await message.answer("❌ Произошла ошибка при обработке ID. Попробуйте снова:")
        print(f"Error in process_complete_task_id_input: {e}")


async def process_complete_task_id(message: Message, state: FSMContext, task_id: int):
    """Обработка ID задачи для завершения"""
    try:
        task = await db.get_task(task_id)

        if not task:
            await message.answer(
                "❌ Задача не найдена!", reply_markup=get_tasks_keyboard()
            )
            await state.clear()
            return

        if len(task) < 2:
            await message.answer(
                "❌ Ошибка данных задачи!", reply_markup=get_tasks_keyboard()
            )
            await state.clear()
            return

        user_id_from_task = task[1]
        if isinstance(user_id_from_task, str):
            try:
                user_id_from_task = int(user_id_from_task)
            except ValueError:
                await message.answer(
                    "❌ Ошибка формата данных задачи!",
                    reply_markup=get_tasks_keyboard(),
                )
                await state.clear()
                return

        if user_id_from_task != message.from_user.id:
            await message.answer(
                "❌ Это не ваша задача!", reply_markup=get_tasks_keyboard()
            )
            await state.clear()
            return

        if len(task) < 10:
            await message.answer(
                "❌ Неполные данные задачи!", reply_markup=get_tasks_keyboard()
            )
            await state.clear()
            return

        content = task[2] if len(task) > 2 else ""
        due_date = task[3] if len(task) > 3 else None
        is_deleted = bool(task[9]) if len(task) > 9 else False

        if is_deleted:
            await message.answer(
                "❌ Эта задача была удалена!", reply_markup=get_tasks_keyboard()
            )
            await state.clear()
            return

        await state.update_data(complete_task_id=task_id, complete_task_content=content)

        confirm_text = f"✅ Вы хотите завершить задачу?\n\n📝 {content}\n"

        if due_date:
            try:
                due_datetime = datetime.fromisoformat(due_date)
                if due_datetime.time() == time(23, 59):
                    confirm_text += (
                        f"📅 Срок: {due_datetime.strftime('%d.%m.%Y')} (весь день)\n"
                    )
                else:
                    confirm_text += (
                        f"📅 Срок: {due_datetime.strftime('%d.%m.%Y %H:%M')}\n"
                    )
            except (ValueError, TypeError):
                confirm_text += "📅 Срок: неверный формат даты\n"

        confirm_text += f"\nПодтвердите завершение задачи:"

        await message.answer(confirm_text, reply_markup=get_confirm_keyboard())
        await state.set_state(TaskComplete.waiting_for_confirmation)

    except Exception as e:
        await message.answer(
            "❌ Произошла ошибка при обработке задачи!",
            reply_markup=get_tasks_keyboard(),
        )
        print(f"Error in process_complete_task_id: {e}")
        await state.clear()


@router.message(StateFilter(TaskComplete.waiting_for_confirmation))
async def process_complete_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения завершения"""
    if await handle_navigation(message, state):
        return
    answer = message.text.lower().strip()

    if answer in ["✅ подтвердить", "да", "yes", "y", "д"]:
        data = await state.get_data()
        task_id = data["complete_task_id"]
        content = data["complete_task_content"]

        await db.complete_task(task_id)

        display_content = content
        if len(display_content) > 30:
            display_content = display_content[:30] + "..."

        await message.answer(
            f"✅ Задача #{task_id}: {display_content} - выполнена!",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()

    elif answer in ["❌ отменить", "нет", "no", "n", "н"]:
        await message.answer(
            "❌ Завершение задачи отменено", reply_markup=get_tasks_keyboard()
        )
        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, используйте кнопки для подтверждения:")


@router.message(F.text == "🗑️ Удалить задачу")
@router.message(Command("delete"))
async def cmd_delete(message: Message, state: FSMContext):
    """Начать процесс удаления задачи"""
    await message.answer(
        "🗑️ Удаление задачи\n\n" "Введите ID задачи для удаления:",
        reply_markup=get_back_keyboard(),
    )
    await state.set_state(TaskDelete.waiting_for_task_id)


@router.message(StateFilter(TaskDelete.waiting_for_task_id))
async def process_delete_task_id_input(message: Message, state: FSMContext):
    """Обработка ввода ID задачи для удаления"""
    if await handle_navigation(message, state):
        return
    user_input = message.text.strip()

    if not user_input:
        await message.answer("❌ ID не может быть пустым! Введите число:")
        return

    if not user_input.isdigit():
        await message.answer("❌ Неверный формат ID! Введите число:")
        return

    try:
        task_id = int(user_input)
        await process_delete_task_id(message, state, task_id)
    except ValueError:
        await message.answer("❌ Неверный формат ID! Введите корректное число:")
    except Exception as e:
        await message.answer("❌ Произошла ошибка при обработке ID. Попробуйте снова:")
        print(f"Error in process_delete_task_id_input: {e}")


async def process_delete_task_id(message: Message, state: FSMContext, task_id: int):
    """Обработка ID задачи для удаления"""
    try:
        task = await db.get_task(task_id)

        if not task:
            await message.answer(
                "❌ Задача не найдена! Проверьте ID и попробуйте снова:",
                reply_markup=get_back_keyboard(),
            )
            return

        if len(task) < 2:
            await message.answer(
                "❌ Ошибка данных задачи! Попробуйте другую задачу:",
                reply_markup=get_back_keyboard(),
            )
            return

        user_id_from_task = task[1]
        if isinstance(user_id_from_task, str):
            try:
                user_id_from_task = int(user_id_from_task)
            except ValueError:
                await message.answer(
                    "❌ Ошибка формата данных задачи! Попробуйте другую задачу:",
                    reply_markup=get_back_keyboard(),
                )
                return

        if user_id_from_task != message.from_user.id:
            await message.answer(
                "❌ Это не ваша задача! Вы можете удалять только свои задачи. Попробуйте другой ID:",
                reply_markup=get_back_keyboard(),
            )
            return

        is_deleted = False
        try:
            if len(task) > 9:
                is_deleted = bool(task[9])
        except (IndexError, TypeError):
            is_deleted = False

        if is_deleted:
            await message.answer(
                "❌ Эта задача уже удалена! Выберите другую задачу:",
                reply_markup=get_back_keyboard(),
            )
            return

        task_data = extract_task_data(task)
        if not task_data:
            await message.answer(
                "❌ Ошибка данных задачи! Попробуйте другую задачу:",
                reply_markup=get_back_keyboard(),
            )
            return

        task_id, content, due_date, priority, status, _ = task_data

        await state.update_data(
            delete_task_id=task_id,
            delete_task_content=content,
            delete_task_due_date=due_date,
            delete_task_priority=priority,
        )

        confirm_text = f"🗑️ Вы хотите удалить задачу?\n\n" f"📝 {content}\n"

        due_text = format_due_date(due_date)
        confirm_text += f"{due_text}\n"

        priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        priority_texts = {"high": "высокий", "medium": "средний", "low": "низкий"}
        confirm_text += f"🎯 Приоритет: {priority_icons.get(priority, '🟡')} {priority_texts.get(priority, 'средний')}\n"

        confirm_text += f"\n⚠️ Внимание: Задача будет перемещена в корзину и удалена через 30 дней.\n\n"
        confirm_text += "Подтвердите удаление задачи:"

        await message.answer(confirm_text, reply_markup=get_confirm_keyboard())
        await state.set_state(TaskDelete.waiting_for_confirmation)

    except Exception as e:
        error_msg = "❌ Произошла ошибка при обработке задачи. Попробуйте снова."
        await message.answer(error_msg, reply_markup=get_back_keyboard())
        print(f"Error in process_delete_task_id: {e}")


@router.message(StateFilter(TaskDelete.waiting_for_confirmation))
async def process_delete_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения удаления"""
    if await handle_navigation(message, state):
        return
    answer = message.text.lower().strip()

    if answer in ["✅ подтвердить", "да", "yes", "y", "д", "удалить", "delete"]:
        try:
            data = await state.get_data()
            task_id = data["delete_task_id"]
            content = data["delete_task_content"]

            await db.delete_task(task_id)

            display_content = content
            if len(display_content) > 30:
                display_content = display_content[:30] + "..."

            await message.answer(
                f"🗑️ Задача #{task_id} '{display_content}' удалена!\n\n"
                f"💡 Вы можете восстановить её в течение 30 дней через меню задач",
                reply_markup=get_tasks_keyboard(),
            )
            await state.clear()

        except Exception as e:
            await message.answer(
                "❌ Ошибка при удалении задачи! Попробуйте снова.",
                reply_markup=get_tasks_keyboard(),
            )
            print(f"Error in process_delete_confirmation: {e}")
            await state.clear()

    elif answer in ["❌ отменить", "нет", "no", "n", "н", "отмена", "cancel"]:
        await message.answer(
            "✅ Удаление задачи отменено", reply_markup=get_tasks_keyboard()
        )
        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, используйте кнопки для подтверждения:")


@router.message(F.text == "🔄 Восстановить задачу")
@router.message(Command("restore"))
async def cmd_restore(message: Message, state: FSMContext):
    """Начать процесс восстановления задачи"""
    await message.answer(
        "🔄 Восстановление задачи\n\n" "Введите ID задачи для восстановления:",
        reply_markup=get_back_keyboard(),
    )
    await state.set_state(TaskRestore.waiting_for_task_id)


@router.message(StateFilter(TaskRestore.waiting_for_task_id))
async def process_restore_task_id_input(message: Message, state: FSMContext):
    """Обработка ввода ID задачи для восстановления"""
    if await handle_navigation(message, state):
        return
    try:
        task_id = int(message.text)
        await process_restore_task_id(message, state, task_id)
    except ValueError:
        await message.answer("❌ Неверный формат ID! Введите число:")


async def process_restore_task_id(message: Message, state: FSMContext, task_id: int):
    """Обработка ID задачи для восстановления"""
    task = await db.get_task(task_id)

    if not task:
        await message.answer("❌ Задача не найдена!", reply_markup=get_tasks_keyboard())
        await state.clear()
        return

    if task[1] != message.from_user.id:
        await message.answer(
            "❌ Это не ваша задача!", reply_markup=get_tasks_keyboard()
        )
        await state.clear()
        return

    is_deleted = False
    if len(task) > 9:
        is_deleted = task[9]
    elif len(task) > 6:
        is_deleted = task[6]
    elif len(task) > 5:
        is_deleted = task[5]

    if not is_deleted:
        await message.answer(
            "❌ Эта задача не была удалена!", reply_markup=get_tasks_keyboard()
        )
        await state.clear()
        return

    task_data = extract_task_data(task)
    if not task_data:
        await message.answer(
            "❌ Ошибка данных задачи!", reply_markup=get_tasks_keyboard()
        )
        await state.clear()
        return

    task_id, content, due_date, priority, status, _ = task_data

    await state.update_data(restore_task_id=task_id, restore_task_content=content)

    confirm_text = f"🔄 Вы хотите восстановить задачу?\n\n" f"📝 {content}\n"

    if due_date:
        due_datetime = datetime.fromisoformat(due_date)
        if due_datetime.time() == time(23, 59):
            confirm_text += (
                f"📅 Срок: {due_datetime.strftime('%d.%m.%Y')} (весь день)\n"
            )
        else:
            confirm_text += f"📅 Срок: {due_datetime.strftime('%d.%m.%Y %H:%M')}\n"

    priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    confirm_text += f"🎯 Приоритет: {priority_icons.get(priority, '🟡')}\n"

    confirm_text += f"\nПодтвердите восстановление задачи:"

    await message.answer(confirm_text, reply_markup=get_confirm_keyboard())
    await state.set_state(TaskRestore.waiting_for_confirmation)


@router.message(StateFilter(TaskRestore.waiting_for_confirmation))
async def process_restore_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения восстановления"""
    if await handle_navigation(message, state):
        return
    answer = message.text.lower().strip()

    if answer in ["✅ подтвердить", "да", "yes", "y", "д"]:
        data = await state.get_data()
        task_id = data["restore_task_id"]
        content = data["restore_task_content"]

        await db.restore_task(task_id)

        display_content = content
        if len(display_content) > 30:
            display_content = display_content[:30] + "..."

        await message.answer(
            f"✅ Задача #{task_id} '{display_content}' восстановлена!",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()

    elif answer in ["❌ отменить", "нет", "no", "n", "н"]:
        await message.answer(
            "❌ Восстановление задачи отменено", reply_markup=get_tasks_keyboard()
        )
        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, используйте кнопки для подтверждения:")


@router.message(F.text == "✏️ Редактировать задачу")
@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext):
    """Начать процесс редактирования задачи"""
    await message.answer(
        "✏️ Редактирование задачи\n\n" "Введите ID задачи для редактирования:",
        reply_markup=get_back_keyboard(),
    )
    await state.set_state(TaskEdit.waiting_for_task_id)


@router.message(StateFilter(TaskEdit.waiting_for_task_id))
async def process_edit_task_id(message: Message, state: FSMContext):
    """Обработка ввода ID задачи для редактирования"""
    if await handle_navigation(message, state):
        return
    try:
        task_id = int(message.text)
        task = await db.get_task(task_id)

        if not task:
            await message.answer(
                "❌ Задача не найдена!", reply_markup=get_tasks_keyboard()
            )
            await state.clear()
            return

        if task[1] != message.from_user.id:
            await message.answer(
                "❌ Это не ваша задача!", reply_markup=get_tasks_keyboard()
            )
            await state.clear()
            return

        is_deleted = False
        if len(task) > 9:
            is_deleted = task[9]
        elif len(task) > 6:
            is_deleted = task[6]
        elif len(task) > 5:
            is_deleted = task[5]

        if is_deleted:
            await message.answer(
                "❌ Эта задача была удалена!", reply_markup=get_tasks_keyboard()
            )
            await state.clear()
            return

        await state.update_data(
            edit_task_id=task_id,
            edit_task_content=task[2],
            edit_task_due_date=task[3] if len(task) > 3 else None,
            edit_task_priority=task[4] if len(task) > 4 else "medium",
        )

        await show_edit_options(message, state)

    except ValueError:
        await message.answer(
            "❌ Неверный формат ID! Введите число:", reply_markup=get_back_keyboard()
        )
        return


async def show_edit_options(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data["edit_task_id"]
    content = data["edit_task_content"]
    due_date = data["edit_task_due_date"]
    priority = data["edit_task_priority"]

    priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    priority_texts = {"high": "высокий", "medium": "средний", "low": "низкий"}

    task_info = f"✏️ Редактирование задачи #{task_id}\n\n"
    task_info += f"📝 Текст: {content}\n"

    if due_date:
        due_datetime = datetime.fromisoformat(due_date)
        if due_datetime.time() == time(23, 59):
            task_info += f"📅 Срок: {due_datetime.strftime('%d.%m.%Y')} (весь день)\n"
        else:
            task_info += f"📅 Срок: {due_datetime.strftime('%d.%m.%Y %H:%M')}\n"
    else:
        task_info += "📅 Срок: без срока\n"

    task_info += f"🎯 Приоритет: {priority_icons.get(priority, '🟡')} {priority_texts.get(priority, 'средний')}\n"

    task_info += "\nЧто хотите изменить?"

    await message.answer(task_info, reply_markup=get_edit_keyboard())
    await state.set_state(TaskEdit.waiting_for_edit_choice)


@router.message(StateFilter(TaskEdit.waiting_for_edit_choice))
async def process_edit_choice(message: Message, state: FSMContext):
    """Обработка выбора опции редактирования"""
    if await handle_navigation(message, state):
        return
    choice = message.text

    if choice == "📝 Текст задачи":
        await message.answer(
            "📝 Введите новый текст задачи:", reply_markup=get_back_keyboard()
        )
        await state.set_state(TaskEdit.waiting_for_new_content)

    elif choice == "📅 Дата и время":
        await message.answer(
            "📅 Введите новую дату (в формате ГГГГ-ММ-ДД):\n"
            "Или напишите 'нет' чтобы убрать срок:",
            reply_markup=get_back_keyboard(),
        )
        await state.set_state(TaskEdit.waiting_for_new_date)

    elif choice == "🎯 Приоритет":
        await message.answer(
            "🎯 Выберите новый приоритет:", reply_markup=get_priority_keyboard()
        )
        await state.set_state(TaskEdit.waiting_for_new_priority)

    else:
        await message.answer("❌ Пожалуйста, выберите вариант из меню:")


@router.message(StateFilter(TaskEdit.waiting_for_new_content))
async def process_new_content(message: Message, state: FSMContext):
    """Обработка нового текста задачи"""
    if await handle_navigation(message, state):
        return
    new_content = message.text
    data = await state.get_data()
    task_id = data["edit_task_id"]

    await db.update_task_content(task_id, new_content)
    await message.answer(f"✅ Текст задачи #{task_id} обновлен!")
    await message.answer(
        "🔄 Хотите изменить что-то еще в этой задаче?",
        reply_markup=get_confirm_keyboard(),
    )
    await state.set_state(TaskEdit.waiting_for_continue_edit)


@router.message(StateFilter(TaskEdit.waiting_for_new_date))
async def process_new_date(message: Message, state: FSMContext):
    """Обработка новой даты"""
    if await handle_navigation(message, state):
        return
    if message.text.lower() == "нет":
        data = await state.get_data()
        task_id = data["edit_task_id"]

        await db.update_task_due_date(task_id, None)
        await message.answer(f"✅ Срок выполнения задачи #{task_id} убран!")
        await message.answer(
            "🔄 Хотите изменить что-то еще в этой задаче?",
            reply_markup=get_confirm_keyboard(),
        )
        await state.set_state(TaskEdit.waiting_for_continue_edit)
        return

    try:
        date_only = datetime.strptime(message.text, "%Y-%m-%d").date()
        if date_only < datetime.now().date():
            await message.answer(
                "❌ Нельзя установить прошедшую дату! Попробуйте снова:"
            )
            return

        await state.update_data(new_due_date=date_only)
        await message.answer(
            "⏰ Хотите указать время для задачи?\n"
            "• Напишите время в формате ЧЧ:ММ (например, 14:30)\n"
            "• Или напишите 'нет' чтобы установить только дату\n",
            reply_markup=get_back_keyboard(),
        )
        await state.set_state(TaskEdit.waiting_for_new_time)

    except ValueError:
        await message.answer(
            "❌ Неверный формат даты! Используйте: ГГГГ-ММ-ДД\nПопробуйте снова:"
        )


@router.message(StateFilter(TaskEdit.waiting_for_new_time))
async def process_new_time(message: Message, state: FSMContext):
    """Обработка нового времени"""
    if await handle_navigation(message, state):
        return
    data = await state.get_data()
    task_id = data["edit_task_id"]
    due_date = data["new_due_date"]
    time_text = message.text.lower()

    if time_text == "нет":
        due_datetime = datetime.combine(due_date, time(23, 59))
        response_text = f"✅ Задача обновлена! Новый срок: {due_datetime.strftime('%d.%m.%Y')} (весь день)"
    else:
        try:
            time_only = datetime.strptime(time_text, "%H:%M").time()
            due_datetime = datetime.combine(due_date, time_only)

            if due_datetime < datetime.now():
                await message.answer(
                    "❌ Нельзя установить прошедшее время! Попробуйте снова:"
                )
                return

            response_text = f"✅ Задача обновлена! Новый срок: {due_datetime.strftime('%d.%m.%Y %H:%M')}"

        except ValueError:
            await message.answer(
                "❌ Неверный формат времени! Используйте: ЧЧ:ММ\nПопробуйте снова:"
            )
            return

    await db.update_task_due_date(task_id, due_datetime)
    await message.answer(f"{response_text}\nID задачи: {task_id}")
    await message.answer(
        "🔄 Хотите изменить что-то еще в этой задаче?",
        reply_markup=get_confirm_keyboard(),
    )
    await state.set_state(TaskEdit.waiting_for_continue_edit)


@router.message(StateFilter(TaskEdit.waiting_for_new_priority))
async def process_new_priority(message: Message, state: FSMContext):
    """Обработка нового приоритета"""
    if await handle_navigation(message, state):
        return
    priority_map = {"🔴 Высокий": "high", "🟡 Средний": "medium", "🟢 Низкий": "low"}

    if message.text in priority_map:
        priority = priority_map[message.text]
    else:
        await message.answer(
            "❌ Пожалуйста, выберите приоритет из предложенных вариантов:"
        )
        return

    data = await state.get_data()
    task_id = data["edit_task_id"]

    await db.update_task_priority(task_id, priority)

    priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    priority_texts = {"high": "высокий", "medium": "средний", "low": "низкий"}

    await message.answer(
        f"✅ Приоритет задачи #{task_id} изменен на: "
        f"{priority_icons[priority]} {priority_texts[priority]}"
    )
    await message.answer(
        "🔄 Хотите изменить что-то еще в этой задаче?",
        reply_markup=get_confirm_keyboard(),
    )
    await state.set_state(TaskEdit.waiting_for_continue_edit)


@router.message(StateFilter(TaskEdit.waiting_for_continue_edit))
async def process_continue_edit(message: Message, state: FSMContext):
    """Обработка продолжения редактирования"""
    if await handle_navigation(message, state):
        return
    answer = message.text.lower().strip()

    if answer in ["✅ подтвердить", "да", "yes", "y", "д"]:
        await show_edit_options(message, state)
        await state.set_state(TaskEdit.waiting_for_edit_choice)

    elif answer in ["❌ отменить", "нет", "no", "n", "н"]:
        await message.answer(
            "✅ Редактирование завершено!", reply_markup=get_tasks_keyboard()
        )
        await state.clear()

    else:
        await message.answer("❌ Пожалуйста, используйте кнопки для подтверждения:")


@router.message(F.text == "🎯 Фильтры задач")
async def handle_filters(message: Message, state: FSMContext):
    """Показать меню фильтров"""
    await show_filter_menu(message, state)


async def show_filter_menu(message: Message, state: FSMContext):
    """Показать меню фильтров"""
    filter_menu = (
        "🎯 Фильтрация задач\n\n"
        "Выберите тип фильтра:\n\n"
        "🎯 По приоритету\n"
        "📊 По статусу\n"
        "📅 По дате\n"
        "🏷️ По тегу\n"
        "🔄 Комбинированный\n"
        "📋 Все активные\n\n"
        "🔙 Назад к задачам"
    )

    await message.answer(filter_menu, reply_markup=get_filter_keyboard())
    await state.set_state(TaskFilter.waiting_for_filter_choice)


@router.message(StateFilter(TaskFilter.waiting_for_filter_choice))
async def process_filter_choice(message: Message, state: FSMContext):
    """Обработка выбора типа фильтра"""
    if await handle_navigation(message, state):
        return
    if message.text == "🎯 По приоритету":
        await state.update_data(current_filters={}, filter_type="single")
        await show_priority_options(message, state)

    elif message.text == "📊 По статусу":
        await state.update_data(current_filters={}, filter_type="single")
        await show_status_options(message, state)

    elif message.text == "📅 По дате":
        await state.update_data(current_filters={}, filter_type="single")
        await show_date_options(message, state)

    elif message.text == "🏷️ По тегу":
        await state.update_data(current_filters={}, filter_type="single")
        await message.answer(
            "🏷️ Фильтр по тегу\n\n" "Введите название тега:",
            reply_markup=get_back_keyboard(),
        )
        await state.set_state(TaskFilter.waiting_for_tag)

    elif message.text == "🔄 Комбинированный":
        await state.update_data(
            current_filters={}, filter_type="combined", combined_step=0
        )
        await continue_combined_filter(message, state, {})

    elif message.text == "📋 Все активные":
        await show_all_tasks(message)
        await state.clear()

    else:
        await message.answer(
            "❌ Пожалуйста, выберите вариант из меню:",
            reply_markup=get_filter_keyboard(),
        )


@router.message(StateFilter(TaskFilter.waiting_for_priority))
async def process_filter_priority(message: Message, state: FSMContext):
    """Обработка выбора приоритета для фильтрации"""
    if await handle_navigation(message, state):
        return

    priority_map = {
        "🔴 Высокий": "high",
        "🟡 Средний": "medium",
        "🟢 Низкий": "low",
        "📋 Все приоритеты": None,
    }

    if message.text not in priority_map:
        await message.answer(
            "❌ Пожалуйста, выберите приоритет из предложенных вариантов:",
            reply_markup=get_priority_keyboard(),
        )
        return

    selected_priority = priority_map[message.text]
    data = await state.get_data()
    current_filters = data.get("current_filters", {})
    filter_type = data.get("filter_type", "single")

    if selected_priority is not None:
        current_filters["priority"] = selected_priority
    else:

        if "priority" in current_filters:
            del current_filters["priority"]

    await state.update_data(current_filters=current_filters)

    if filter_type == "combined":
        await continue_combined_filter(message, state, current_filters)
    else:
        await apply_single_filter(message, state, current_filters)


@router.message(StateFilter(TaskFilter.waiting_for_status))
async def process_filter_status(message: Message, state: FSMContext):
    """Обработка выбора статуса для фильтрации"""
    if await handle_navigation(message, state):
        return
    status_map = {
        "✅ Выполненные": "completed",
        "📝 Активные": "pending",
        "🗑️ Удаленные": "deleted",
        "📋 Все статусы": None,
    }

    if message.text not in status_map:
        await message.answer(
            "❌ Пожалуйста, выберите статус из предложенных вариантов:"
        )
        return

    selected_status = status_map[message.text]
    data = await state.get_data()
    current_filters = data.get("current_filters", {})
    filter_type = data.get("filter_type", "single")

    if selected_status:
        current_filters["status"] = selected_status
    elif "status" in current_filters:
        del current_filters["status"]

    await state.update_data(current_filters=current_filters)

    if filter_type == "combined":
        await continue_combined_filter(message, state, current_filters)
    else:
        await apply_single_filter(message, state, current_filters)


@router.message(StateFilter(TaskFilter.waiting_for_date))
async def process_filter_date(message: Message, state: FSMContext):
    """Обработка выбора даты для фильтрации"""
    if await handle_navigation(message, state):
        return
    date_map = {
        "📅 Сегодня": "today",
        "📅 Завтра": "tomorrow",
        "📅 Неделя": "week",
        "⚠️ Просроченные": "overdue",
        "📋 Все даты": None,
    }

    if message.text not in date_map:
        await message.answer(
            "❌ Пожалуйста, выберите период из предложенных вариантов:"
        )
        return

    selected_date = date_map[message.text]
    data = await state.get_data()
    current_filters = data.get("current_filters", {})
    filter_type = data.get("filter_type", "single")

    if selected_date:
        current_filters["date"] = selected_date
    elif "date" in current_filters:
        del current_filters["date"]

    await state.update_data(current_filters=current_filters)

    if filter_type == "combined":
        await continue_combined_filter(message, state, current_filters)
    else:
        await apply_single_filter(message, state, current_filters)


@router.message(StateFilter(TaskFilter.waiting_for_tag))
async def process_filter_tag(message: Message, state: FSMContext):
    """Обработка ввода тега для фильтрации"""
    if await handle_navigation(message, state):
        return
    tag_name = message.text.strip()
    if not tag_name:
        await message.answer("❌ Название тега не может быть пустым! Попробуйте снова:")
        return

    if tag_name.startswith("#"):
        tag_name = tag_name[1:]

    user_tags = await db.get_user_tags(message.from_user.id)
    tag_exists = (
        any(tag[1].lower() == tag_name.lower() for tag in user_tags)
        if user_tags
        else False
    )

    if not tag_exists:
        tag_list = (
            ", ".join([f"#{tag[1]}" for tag in user_tags]) if user_tags else "нет тегов"
        )
        await message.answer(
            f"❌ Тег '#{tag_name}' не найден!\n\n"
            f"📋 Ваши теги: {tag_list}\n\n"
            "Введите существующий тег или создайте новый через меню тегов:",
            reply_markup=get_back_keyboard(),
        )
        return

    data = await state.get_data()
    current_filters = data.get("current_filters", {})
    current_filters["tag"] = tag_name

    await state.update_data(current_filters=current_filters)

    if data.get("filter_type") == "combined":
        await continue_combined_filter(message, state, current_filters)
    else:
        await apply_single_filter(message, state, current_filters)


@router.message(F.text == "🔄 Комбинированный")
async def handle_combined_filter(message: Message, state: FSMContext):
    """Начать комбинированную фильтрацию"""
    await state.update_data(current_filters={}, filter_type="combined", combined_step=0)
    await continue_combined_filter(message, state, {})


async def continue_combined_filter(
    message: Message, state: FSMContext, current_filters: dict
):
    """Продолжить комбинированную фильтрацию"""
    data = await state.get_data()
    step = data.get("combined_step", 0)

    steps = [
        {"name": "приоритет", "handler": show_priority_options},
        {"name": "статус", "handler": show_status_options},
        {"name": "дату", "handler": show_date_options},
    ]

    if step < len(steps):
        current_step = steps[step]

        continue_text = (
            f"🔄 Комбинированная фильтрация\n\n"
            f"Текущие фильтры: {describe_filters(current_filters)}\n\n"
            f"Теперь выберите {current_step['name']}:"
        )

        await message.answer(continue_text)
        await current_step["handler"](message, state)

        await state.update_data(
            combined_step=step + 1,
            current_filters=current_filters,
            filter_type="combined",
        )
    else:
        filter_desc = describe_filters(current_filters)
        tasks_count = await count_filtered_tasks(message.from_user.id, current_filters)

        result_text = (
            f"🎯 Все фильтры применены: {filter_desc}\n"
            f"📊 Найдено задач: {tasks_count}\n\n"
            "Показать задачи?"
        )

        await message.answer(result_text, reply_markup=get_confirm_keyboard())
        await state.set_state(TaskFilter.waiting_for_confirmation)


@router.message(StateFilter(TaskFilter.waiting_for_confirmation))
async def process_filter_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения применения фильтра"""
    if await handle_navigation(message, state):
        return
    answer = message.text.lower().strip()

    if answer in ["✅ подтвердить", "да", "yes", "y", "д"]:
        data = await state.get_data()
        filters = data.get("current_filters", {})

        tasks = await db.get_filtered_tasks(message.from_user.id, filters)

        if not tasks:
            await message.answer(
                "❌ Задачи не найдены по выбранным фильтрам",
                reply_markup=get_tasks_keyboard(),
            )
        else:
            filter_desc = describe_filters(filters)
            await format_and_send_tasks(message, tasks, f"🎯 Задачи ({filter_desc})")

        await state.clear()

    elif answer in ["❌ отменить", "нет", "no", "n", "н"]:
        await message.answer(
            "❌ Фильтрация отменена", reply_markup=get_tasks_keyboard()
        )
        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, используйте кнопки для подтверждения:")


async def apply_single_filter(message: Message, state: FSMContext, filters: dict):
    """Применить одиночный фильтр и показать результат"""
    tasks_count = await count_filtered_tasks(message.from_user.id, filters)
    filter_desc = describe_filters(filters)

    if tasks_count == 0:
        await message.answer(
            f"❌ По фильтру '{filter_desc}' задач не найдено",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()
        return

    result_text = (
        f"🎯 Фильтр: {filter_desc}\n"
        f"📊 Найдено задач: {tasks_count}\n\n"
        "Показать задачи?"
    )

    await message.answer(result_text, reply_markup=get_confirm_keyboard())
    await state.set_state(TaskFilter.waiting_for_confirmation)


async def count_filtered_tasks(user_id: int, filters: dict) -> int:
    """Посчитать количество задач по фильтрам"""
    tasks = await db.get_filtered_tasks(user_id, filters)
    return len(tasks)


def describe_filters(filters: dict) -> str:
    """Описание примененных фильтров на русском"""
    if not filters:
        return "все задачи"

    descriptions = []

    priority_names = {
        "high": "🔴 высокий приоритет",
        "medium": "🟡 средний приоритет",
        "low": "🟢 низкий приоритет",
        None: "все приоритеты",
    }

    status_names = {
        "pending": "активные",
        "completed": "✅ выполненные",
        "deleted": "🗑️ удаленные",
    }

    date_names = {
        "today": "📅 сегодня",
        "tomorrow": "📅 завтра",
        "week": "📅 неделя",
        "overdue": "⚠️ просроченные",
    }

    if "priority" in filters:
        descriptions.append(
            priority_names.get(filters["priority"], filters["priority"])
        )

    if "status" in filters:
        descriptions.append(status_names.get(filters["status"], filters["status"]))

    if "tag" in filters:
        descriptions.append(f"🏷️ #{filters['tag']}")

    if "date" in filters:
        descriptions.append(date_names.get(filters["date"], filters["date"]))

    return ", ".join(descriptions) if descriptions else "все задачи"


async def show_priority_options(message: Message, state: FSMContext):
    """Показать опции приоритета для фильтрации"""
    priority_menu = (
        "🎯 Фильтр по приоритету\n\n"
        "Выберите приоритет:\n\n"
        "🔴 Высокий\n"
        "🟡 Средний\n"
        "🟢 Низкий\n"
        "📋 Все приоритеты\n"
    )

    await message.answer(priority_menu, reply_markup=get_priority_keyboard())
    await state.set_state(TaskFilter.waiting_for_priority)


async def show_status_options(message: Message, state: FSMContext):
    """Показать опции статуса для фильтрации"""
    status_menu = (
        "📊 Фильтр по статусу\n\n"
        "Выберите статус:\n\n"
        "✅ Выполненные\n"
        "📝 Активные\n"
        "🗑️ Удаленные\n"
        "📋 Все статусы\n"
    )

    await message.answer(status_menu, reply_markup=get_status_keyboard())
    await state.set_state(TaskFilter.waiting_for_status)


async def show_date_options(message: Message, state: FSMContext):
    """Показать опции даты для фильтрации"""
    date_menu = (
        "📅 Фильтр по дате\n\n"
        "Выберите период:\n\n"
        "📅 Сегодня\n"
        "📅 Завтра\n"
        "📅 Неделя\n"
        "⚠️ Просроченные\n"
        "📋 Все даты\n"
        "🔙 Назад к фильтрам"
    )

    await message.answer(date_menu, reply_markup=get_filter_date())
    await state.set_state(TaskFilter.waiting_for_date)


@router.message(F.text == "🏷️ Управление тегами")
async def handle_tags_main(message: Message):
    """Меню управления тегами"""
    await message.answer(
        "🏷️ Управление тегами\n\n" "Выберите действие:", reply_markup=get_tags_keyboard()
    )


@router.message(F.text == "🏷️ Создать тег")
@router.message(Command("newtag"))
async def cmd_new_tag(message: Message, state: FSMContext):
    """Создание нового тега"""
    await message.answer(
        "🏷️ Создание нового тега\n\n" "Введите название тега:",
        reply_markup=get_back_keyboard(),
    )
    await state.set_state(NewTagStates.waiting_for_tag_name)


@router.message(StateFilter(NewTagStates.waiting_for_tag_name))
async def process_new_tag_name(message: Message, state: FSMContext):
    """Обработка названия нового тега"""
    if await handle_navigation(message, state):
        return
    tag_name = message.text.strip()

    if not tag_name:
        await message.answer("❌ Название тега не может быть пустым! Попробуйте снова:")
        return

    try:
        tag_id = await db.create_tag(message.from_user.id, tag_name)
        await message.answer(
            f"✅ Тег #{tag_name} создан!", reply_markup=get_tags_keyboard()
        )
        await state.clear()
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при создании тега: {e}", reply_markup=get_tags_keyboard()
        )
        await state.clear()


@router.message(F.text == "📋 Список тегов")
@router.message(Command("tags"))
async def cmd_tags(message: Message):
    """Показать все теги пользователя"""
    tags = await db.get_user_tags(message.from_user.id)

    if not tags:
        await message.answer(
            "🏷️ У вас пока нет тегов.\n\n"
            "Создайте первый тег через меню управления тегами",
            reply_markup=get_tags_keyboard(),
        )
        return

    tags_text = "🏷️ Ваши теги:\n\n"
    for tag in tags:
        tag_id, name, color = tag
        tags_text += f"• {name}\n"

    await message.answer(tags_text, reply_markup=get_tags_keyboard())


@router.message(F.text == "➖ Удалить с задачи")
async def handle_remove_tag_from_task(message: Message, state: FSMContext):
    """Начать процесс удаления тега с задачи"""
    await message.answer(
        "➖ Удаление тега с задачи\n\n" "Введите ID задачи:",
        reply_markup=get_back_keyboard(),
    )
    await state.set_state(DelTagStates.waiting_for_task_id)


@router.message(StateFilter(DelTagStates.waiting_for_task_id))
async def process_remove_tag_task_id(message: Message, state: FSMContext):
    """Обработка ID задачи для удаления тега"""
    if await handle_navigation(message, state):
        return

    try:
        task_id = int(message.text)
        task = await db.get_task(task_id)

        if not task or task[1] != message.from_user.id:
            await message.answer(
                "❌ Задача не найдена или не принадлежит вам!",
                reply_markup=get_tags_keyboard(),
            )
            await state.clear()
            return

        task_tags = await db.get_task_tags(task_id)
        if not task_tags:
            await message.answer(
                "❌ У этой задачи нет тегов!", reply_markup=get_tags_keyboard()
            )
            await state.clear()
            return

        tags_text = "🏷️ Теги задачи:\n" + "\n".join(
            [f"• #{tag[1]}" for tag in task_tags]
        )
        await message.answer(
            f"{tags_text}\n\nВведите название тега для удаления:",
            reply_markup=get_back_keyboard(),
        )
        await state.update_data(deltag_task_id=task_id)
        await state.set_state(DelTagStates.waiting_for_tag_name)

    except ValueError:
        await message.answer("❌ Неверный формат ID! Введите число:")


@router.message(StateFilter(DelTagStates.waiting_for_tag_name))
async def process_remove_tag_name(message: Message, state: FSMContext):
    """Обработка названия тега для удаления"""
    if await handle_navigation(message, state):
        return

    tag_name = message.text.strip()
    if not tag_name:
        await message.answer("❌ Название тега не может быть пустым! Попробуйте снова:")
        return

    data = await state.get_data()
    task_id = data["deltag_task_id"]

    task_tags = await db.get_task_tags(task_id)
    tag_exists = any(tag[1].lower() == tag_name.lower() for tag in task_tags)

    if not tag_exists:
        await message.answer(
            f"❌ Тег '#{tag_name}' не найден у этой задачи!\n\n"
            f"Доступные теги:\n" + "\n".join([f"• #{tag[1]}" for tag in task_tags]),
            reply_markup=get_back_keyboard(),
        )
        return

    tag_id = None
    for tag in task_tags:
        if tag[1].lower() == tag_name.lower():
            tag_id = tag[0]
            break

    if not tag_id:
        await message.answer(
            "❌ Ошибка при поиске тега!", reply_markup=get_tags_keyboard()
        )
        await state.clear()
        return

    await state.update_data(deltag_tag_id=tag_id, deltag_tag_name=tag_name)

    task = await db.get_task(task_id)
    task_content = task[2] if len(task) > 2 else "Неизвестная задача"

    confirm_text = (
        f"➖ Удалить тег с задачи?\n\n"
        f"📝 Задача #{task_id}: {task_content}\n"
        f"🏷️ Тег: #{tag_name}\n\n"
        f"Подтвердите удаление:"
    )

    await message.answer(confirm_text, reply_markup=get_confirm_keyboard())
    await state.set_state(DelTagStates.waiting_for_confirmation)


@router.message(StateFilter(DelTagStates.waiting_for_confirmation))
async def process_remove_tag_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения удаления тега с задачи"""
    if await handle_navigation(message, state):
        return

    answer = message.text.lower().strip()

    if answer in ["✅ подтвердить", "да", "yes", "y", "д"]:
        data = await state.get_data()
        task_id = data["deltag_task_id"]
        tag_id = data["deltag_tag_id"]
        tag_name = data["deltag_tag_name"]

        try:
            await db.remove_tag_from_task(task_id, tag_id)
            await message.answer(
                f"✅ Тег '#{tag_name}' удален с задачи #{task_id}!",
                reply_markup=get_tags_keyboard(),
            )
        except Exception as e:
            await message.answer(
                f"❌ Ошибка при удалении тега: {e}", reply_markup=get_tags_keyboard()
            )

        await state.clear()

    elif answer in ["❌ отменить", "нет", "no", "n", "н"]:
        await message.answer(
            "❌ Удаление тега отменено", reply_markup=get_tags_keyboard()
        )
        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, используйте кнопки для подтверждения:")


@router.message(F.text == "🗑️ Удалить тег полностью")
async def handle_delete_tag_completely(message: Message, state: FSMContext):
    """Начать процесс полного удаления тега"""
    user_tags = await db.get_user_tags(message.from_user.id)

    if not user_tags:
        await message.answer(
            "🏷️ У вас пока нет тегов для удаления.", reply_markup=get_tags_keyboard()
        )
        return

    tags_text = "🏷️ Ваши теги:\n" + "\n".join([f"• #{tag[1]}" for tag in user_tags])
    await message.answer(
        f"{tags_text}\n\nВведите название тега для полного удаления:",
        reply_markup=get_back_keyboard(),
    )
    await state.set_state(RemoveTagStates.waiting_for_tag_name)


@router.message(StateFilter(RemoveTagStates.waiting_for_tag_name))
async def process_delete_tag_name(message: Message, state: FSMContext):
    """Обработка названия тега для полного удаления"""
    if await handle_navigation(message, state):
        return

    tag_name = message.text.strip()
    if not tag_name:
        await message.answer("❌ Название тега не может быть пустым! Попробуйте снова:")
        return

    user_tags = await db.get_user_tags(message.from_user.id)
    tag_exists = any(tag[1].lower() == tag_name.lower() for tag in user_tags)

    if not tag_exists:
        tags_list = (
            ", ".join([f"#{tag[1]}" for tag in user_tags]) if user_tags else "нет тегов"
        )
        await message.answer(
            f"❌ Тег '#{tag_name}' не найден!\n\n"
            f"Ваши теги: {tags_list}\n\n"
            "Введите существующий тег:",
            reply_markup=get_back_keyboard(),
        )
        return

    tag_id = None
    for tag in user_tags:
        if tag[1].lower() == tag_name.lower():
            tag_id = tag[0]
            break

    if not tag_id:
        await message.answer(
            "❌ Ошибка при поиске тега!", reply_markup=get_tags_keyboard()
        )
        await state.clear()
        return

    tasks_with_tag = await db.get_tasks_by_tag(message.from_user.id, tag_name)

    await state.update_data(
        remove_tag_id=tag_id, remove_tag_name=tag_name, tasks_count=len(tasks_with_tag)
    )

    confirm_text = (
        f"🗑️ Полное удаление тега\n\n"
        f"🏷️ Тег: #{tag_name}\n"
        f"📊 Используется в {len(tasks_with_tag)} задачах\n\n"
        f"⚠️ Внимание: Тег будет полностью удален из системы!\n"
        f"Он пропадет из всех задач, где используется.\n\n"
        f"Подтвердите удаление:"
    )

    await message.answer(confirm_text, reply_markup=get_confirm_keyboard())
    await state.set_state(RemoveTagStates.waiting_for_confirmation)


@router.message(StateFilter(RemoveTagStates.waiting_for_confirmation))
async def process_delete_tag_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения полного удаления тега"""
    if await handle_navigation(message, state):
        return

    answer = message.text.lower().strip()

    if answer in ["✅ подтвердить", "да", "yes", "y", "д"]:
        data = await state.get_data()
        tag_id = data["remove_tag_id"]
        tag_name = data["remove_tag_name"]
        tasks_count = data["tasks_count"]

        try:
            await db.delete_tag(tag_id)

            result_text = f"✅ Тег '#{tag_name}' полностью удален!"
            if tasks_count > 0:
                result_text += f"\n🗑️ Удален из {tasks_count} задач"

            await message.answer(result_text, reply_markup=get_tags_keyboard())

        except Exception as e:
            await message.answer(
                f"❌ Ошибка при удалении тега: {e}", reply_markup=get_tags_keyboard()
            )

        await state.clear()

    elif answer in ["❌ отменить", "нет", "no", "n", "н"]:
        await message.answer(
            "❌ Удаление тега отменено", reply_markup=get_tags_keyboard()
        )
        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, используйте кнопки для подтверждения:")


async def handle_tag_navigation(message: Message, state: FSMContext):
    """Обработка навигации в меню тегов"""
    if message.text == "🔙 Назад":
        await handle_tags_main(message)
        await state.clear()
        return True
    elif message.text == "🔙 Назад к задачам":
        await handle_tasks_main(message)
        await state.clear()
        return True
    elif message.text == "❌ Отмена":
        await handle_tags_main(message)
        await state.clear()
        return True
    return False


@router.message(StateFilter(NewTagStates.waiting_for_tag_name))
async def process_new_tag_name(message: Message, state: FSMContext):
    """Обработка названия нового тега"""
    if await handle_tag_navigation(message, state):
        return

    tag_name = message.text.strip()

    if not tag_name:
        await message.answer("❌ Название тега не может быть пустым! Попробуйте снова:")
        return

    try:
        tag_id = await db.create_tag(message.from_user.id, tag_name)
        await message.answer(
            f"✅ Тег '{tag_name}' создан!", reply_markup=get_tags_keyboard()
        )
        await state.clear()
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при создании тега: {e}", reply_markup=get_tags_keyboard()
        )
        await state.clear()


@router.message(StateFilter(AddTagStates.waiting_for_task_id))
async def process_addtag_task_id(message: Message, state: FSMContext):
    """Обработка ID задачи для добавления тега"""
    if await handle_tag_navigation(message, state):
        return

    try:
        task_id = int(message.text)
        await state.update_data(addtag_task_id=task_id)

        task = await db.get_task(task_id)
        if not task or task[1] != message.from_user.id:
            await message.answer(
                "❌ Задача не найдена или не принадлежит вам!",
                reply_markup=get_tags_keyboard(),
            )
            await state.clear()
            return

        await message.answer(
            f"➕ Добавление тега к задаче #{task_id}\n\n" "Введите название тега:",
            reply_markup=get_back_keyboard(),
        )
        await state.set_state(AddTagStates.waiting_for_tag_name)

    except ValueError:
        await message.answer(
            "❌ Неверный формат ID! Введите число:", reply_markup=get_back_keyboard()
        )


@router.message(F.text == "🔙 Назад")
async def handle_back(message: Message, state: FSMContext):
    """Обработка кнопки Назад"""
    current_state = await state.get_state()

    if current_state:
        await handle_tasks_main(message)
        await state.clear()
    else:
        await message.answer("🏠 Главное меню", reply_markup=get_main_keyboard())


@router.message(F.text == "🔙 Назад к задачам")
async def handle_back_to_tasks(message: Message):
    """Вернуться к меню задач"""
    await handle_tasks_main(message)


@router.message(F.text == "🔙 Назад в меню")
async def handle_back_to_main(message: Message):
    """Вернуться в главное меню"""
    await message.answer("🏠 Главное меню", reply_markup=get_main_keyboard())


@router.message(Command("cleanup"))
async def cmd_cleanup(message: Message):
    """Очистка старых данных"""
    await message.answer(
        "🧹 Очистка старых данных\n\n" "Эта функция доступна через команду /cleanup",
        reply_markup=get_tasks_keyboard(),
    )


@router.message(Command("storage"))
async def cmd_storage(message: Message):
    """Информация о настройках хранения данных"""
    storage_info = (
        "📊 Настройки хранения данных:\n\n"
        "✅ Активные задачи: бессрочно\n"
        "✅ Выполненные задачи: 30 дней\n"
        "🗑️ Удаленные задачи: 30 дней\n"
        "😊 Записи настроения: 90 дней\n\n"
        "⚙️ Команды:\n"
        "/cleanup - очистка вручную\n"
        "/storage_info - статистика хранилища"
    )
    await message.answer(storage_info, reply_markup=get_tasks_keyboard())


@router.message(F.text == "➕ Добавить к задаче")
@router.message(Command("addtag"))
async def cmd_add_tag(message: Message, state: FSMContext):
    """Начать процесс добавления тега к задаче"""
    await message.answer(
        "➕ Добавление тега к задаче\n\n" "Введите ID задачи:",
        reply_markup=get_back_keyboard(),
    )
    await state.set_state(AddTagStates.waiting_for_task_id)


@router.message(StateFilter(AddTagStates.waiting_for_task_id))
async def process_addtag_task_id(message: Message, state: FSMContext):
    """Обработка ID задачи для добавления тега"""

    try:
        task_id = int(message.text)
        await state.update_data(addtag_task_id=task_id)

        task = await db.get_task(task_id)
        if not task or task[1] != message.from_user.id:
            await message.answer(
                "❌ Задача не найдена или не принадлежит вам!",
                reply_markup=get_tags_keyboard(),
            )
            await state.clear()
            return

        await message.answer(
            f"➕ Добавление тега к задаче #{task_id}\n\n" "Введите название тега:",
            reply_markup=get_back_keyboard(),
        )
        await state.set_state(AddTagStates.waiting_for_tag_name)

    except ValueError:
        await message.answer(
            "❌ Неверный формат ID! Введите число:", reply_markup=get_back_keyboard()
        )


@router.message(StateFilter(AddTagStates.waiting_for_tag_name))
async def process_addtag_tag_name(message: Message, state: FSMContext):
    """Обработка названия тега"""
    if await handle_navigation(message, state):
        return
    tag_name = message.text.strip()

    if not tag_name:
        await message.answer(
            "❌ Название тега не может быть пустым! Попробуйте снова:",
            reply_markup=get_back_keyboard(),
        )
        return

    data = await state.get_data()
    task_id = data["addtag_task_id"]
    await process_add_tag_complete(message, state, task_id, tag_name)


async def process_add_tag_complete(
    message: Message, state: FSMContext, task_id: int, tag_name: str
):
    """Завершение процесса добавления тега"""
    try:
        task = await db.get_task(task_id)
        if not task or task[1] != message.from_user.id:
            await message.answer("❌ Задача не найдена или не принадлежит вам!")
            await state.clear()
            return

        tag_id = await db.create_tag(message.from_user.id, tag_name)

        if not tag_id:
            await message.answer("❌ Ошибка при создании тега!")
            await state.clear()
            return

        existing_tags = await db.get_task_tags(task_id)
        if any(tag[1].lower() == tag_name.lower() for tag in existing_tags):
            await message.answer(
                f"✅ Тег '{tag_name}' уже добавлен к задаче #{task_id}!"
            )
            await state.clear()
            return

        task_content = task[2]
        if len(task_content) > 40:
            task_content = task_content[:40] + "..."

        confirm_text = (
            f"🏷️ Добавить тег к задаче?\n\n"
            f"📝 Задача #{task_id}: {task_content}\n"
            f"🏷️ Тег: #{tag_name}\n\n"
            f"Подтвердите добавление (да/нет):"
        )

        await state.update_data(
            addtag_task_id=task_id, addtag_tag_name=tag_name, addtag_tag_id=tag_id
        )
        await message.answer(confirm_text, reply_markup=get_confirm_keyboard())
        await state.set_state(AddTagStates.waiting_for_confirmation)

    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении тега: {e}")
        await state.clear()


@router.message(StateFilter(AddTagStates.waiting_for_confirmation))
async def process_addtag_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения добавления тега"""
    if await handle_navigation(message, state):
        return
    answer = message.text.lower().strip()

    if answer in ["✅ подтвердить", "да", "yes", "y", "д"]:
        data = await state.get_data()
        task_id = data["addtag_task_id"]
        tag_name = data["addtag_tag_name"]
        tag_id = data["addtag_tag_id"]

        await db.add_tag_to_task(task_id, tag_id)
        await message.answer(
            f"✅ Тег '{tag_name}' добавлен к задаче #{task_id}!",
            reply_markup=get_tags_keyboard(),
        )
        await state.clear()

    elif answer in ["❌ отменить", "нет", "no", "n", "н"]:
        await message.answer(
            "❌ Добавление тега отменено", reply_markup=get_tags_keyboard()
        )
        await state.clear()
    else:
        await message.answer("❌ Пожалуйста, используйте кнопки для подтверждения:")


@router.message(F.text == "🔄 Комбинированный")
async def handle_combined_filter(message: Message, state: FSMContext):
    """Начать комбинированную фильтрацию"""
    await state.update_data(current_filters={}, filter_type="combined", combined_step=0)
    await continue_combined_filter(message, state, {})


async def continue_combined_filter(
    message: Message, state: FSMContext, current_filters: dict
):
    """Продолжить комбинированную фильтрацию"""
    data = await state.get_data()
    step = data.get("combined_step", 0)

    steps = [
        {"name": "приоритет", "handler": show_priority_options},
        {"name": "статус", "handler": show_status_options},
        {"name": "дату", "handler": show_date_options},
    ]

    if step < len(steps):
        current_step = steps[step]

        continue_text = (
            f"🔄 Комбинированная фильтрация\n\n"
            f"Текущие фильтры: {describe_filters(current_filters)}\n\n"
            f"Теперь выберите {current_step['name']}:"
        )

        await message.answer(continue_text)
        await current_step["handler"](message, state)

        await state.update_data(
            combined_step=step + 1,
            current_filters=current_filters,
            filter_type="combined",
        )
    else:
        filter_desc = describe_filters(current_filters)
        tasks_count = await count_filtered_tasks(message.from_user.id, current_filters)

        result_text = (
            f"🎯 Все фильтры применены: {filter_desc}\n"
            f"📊 Найдено задач: {tasks_count}\n\n"
            "Показать задачи?"
        )

        await message.answer(result_text, reply_markup=get_confirm_keyboard())
        await state.set_state(TaskFilter.waiting_for_confirmation)


@router.message(F.text.in_(["срочные", "urgent", "горящие"]))
async def handle_urgent_keywords(message: Message):
    """Обработка ключевых слов для срочных задач"""
    await cmd_urgent(message)


@router.message(F.text.in_(["ближайшие", "upcoming", "скоро"]))
async def handle_upcoming_keywords(message: Message):
    """Обработка ключевых слов для ближайших задач"""
    await cmd_upcoming(message)


@router.message(F.text.in_(["просроченные", "overdue"]))
async def handle_overdue_keywords(message: Message):
    """Обработка ключевых слов для просроченных задач"""
    await cmd_overdue(message)


@router.message(F.text == "🔔 Уведомления")
async def handle_notifications_button(message: Message):
    """Обработка кнопки уведомлений из главного меню"""
    await cmd_reminders(message)


@router.message(Command("reminders"))
async def cmd_reminders(message: Message, state: FSMContext = None):
    """Меню управления напоминаниями с клавиатурой"""
    settings = await db.get_reminder_settings(message.from_user.id)

    settings_text = (
        "🔔 <b>Управление напоминаниями</b>\n\n"
        f"✅ Напоминания о дедлайнах: {'ВКЛ' if settings[1] else 'ВЫКЛ'}\n"
        f"⏰ Часов до дедлайна: {settings[2]}\n"
        f"⚠️ Напоминания о просрочке: {'ВКЛ' if settings[3] else 'ВЫКЛ'}\n\n"
        "Выберите действие:"
    )

    await message.answer(
        settings_text, parse_mode="HTML", reply_markup=get_notifications_keyboard()
    )


@router.message(F.text == "🔔 Настройка напоминаний")
async def handle_reminder_settings_button(message: Message, state: FSMContext):
    """Обработка кнопки настройки напоминаний"""
    settings = await db.get_reminder_settings(message.from_user.id)

    settings_text = (
        "🔔 <b>Настройка напоминаний</b>\n\n"
        f"Текущий статус:\n"
        f"• Напоминания: {'✅ ВКЛ' if settings[1] else '🔇 ВЫКЛ'}\n"
        f"• Просрочка: {'⚠️ ВКЛ' if settings[3] else '🔕 ВЫКЛ'}\n"
        f"• Часов до дедлайна: {settings[2]}\n\n"
        "Выберите настройку для изменения:"
    )

    await message.answer(
        settings_text, parse_mode="HTML", reply_markup=get_reminder_settings_keyboard()
    )
    await state.set_state(ReminderSettings.waiting_for_settings_choice)


@router.message(F.text == "⏰ Время уведомлений")
async def handle_notification_time_button(message: Message, state: FSMContext):
    """Обработка кнопки настройки времени уведомлений"""
    settings = await db.get_reminder_settings(message.from_user.id)
    daily_time = settings[4] if len(settings) > 4 else "09:00"

    await message.answer(
        f"⏰ <b>Настройка времени ежедневных уведомлений</b>\n\n"
        f"Текущее время: <b>{daily_time}</b>\n\n"
        f"Введите новое время в формате ЧЧ:ММ (например, 09:00 или 18:30):\n\n"
        f"💡 <i>Уведомления приходят раз в день в указанное время</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(DailyReminderSettings.waiting_for_daily_time)


@router.message(F.text == "📱 Типы уведомлений")
async def handle_notification_types_button(message: Message):
    """Обработка кнопки типов уведомлений"""
    settings = await db.get_reminder_settings(message.from_user.id)

    types_text = (
        "📱 <b>Типы уведомлений</b>\n\n"
        "Доступные типы напоминаний:\n\n"
        "🔔 <b>Напоминания о дедлайнах</b>\n"
        f"• Статус: {'✅ ВКЛ' if settings[1] else '🔇 ВЫКЛ'}\n"
        f"• За сколько часов: {settings[2]} ч\n"
        "• Присылаются перед сроком выполнения задачи\n\n"
        "⚠️ <b>Напоминания о просрочке</b>\n"
        f"• Статус: {'✅ ВКЛ' if settings[3] else '🔇 ВЫКЛ'}\n"
        "• Присылаются для просроченных задач\n\n"
        "🌅 <b>Ежедневные уведомления</b>\n"
        "• Сводка по просроченным задачам\n"
        "• Приходят один раз в день\n\n"
        "⚙️ Для изменения настроек используйте кнопки ниже:"
    )

    await message.answer(
        types_text, parse_mode="HTML", reply_markup=get_reminder_settings_keyboard()
    )


@router.message(F.text == "🔕 Отключить все")
async def handle_disable_all_button(message: Message):
    """Обработка кнопки отключения всех уведомлений"""
    await db.update_reminder_settings(
        message.from_user.id, enable_reminders=0, enable_overdue_reminders=0
    )
    await message.answer(
        "🔇 <b>Все напоминания отключены!</b>\n\n"
        "Вы больше не будете получать:\n"
        "• Напоминания о дедлайнах\n"
        "• Уведомления о просрочке\n"
        "• Ежедневные сводки\n\n"
        "Чтобы включить обратно, используйте кнопку '🔔 Включить все'",
        parse_mode="HTML",
        reply_markup=get_notifications_keyboard(),
    )


@router.message(F.text == "🔔 Включить все")
async def handle_enable_all_button(message: Message):
    """Обработка кнопки включения всех уведомлений"""
    await db.update_reminder_settings(
        message.from_user.id, enable_reminders=1, enable_overdue_reminders=1
    )
    await message.answer(
        "✅ <b>Все напоминания включены!</b>\n\n"
        "Теперь вы будете получать:\n"
        "• Напоминания о дедлайнах\n"
        "• Уведомления о просрочке\n"
        "• Ежедневные сводки\n\n"
        "Настройте параметры с помощью кнопок ниже:",
        parse_mode="HTML",
        reply_markup=get_notifications_keyboard(),
    )


@router.message(F.text == "📊 Статус уведомлений")
async def handle_notification_status_button(message: Message):
    """Обработка кнопки статуса уведомлений"""
    await cmd_reminder_settings(message)


@router.message(F.text == "✅ Напоминания ВКЛ")
async def handle_reminders_on_button(message: Message):
    """Включение напоминаний о дедлайнах"""
    await db.update_reminder_settings(message.from_user.id, enable_reminders=1)
    await message.answer(
        "✅ <b>Напоминания о дедлайнах включены!</b>\n\n"
        "Вы будете получать уведомления за установленное количество часов до срока выполнения задач.",
        parse_mode="HTML",
        reply_markup=get_reminder_settings_keyboard(),
    )


@router.message(F.text == "🔇 Напоминания ВЫКЛ")
async def handle_reminders_off_button(message: Message):
    """Выключение напоминаний о дедлайнах"""
    await db.update_reminder_settings(message.from_user.id, enable_reminders=0)
    await message.answer(
        "🔇 <b>Напоминания о дедлайнах выключены!</b>\n\n"
        "Вы не будете получать уведомления о приближающихся дедлайнах.",
        parse_mode="HTML",
        reply_markup=get_reminder_settings_keyboard(),
    )


@router.message(F.text == "⚠️ Просрочка ВКЛ")
async def handle_overdue_on_button(message: Message):
    """Включение напоминаний о просрочке"""
    await db.update_reminder_settings(message.from_user.id, enable_overdue_reminders=1)
    await message.answer(
        "⚠️ <b>Напоминания о просрочке включены!</b>\n\n"
        "Вы будете получать уведомления о просроченных задачах.",
        parse_mode="HTML",
        reply_markup=get_reminder_settings_keyboard(),
    )


@router.message(F.text == "🔕 Просрочка ВЫКЛ")
async def handle_overdue_off_button(message: Message):
    """Выключение напоминаний о просрочке"""
    await db.update_reminder_settings(message.from_user.id, enable_overdue_reminders=0)
    await message.answer(
        "🔕 <b>Напоминания о просрочке выключены!</b>\n\n"
        "Вы не будете получать уведомления о просроченных задачах.",
        parse_mode="HTML",
        reply_markup=get_reminder_settings_keyboard(),
    )


@router.message(F.text == "⏰ Изменить время")
async def handle_change_time_button(message: Message, state: FSMContext):
    """Обработка кнопки изменения времени напоминаний"""
    settings = await db.get_reminder_settings(message.from_user.id)
    current_hours = settings[2]

    await message.answer(
        f"⏰ <b>Изменение времени напоминаний</b>\n\n"
        f"Текущее значение: <b>{current_hours} часов</b> до дедлайна\n\n"
        f"Введите новое количество часов (от 1 до 24):\n\n"
        f"💡 <i>Рекомендуется устанавливать 1-3 часа для своевременных напоминаний</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(ReminderSettings.waiting_for_reminder_hours)


@router.message(StateFilter(ReminderSettings.waiting_for_reminder_hours))
async def process_reminder_hours(message: Message, state: FSMContext):
    """Обработка ввода часов для напоминаний"""
    if await handle_navigation(message, state):
        return
    try:
        hours = int(message.text.strip())

        if hours < 1 or hours > 24:
            await message.answer(
                "❌ Число должно быть от 1 до 24! Попробуйте снова:",
                reply_markup=get_cancel_keyboard(),
            )
            return

        await db.update_reminder_settings(
            message.from_user.id, reminder_before_hours=hours
        )
        await message.answer(
            f"✅ <b>Время напоминаний обновлено!</b>\n\n"
            f"Теперь напоминания будут приходить за <b>{hours} ч</b> до дедлайна.",
            parse_mode="HTML",
            reply_markup=get_reminder_settings_keyboard(),
        )
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Неверный формат! Введите число от 1 до 24:",
            reply_markup=get_cancel_keyboard(),
        )


@router.message(StateFilter(DailyReminderSettings.waiting_for_daily_time))
async def process_daily_reminder_time(message: Message, state: FSMContext):
    """Обработка ввода времени ежедневных уведомлений"""
    if await handle_navigation(message, state):
        return
    time_input = message.text.strip()

    try:
        datetime.strptime(time_input, "%H:%M")

        await db.update_reminder_settings_with_time(
            message.from_user.id, daily_overdue_time=time_input
        )

        await message.answer(
            f"✅ <b>Время ежедневных уведомлений установлено!</b>\n\n"
            f"Теперь вы будете получать уведомления о просроченных задачах "
            f"каждый день в <b>{time_input}</b>",
            parse_mode="HTML",
            reply_markup=get_notifications_keyboard(),
        )
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Неверный формат времени!\n\n"
            "Введите время в формате ЧЧ:ММ (например, 09:00 или 18:30):",
            reply_markup=get_cancel_keyboard(),
        )


@router.message(F.text == "🔙 Назад к уведомлениям")
async def handle_back_to_notifications(message: Message):
    """Возврат к меню уведомлений"""
    await cmd_reminders(message)


@router.message(F.text == "🔙 Назад в меню")
async def handle_back_to_main_menu(message: Message):
    """Возврат в главное меню"""
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())


@router.message(Command("reminder_settings"))
async def cmd_reminder_settings(message: Message):
    """Показывает текущие настройки напоминаний"""
    settings = await db.get_reminder_settings(message.from_user.id)

    daily_time = settings[4] if len(settings) > 4 else "09:00"

    settings_text = (
        "🔔 <b>Текущие настройки напоминаний</b>\n\n"
        f"✅ Напоминания о дедлайнах: {'ВКЛ' if settings[1] else 'ВЫКЛ'}\n"
        f"⏰ Часов до дедлайна: {settings[2]}\n"
        f"⚠️ Напоминания о просрочке: {'ВКЛ' if settings[3] else 'ВЫКЛ'}\n"
        f"🌅 Время ежедневных уведомлений: <b>{daily_time}</b>\n\n"
        "Для изменения настроек используйте меню уведомлений:"
    )

    await message.answer(
        settings_text, parse_mode="HTML", reply_markup=get_notifications_keyboard()
    )


@router.message(Command("overdue"))
async def cmd_overdue(message: Message):
    """Показывает просроченные задачи - УПРОЩЕННАЯ ВЕРСИЯ"""
    try:
        user_id = message.from_user.id
        overdue_tasks = await db.get_overdue_tasks(user_id)

        if not overdue_tasks:
            await message.answer(
                "🎉 У вас нет просроченных задач!",
                reply_markup=get_quick_actions_keyboard(),
            )
            return

        tasks_text = "⚠️ <b>Просроченные задачи:</b>\n\n"

        for task in overdue_tasks:
            task_data = extract_task_data(task)
            if not task_data:
                continue

            task_id, content, due_date, priority, status, is_deleted = task_data

            due_datetime = datetime.fromisoformat(due_date)
            overdue_time = datetime.now() - due_datetime
            overdue_days = overdue_time.days

            priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}

            display_content = content
            if len(display_content) > 35:
                display_content = display_content[:35] + "..."

            tasks_text += f"{priority_icons.get(priority, '🟡')} <b>#{task_id}</b> - {display_content}\n"
            tasks_text += f"   📅 Был срок: {due_datetime.strftime('%d.%m.%Y %H:%M')}\n"

            if overdue_days == 1:
                tasks_text += f"   ⏰ Просрочена: 1 день\n\n"
            elif overdue_days > 0:
                tasks_text += f"   ⏰ Просрочена: {overdue_days} дней\n\n"
            else:
                tasks_text += f"   ⏰ Просрочена: {int(overdue_time.total_seconds() / 3600)} часов\n\n"

        stats = await db.get_overdue_tasks_stats(user_id)
        tasks_text += f"📊 Всего просроченных задач: <b>{stats['total_overdue']}</b>"

        await message.answer(
            tasks_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка при получении просроченных задач: {e}")


@router.message(Command("upcoming"))
async def cmd_upcoming(message: Message):
    """Показывает задачи с приближающимися сроками"""
    try:
        user_id = message.from_user.id
        today_tasks = await db.get_today_tasks(user_id)
        urgent_tasks = await db.get_urgent_tasks(user_id)
        soon_tasks = [task for task in urgent_tasks if task not in today_tasks]

        tasks_text = "⏰ <b>Задачи с приближающимися сроками</b>\n\n"

        if today_tasks:
            tasks_text += f"🔥 <b>СЕГОДНЯ</b> ({len(today_tasks)}):\n"
            for task in today_tasks[:3]:
                task_data = extract_task_data(task)
                if task_data:
                    task_id, content, due_date, priority, status, is_deleted = task_data
                    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                        priority, "🟡"
                    )

                    display_content = (
                        content[:35] + "..." if len(content) > 35 else content
                    )
                    tasks_text += (
                        f"{priority_icon} <b>#{task_id}</b> {display_content}\n"
                    )
            tasks_text += "\n"

        if soon_tasks:
            tasks_text += f"🔔 <b>СКОРО</b> ({len(soon_tasks)}):\n"
            for task in soon_tasks[:3]:
                task_data = extract_task_data(task)
                if task_data:
                    task_id, content, due_date, priority, status, is_deleted = task_data
                    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                        priority, "🟡"
                    )

                    display_content = (
                        content[:35] + "..." if len(content) > 35 else content
                    )
                    due_datetime = datetime.fromisoformat(due_date.replace(" ", "T"))
                    time_left = due_datetime - datetime.now()

                    if time_left.days > 0:
                        time_text = f"через {time_left.days} дн"
                    else:
                        hours_left = time_left.seconds // 3600
                        time_text = f"через {hours_left} ч"

                    tasks_text += (
                        f"{priority_icon} <b>#{task_id}</b> {display_content}\n"
                    )
                    tasks_text += f"   📅 {time_text}\n"
            tasks_text += "\n"

        if not today_tasks and not soon_tasks:
            tasks_text += "🎉 Нет задач с приближающимися сроками!\n\n"
            tasks_text += "💡 Создайте новые задачи с дедлайнами"

        await message.answer(
            tasks_text, parse_mode="HTML", reply_markup=get_quick_actions_keyboard()
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка при получении задач: {e}")


@router.message(F.text.in_(["срочные", "urgent", "горящие"]))
async def handle_urgent_keywords(message: Message):
    """Обработка ключевых слов для срочных задач"""
    await cmd_overdue(message)


@router.message(F.text.in_(["ближайшие", "upcoming", "скоро"]))
async def handle_upcoming_keywords(message: Message):
    """Обработка ключевых слов для ближайших задач"""
    await cmd_upcoming(message)


@router.message(F.text == "📊 Группировка задач")
@router.message(Command("group"))
async def cmd_group(message: Message, state: FSMContext):
    """Меню группировки задач"""
    group_menu = (
        "📊 <b>ГРУППИРОВКА ЗАДАЧ</b>\n\n"
        "🎯 <b>Сгруппируйте задачи для лучшего обзора:</b>\n\n"
        "🏷️  <b>По тегам</b> - группировка тегам\n"
        "🎯 <b>По приоритетам</b> - по уровню важности и срочности\n"
        "📅 <b>По датам</b> - хронологический порядок выполнения\n"
        "📊 <b>По статусу</b> - активные, выполненные, удаленные\n"
        "🔄 <b>Комбинированная</b> - несколько критериев сразу\n"
        "📋 <b>Все задачи</b> - полный обзор без группировки\n\n"
    )

    await message.answer(
        group_menu, parse_mode="HTML", reply_markup=get_grouping_keyboard()
    )
    await state.set_state(TaskGrouping.waiting_for_group_type)


@router.message(StateFilter(TaskGrouping.waiting_for_group_type))
async def process_group_type(message: Message, state: FSMContext):
    """Обработка выбора типа группировки"""
    if await handle_navigation(message, state):
        return

    if message.text == "🏷️ По тегам":
        await group_by_tags(message, state)

    elif message.text == "🎯 По приоритетам":
        await message.answer(
            "🎯 Выберите приоритет для группировки:",
            parse_mode="HTML",
            reply_markup=get_grouping_priority_keyboard(),
        )
        await state.set_state(TaskGrouping.waiting_for_specific_choice)
        await state.update_data(group_type="priority")

    elif message.text == "📅 По датам":
        await message.answer(
            "📅 Выберите период для группировки:",
            parse_mode="HTML",
            reply_markup=get_grouping_period_keyboard(),
        )
        await state.set_state(TaskGrouping.waiting_for_specific_choice)
        await state.update_data(group_type="date")

    elif message.text == "📊 По статусу":
        await message.answer(
            "📊 Выберите статус для группировки:",
            parse_mode="HTML",
            reply_markup=get_grouping_status_keyboard(),
        )
        await state.set_state(TaskGrouping.waiting_for_specific_choice)
        await state.update_data(group_type="status")

    elif message.text == "🔄 Комбинированная":
        await message.answer(
            "🔄 <b>Выберите тип комбинированной группировки:</b>",
            parse_mode="HTML",
            reply_markup=get_grouping_combined_keyboard(),
        )
        await state.set_state(TaskGrouping.waiting_for_specific_choice)
        await state.update_data(group_type="combined")

    elif message.text == "📋 Все задачи":
        await show_all_tasks(message)
        await state.clear()
    else:
        await message.answer(
            "❌ Пожалуйста, выберите тип группировки из меню:",
            reply_markup=get_tasks_keyboard(),
        )


async def group_by_tags(message: Message, state: FSMContext):
    """Группировка задач по тегам"""
    user_id = message.from_user.id
    tasks = await db.get_user_tasks_with_priority(user_id, "pending")

    if not tasks:
        await message.answer(
            "🎉 Нет активных задач для группировки!",
            reply_markup=get_tasks_keyboard(),
        )
        return

    tasks_by_tag = {}
    tasks_without_tags = []

    for task in tasks:
        task_data = extract_task_data(task)
        if not task_data:
            continue

        task_id, content, due_date, priority, status, is_deleted = task_data
        task_tags = await db.get_task_tags(task_id)

        if task_tags:
            for tag in task_tags:
                tag_name = tag[1]
                if tag_name not in tasks_by_tag:
                    tasks_by_tag[tag_name] = []
                tasks_by_tag[tag_name].append(task)
        else:
            tasks_without_tags.append(task)

    grouped_text = "🏷️ <b>ГРУППИРОВКА ПО ТЕГАМ</b> 🏷️\n\n"

    if tasks_by_tag:
        for tag_name, tag_tasks in tasks_by_tag.items():
            grouped_text += f"🔸 <b>#{tag_name}</b> ({len(tag_tasks)} задач):\n"
            for task in tag_tasks[:5]:
                task_data = extract_task_data(task)
                if task_data:
                    task_id, content, due_date, priority, status, is_deleted = task_data
                    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                        priority, "🟡"
                    )
                    due_text = format_due_date(due_date)

                    display_content = content
                    if len(display_content) > 30:
                        display_content = display_content[:30] + "..."

                    grouped_text += f"   {priority_icon} #{task_id} {display_content}\n"
                    grouped_text += f"      {due_text}\n"

            if len(tag_tasks) > 5:
                grouped_text += f"   ... и еще {len(tag_tasks) - 5} задач\n"
            grouped_text += "\n"

    if tasks_without_tags:
        grouped_text += f"🔸 <b>Без тегов</b> ({len(tasks_without_tags)} задач):\n"
        for task in tasks_without_tags[:5]:
            task_data = extract_task_data(task)
            if task_data:
                task_id, content, due_date, priority, status, is_deleted = task_data
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    priority, "🟡"
                )
                due_text = format_due_date(due_date)

                display_content = content
                if len(display_content) > 30:
                    display_content = display_content[:30] + "..."

                grouped_text += f"   {priority_icon} #{task_id} {display_content}\n"
                grouped_text += f"      {due_text}\n"

        if len(tasks_without_tags) > 5:
            grouped_text += f"   ... и еще {len(tasks_without_tags) - 5} задач\n"

    grouped_text += (
        f"\n📊 <b>Итого:</b> {len(tasks)} задач в {len(tasks_by_tag)} категориях"
    )

    await message.answer(
        grouped_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
    )
    await state.clear()


async def group_by_priority(message: Message, state: FSMContext):
    """Группировка задач по приоритетам"""
    user_id = message.from_user.id

    try:
        priority_stats = await db.get_tasks_grouped_by_priority_detailed(user_id)

        if not priority_stats:
            await message.answer(
                "🎉 Нет активных задач для группировки!",
                reply_markup=get_tasks_keyboard(),
            )
            return

        high_tasks = await db.get_tasks_by_priority(user_id, "high")
        medium_tasks = await db.get_tasks_by_priority(user_id, "medium")
        low_tasks = await db.get_tasks_by_priority(user_id, "low")

        grouped_text = "🎯 <b>ГРУППИРОВКА ПО ПРИОРИТЕТАМ</b> 🎯\n\n"

        priority_info = {
            "high": {"icon": "🔴", "name": "ВЫСОКИЙ ПРИОРИТЕТ", "tasks": high_tasks},
            "medium": {
                "icon": "🟡",
                "name": "СРЕДНИЙ ПРИОРИТЕТ",
                "tasks": medium_tasks,
            },
            "low": {"icon": "🟢", "name": "НИЗКИЙ ПРИОРИТЕТ", "tasks": low_tasks},
        }

        total_tasks = 0

        for priority_data in priority_stats:
            priority, total, overdue, no_date = priority_data
            total_tasks += total

            if priority in priority_info and total > 0:
                info = priority_info[priority]
                tasks_list = info["tasks"]

                grouped_text += (
                    f"{info['icon']} <b>{info['name']}</b> ({total} задач):\n"
                )

                if overdue > 0:
                    grouped_text += f"   ⚠️ Просрочено: {overdue}\n"
                if no_date > 0:
                    grouped_text += f"   ⏳ Без срока: {no_date}\n"

                for task in tasks_list:
                    task_data = extract_task_data(task)
                    if task_data:
                        (
                            task_id,
                            content,
                            due_date,
                            task_priority,
                            status,
                            is_deleted,
                        ) = task_data

                        display_content = (
                            content[:25] + "..." if len(content) > 25 else content
                        )
                        due_text = format_due_date(due_date)

                        grouped_text += f"   #{task_id} {display_content}\n"
                        if due_date:
                            grouped_text += f"      {due_text}\n"

                if len(tasks_list) > 3:
                    grouped_text += f"   ... и еще {len(tasks_list) - 3} задач\n"
                grouped_text += "\n"

        grouped_text += f"📊 <b>ОБЩАЯ СТАТИСТИКА:</b>\n"
        for priority_data in priority_stats:
            priority, total, overdue, no_date = priority_data
            if total > 0:
                icon = priority_info[priority]["icon"]
                grouped_text += (
                    f"   {icon} {priority_info[priority]['name']}: {total} задач"
                )
                if overdue > 0:
                    grouped_text += f" (⚠️{overdue})"
                grouped_text += "\n"

        grouped_text += f"   📊 Всего активных задач: {total_tasks}"

        await message.answer(
            grouped_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )
        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при группировке по приоритетам: {e}",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()


async def group_by_date(message: Message, state: FSMContext):
    """Группировка задач по датам"""
    user_id = message.from_user.id
    tasks = await db.get_user_tasks_with_priority(user_id, "pending")

    if not tasks:
        await message.answer(
            "🎉 Нет активных задач для группировки!",
            reply_markup=get_tasks_keyboard(),
        )
        return

    tasks_by_date = {}
    tasks_without_date = []
    today = datetime.now().date()

    for task in tasks:
        task_data = extract_task_data(task)
        if not task_data:
            continue

        task_id, content, due_date, priority, status, is_deleted = task_data

        if due_date:
            try:
                due_datetime = datetime.fromisoformat(due_date.replace(" ", "T"))
                date_key = due_datetime.date()

                if date_key not in tasks_by_date:
                    tasks_by_date[date_key] = []
                tasks_by_date[date_key].append(task)
            except (ValueError, TypeError):
                tasks_without_date.append(task)
        else:
            tasks_without_date.append(task)

    sorted_dates = sorted(tasks_by_date.keys())

    grouped_text = "📅 <b>ГРУППИРОВКА ПО ДАТАМ</b> 📅\n\n"

    for date in sorted_dates:
        date_tasks = tasks_by_date[date]
        if date == today:
            date_category = "🎯 СЕГОДНЯ"
        elif date == today + timedelta(days=1):
            date_category = "⏰ ЗАВТРА"
        elif date < today:
            date_category = "⚠️ ПРОСРОЧЕННЫЕ"
        elif (date - today).days <= 7:
            date_category = "📈 ЭТА НЕДЕЛЯ"
        else:
            date_category = "📅 БУДУЩЕЕ"

        grouped_text += f"🕐 <b>{date_category}</b> - {date.strftime('%d.%m.%Y')} ({len(date_tasks)} задач):\n"

        for task in date_tasks[:6]:
            task_data = extract_task_data(task)
            if task_data:
                task_id, content, due_date, priority, status, is_deleted = task_data
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    priority, "🟡"
                )

                display_content = content
                if len(display_content) > 30:
                    display_content = display_content[:30] + "..."

                grouped_text += f"   {priority_icon} #{task_id} {display_content}\n"

        if len(date_tasks) > 6:
            grouped_text += f"   ... и еще {len(date_tasks) - 6} задач\n"
        grouped_text += "\n"

    if tasks_without_date:
        grouped_text += f"⏳ <b>БЕЗ СРОКА</b> ({len(tasks_without_date)} задач):\n"
        for task in tasks_without_date[:8]:
            task_data = extract_task_data(task)
            if task_data:
                task_id, content, due_date, priority, status, is_deleted = task_data
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    priority, "🟡"
                )

                display_content = content
                if len(display_content) > 30:
                    display_content = display_content[:30] + "..."

                grouped_text += f"   {priority_icon} #{task_id} {display_content}\n"

        if len(tasks_without_date) > 8:
            grouped_text += f"   ... и еще {len(tasks_without_date) - 8} задач\n"

    total_tasks = len(tasks)
    grouped_text += f"\n📊 <b>Итого:</b> {total_tasks} задач по датам выполнения"

    await message.answer(
        grouped_text,
        parse_mode="HTML",
        reply_markup=get_tasks_keyboard(),
    )
    await state.clear()


async def group_by_status(message: Message, state: FSMContext):
    """Группировка задач по статусам"""
    user_id = message.from_user.id

    try:
        active_tasks = await db.get_user_tasks_with_priority(user_id, "pending")
        completed_tasks = await db.get_user_tasks(user_id, "completed")
        deleted_tasks = await db.get_deleted_tasks(user_id)

        grouped_text = "📊 <b>ГРУППИРОВКА ПО СТАТУСАМ</b> 📊\n\n"

        if active_tasks:
            grouped_text += f"📝 <b>АКТИВНЫЕ ЗАДАЧИ</b> ({len(active_tasks)}):\n"
            for task in active_tasks[:5]:
                task_data = extract_task_data(task)
                if task_data:
                    task_id, content, due_date, priority, status, is_deleted = task_data
                    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                        priority, "🟡"
                    )
                    due_text = format_due_date(due_date)

                    display_content = content
                    if len(display_content) > 25:
                        display_content = display_content[:25] + "..."

                    grouped_text += f"   {priority_icon} #{task_id} {display_content}\n"
                    grouped_text += f"      {due_text}\n"

            if len(active_tasks) > 5:
                grouped_text += f"   ... и еще {len(active_tasks) - 5} активных задач\n"
            grouped_text += "\n"

        if completed_tasks:
            grouped_text += f"✅ <b>ВЫПОЛНЕННЫЕ ЗАДАЧИ</b> ({len(completed_tasks)}):\n"
            for task in completed_tasks[:3]:
                task_data = extract_task_data(task)
                if task_data:
                    task_id, content, due_date, priority, status, is_deleted = task_data

                    display_content = content
                    if len(display_content) > 30:
                        display_content = display_content[:30] + "..."

                    grouped_text += f"   ✅ #{task_id} {display_content}\n"

            if len(completed_tasks) > 3:
                grouped_text += (
                    f"   ... и еще {len(completed_tasks) - 3} выполненных задач\n"
                )
            grouped_text += "\n"

        if deleted_tasks:
            grouped_text += f"🗑️ <b>УДАЛЕННЫЕ ЗАДАЧИ</b> ({len(deleted_tasks)}):\n"
            for task in deleted_tasks[:3]:
                task_data = extract_task_data(task)
                if task_data:
                    task_id, content, due_date, priority, status, is_deleted = task_data

                    display_content = content
                    if len(display_content) > 30:
                        display_content = display_content[:30] + "..."

                    grouped_text += f"   🗑️ #{task_id} {display_content}\n"

            if len(deleted_tasks) > 3:
                grouped_text += (
                    f"   ... и еще {len(deleted_tasks) - 3} удаленных задач\n"
                )

        total_tasks = len(active_tasks) + len(completed_tasks) + len(deleted_tasks)
        grouped_text += f"\n📈 <b>ОБЩАЯ СТАТИСТИКА:</b>\n"
        grouped_text += f"   📝 Активные: {len(active_tasks)}\n"
        grouped_text += f"   ✅ Выполненные: {len(completed_tasks)}\n"
        grouped_text += f"   🗑️ Удаленные: {len(deleted_tasks)}\n"
        grouped_text += f"   📊 Всего: {total_tasks} задач"

        await message.answer(
            grouped_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )
        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при группировке по статусам: {e}",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()


async def combined_grouping(message: Message, state: FSMContext):
    """Упрощенная комбинированная группировка по приоритету и дате"""
    user_id = message.from_user.id

    try:
        tasks = await db.get_user_tasks_with_priority(user_id, "pending")

        if not tasks:
            await message.answer(
                "🎉 Нет активных задач для группировки!",
                reply_markup=get_tasks_keyboard(),
            )
            return

        today = datetime.now().date()
        grouped_data = {}

        for task in tasks:
            task_data = extract_task_data(task)
            if not task_data:
                continue

            task_id, content, due_date, priority, status, is_deleted = task_data

            if not due_date:
                date_category = "⏳ Без срока"
            else:
                try:
                    due_datetime = datetime.fromisoformat(due_date.replace(" ", "T"))
                    task_date = due_datetime.date()

                    if task_date == today:
                        date_category = "🎯 Сегодня"
                    elif task_date == today + timedelta(days=1):
                        date_category = "⏰ Завтра"
                    elif task_date < today:
                        date_category = "⚠️ Просрочено"
                    elif (task_date - today).days <= 7:
                        date_category = "📅 Эта неделя"
                    else:
                        date_category = "🗓️ Будущее"
                except (ValueError, TypeError):
                    date_category = "⏳ Без срока"

            group_key = f"{priority}_{date_category}"

            if group_key not in grouped_data:
                grouped_data[group_key] = []

            grouped_data[group_key].append(task_data)

        grouped_text = "🔄 <b>КОМБИНИРОВАННАЯ ГРУППИРОВКА</b> 🔄\n\n"
        grouped_text += "<i>Приоритет × Категория даты</i>\n\n"

        priority_order = {"high": 1, "medium": 2, "low": 3}
        date_order = {
            "🎯 Сегодня": 1,
            "⏰ Завтра": 2,
            "⚠️ Просрочено": 3,
            "📅 Эта неделя": 4,
            "🗓️ Будущее": 5,
            "⏳ Без срока": 6,
        }

        sorted_groups = sorted(
            grouped_data.items(),
            key=lambda x: (
                priority_order.get(x[0].split("_")[0], 4),
                date_order.get(x[0].split("_")[1], 7),
            ),
        )

        current_priority = None

        for group_key, tasks_list in sorted_groups:
            priority, date_category = group_key.split("_", 1)

            if priority != current_priority:
                current_priority = priority
                priority_name = {
                    "high": "🔴 ВЫСОКИЙ ПРИОРИТЕТ",
                    "medium": "🟡 СРЕДНИЙ ПРИОРИТЕТ",
                    "low": "🟢 НИЗКИЙ ПРИОРИТЕТ",
                }.get(priority, "🎯 ПРИОРИТЕТ")

                grouped_text += f"🎪 <b>{priority_name}</b>:\n"

            grouped_text += f"   📅 {date_category}: {len(tasks_list)} задач\n"

        grouped_text += "\n"

        grouped_text += "🚨 <b>САМЫЕ ВАЖНЫЕ ЗАДАЧИ:</b>\n\n"

        important_groups = [
            key
            for key in grouped_data.keys()
            if key.startswith("high_")
            and not key.endswith("🗓️ Будущее")
            and not key.endswith("⏳ Без срока")
        ]

        if not important_groups:
            important_groups = [
                key for key in grouped_data.keys() if key.startswith("high_")
            ]

        for group_key in important_groups[:3]:
            priority, date_category = group_key.split("_", 1)
            tasks_list = grouped_data[group_key]

            grouped_text += f"🔴 <b>{date_category}</b> ({len(tasks_list)} задач):\n"

            for task_data in tasks_list[:3]:
                task_id, content, due_date, priority, status, is_deleted = task_data

                display_content = content
                if len(display_content) > 25:
                    display_content = display_content[:25] + "..."

                grouped_text += f"   #{task_id} {display_content}\n"

            if len(tasks_list) > 3:
                grouped_text += f"   ... и еще {len(tasks_list) - 3} задач\n"
            grouped_text += "\n"

        total_tasks = len(tasks)
        high_count = sum(
            len(tasks) for key, tasks in grouped_data.items() if key.startswith("high_")
        )
        medium_count = sum(
            len(tasks)
            for key, tasks in grouped_data.items()
            if key.startswith("medium_")
        )
        low_count = sum(
            len(tasks) for key, tasks in grouped_data.items() if key.startswith("low_")
        )

        grouped_text += f"📈 <b>ОБЩАЯ СТАТИСТИКА:</b>\n"
        grouped_text += f"   🔴 Высокий: {high_count} задач\n"
        grouped_text += f"   🟡 Средний: {medium_count} задач\n"
        grouped_text += f"   🟢 Низкий: {low_count} задач\n"
        grouped_text += f"   📊 Всего: {total_tasks} активных задач"

        await message.answer(
            grouped_text,
            parse_mode="HTML",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при комбинированной группировке: {str(e)}",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()


async def group_by_specific_priority(
    message: Message, state: FSMContext, priority: str
):
    """Группировка по конкретному приоритету с красивым оформлением"""
    user_id = message.from_user.id

    try:
        tasks = await db.get_tasks_by_priority(user_id, priority)

        if not tasks:
            priority_names = {
                "high": "🔴 высоким",
                "medium": "🟡 средним",
                "low": "🟢 низким",
            }
            priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}

            empty_message = (
                f"{priority_icons[priority]} <b>ЗАДАЧИ С {priority_names[priority].upper()} ПРИОРИТЕТОМ</b>\n\n"
                "✨ <i>Пока нет задач в этой категории!</i>\n\n"
                "💡 <b>Советы:</b>\n"
                "• Создайте новые задачи через '📝 Новая задача'\n"
                "• Установите соответствующий приоритет\n"
                "• Используйте теги для лучшей организации"
            )

            await message.answer(
                empty_message,
                parse_mode="HTML",
                reply_markup=get_tasks_keyboard(),
            )
            await state.clear()
            return

        priority_config = {
            "high": {
                "icon": "🔴",
                "name": "ВЫСОКИЙ ПРИОРИТЕТ",
                "emoji": "🚨",
                "color": "🔴",
                "description": "Критически важные задачи требующие немедленного внимания",
                "header_emoji": "🎯",
            },
            "medium": {
                "icon": "🟡",
                "name": "СРЕДНИЙ ПРИОРИТЕТ",
                "emoji": "⚡",
                "color": "🟡",
                "description": "Важные задачи с установленными сроками",
                "header_emoji": "📅",
            },
            "low": {
                "icon": "🟢",
                "name": "НИЗКИЙ ПРИОРИТЕТ",
                "emoji": "📋",
                "color": "🟢",
                "description": "Задачи без строгих дедлайнов",
                "header_emoji": "🗓️",
            },
        }

        config = priority_config[priority]
        today = datetime.now().date()

        stats = {
            "total": len(tasks),
            "with_date": 0,
            "without_date": 0,
            "overdue": 0,
            "today": 0,
            "tomorrow": 0,
            "this_week": 0,
            "urgent": 0,
            "with_tags": 0,
            "without_tags": 0,
        }

        processed_tasks = []
        for task in tasks:
            task_data = extract_task_data(task)
            if not task_data:
                continue

            task_id, content, due_date, task_priority, status, is_deleted = task_data

            task_tags = await db.get_task_tags(task_id)
            has_tags = bool(task_tags)

            if has_tags:
                stats["with_tags"] += 1
            else:
                stats["without_tags"] += 1

            due_info = {
                "text": "",
                "is_urgent": False,
                "is_overdue": False,
                "is_today": False,
            }

            if due_date:
                stats["with_date"] += 1
                try:
                    due_datetime = datetime.fromisoformat(due_date.replace(" ", "T"))
                    due_date_only = due_datetime.date()

                    if due_date_only < today:
                        due_info["text"] = (
                            f"🚨 <b>ПРОСРОЧЕНА:</b> {due_datetime.strftime('%d.%m.%Y %H:%M')}"
                        )
                        due_info["is_overdue"] = True
                        due_info["is_urgent"] = True
                        stats["overdue"] += 1
                    elif due_date_only == today:
                        time_part = due_datetime.strftime("%H:%M")
                        if time_part == "23:59":
                            due_info["text"] = f"🎯 <b>СЕГОДНЯ</b> (весь день)"
                        else:
                            due_info["text"] = f"🎯 <b>СЕГОДНЯ</b> в {time_part}"
                        due_info["is_today"] = True
                        due_info["is_urgent"] = True
                        stats["today"] += 1
                        stats["urgent"] += 1
                    elif due_date_only == today + timedelta(days=1):
                        due_info["text"] = (
                            f"⏰ <b>ЗАВТРА:</b> {due_datetime.strftime('%d.%m.%Y %H:%M')}"
                        )
                        due_info["is_urgent"] = True
                        stats["tomorrow"] += 1
                        stats["urgent"] += 1
                    elif (due_date_only - today).days <= 7:
                        due_info["text"] = (
                            f"📅 <b>НА НЕДЕЛЕ:</b> {due_datetime.strftime('%d.%m.%Y')}"
                        )
                        stats["this_week"] += 1
                    else:
                        due_info["text"] = f"🗓️ {due_datetime.strftime('%d.%m.%Y')}"
                except (ValueError, TypeError):
                    due_info["text"] = "📅 Дата в неверном формате"
            else:
                stats["without_date"] += 1
                due_info["text"] = "⏳ Без срока"

            processed_tasks.append(
                {
                    "id": task_id,
                    "content": content,
                    "due_info": due_info,
                    "tags": task_tags,
                    "has_tags": has_tags,
                }
            )

        header_text = (
            f"{config['emoji']} <b>{config['name']}</b> {config['emoji']}\n"
            f"<i>{config['description']}</i>\n\n"
            f"{config['header_emoji']} <b>ОБЗОР КАТЕГОРИИ</b>\n"
            f"<code>┌{'─' * 35}┐</code>\n"
            f"<code>│</code> 📊 Всего задач: <b>{stats['total']}</b>\n"
            f"<code>│</code> 📅 Со сроком: <b>{stats['with_date']}</b>\n"
            f"<code>│</code> ⏳ Без срока: <b>{stats['without_date']}</b>\n"
            f"<code>│</code> 🏷️ С тегами: <b>{stats['with_tags']}</b>\n"
            f"<code>│</code> 🔸 Без тегов: <b>{stats['without_tags']}</b>\n"
        )

        if stats["urgent"] > 0:
            header_text += f"<code>│</code> ⚡ Срочные: <b>{stats['urgent']}</b>\n"
        if stats["overdue"] > 0:
            header_text += (
                f"<code>│</code> 🚨 Просроченные: <b>{stats['overdue']}</b>\n"
            )
        if stats["today"] > 0:
            header_text += f"<code>│</code> 🎯 На сегодня: <b>{stats['today']}</b>\n"

        header_text += f"<code>└{'─' * 35}┘</code>"

        await message.answer(header_text, parse_mode="HTML")

        urgent_tasks = [t for t in processed_tasks if t["due_info"]["is_urgent"]]
        if urgent_tasks:
            urgent_text = f"🚨 <b>ТРЕБУЮТ ВНИМАНИЯ</b> 🚨\n\n"

            for task in urgent_tasks[:8]:
                tags_text = ""
                if task["tags"]:
                    tags_text = " ".join(
                        [f"<code>#{tag[1]}</code>" for tag in task["tags"]]
                    )

                display_content = task["content"]
                if len(display_content) > 45:
                    display_content = task["content"][:42] + "..."

                urgent_text += (
                    f"{config['icon']} <b>#{task['id']}</b>\n"
                    f"📝 {display_content}\n"
                    f"⏰ {task['due_info']['text']}\n"
                )

                if tags_text:
                    urgent_text += f"🏷️ {tags_text}\n"

                urgent_text += "\n"

            if len(urgent_tasks) > 8:
                urgent_text += (
                    f"<i>... и еще {len(urgent_tasks) - 8} срочных задач</i>\n"
                )

            await message.answer(urgent_text, parse_mode="HTML")

        if stats["total"] <= 15:
            tasks_text = f"📋 <b>ВСЕ ЗАДАЧИ КАТЕГОРИИ</b> 📋\n\n"

            for i, task in enumerate(processed_tasks, 1):
                tags_text = ""
                if task["tags"]:
                    tags_text = " ".join(
                        [f"<code>#{tag[1]}</code>" for tag in task["tags"]]
                    )

                display_content = task["content"]
                if len(display_content) > 40:
                    display_content = task["content"][:37] + "..."

                tasks_text += (
                    f"<code>┌{'─' * 35}┐</code>\n"
                    f"<b>#{task['id']}</b> │ {config['icon']} <b>Задача {i}</b>\n"
                    f"<code>│</code> 📝 {display_content}\n"
                    f"<code>│</code> {task['due_info']['text']}\n"
                )

                if tags_text:
                    tasks_text += f"<code>│</code> 🏷️ {tags_text}\n"

                tasks_text += f"<code>└{'─' * 35}┘</code>\n\n"

            tasks_text += f"📈 <b>Итого:</b> {stats['total']} задач в категории"

            await message.answer(
                tasks_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
            )

        else:
            summary_text = (
                f"📁 <b>ПОЛНЫЙ СПИСОК ЗАДАЧ</b> 📁\n\n"
                f"<code>┌{'─' * 30}┐</code>\n"
                f"<code>│</code> 🎯 Всего задач: <b>{stats['total']}</b>\n"
            )

            date_groups = {
                "🚨 Просроченные": stats["overdue"],
                "🎯 На сегодня": stats["today"],
                "⏰ На завтра": stats["tomorrow"],
                "📅 На неделе": stats["this_week"],
                "🗓️ В будущем": stats["with_date"]
                - (
                    stats["overdue"]
                    + stats["today"]
                    + stats["tomorrow"]
                    + stats["this_week"]
                ),
                "⏳ Без срока": stats["without_date"],
            }

            for group_name, count in date_groups.items():
                if count > 0:
                    summary_text += f"<code>│</code> {group_name}: <b>{count}</b>\n"

            summary_text += (
                f"<code>└{'─' * 30}┘</code>\n\n"
                f"💡 <b>Для детального просмотра:</b>\n"
                f"• Используйте фильтры по датам\n"
                f"• Примените группировку по тегам\n"
                f"• Просмотрите задачи поэтапно"
            )

            await message.answer(
                summary_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
            )

    except Exception as e:
        error_text = (
            "❌ <b>ОШИБКА ПРИ ГРУППИРОВКЕ</b>\n\n"
            f"<code>┌{'─' * 25}┐</code>\n"
            f"<code>│</code> 🚫 Не удалось загрузить задачи\n"
            f"<code>│</code> 📝 По приоритету: {priority}\n"
            f"<code>│</code> 🔧 Ошибка: {str(e)[:50]}...\n"
            f"<code>└{'─' * 25}┘</code>\n\n"
            "🔄 <i>Попробуйте еще раз или обратитесь в поддержку</i>"
        )

        await message.answer(
            error_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )
        print(f"Error in group_by_specific_priority: {e}")

    finally:
        await state.clear()


async def group_by_specific_period(message: Message, state: FSMContext, period: str):
    """Группировка по конкретному периоду"""
    user_id = message.from_user.id
    today = datetime.now().date()

    if period == "today":
        target_date = today
        period_name = "сегодня"
    elif period == "tomorrow":
        target_date = today + timedelta(days=1)
        period_name = "завтра"
    elif period == "week":
        tasks = await db.get_user_tasks_with_priority(user_id, "pending")
        week_tasks = []

        for task in tasks:
            task_data = extract_task_data(task)
            if task_data and task_data[2]:
                try:
                    due_date = datetime.fromisoformat(
                        task_data[2].replace(" ", "T")
                    ).date()
                    if 0 <= (due_date - today).days <= 7:
                        week_tasks.append(task)
                except (ValueError, TypeError):
                    continue

        await show_period_tasks(message, state, week_tasks, "ближайшую неделю")
        return
    elif period == "month":
        tasks = await db.get_user_tasks_with_priority(user_id, "pending")
        month_tasks = []

        for task in tasks:
            task_data = extract_task_data(task)
            if task_data and task_data[2]:
                try:
                    due_date = datetime.fromisoformat(
                        task_data[2].replace(" ", "T")
                    ).date()
                    if 0 <= (due_date - today).days <= 30:
                        month_tasks.append(task)
                except (ValueError, TypeError):
                    continue

        await show_period_tasks(message, state, month_tasks, "ближайший месяц")
        return

    tasks = await db.get_tasks_by_date(
        user_id, datetime.combine(target_date, datetime.min.time())
    )
    await show_period_tasks(message, state, tasks, period_name)


async def show_period_tasks(
    message: Message, state: FSMContext, tasks: list, period_name: str
):
    """Показывает задачи за период с минимальным оформлением"""
    if not tasks:
        await message.answer(
            f"🎉 Нет задач на {period_name}!", reply_markup=get_tasks_keyboard()
        )
        await state.clear()
        return

    grouped_text = (
        f"📅 <b>ЗАДАЧИ НА {period_name.upper()}</b> 📅\n" f"<code>┌{'─' * 35}┐</code>\n"
    )

    for task in tasks:
        task_data = extract_task_data(task)
        if not task_data:
            continue

        task_id, content, due_date, priority, status, is_deleted = task_data

        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
        due_text = format_due_date(due_date)

        display_content = content[:35] + "..." if len(content) > 35 else content

        grouped_text += (
            f"<code>├{'─' * 35}┤</code>\n"
            f"{priority_icon} <b>#{task_id}</b> {display_content}\n"
            f"<code>│</code> {due_text}\n"
        )

    grouped_text += (
        f"<code>└{'─' * 35}┘</code>\n\n" f"📊 <b>Всего:</b> {len(tasks)} задач"
    )

    await message.answer(
        grouped_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
    )
    await state.clear()


async def group_by_specific_status(message: Message, state: FSMContext, status: str):
    """Группировка по конкретному статусу"""
    user_id = message.from_user.id

    if status == "pending":
        tasks = await db.get_user_tasks_with_priority(user_id, "pending")
        status_name = "активные"
    elif status == "completed":
        tasks = await db.get_user_tasks(user_id, "completed")
        status_name = "выполненные"
    elif status == "deleted":
        tasks = await db.get_deleted_tasks(user_id)
        status_name = "удаленные"

    if not tasks:
        await message.answer(
            f"🎉 Нет {status_name} задач!", reply_markup=get_tasks_keyboard()
        )
        await state.clear()
        return

    status_icon = {"pending": "📝", "completed": "✅", "deleted": "🗑️"}[status]
    grouped_text = (
        f"{status_icon} <b>{status_name.upper()} ЗАДАЧИ</b> {status_icon}\n\n"
    )

    for task in tasks[:10]:
        task_data = extract_task_data(task)
        if task_data:
            task_id, content, due_date, priority, status_val, is_deleted = task_data

            display_content = content[:40] + "..." if len(content) > 40 else content
            grouped_text += f"#{task_id} {display_content}\n"

            if due_date and status == "pending":
                due_text = format_due_date(due_date)
                grouped_text += f"   {due_text}\n"

            grouped_text += "\n"

    if len(tasks) > 10:
        grouped_text += f"... и еще {len(tasks) - 10} задач\n\n"

    grouped_text += f"📊 <b>Всего:</b> {len(tasks)} задач"

    await message.answer(
        grouped_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
    )
    await state.clear()


async def combined_tag_priority(message: Message, state: FSMContext):
    """Комбинированная группировка: Тег + Приоритет"""
    user_id = message.from_user.id

    try:
        tasks = await db.get_user_tasks_with_priority(user_id, "pending")

        if not tasks:
            await message.answer(
                "🎉 Нет активных задач для группировки!",
                reply_markup=get_tasks_keyboard(),
            )
            await state.clear()
            return

        grouped_data = {}
        tasks_without_tags = []

        for task in tasks:
            task_data = extract_task_data(task)
            if not task_data:
                continue

            task_id, content, due_date, priority, status, is_deleted = task_data
            task_tags = await db.get_task_tags(task_id)

            if task_tags:
                for tag in task_tags:
                    tag_name = tag[1]
                    if tag_name not in grouped_data:
                        grouped_data[tag_name] = {"high": [], "medium": [], "low": []}
                    grouped_data[tag_name][priority].append(task_data)
            else:
                tasks_without_tags.append(task_data)

        grouped_text = "🏷️ <b>КОМБИНИРОВАННАЯ ГРУППИРОВКА</b> 🎯\n\n"
        grouped_text += "<i>Тег × Приоритет</i>\n\n"

        if grouped_data:
            for tag_name, priorities in grouped_data.items():
                total_tag_tasks = sum(len(tasks) for tasks in priorities.values())
                if total_tag_tasks > 0:
                    grouped_text += (
                        f"🔸 <b>#{tag_name}</b> ({total_tag_tasks} задач):\n"
                    )

                    for priority in ["high", "medium", "low"]:
                        tasks_list = priorities[priority]
                        if tasks_list:
                            priority_icon = {
                                "high": "🔴",
                                "medium": "🟡",
                                "low": "🟢",
                            }.get(priority, "🟡")
                            grouped_text += (
                                f"   {priority_icon} {len(tasks_list)} задач\n"
                            )

                    grouped_text += "\n"

        if tasks_without_tags:
            grouped_text += f"🔸 <b>Без тегов</b> ({len(tasks_without_tags)} задач):\n"

            no_tag_priorities = {"high": [], "medium": [], "low": []}
            for task_data in tasks_without_tags:
                priority = task_data[3]
                if priority in no_tag_priorities:
                    no_tag_priorities[priority].append(task_data)

            for priority in ["high", "medium", "low"]:
                tasks_list = no_tag_priorities[priority]
                if tasks_list:
                    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                        priority, "🟡"
                    )
                    grouped_text += f"   {priority_icon} {len(tasks_list)} задач\n"

        total_tasks = len(tasks)
        grouped_text += f"\n📊 <b>Всего активных задач:</b> {total_tasks}"

        await message.answer(
            grouped_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )
        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при группировке тег+приоритет: {str(e)}",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()


async def combined_date_status(message: Message, state: FSMContext):
    """Комбинированная группировка: Дата + Статус"""
    user_id = message.from_user.id

    try:

        active_tasks = await db.get_user_tasks_with_priority(user_id, "pending")
        completed_tasks = await db.get_user_tasks(user_id, "completed")

        today = datetime.now().date()

        active_by_date = {}
        active_without_date = []

        for task in active_tasks:
            task_data = extract_task_data(task)
            if not task_data:
                continue

            task_id, content, due_date, priority, status, is_deleted = task_data

            if due_date:
                try:
                    due_datetime = datetime.fromisoformat(due_date.replace(" ", "T"))
                    date_key = due_datetime.date()

                    if date_key not in active_by_date:
                        active_by_date[date_key] = []
                    active_by_date[date_key].append(task_data)
                except (ValueError, TypeError):
                    active_without_date.append(task_data)
            else:
                active_without_date.append(task_data)

        grouped_text = "📅 <b>КОМБИНИРОВАННАЯ ГРУППИРОВКА</b> 📊\n\n"
        grouped_text += "<i>Дата × Статус</i>\n\n"

        grouped_text += "📝 <b>АКТИВНЫЕ ЗАДАЧИ:</b>\n"

        sorted_dates = sorted(active_by_date.keys())
        for date in sorted_dates[:5]:
            date_tasks = active_by_date[date]

            if date == today:
                date_category = "🎯 Сегодня"
            elif date == today + timedelta(days=1):
                date_category = "⏰ Завтра"
            elif date < today:
                date_category = "⚠️ Просрочено"
            else:
                date_category = f"📅 {date.strftime('%d.%m')}"

            grouped_text += f"   {date_category}: {len(date_tasks)} задач\n"

        if active_without_date:
            grouped_text += f"   ⏳ Без срока: {len(active_without_date)} задач\n"

        if len(sorted_dates) > 5:
            grouped_text += f"   ... и еще {len(sorted_dates) - 5} дат\n"

        grouped_text += "\n"

        if completed_tasks:
            grouped_text += (
                f"✅ <b>ВЫПОЛНЕННЫЕ ЗАДАЧИ:</b> {len(completed_tasks)} задач\n"
            )

        total_tasks = len(active_tasks) + len(completed_tasks)
        grouped_text += f"\n📊 <b>Всего задач:</b> {total_tasks}"

        await message.answer(
            grouped_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )
        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при группировке дата+статус: {str(e)}",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()


async def combined_tag_status(message: Message, state: FSMContext):
    """Комбинированная группировка: Тег + Статус"""
    user_id = message.from_user.id

    try:
        active_tasks = await db.get_user_tasks_with_priority(user_id, "pending")
        completed_tasks = await db.get_user_tasks(user_id, "completed")

        active_by_tag = {}
        active_without_tags = []

        for task in active_tasks:
            task_data = extract_task_data(task)
            if not task_data:
                continue

            task_id, content, due_date, priority, status, is_deleted = task_data
            task_tags = await db.get_task_tags(task_id)

            if task_tags:
                for tag in task_tags:
                    tag_name = tag[1]
                    if tag_name not in active_by_tag:
                        active_by_tag[tag_name] = []
                    active_by_tag[tag_name].append(task_data)
            else:
                active_without_tags.append(task_data)

        grouped_text = "🏷️ <b>КОМБИНИРОВАННАЯ ГРУППИРОВКА</b> 📊\n\n"
        grouped_text += "<i>Тег × Статус</i>\n\n"

        grouped_text += "📝 <b>АКТИВНЫЕ ЗАДАЧИ:</b>\n"

        if active_by_tag:
            for tag_name, tag_tasks in list(active_by_tag.items())[:6]:
                grouped_text += f"   #{tag_name}: {len(tag_tasks)} задач\n"

        if active_without_tags:
            grouped_text += f"   Без тегов: {len(active_without_tags)} задач\n"

        if len(active_by_tag) > 6:
            grouped_text += f"   ... и еще {len(active_by_tag) - 6} тегов\n"

        grouped_text += "\n"

        if completed_tasks:
            grouped_text += (
                f"✅ <b>ВЫПОЛНЕННЫЕ ЗАДАЧИ:</b> {len(completed_tasks)} задач\n"
            )

        total_tasks = len(active_tasks) + len(completed_tasks)
        grouped_text += f"\n📊 <b>Всего задач:</b> {total_tasks}"

        await message.answer(
            grouped_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )
        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при группировке тег+статус: {str(e)}",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()


async def triple_grouping(message: Message, state: FSMContext):
    """Тройная группировка: Приоритет + Дата + Статус"""
    user_id = message.from_user.id

    try:
        active_tasks = await db.get_user_tasks_with_priority(user_id, "pending")
        completed_tasks = await db.get_user_tasks(user_id, "completed")

        today = datetime.now().date()

        active_summary = {
            "high": {
                "today": 0,
                "tomorrow": 0,
                "overdue": 0,
                "future": 0,
                "no_date": 0,
            },
            "medium": {
                "today": 0,
                "tomorrow": 0,
                "overdue": 0,
                "future": 0,
                "no_date": 0,
            },
            "low": {"today": 0, "tomorrow": 0, "overdue": 0, "future": 0, "no_date": 0},
        }

        for task in active_tasks:
            task_data = extract_task_data(task)
            if not task_data:
                continue

            task_id, content, due_date, priority, status, is_deleted = task_data

            if due_date:
                try:
                    due_datetime = datetime.fromisoformat(due_date.replace(" ", "T"))
                    task_date = due_datetime.date()

                    if task_date == today:
                        date_category = "today"
                    elif task_date == today + timedelta(days=1):
                        date_category = "tomorrow"
                    elif task_date < today:
                        date_category = "overdue"
                    else:
                        date_category = "future"
                except (ValueError, TypeError):
                    date_category = "no_date"
            else:
                date_category = "no_date"

            if priority in active_summary and date_category in active_summary[priority]:
                active_summary[priority][date_category] += 1

        grouped_text = "🎯 <b>ТРОЙНАЯ ГРУППИРОВКА</b> 📅📊\n\n"
        grouped_text += "<i>Приоритет × Дата × Статус</i>\n\n"

        grouped_text += "📝 <b>АКТИВНЫЕ ЗАДАЧИ:</b>\n\n"

        priority_names = {
            "high": "🔴 Высокий",
            "medium": "🟡 Средний",
            "low": "🟢 Низкий",
        }
        date_names = {
            "today": "🎯 Сегодня",
            "tomorrow": "⏰ Завтра",
            "overdue": "⚠️ Просрочено",
            "future": "📅 Будущее",
            "no_date": "⏳ Без срока",
        }

        for priority in ["high", "medium", "low"]:
            total_priority = sum(active_summary[priority].values())
            if total_priority > 0:
                grouped_text += f"{priority_names[priority]} ({total_priority}):\n"

                for date_cat in ["today", "tomorrow", "overdue", "future", "no_date"]:
                    count = active_summary[priority][date_cat]
                    if count > 0:
                        grouped_text += f"   {date_names[date_cat]}: {count}\n"

                grouped_text += "\n"

        if completed_tasks:
            grouped_text += f"✅ <b>ВЫПОЛНЕННЫЕ ЗАДАЧИ:</b> {len(completed_tasks)}\n"

        total_active = len(active_tasks)
        total_completed = len(completed_tasks)
        total_all = total_active + total_completed

        grouped_text += f"\n📈 <b>ОБЩАЯ СТАТИСТИКА:</b>\n"
        grouped_text += f"   📝 Активные: {total_active}\n"
        grouped_text += f"   ✅ Выполненные: {total_completed}\n"
        grouped_text += f"   📊 Всего: {total_all}"

        await message.answer(
            grouped_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )
        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при тройной группировке: {str(e)}",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()


async def combined_priority_date(message: Message, state: FSMContext):
    """Комбинированная группировка: Приоритет + Дата"""
    user_id = message.from_user.id

    try:
        tasks = await db.get_user_tasks_with_priority(user_id, "pending")

        if not tasks:
            await message.answer(
                "🎉 Нет активных задач для группировки!",
                reply_markup=get_tasks_keyboard(),
            )
            await state.clear()
            return

        today = datetime.now().date()
        grouped_data = {}

        for task in tasks:
            task_data = extract_task_data(task)
            if not task_data:
                continue

            task_id, content, due_date, priority, status, is_deleted = task_data

            if not due_date:
                date_category = "⏳ Без срока"
            else:
                try:
                    due_datetime = datetime.fromisoformat(due_date.replace(" ", "T"))
                    task_date = due_datetime.date()

                    if task_date == today:
                        date_category = "🎯 Сегодня"
                    elif task_date == today + timedelta(days=1):
                        date_category = "⏰ Завтра"
                    elif task_date < today:
                        date_category = "⚠️ Просрочено"
                    elif (task_date - today).days <= 7:
                        date_category = "📅 Эта неделя"
                    else:
                        date_category = "🗓️ Будущее"
                except (ValueError, TypeError):
                    date_category = "⏳ Без срока"

            if priority not in grouped_data:
                grouped_data[priority] = {}
            if date_category not in grouped_data[priority]:
                grouped_data[priority][date_category] = []

            grouped_data[priority][date_category].append(task_data)

        grouped_text = "🔄 <b>КОМБИНИРОВАННАЯ ГРУППИРОВКА</b> 🔄\n\n"
        grouped_text += "<i>Приоритет × Дата выполнения</i>\n\n"

        priority_names = {
            "high": "🔴 ВЫСОКИЙ ПРИОРИТЕТ",
            "medium": "🟡 СРЕДНИЙ ПРИОРИТЕТ",
            "low": "🟢 НИЗКИЙ ПРИОРИТЕТ",
        }

        date_order = {
            "🎯 Сегодня": 1,
            "⏰ Завтра": 2,
            "⚠️ Просрочено": 3,
            "📅 Эта неделя": 4,
            "🗓️ Будущее": 5,
            "⏳ Без срока": 6,
        }

        for priority in ["high", "medium", "low"]:
            if priority in grouped_data and grouped_data[priority]:
                total_priority_tasks = sum(
                    len(tasks) for tasks in grouped_data[priority].values()
                )
                grouped_text += f"🎪 <b>{priority_names[priority]}</b> ({total_priority_tasks} задач):\n"

                sorted_dates = sorted(
                    grouped_data[priority].items(),
                    key=lambda x: date_order.get(x[0], 7),
                )

                for date_category, tasks_list in sorted_dates:
                    grouped_text += f"   📅 {date_category}: {len(tasks_list)} задач\n"

                grouped_text += "\n"

        grouped_text += "🚨 <b>САМЫЕ ВАЖНЫЕ ЗАДАЧИ:</b>\n\n"

        urgent_tasks = []
        for priority in ["high", "medium"]:
            if priority in grouped_data:
                for date_category in ["🎯 Сегодня", "⏰ Завтра", "⚠️ Просрочено"]:
                    if date_category in grouped_data[priority]:
                        urgent_tasks.extend(
                            [
                                (task_data, priority, date_category)
                                for task_data in grouped_data[priority][date_category]
                            ]
                        )

        if urgent_tasks:
            for task_data, priority, date_category in urgent_tasks[:8]:
                task_id, content, due_date, task_priority, status, is_deleted = (
                    task_data
                )
                priority_icon = {"high": "🔴", "medium": "🟡"}.get(priority, "🟡")

                display_content = content[:30] + "..." if len(content) > 30 else content
                grouped_text += f"{priority_icon} <b>#{task_id}</b> {display_content}\n"
                grouped_text += f"   📅 {date_category}\n\n"
        else:
            grouped_text += "✅ Нет срочных задач!\n\n"

        total_tasks = len(tasks)
        high_count = sum(len(tasks) for tasks in grouped_data.get("high", {}).values())
        medium_count = sum(
            len(tasks) for tasks in grouped_data.get("medium", {}).values()
        )
        low_count = sum(len(tasks) for tasks in grouped_data.get("low", {}).values())

        grouped_text += f"📈 <b>ОБЩАЯ СТАТИСТИКА:</b>\n"
        grouped_text += f"   🔴 Высокий приоритет: {high_count} задач\n"
        grouped_text += f"   🟡 Средний приоритет: {medium_count} задач\n"
        grouped_text += f"   🟢 Низкий приоритет: {low_count} задач\n"
        grouped_text += f"   📊 Всего активных задач: {total_tasks}"

        await message.answer(
            grouped_text, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )
        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при комбинированной группировке: {str(e)}",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()


@router.message(StateFilter(TaskGrouping.waiting_for_specific_choice))
async def process_specific_choice(message: Message, state: FSMContext):
    """Единый обработчик для всех подменю группировки"""
    if await handle_navigation(message, state):
        return

    data = await state.get_data()
    group_type = data.get("group_type")

    try:
        if group_type == "priority":
            await process_priority_group_choice(message, state)
        elif group_type == "date":
            await process_date_group_choice(message, state)
        elif group_type == "status":
            await process_status_group_choice(message, state)
        elif group_type == "combined":
            await process_combined_group_choice(message, state)
        else:
            await message.answer(
                "❌ Ошибка типа группировки. Попробуйте снова:",
                reply_markup=get_tasks_keyboard(),
            )
            await state.clear()
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при обработке выбора: {e}",
            reply_markup=get_tasks_keyboard(),
        )
        await state.clear()


async def process_priority_group_choice(message: Message, state: FSMContext):
    """Обработка выбора приоритета для группировки"""
    priority_map = {
        "🔴 Высокий": "high",
        "🟡 Средний": "medium",
        "🟢 Низкий": "low",
        "🎯 Все приоритеты": "all",
    }

    if message.text not in priority_map:
        await message.answer(
            "❌ Пожалуйста, выберите приоритет из меню:",
            reply_markup=get_grouping_priority_keyboard(),
        )
        return

    priority = priority_map[message.text]

    if priority == "all":
        await group_by_priority(message, state)
    else:
        await group_by_specific_priority(message, state, priority)


async def process_date_group_choice(message: Message, state: FSMContext):
    """Обработка выбора даты для группировки"""
    period_map = {
        "📅 Сегодня": "today",
        "📅 Завтра": "tomorrow",
        "📅 Неделя": "week",
        "📅 Месяц": "month",
        "📅 Все время": "all",
    }

    if message.text not in period_map:
        await message.answer(
            "❌ Пожалуйста, выберите период из меню:",
            reply_markup=get_grouping_period_keyboard(),
        )
        return

    period = period_map[message.text]

    if period == "all":
        await group_by_date(message, state)
    else:
        await group_by_specific_period(message, state, period)


async def process_status_group_choice(message: Message, state: FSMContext):
    """Обработка выбора статуса для группировки"""
    status_map = {
        "📝 Активные": "pending",
        "✅ Выполненные": "completed",
        "🗑️ Удаленные": "deleted",
        "📊 Все статусы": "all",
    }

    if message.text not in status_map:
        await message.answer(
            "❌ Пожалуйста, выберите статус из меню:",
            reply_markup=get_grouping_status_keyboard(),
        )
        return

    status = status_map[message.text]

    if status == "all":
        await group_by_status(message, state)
    else:
        await group_by_specific_status(message, state, status)


async def process_combined_group_choice(message: Message, state: FSMContext):
    """Обработка выбора комбинированной группировки"""
    combined_map = {
        "🎯 Приоритет + Дата": "priority_date",
        "🏷️ Тег + Приоритет": "tag_priority",
        "📅 Дата + Статус": "date_status",
        "🏷️ Тег + Статус": "tag_status",
        "🔄 Тройная группировка": "triple",
    }

    if message.text not in combined_map:
        await message.answer(
            "❌ Пожалуйста, выберите тип группировки из меню:",
            reply_markup=get_grouping_combined_keyboard(),
        )
        return

    combined_type = combined_map[message.text]

    if combined_type == "priority_date":
        await combined_priority_date(message, state)
    elif combined_type == "tag_priority":
        await combined_tag_priority(message, state)
    elif combined_type == "date_status":
        await combined_date_status(message, state)
    elif combined_type == "tag_status":
        await combined_tag_status(message, state)
    elif combined_type == "triple":
        await triple_grouping(message, state)
