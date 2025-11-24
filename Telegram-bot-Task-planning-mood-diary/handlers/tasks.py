from aiogram import Router, F
import asyncio
from aiogram.types import Message
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
    get_confirm_keyboard,
    get_back_keyboard,
    get_cancel_keyboard,
    get_confirm_keyboard,
    get_cancel_keyboard,
    get_back_keyboard,
    get_quick_actions_keyboard,
    get_status_keyboard,
    get_filter_date,
    get_grouping_keyboard,
    get_task_actions_keyboard,
    get_actual_keyboard,
    get_view_keyboard,
    get_distributions_keyboard,
    get_report_keyboard,
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


class CleanupStates(StatesGroup):
    waiting_for_days = State()
    waiting_for_confirmation = State()


class TaskFilter(StatesGroup):
    waiting_for_filter_choice = State()
    waiting_for_priority = State()
    waiting_for_status = State()
    waiting_for_tag = State()
    waiting_for_date = State()
    waiting_for_confirmation = State()
    waiting_for_combined_next = State()


class TaskGrouping(StatesGroup):
    waiting_for_group_type = State()
    waiting_for_specific_choice = State()
    waiting_for_confirmation = State()


@router.message(F.text == "📋 Задачи")
@router.message(Command("tasks"))
async def handle_tasks_main(message: Message):
    """Главное меню задач"""
    await message.answer(
        "📋 Управление задачами\n\n" "Выберите действие:",
        reply_markup=get_tasks_keyboard(),
    )


@router.message(F.text == "📝 Действия с задачами")
async def cmd_quick_actions(message: Message, state: FSMContext):
    await message.answer(
        "📋 Действия с задачей\n\n" "Выберите действие:",
        reply_markup=get_task_actions_keyboard(),
    )


@router.message(F.text == "📅 Актуальное")
async def cmd_quick_actions(message: Message, state: FSMContext):
    await message.answer(
        "📅 Просмотр актуального\n\n" "Выберите действие:",
        reply_markup=get_actual_keyboard(),
    )


@router.message(F.text == "📊 Просмотр задач")
async def cmd_quick_actions(message: Message, state: FSMContext):
    await message.answer(
        "📊 Просмотр задач\n\n" "Выберите действие:",
        reply_markup=get_view_keyboard(),
    )


@router.message(F.text == "🏷️ Анализ распределений")
async def cmd_quick_actions(message: Message, state: FSMContext):
    await message.answer(
        "🏷️ Аналитика распределений\n\n" "Выберите действие:",
        reply_markup=get_distributions_keyboard(),
    )


@router.message(F.text == "📋 Обзорные отчеты")
async def cmd_quick_actions(message: Message, state: FSMContext):
    await message.answer(
        "📋 Просмотр отчета\n\n" "Выберите действие:",
        reply_markup=get_report_keyboard(),
    )


@router.message(F.text == "📝 Новая задача")
@router.message(Command("plan"))
async def cmd_plan(message: Message, state: FSMContext):
    """Начать создание новой задачи"""
    await message.answer("📝 Опишите вашу задачу:", reply_markup=get_cancel_keyboard())
    await state.set_state(TaskCreation.waiting_for_content)


@router.message(F.text == "📋 Список задач")
async def handle_show_tasks(message: Message):
    """Показать все активные задачи"""
    await show_all_tasks(message)


@router.message(F.text == "🚨 Срочные задачи")
@router.message(Command("urgent"))
async def cmd_urgent(message: Message):
    """Показать срочные задачи"""
    await show_urgent_tasks(message)


@router.message(F.text == "⏰ Ближайшие задачи")
@router.message(Command("upcoming"))
async def cmd_upcoming(message: Message):
    """Показать ближайшие задачи"""
    await show_upcoming_tasks(message)


@router.message(F.text == "⚠️ Просроченные")
@router.message(Command("overdue"))
async def cmd_overdue(message: Message):
    """Показать просроченные задачи"""
    await show_overdue_tasks(message)


@router.message(F.text == "📅 Задачи на сегодня")
async def handle_today_tasks(message: Message):
    """Показать задачи на сегодня"""
    await show_today_tasks(message)


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


