from aiogram import Router, F
from aiogram.types import (
    Message,
    BufferedInputFile,
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from datetime import datetime, timedelta
import os
from PIL import Image, ImageDraw, ImageFont
import tempfile

from handlers.common import handle_navigation

from keyboards import (
    get_main_keyboard,
    get_moods_keyboard,
    get_mood_selection_keyboard,
    get_mood_period_keyboard,
    get_mood_calendar_keyboard,
    get_back_keyboard,
    get_back_moods_keyboard,
    get_notes_keyboard,
)

router = Router()

MOOD_EMOJIS = {
    "отлично": "😊",
    "хорошо": "🙂",
    "нормально": "😐",
    "плохо": "😔",
    "ужасно": "😢",
}


EMOJI_TO_MOOD = {
    "😊": "отлично",
    "🙂": "хорошо",
    "😐": "нормально",
    "😔": "плохо",
    "😢": "ужасно",
}


class MoodStates(StatesGroup):
    waiting_for_mood = State()
    waiting_for_notes = State()
    waiting_for_note_update = State()
    waiting_for_stats_period = State()
    waiting_for_mood_update = State()


class MoodCalendarStates(StatesGroup):
    waiting_for_calendar_period = State()


@router.message(F.text == "😊 Настроения")
@router.message(Command("mood"))
async def cmd_mood(message: Message):
    """Главное меню настроений"""
    await message.answer(
        "😊 Управление настроениями\n\n" "Выберите действие:",
        reply_markup=get_moods_keyboard(),
    )


@router.message(F.text == "😊 Записать настроение")
async def handle_record_mood(message: Message, state: FSMContext):
    """Начать процесс записи настроения"""
    today_mood = await db.get_today_mood(message.from_user.id)

    if today_mood:
        mood_id, user_id, mood, notes, date = today_mood
        emoji = MOOD_EMOJIS.get(mood, "")

        await message.answer(
            f"💭 Хотите изменить настроение ?\n\n",
            reply_markup=get_mood_selection_keyboard(),
        )
        await state.update_data(
            existing_mood=True, current_mood=mood, current_notes=notes
        )
    else:
        await message.answer(
            "😊 Как ваше настроение сегодня?\n\n" "Выберите вариант из меню ниже:",
            reply_markup=get_mood_selection_keyboard(),
        )
        await state.update_data(existing_mood=False)

    await state.set_state(MoodStates.waiting_for_mood)


@router.message(F.text == "📝 Заметки")
async def cmd_quick_actions(message: Message, state: FSMContext):
    await message.answer(
        "📝 Действия с заметками\n\n" "Выберите действие:",
        reply_markup=get_notes_keyboard(),
    )


@router.message(F.text == "📊 Сегодняшнее настроение")
@router.message(Command("mood_today"))
async def handle_today_mood(message: Message):
    """Показать сегодняшнее настроение"""
    mood_data = await db.get_today_mood(message.from_user.id)

    if mood_data:
        mood_id, user_id, mood, notes, date = mood_data
        emoji = MOOD_EMOJIS.get(mood, "")
        response = f"📊 Сегодняшнее настроение: {mood} {emoji}"

        if notes:
            response += f"\n📝 Заметка: {notes}"
        else:
            response += f"\n💭 Заметка: не добавлена"

        response += f"\n\n🔄 Чтобы изменить: нажмите '😊 Записать настроение'"
    else:
        response = (
            "📝 Вы еще не отмечали настроение сегодня.\n"
            "Нажмите '😊 Записать настроение' чтобы записать настроение"
        )

    await message.answer(response, reply_markup=get_moods_keyboard())


@router.message(F.text == "📝 Добавить заметку")
@router.message(F.text == "✏️ Изменить заметку")
async def handle_mood_note(message: Message, state: FSMContext):
    """Добавить/изменить заметку к сегодняшнему настроению"""
    mood_data = await db.get_today_mood(message.from_user.id)

    if not mood_data:
        await message.answer(
            "❌ Сначала укажите настроение через '😊 Записать настроение'",
            reply_markup=get_moods_keyboard(),
        )
        return

    mood_id, user_id, mood, notes, date = mood_data
    emoji = MOOD_EMOJIS.get(mood, "")

    if message.text == "✏️ Изменить заметку" and notes:
        await message.answer(
            f"{emoji} Текущая заметка: {notes}\n\n" f"📝 Введите новую заметку:",
            reply_markup=get_back_moods_keyboard(),
        )
    else:
        await message.answer(
            f"{emoji} Настроение: {mood}\n\n"
            f"📝 Введите заметку к вашему настроению:",
            reply_markup=get_back_moods_keyboard(),
        )

    await state.update_data(
        current_mood=mood,
        current_notes=notes,
        update_notes_only=True,
        is_editing_note=True,
    )
    await state.set_state(MoodStates.waiting_for_note_update)


@router.message(F.text == "🗑️ Удалить заметку")
async def handle_delete_mood_note(message: Message):
    """Удалить заметку к сегодняшнему настроению"""
    try:
        print(
            f"🔍 [DELETE_MOOD_NOTE] Начинаем удаление заметки для пользователя {message.from_user.id}"
        )

        mood_data = await db.get_today_mood(message.from_user.id)

        if not mood_data:
            await message.answer(
                "❌ У вас нет записи настроения на сегодня",
                reply_markup=get_moods_keyboard(),
            )
            return

        mood_id, user_id, mood, notes, date = mood_data
        emoji = MOOD_EMOJIS.get(mood, "")

        if notes is None or (isinstance(notes, str) and notes.strip() == ""):
            await message.answer(
                f"{emoji} У вас нет заметки к настроению '{mood}'",
                reply_markup=get_moods_keyboard(),
            )
            return

        success = await db.update_mood_notes(message.from_user.id, None)

        if success:
            await message.answer(
                f"🗑️ Заметка удалена для настроения '{mood}' {emoji}",
                reply_markup=get_moods_keyboard(),
            )
        else:
            await message.answer(
                f"❌ Не удалось удалить заметку (функция вернула False)",
                reply_markup=get_moods_keyboard(),
            )

    except Exception as e:
        print(f"❌ [DELETE_MOOD_NOTE] Ошибка: {e}")
        import traceback

        traceback.print_exc()
        await message.answer(
            f"❌ Ошибка при удалении заметки: {e}",
            reply_markup=get_moods_keyboard(),
        )


@router.message(F.text == "📈 Статистика настроений")
@router.message(Command("mood_stats"))
async def handle_mood_stats(message: Message, state: FSMContext):
    """Начать процесс получения статистики настроения"""
    await message.answer(
        "📊 Статистика настроения\n\n" "Выберите период для анализа:",
        reply_markup=get_mood_period_keyboard(),
    )
    await state.set_state(MoodStates.waiting_for_stats_period)


@router.message(F.text == "📅 Календарь настроений")
@router.message(Command("mood_calendar"))
async def handle_mood_calendar(message: Message, state: FSMContext):
    """Начать процесс настройки календаря настроений"""
    await message.answer(
        "📅 Календарь настроений\n\n"
        "Выберите период для отображения или введите сами нужное количество дней:",
        reply_markup=get_mood_calendar_keyboard(),
    )
    await state.set_state(MoodCalendarStates.waiting_for_calendar_period)


@router.message(StateFilter(MoodStates.waiting_for_mood))
async def process_mood_selection(message: Message, state: FSMContext):
    """Обработка выбора настроения"""
    if await handle_navigation(message, state):
        return

    selected_mood = None

    mood_mapping = {
        "😊 Отлично": "отлично",
        "🙂 Хорошо": "хорошо",
        "😐 Нормально": "нормально",
        "😔 Плохо": "плохо",
        "😢 Ужасно": "ужасно",
    }
    selected_mood = mood_mapping.get(message.text)

    if not selected_mood:
        await message.answer(
            "❌ Пожалуйста, выберите настроение из предложенных вариантов:",
            reply_markup=get_mood_selection_keyboard(),
        )
        return

    data = await state.get_data()
    existing_mood = data.get("existing_mood", False)
    current_mood = data.get("current_mood")
    current_notes = data.get("current_notes", "")

    if existing_mood and current_mood == selected_mood:
        emoji = MOOD_EMOJIS.get(selected_mood, "")
        response = f"✅ Настроение осталось прежним: {selected_mood} {emoji}"
        if current_notes:
            response += f"\n📝 Заметка: {current_notes}"
        await message.answer(response, reply_markup=get_moods_keyboard())
        await state.clear()
        return

    elif existing_mood:
        old_emoji = MOOD_EMOJIS.get(current_mood, "")
        new_emoji = MOOD_EMOJIS.get(selected_mood, "")

        await db.update_mood_with_notes(
            message.from_user.id, selected_mood, current_notes
        )

        response = (
            f"✅ Настроение обновлено!\n\n"
            f"Было: {current_mood} {old_emoji}\n"
            f"Стало: {selected_mood} {new_emoji}"
        )
        if current_notes:
            response += f"\n📝 Заметка сохранена: {current_notes}"

        await message.answer(response, reply_markup=get_moods_keyboard())
        await state.clear()
        return
    else:
        emoji = MOOD_EMOJIS[selected_mood]
        await message.answer(
            f"{emoji} Настроение '{selected_mood}' записано!\n\n"
            f"💭 Хотите добавить заметку? (напишите текст или 'нет' чтобы пропустить)",
            reply_markup=get_back_keyboard(),
        )
        await state.update_data(selected_mood=selected_mood)
        await state.set_state(MoodStates.waiting_for_notes)


@router.message(StateFilter(MoodStates.waiting_for_mood_update))
async def process_mood_update_confirmation(message: Message, state: FSMContext):
    """Обработка подтверждения изменения настроения"""
    if await handle_navigation(message, state):
        return
    answer = message.text.lower().strip()

    if answer in ["✅ подтвердить", "да", "yes", "y", "д"]:
        data = await state.get_data()
        selected_mood = data["selected_mood"]
        current_notes = data.get("current_notes")

        await db.update_mood_with_notes(
            message.from_user.id, selected_mood, current_notes
        )

        emoji = MOOD_EMOJIS.get(selected_mood, "")
        await message.answer(
            f"✅ Настроение обновлено на: {selected_mood} {emoji}\n\n"
            f"💭 Хотите изменить заметку? (напишите текст или 'нет' чтобы оставить текущую)",
            reply_markup=get_back_keyboard(),
        )
        await state.set_state(MoodStates.waiting_for_note_update)


@router.message(StateFilter(MoodStates.waiting_for_notes))
async def process_mood_notes(message: Message, state: FSMContext):
    """Обработка заметки для нового настроения"""
    if await handle_navigation(message, state):
        return
    data = await state.get_data()
    mood_name = data["selected_mood"]
    user_notes = message.text.strip()

    emoji = MOOD_EMOJIS[mood_name]

    if user_notes.lower() == "нет":
        await db.add_mood_with_notes(message.from_user.id, mood_name, None)
        response = (
            f"{emoji} Настроение '{mood_name}' записано!\n💭 Заметка не добавлена"
        )
    else:
        await db.add_mood_with_notes(message.from_user.id, mood_name, user_notes)
        response = (
            f"{emoji} Настроение '{mood_name}' записано!\n📝 Заметка: {user_notes}"
        )

    await message.answer(response, reply_markup=get_moods_keyboard())
    await state.clear()


@router.message(StateFilter(MoodStates.waiting_for_note_update))
async def process_mood_note_update(message: Message, state: FSMContext):
    """Обработка обновления заметки для существующего настроения"""

    if message.text in ["❌ Отмена", "🔙 Назад"]:
        print(f"🚨 DEBUG MOOD NOTE: Cancel/back detected")
        await message.answer(
            "❌ Добавление заметки отменено", reply_markup=get_back_moods_keyboard()
        )
        await state.clear()
        return
    if await handle_navigation(message, state):
        return

    data = await state.get_data()
    mood_name = data.get("selected_mood") or data.get("current_mood")
    update_notes_only = data.get("update_notes_only", False)
    current_notes = data.get("current_notes")
    user_notes = message.text.strip()

    emoji = MOOD_EMOJIS.get(mood_name, "")

    if user_notes.lower() == "нет":
        notes_text = None
        note_action = "удалена" if current_notes else "не добавлена"
    else:
        notes_text = user_notes
        note_action = "обновлена"

    try:
        if update_notes_only:
            await db.update_mood_notes(message.from_user.id, notes_text)
            response = f"📝 Заметка {note_action} для настроения '{mood_name}' {emoji}"
        else:
            await db.update_mood_with_notes(message.from_user.id, mood_name, notes_text)
            response = f"✅ Настроение обновлено: '{mood_name}' {emoji}\n📝 Заметка {note_action}"

        if notes_text and note_action != "не добавлена":
            response += f"\n💬 Текст: {notes_text}"

        await message.answer(response, reply_markup=get_back_moods_keyboard())

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при обновлении заметки: {e}",
            reply_markup=get_back_moods_keyboard(),
        )

    await state.clear()


