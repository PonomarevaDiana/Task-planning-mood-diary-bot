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
    get_main_keyboard,
    get_cancel_keyboard,
    get_notifications_keyboard,
    get_reminder_settings_keyboard,
    get_cancel_keyboard,
    get_time_reminder_keyboard,
)

router = Router()


class ReminderSettings(StatesGroup):
    waiting_for_settings_choice = State()
    waiting_for_reminders_setting = State()
    waiting_for_overdue_setting = State()
    waiting_for_reminder_hours = State()


class DailyReminderSettings(StatesGroup):
    waiting_for_daily_time = State()


@router.message(F.text == "🔔 Уведомления")
async def handle_notifications_button(message: Message):
    """Обработка кнопки уведомлений из главного меню"""
    await cmd_reminders(message)


@router.message(F.text == "⏰ Настройка времени")
async def cmd_quick_actions(message: Message, state: FSMContext):
    await message.answer(
        "⏰ Настройка времени\n\n" "Выберите действие:",
        reply_markup=get_time_reminder_keyboard(),
    )


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


@router.message(F.text == "⏰ Время ежедневных уведомлений")
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


@router.message(F.text == "⏰ Изменить время дедлайнов")
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