@router.message(F.text == "🗑️ Удалить задачу")
@router.message(Command("delete"))
async def cmd_delete(message: Message, state: FSMContext):
    """Начать процесс удаления задачи"""
    await message.answer(
        "🗑️ Удаление задачи\n\n" "Введите ID задачи для удаления:",
        reply_markup=get_back_keyboard(),
    )
    await state.set_state(TaskDelete.waiting_for_task_id)


@router.message(F.text == "🔄 Восстановить задачу")
@router.message(Command("restore"))
async def cmd_restore(message: Message, state: FSMContext):
    """Начать процесс восстановления задачи"""
    await message.answer(
        "🔄 Восстановление задачи\n\n" "Введите ID задачи для восстановления:",
        reply_markup=get_back_keyboard(),
    )
    await state.set_state(TaskRestore.waiting_for_task_id)


@router.message(F.text == "✏️ Редактировать задачу")
@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext):
    """Начать процесс редактирования задачи"""
    await message.answer(
        "✏️ Редактирование задачи\n\n" "Введите ID задачи для редактирования:",
        reply_markup=get_back_keyboard(),
    )
    await state.set_state(TaskEdit.waiting_for_task_id)


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


@router.message(F.text == "🔄 Комбинированный")
async def handle_combined_filter(message: Message, state: FSMContext):
    """Начать комбинированную фильтрацию"""
    await state.update_data(current_filters={}, filter_type="combined", combined_step=0)
    await continue_combined_filter(message, state, {})


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

        if due_datetime.time() == time(23, 59):
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


def create_task_card(task_data, task_tags=None):
    """Создает  карточку задачи"""
    if not task_data:
        return "❌ Ошибка данных задачи"

    task_id, content, due_date, priority, status, is_deleted = task_data
    priority_config = {
        "high": {"icon": "🔴", "name": "ВЫСОКИЙ"},
        "medium": {"icon": "🟡", "name": "СРЕДНИЙ"},
        "low": {"icon": "🟢", "name": "НИЗКИЙ"},
    }

    status_config = {
        "pending": {"icon": "📝", "name": "АКТИВНА"},
        "completed": {"icon": "✅", "name": "ВЫПОЛНЕНА"},
        "deleted": {"icon": "🗑️", "name": "УДАЛЕНА"},
    }

    config = priority_config.get(priority, priority_config["medium"])
    status_info = status_config.get(status, status_config["pending"])
    card = f"{config['icon']} <b>ЗАДАЧА #{task_id}</b> {status_info['icon']}\n"

    if len(content) > 50:
        words = content.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line + word) <= 35:
                current_line += word + " "
            else:
                lines.append(current_line.strip())
                current_line = word + " "

        if current_line:
            lines.append(current_line.strip())

        for i, line in enumerate(lines):
            prefix = "📝 " if i == 0 else "   "
            card += f"<code></code>{prefix}{line}\n"
    else:
        card += f"<code></code>{content}\n"

    card += f"<code></code>Приоритет: {config['icon']} {config['name']}\n"
    card += f"<code></code> Статус: {status_info['icon']} {status_info['name']}\n"

    due_text = format_due_date(due_date)
    card += f"<code></code>{due_text}\n"

    if task_tags:
        tags_text = " ".join([f"<code>#{tag[1]}</code>" for tag in task_tags])
        card += f"<code></code>Теги: {tags_text}\n"

    return card


def describe_filters(filters: dict) -> str:
    """Описание примененных фильтров"""
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