@router.message(StateFilter(MoodStates.waiting_for_stats_period))
@router.message(StateFilter(MoodCalendarStates.waiting_for_calendar_period))
async def process_period_selection(message: Message, state: FSMContext):
    """Универсальный обработчик периодов для статистики и календаря"""
    if await handle_navigation(message, state):
        return
    period_mapping = {
        "📅 7 дней": 7,
        "📅 14 дней": 14,
        "📅 30 дней": 30,
        "📅 60 дней": 60,
        "📅 90 дней": 90,
    }

    if message.text in period_mapping:
        days = period_mapping[message.text]
    else:
        try:
            days_text = message.text.strip()
            if not days_text:
                days = 30
            else:
                days = int(days_text)
        except ValueError:
            await message.answer(
                "❌ Неверный формат! Выберите период из меню или введите число:",
                reply_markup=get_mood_period_keyboard(),
            )
            return

    if days < 1:
        await message.answer(
            "❌ Количество дней должно быть положительным!",
            reply_markup=get_mood_period_keyboard(),
        )
        return

    if days > 365:
        await message.answer(
            "❌ Слишком большой период! Максимум 365 дней.",
            reply_markup=get_mood_period_keyboard(),
        )
        return

    stats = await db.get_mood_statistics(message.from_user.id, days)

    if not stats:
        await message.answer(
            f"📊 За последние {days} дней нет данных о настроении.",
            reply_markup=get_moods_keyboard(),
        )
        await state.clear()
        return

    current_state = await state.get_state()

    if current_state == MoodStates.waiting_for_stats_period.state:
        await send_mood_statistics(message, stats, days)
    else:
        await send_mood_calendar(message, stats, days)

    await state.clear()


