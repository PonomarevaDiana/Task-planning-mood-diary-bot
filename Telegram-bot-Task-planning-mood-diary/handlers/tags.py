from aiogram import Router, F
import aiosqlite
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
    get_tags_keyboard,
    get_confirm_keyboard,
    get_back_keyboard,
    get_confirm_keyboard,
    get_back_keyboard,
)

router = Router()


class TagStates(StatesGroup):
    waiting_for_tag_name = State()
    waiting_for_tag_color = State()
    waiting_for_tag_selection = State()
    waiting_for_task_for_tag = State()


class NewTagStates(StatesGroup):
    waiting_for_tag_name = State()


class RemoveTagStates(StatesGroup):
    waiting_for_tag_name = State()
    waiting_for_confirmation = State()


class DelTagStates(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_tag_name = State()
    waiting_for_confirmation = State()


class AddTagStates(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_tag_name = State()
    waiting_for_confirmation = State()
    waiting_for_tag_creation = State()


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