async def format_and_send_tasks(
    message: Message, tasks: list, title: str = "📋 Ваши задачи"
):
    """Форматирует и отправляет задачи с разбивкой на несколько сообщений"""
    if not tasks:
        await message.answer(
            "🎉 <b>Пока нет задач!</b>\n\n"
            "<i>Используйте кнопку '📝 Новая задача' чтобы создать первую</i>",
            parse_mode="HTML",
            reply_markup=get_tasks_keyboard(),
        )
        return

    chunk_size = 10
    task_chunks = [tasks[i : i + chunk_size] for i in range(0, len(tasks), chunk_size)]

    for chunk_index, task_chunk in enumerate(task_chunks):
        if chunk_index == 0:

            tasks_text = f"<b>{title}</b>\n\n"
        else:

            tasks_text = f"<b>{title} (продолжение {chunk_index + 1})</b>\n\n"

        for i, task in enumerate(task_chunk, 1):
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

            display_content = content
            if len(display_content) > 50:
                display_content = display_content[:47] + "..."

            tasks_text += f"{icon} <b>#{task_id}</b> - {display_content}\n"

            if due_date:
                due_text = format_due_date(due_date)
                tasks_text += f"{due_text}\n"

            if tags_text:
                tasks_text += f"🏷️ {tags_text}\n"

            tasks_text += "\n"

        if chunk_index == len(task_chunks) - 1:
            tasks_text += f"<i>Всего: {len(tasks)} задач</i>"

        if len(tasks_text) > 4000:
            tasks_text = f"<b>{title}</b>\n\n"
            for task in task_chunk:
                task_data = extract_task_data(task)
                if not task_data:
                    continue
                task_id, content, due_date, priority, status, is_deleted = task_data

                icon = (
                    "✅"
                    if status == "completed"
                    else (
                        "🗑️"
                        if is_deleted
                        else {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                            priority, "🟡"
                        )
                    )
                )
                display_content = content[:40] + "..." if len(content) > 40 else content
                tasks_text += f"{icon} <b>#{task_id}</b> {display_content}\n"

            if chunk_index == len(task_chunks) - 1:
                tasks_text += f"\n<i>Всего: {len(tasks)} задач</i>"

        await message.answer(
            tasks_text,
            parse_mode="HTML",
            reply_markup=(
                get_tasks_keyboard() if chunk_index == len(task_chunks) - 1 else None
            ),
        )


async def show_all_tasks(message: Message):
    """Показать все активные задачи"""
    tasks = await db.get_user_tasks_with_priority(message.from_user.id, "pending")

    if not tasks:
        await message.answer(
            "🎉 У вас нет активных задач!", reply_markup=get_tasks_keyboard()
        )
        return

    await format_and_send_tasks(message, tasks, "📋 Ваши активные задачи")


async def show_urgent_tasks(message: Message):
    """Показать срочные задачи"""
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


async def show_upcoming_tasks(message: Message):
    """Показать ближайшие задачи"""
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


async def show_overdue_tasks(message: Message):
    """Показать просроченные задачи"""
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


async def show_today_tasks(message: Message):
    """Показать задачи на сегодня"""
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
    """Получить статистику хранилища"""
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

    if reminder_manager:
        try:
            await reminder_manager.update_reminders_for_edited_task(
                user_id=message.from_user.id, task_id=task_id, new_due_date=due_datetime
            )
            response_text += "\n🔔 Напоминания обновлены!"
        except Exception as e:
            print(f"❌ Ошибка при обновлении напоминаний: {e}")
            response_text += "\n⚠️ Не удалось обновить напоминания"
    else:
        print(f"❌ Ошибка при обновлении напоминаний")

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
    """Описание примененных фильтров"""
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


@router.message(Command("overdue"))
async def cmd_overdue(message: Message):
    """Показывает просроченные задачи"""
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