async def send_mood_statistics(message: Message, stats: list, days: int):
    """Отправка статистики настроений"""
    mood_counts = {}
    for mood, date in stats:
        mood_counts[mood] = mood_counts.get(mood, 0) + 1

    total_days = len(stats)
    stats_text = f"📊 Статистика настроения за {total_days} дней:\n\n"

    mood_order = ["отлично", "хорошо", "нормально", "плохо", "ужасно"]
    for mood in mood_order:
        if mood in mood_counts:
            count = mood_counts[mood]
            percentage = (count / total_days) * 100
            emoji = MOOD_EMOJIS.get(mood, "")
            stats_text += f"{emoji} {mood}: {count} дней ({percentage:.1f}%)\n"

    if mood_counts:
        most_common_mood = max(mood_counts.items(), key=lambda x: x[1])
        emoji = MOOD_EMOJIS.get(most_common_mood[0], "")
        stats_text += f"\n🎯 Самое частое настроение: {most_common_mood[0]} {emoji}"

    await message.answer(stats_text, reply_markup=get_moods_keyboard())


async def send_mood_calendar(message: Message, stats: list, days: int):
    """Отправка календаря настроений"""
    try:
        await send_calendar_image(message, stats, days)

        calendar_text = await create_beautiful_text_calendar(stats, days)
        await message.answer(
            calendar_text, parse_mode="Markdown", reply_markup=get_moods_keyboard()
        )

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при создании календаря: {e}", reply_markup=get_moods_keyboard()
        )