@router.message(StateFilter(TaskGrouping.waiting_for_group_type))
async def process_group_type(message: Message, state: FSMContext):
    """Обработка выбора типа группировки"""
    if await handle_navigation(message, state):
        return

    if message.text == "🏷️ По тегам":
        await group_by_tags(message, state)

    elif message.text == "🎯 По приоритетам":
        await group_by_priority(message, state)

    elif message.text == "📅 По датам":
        await group_by_date(message, state)

    elif message.text == "📊 По статусу":
        await group_by_status(message, state)

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
        empty_msg = (
            f"🏷️ <b>ГРУППИРОВКА ПО ТЕГАМ</b>\n"
            f"<code></code> 📊 Состояние: <b>НЕТ АКТИВНЫХ ЗАДАЧ</b>\n"
            f"<code></code> 💡 Рекомендации:\n"
            f"<code></code> • Создайте новые задачи\n"
            f"<code></code> • Добавьте к ним теги\n"
            f"<code></code> • Используйте теги для организации\n"
        )
        await message.answer(
            empty_msg, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )
        await state.clear()
        return

    tasks_by_tag = {}
    tasks_without_tags = []

    for task in tasks:
        task_data = extract_task_data(task)
        if not task_data:
            continue

        task_id = task_data[0]
        task_tags = await db.get_task_tags(task_id)

        if task_tags:
            for tag in task_tags:
                tag_name = tag[1]
                if tag_name not in tasks_by_tag:
                    tasks_by_tag[tag_name] = []
                tasks_by_tag[tag_name].append(task)
        else:
            tasks_without_tags.append(task)

    total_tasks = len(tasks)
    total_tags = len(tasks_by_tag)

    header = (
        f"🏷️ <b>ГРУППИРОВКА ПО ТЕГАМ</b>\n"
        f"<code></code> 📊 Всего задач: <b>{total_tasks}</b>\n"
        f"<code></code> 🏷️ Уникальных тегов: <b>{total_tags}</b>\n"
        f"<code></code> 🔸 Без тегов: <b>{len(tasks_without_tags)}</b>\n"
    )

    await message.answer(header, parse_mode="HTML")

    for tag_name, tag_tasks in tasks_by_tag.items():
        await process_tag_group(message, tag_name, tag_tasks)

    if tasks_without_tags:
        await process_tag_group(message, "БЕЗ ТЕГОВ", tasks_without_tags)

    footer = (
        f"📈 <b>ИТОГИ ГРУППИРОВКИ ПО ТЕГАМ</b>\n"
        f"<code></code> 📊 Всего обработано: <b>{total_tasks}</b> задач\n"
        f"<code></code> 🏷️ Тегов использовано: <b>{total_tags}</b>\n"
        f"<code></code> 🔸 Без тегов: <b>{len(tasks_without_tags)}</b>\n"
    )

    await message.answer(footer, parse_mode="HTML", reply_markup=get_tasks_keyboard())
    await state.clear()


async def process_tag_group(message: Message, tag_name: str, tasks: list):
    """Обрабатывает одну группу тегов"""
    total_tasks = len(tasks)
    overdue_count = 0
    today_count = 0
    urgent_count = 0

    for task in tasks:
        task_data = extract_task_data(task)
        if task_data and task_data[2]:
            try:
                due_date = task_data[2]
                if "T" in due_date:
                    due_datetime = datetime.fromisoformat(due_date)
                else:
                    due_datetime = datetime.fromisoformat(due_date + "T00:00:00")

                if due_datetime < datetime.now():
                    overdue_count += 1
                elif due_datetime.date() == datetime.now().date():
                    today_count += 1
                    urgent_count += 1
                elif (due_datetime.date() - datetime.now().date()).days <= 2:
                    urgent_count += 1
            except:
                pass

    if tag_name == "БЕЗ ТЕГОВ":
        group_header = "🔸 <b>ЗАДАЧИ БЕЗ ТЕГОВ</b>"
        icon = "🔸"
    else:
        group_header = f"🏷️ <b>ТЕГ: #{tag_name}</b>"
        icon = "🏷️"

    header = (
        f"{group_header}\n" f"<code></code> 📊 Задач в группе: <b>{total_tasks}</b>\n"
    )

    if overdue_count > 0:
        header += f"<code></code> 🚨 Просрочено: <b>{overdue_count}</b>\n"
    if today_count > 0:
        header += f"<code></code> 🎯 На сегодня: <b>{today_count}</b>\n"
    if urgent_count > 0:
        header += f"<code></code> ⚡ Срочные: <b>{urgent_count}</b>\n"

    await message.answer(header, parse_mode="HTML")

    for i, task in enumerate(tasks, 1):
        task_data = extract_task_data(task)
        if task_data:
            task_id, content, due_date, priority, status, is_deleted = task_data
            all_task_tags = await db.get_task_tags(task_id)
            card = create_task_card(task_data, all_task_tags)
            card += f"\n📁 <i>Группа: {tag_name} | Задача {i} из {total_tasks}</i>"

            await message.answer(card, parse_mode="HTML")

        if i % 2 == 0:
            await asyncio.sleep(0.1)


async def group_by_priority(message: Message, state: FSMContext):
    """Группировка задач по приоритетам с детальными карточками"""
    user_id = message.from_user.id

    try:
        tasks = await db.get_user_tasks_with_priority(user_id, "pending")

        if not tasks:
            empty_msg = (
                f"🎯 <b>ГРУППИРОВКА ПО ПРИОРИТЕТАМ</b>\n"
                f"<code></code> 📊 Состояние: <b>НЕТ АКТИВНЫХ ЗАДАЧ</b>\n"
                f"<code></code> 💡 Создайте новые задачи!\n"
            )
            await message.answer(
                empty_msg, parse_mode="HTML", reply_markup=get_tasks_keyboard()
            )
            await state.clear()
            return

        tasks_by_priority = {"high": [], "medium": [], "low": []}

        for task in tasks:
            task_data = extract_task_data(task)
            if task_data:
                priority = task_data[3]
                if priority in tasks_by_priority:
                    tasks_by_priority[priority].append(task)

        total_tasks = len(tasks)
        high_count = len(tasks_by_priority["high"])
        medium_count = len(tasks_by_priority["medium"])
        low_count = len(tasks_by_priority["low"])
        header = (
            f"🎯 <b>ГРУППИРОВКА ПО ПРИОРИТЕТАМ</b>\n"
            f"<code></code> 📊 Всего задач: <b>{total_tasks}</b>\n"
            f"<code></code> 🔴 Высокий: <b>{high_count}</b>\n"
            f"<code></code> 🟡 Средний: <b>{medium_count}</b>\n"
            f"<code></code> 🟢 Низкий: <b>{low_count}</b>\n"
        )

        await message.answer(header, parse_mode="HTML")
        priority_config = {
            "high": {"name": "🔴 ВЫСОКИЙ ПРИОРИТЕТ", "icon": "🔴"},
            "medium": {"name": "🟡 СРЕДНИЙ ПРИОРИТЕТ", "icon": "🟡"},
            "low": {"name": "🟢 НИЗКИЙ ПРИОРИТЕТ", "icon": "🟢"},
        }

        for priority, priority_tasks in tasks_by_priority.items():
            if priority_tasks:
                config = priority_config[priority]
                await process_priority_group(
                    message, config["name"], config["icon"], priority_tasks
                )

        footer = (
            f"📈 <b>ИТОГИ ГРУППИРОВКИ ПО ПРИОРИТЕТАМ</b>\n"
            f"<code></code> 📊 Всего обработано: <b>{total_tasks}</b> задач\n"
            f"<code></code> 🔴 Высокий: <b>{high_count}</b>\n"
            f"<code></code> 🟡 Средний: <b>{medium_count}</b>\n"
            f"<code></code> 🟢 Низкий: <b>{low_count}</b>\n"
        )

        await message.answer(
            footer, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )

    except Exception as e:
        error_msg = (
            f"❌ <b>ОШИБКА ГРУППИРОВКИ ПО ПРИОРИТЕТАМ</b>\n"
            f"<code></code> 🔧 Техническая информация:\n"
            f"<code></code> • Ошибка: {str(e)[:50]}...\n"
        )
        await message.answer(
            error_msg, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )

    await state.clear()


async def process_priority_group(
    message: Message, group_name: str, icon: str, tasks: list
):
    """Обрабатывает одну группу приоритетов"""
    total_tasks = len(tasks)
    overdue_count = 0
    today_count = 0
    urgent_count = 0

    for task in tasks:
        task_data = extract_task_data(task)
        if task_data and task_data[2]:
            try:
                due_date = task_data[2]
                if "T" in due_date:
                    due_datetime = datetime.fromisoformat(due_date)
                else:
                    due_datetime = datetime.fromisoformat(due_date + "T00:00:00")

                if due_datetime < datetime.now():
                    overdue_count += 1
                    urgent_count += 1
                elif due_datetime.date() == datetime.now().date():
                    today_count += 1
                    urgent_count += 1
                elif (due_datetime.date() - datetime.now().date()).days <= 2:
                    urgent_count += 1
            except:
                pass

    header = (
        f"{icon} <b>{group_name}</b>\n"
        f"<code></code> 📊 Задач в группе: <b>{total_tasks}</b>\n"
    )

    if overdue_count > 0:
        header += f"<code></code> 🚨 Просрочено: <b>{overdue_count}</b>\n"
    if today_count > 0:
        header += f"<code></code> 🎯 На сегодня: <b>{today_count}</b>\n"
    if urgent_count > 0:
        header += f"<code></code> ⚡ Срочные: <b>{urgent_count}</b>\n"

    await message.answer(header, parse_mode="HTML")
    for i, task in enumerate(tasks, 1):
        task_data = extract_task_data(task)
        if task_data:
            task_id, content, due_date, priority, status, is_deleted = task_data
            task_tags = await db.get_task_tags(task_id)
            card = create_task_card(task_data, task_tags)
            card += f"\n📁 <i>Группа: {group_name} | Задача {i} из {total_tasks}</i>"

            await message.answer(card, parse_mode="HTML")

        if i % 2 == 0:
            await asyncio.sleep(0.1)