async def send_calendar_image(message: Message, stats, days):
    """Отправляет изображение календаря"""
    try:
        image = create_calendar_image(stats, days)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            image.save(f, "PNG")
            temp_file = f.name

        with open(temp_file, "rb") as file:
            await message.answer_photo(
                BufferedInputFile(file.read(), filename="mood_calendar.png"),
                caption=f"🎭 *Календарь эмоционального состояния за {days} дней*\n\n"
                "📊 *Цветовая схема настроений:*\n"
                "🟢 Отлично\n🟡 Хорошо\n🟠 Нормально\n"
                "🔴 Плохо\n🟣 Ужасно\n⚪ Нет записи\n\n"
                "✨ *Сегодняшний день выделен рамкой*",
                parse_mode="Markdown",
            )

        os.unlink(temp_file)

    except Exception as e:
        await message.answer(f"❌ Ошибка при создании изображения календаря: {e}")


def create_calendar_image(stats, days):
    """Создает эстетичное изображение календаря настроений"""
    try:
        mood_by_date = {}
        for mood, date_str in stats:
            date_obj = datetime.fromisoformat(date_str).date()
            mood_by_date[date_obj] = mood

        mood_colors = {
            "отлично": (76, 175, 80),
            "хорошо": (255, 193, 7),
            "нормально": (255, 152, 0),
            "плохо": (244, 67, 54),
            "ужасно": (156, 39, 176),
        }

        default_color = (189, 189, 189)

        cell_size = 40
        padding = 20
        today = datetime.now().date()

        cols = 7
        rows = (days + cols - 1) // cols

        width = cols * cell_size + 2 * padding
        height = rows * cell_size + 2 * padding + 40

        image = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("arial.ttf", 12)
            title_font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
            title_font = ImageFont.load_default()

        title = f"Календарь настроений ({days} дней)"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        draw.text((title_x, 10), title, fill=(0, 0, 0), font=title_font)

        current_date = today - timedelta(days=days - 1)

        for row in range(rows):
            for col in range(cols):
                if current_date > today:
                    break

                x = padding + col * cell_size
                y = padding + 40 + row * cell_size

                mood = mood_by_date.get(current_date)
                color = mood_colors.get(mood, default_color)

                draw.rectangle(
                    [x, y, x + cell_size - 2, y + cell_size - 2],
                    fill=color,
                    outline=(200, 200, 200),
                )

                if current_date == today:
                    draw.rectangle(
                        [x - 2, y - 2, x + cell_size, y + cell_size],
                        outline=(0, 0, 0),
                        width=2,
                    )

                day_text = str(current_date.day)
                text_bbox = draw.textbbox((0, 0), day_text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                text_x = x + (cell_size - text_width) // 2
                text_y = y + (cell_size - text_height) // 2

                brightness = color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114
                text_color = (255, 255, 255) if brightness < 128 else (0, 0, 0)

                draw.text((text_x, text_y), day_text, fill=text_color, font=font)

                current_date += timedelta(days=1)

        return image

    except Exception as e:
        image = Image.new("RGB", (400, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except:
            font = ImageFont.load_default()

        error_text = f"Ошибка создания календаря: {str(e)}"
        draw.text((20, 80), error_text, fill=(255, 0, 0), font=font)
        return image


async def create_beautiful_text_calendar(stats, days):
    """Создает красивую текстовую статистику настроений"""
    mood_counts = {}
    mood_dates = {}

    for mood, date_str in stats:
        mood_counts[mood] = mood_counts.get(mood, 0) + 1
        date_obj = datetime.fromisoformat(date_str)
        if mood not in mood_dates:
            mood_dates[mood] = []
        mood_dates[mood].append(date_obj)

    total_days = len(stats)

    calendar_text = f"🎭 *Календарь настроений за {days} дней*\n\n"

    day_stats = {
        0: 0,
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        6: 0,
    }
    day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    for mood, date in stats:
        date_obj = datetime.fromisoformat(date)
        day_of_week = date_obj.weekday()
        day_stats[day_of_week] += 1

    best_days = sorted(day_stats.items(), key=lambda x: x[1], reverse=True)[:2]

    calendar_text += "📅 *Активность по дням недели:*\n"
    for day_num, count in sorted(day_stats.items()):
        percentage = (count / total_days) * 100 if total_days > 0 else 0
        calendar_text += f"{day_names[day_num]}: {count} зап. ({percentage:.1f}%)\n"

    if mood_counts:
        most_common = max(mood_counts.items(), key=lambda x: x[1])
        least_common = min(mood_counts.items(), key=lambda x: x[1])

        calendar_text += f"\n🎯 *Самое частое настроение:* {most_common[0]} {MOOD_EMOJIS.get(most_common[0], '')}\n"
        calendar_text += f"📉 *Самое редкое настроение:* {least_common[0]} {MOOD_EMOJIS.get(least_common[0], '')}\n"

    calendar_text += f"\n{MOOD_EMOJIS['отлично']} {mood_counts.get('отлично', 0)} "
    calendar_text += f"{MOOD_EMOJIS['хорошо']} {mood_counts.get('хорошо', 0)} "
    calendar_text += f"{MOOD_EMOJIS['нормально']} {mood_counts.get('нормально', 0)} "
    calendar_text += f"{MOOD_EMOJIS['плохо']} {mood_counts.get('плохо', 0)} "
    calendar_text += f"{MOOD_EMOJIS['ужасно']} {mood_counts.get('ужасно', 0)}"

    mood_scores = {"отлично": 5, "хорошо": 4, "нормально": 3, "плохо": 2, "ужасно": 1}

    total_score = 0
    for mood, count in mood_counts.items():
        total_score += mood_scores.get(mood, 3) * count

    if total_days > 0:
        average_score = total_score / total_days
        calendar_text += f"\n\n📊 *Средний балл:* {average_score:.2f}/5.0"

        if average_score >= 4.0:
            calendar_text += " 🌟 Отличные показатели!"
        elif average_score >= 3.0:
            calendar_text += " 👍 Хорошие показатели"
        else:
            calendar_text += " 💭 Есть над чем поработать"

    return calendar_text


def calculate_mood_score(mood_counts):
    """Рассчитывает средний балл настроения от 1 до 5"""
    mood_scores = {"отлично": 5, "хорошо": 4, "нормально": 3, "плохо": 2, "ужасно": 1}

    total_score = 0
    total_count = 0

    for mood, count in mood_counts.items():
        total_score += mood_scores.get(mood, 3) * count
        total_count += count

    return total_score / total_count if total_count > 0 else 0