async def group_by_date(message: Message, state: FSMContext):
    """Группировка задач по датам с детальными карточками"""
    user_id = message.from_user.id

    try:
        tasks = await db.get_user_tasks_with_priority(user_id, "pending")

        if not tasks:
            empty_msg = (
                f"📅 <b>ГРУППИРОВКА ПО ДАТАМ</b>\n"
                f"<code></code> 📊 Состояние: <b>НЕТ АКТИВНЫХ ЗАДАЧ</b>\n"
                f"<code></code> 💡 Создайте задачи со сроками!\n"
            )
            await message.answer(
                empty_msg, parse_mode="HTML", reply_markup=get_tasks_keyboard()
            )
            await state.clear()
            return

        today = datetime.now().date()
        tasks_by_date = {
            "ПРОСРОЧЕННЫЕ": [],
            "СЕГОДНЯ": [],
            "ЗАВТРА": [],
            "ЭТА НЕДЕЛЯ": [],
            "БУДУЩЕЕ": [],
            "БЕЗ СРОКА": [],
        }

        for task in tasks:
            task_data = extract_task_data(task)
            if not task_data:
                continue

            due_date = task_data[2]
            if not due_date:
                tasks_by_date["БЕЗ СРОКА"].append(task)
                continue

            try:
                if "T" in due_date:
                    due_datetime = datetime.fromisoformat(due_date)
                else:
                    due_datetime = datetime.fromisoformat(due_date + "T00:00:00")

                due_date_only = due_datetime.date()

                if due_date_only < today:
                    tasks_by_date["ПРОСРОЧЕННЫЕ"].append(task)
                elif due_date_only == today:
                    tasks_by_date["СЕГОДНЯ"].append(task)
                elif due_date_only == today + timedelta(days=1):
                    tasks_by_date["ЗАВТРА"].append(task)
                elif (due_date_only - today).days <= 7:
                    tasks_by_date["ЭТА НЕДЕЛЯ"].append(task)
                else:
                    tasks_by_date["БУДУЩЕЕ"].append(task)

            except (ValueError, TypeError):
                tasks_by_date["БЕЗ СРОКА"].append(task)

        total_tasks = len(tasks)
        overdue_count = len(tasks_by_date["ПРОСРОЧЕННЫЕ"])
        today_count = len(tasks_by_date["СЕГОДНЯ"])
        tomorrow_count = len(tasks_by_date["ЗАВТРА"])
        week_count = len(tasks_by_date["ЭТА НЕДЕЛЯ"])
        future_count = len(tasks_by_date["БУДУЩЕЕ"])
        no_date_count = len(tasks_by_date["БЕЗ СРОКА"])

        header = (
            f"📅 <b>ГРУППИРОВКА ПО ДАТАМ</b>\n"
            f"<code></code> 📊 Всего задач: <b>{total_tasks}</b>\n"
            f"<code></code> 🚨 Просрочено: <b>{overdue_count}</b>\n"
            f"<code></code> 🎯 Сегодня: <b>{today_count}</b>\n"
            f"<code></code> ⏰ Завтра: <b>{tomorrow_count}</b>\n"
            f"<code></code> 📅 Неделя: <b>{week_count}</b>\n"
            f"<code></code> 🗓️ Будущее: <b>{future_count}</b>\n"
            f"<code></code> ⏳ Без срока: <b>{no_date_count}</b>\n"
        )

        await message.answer(header, parse_mode="HTML")
        date_config = {
            "ПРОСРОЧЕННЫЕ": {"tasks": tasks_by_date["ПРОСРОЧЕННЫЕ"], "icon": "🚨"},
            "СЕГОДНЯ": {"tasks": tasks_by_date["СЕГОДНЯ"], "icon": "🎯"},
            "ЗАВТРА": {"tasks": tasks_by_date["ЗАВТРА"], "icon": "⏰"},
            "ЭТА НЕДЕЛЯ": {"tasks": tasks_by_date["ЭТА НЕДЕЛЯ"], "icon": "📅"},
            "БУДУЩЕЕ": {"tasks": tasks_by_date["БУДУЩЕЕ"], "icon": "🗓️"},
            "БЕЗ СРОКА": {"tasks": tasks_by_date["БЕЗ СРОКА"], "icon": "⏳"},
        }

        for date_name, date_data in date_config.items():
            if date_data["tasks"]:
                await process_date_group(
                    message, date_name, date_data["icon"], date_data["tasks"]
                )

        footer = (
            f"📈 <b>ИТОГИ ГРУППИРОВКИ ПО ДАТАМ</b>\n"
            f"<code></code> 📊 Всего обработано: <b>{total_tasks}</b> задач\n"
            f"<code></code> 🚨 Просрочено: <b>{overdue_count}</b>\n"
            f"<code></code> 🎯 Сегодня: <b>{today_count}</b>\n"
            f"<code></code> ⏰ Завтра: <b>{tomorrow_count}</b>\n"
            f"<code></code> 📅 Неделя: <b>{week_count}</b>\n"
            f"<code></code> 🗓️ Будущее: <b>{future_count}</b>\n"
            f"<code></code> ⏳ Без срока: <b>{no_date_count}</b>\n"
        )

        await message.answer(
            footer, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )

    except Exception as e:
        error_msg = (
            f"❌ <b>ОШИБКА ГРУППИРОВКИ ПО ДАТАМ</b>\n"
            f"<code></code> 🔧 Техническая информация:\n"
            f"<code></code> • Ошибка: {str(e)[:50]}...\n"
        )
        await message.answer(
            error_msg, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )

    await state.clear()


async def group_by_status(message: Message, state: FSMContext):
    """Группировка задач по статусам с детальными карточками"""
    user_id = message.from_user.id

    try:
        active_tasks = await db.get_user_tasks_with_priority(user_id, "pending")
        completed_tasks = await db.get_user_tasks(user_id, "completed")
        deleted_tasks = await db.get_deleted_tasks(user_id)
        total_tasks = len(active_tasks) + len(completed_tasks) + len(deleted_tasks)

        if total_tasks == 0:
            empty_msg = (
                f"📊 <b>ГРУППИРОВКА ПО СТАТУСАМ</b>\n"
                f"<code></code> 📊 Состояние: <b>НЕТ ЗАДАЧ</b>\n"
                f"<code></code> 💡 Создайте первую задачу!\n"
            )
            await message.answer(
                empty_msg, parse_mode="HTML", reply_markup=get_tasks_keyboard()
            )
            await state.clear()
            return

        header = (
            f"📊 <b>ГРУППИРОВКА ПО СТАТУСАМ</b>\n"
            f"<code></code> 📊 Всего задач: <b>{total_tasks}</b>\n"
            f"<code></code> 📝 Активные: <b>{len(active_tasks)}</b>\n"
            f"<code></code> ✅ Выполненные: <b>{len(completed_tasks)}</b>\n"
            f"<code></code> 🗑️ Удаленные: <b>{len(deleted_tasks)}</b>\n"
        )

        await message.answer(header, parse_mode="HTML")
        status_config = {
            "АКТИВНЫЕ": {"tasks": active_tasks, "icon": "📝"},
            "ВЫПОЛНЕННЫЕ": {"tasks": completed_tasks, "icon": "✅"},
            "УДАЛЕННЫЕ": {"tasks": deleted_tasks, "icon": "🗑️"},
        }

        for status_name, status_data in status_config.items():
            if status_data["tasks"]:
                await process_status_group(
                    message, status_name, status_data["icon"], status_data["tasks"]
                )

        footer = (
            f"📈 <b>ИТОГИ ГРУППИРОВКИ ПО СТАТУСАМ</b>\n"
            f"<code></code> 📊 Всего обработано: <b>{total_tasks}</b> задач\n"
            f"<code></code> 📝 Активные: <b>{len(active_tasks)}</b>\n"
            f"<code></code> ✅ Выполненные: <b>{len(completed_tasks)}</b>\n"
            f"<code></code> 🗑️ Удаленные: <b>{len(deleted_tasks)}</b>\n"
        )

        await message.answer(
            footer, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )

    except Exception as e:
        error_msg = (
            f"❌ <b>ОШИБКА ГРУППИРОВКИ ПО СТАТУСАМ</b>\n"
            f"<code></code> 🔧 Техническая информация:\n"
            f"<code></code> • Ошибка: {str(e)[:50]}...\n"
        )
        await message.answer(
            error_msg, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )

    await state.clear()


async def process_status_group(
    message: Message, status_name: str, icon: str, tasks: list
):
    """Обрабатывает одну группу статусов"""
    total_tasks = len(tasks)

    header = (
        f"{icon} <b>СТАТУС: {status_name}</b>\n"
        f"<code></code> 📊 Задач в группе: <b>{total_tasks}</b>\n"
    )
    await message.answer(header, parse_mode="HTML")
    for i, task in enumerate(tasks, 1):
        task_data = extract_task_data(task)
        if task_data:
            task_id, content, due_date, priority, status, is_deleted = task_data

            task_tags = await db.get_task_tags(task_id)
            card = create_task_card(task_data, task_tags)
            card += f"\n📁 <i>Группа: {status_name} | Задача {i} из {total_tasks}</i>"

            await message.answer(card, parse_mode="HTML")

        if i % 2 == 0:
            await asyncio.sleep(0.1)


async def process_date_group(message: Message, date_name: str, icon: str, tasks: list):
    """Обрабатывает одну группу дат"""
    total_tasks = len(tasks)

    header = (
        f"{icon} <b>ДАТА: {date_name}</b>\n"
        f"<code></code> 📊 Задач в группе: <b>{total_tasks}</b>\n"
    )

    await message.answer(header, parse_mode="HTML")

    for i, task in enumerate(tasks, 1):
        task_data = extract_task_data(task)
        if task_data:
            task_id, content, due_date, priority, status, is_deleted = task_data

            task_tags = await db.get_task_tags(task_id)
            card = create_task_card(task_data, task_tags)
            card += f"\n📁 <i>Группа: {date_name} | Задача {i} из {total_tasks}</i>"

            await message.answer(card, parse_mode="HTML")
        if i % 2 == 0:
            await asyncio.sleep(0.1)


async def group_by_specific_status(message: Message, state: FSMContext, status: str):
    """Группировка по конкретному статусу с детальными карточками"""
    user_id = message.from_user.id

    if status == "pending":
        tasks = await db.get_user_tasks_with_priority(user_id, "pending")
        status_name = "АКТИВНЫЕ"
        icon = "📝"
    elif status == "completed":
        tasks = await db.get_user_tasks(user_id, "completed")
        status_name = "ВЫПОЛНЕННЫЕ"
        icon = "✅"
    elif status == "deleted":
        tasks = await db.get_deleted_tasks(user_id)
        status_name = "УДАЛЕННЫЕ"
        icon = "🗑️"

    if not tasks:
        empty_msg = (
            f"{icon} <b>СТАТУС: {status_name}</b>\n"
            f"<code></code> 📊 Состояние: <b>НЕТ ЗАДАЧ</b>\n"
            f"<code></code> 💡 Создайте задачи с этим статусом!\n"
        )
        await message.answer(
            empty_msg, parse_mode="HTML", reply_markup=get_tasks_keyboard()
        )
        await state.clear()
        return

    await process_status_group(message, status_name, icon, tasks)
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
    """Показывает задачи за период"""
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
            f"{priority_icon} <b>#{task_id}</b> {display_content}\n"
            f"<code></code> {due_text}\n"
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
