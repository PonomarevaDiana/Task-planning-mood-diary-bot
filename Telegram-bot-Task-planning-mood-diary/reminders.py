import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, exceptions
from database import db
import logging
import aiosqlite

logger = logging.getLogger(__name__)


class ReminderManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self.db_path = db.db_path

    async def start(self):
        """Запускает менеджер напоминаний"""
        self.is_running = True
        asyncio.create_task(self._reminder_worker())
        logger.info("ReminderManager started")

    async def stop(self):
        """Останавливает менеджер напоминаний"""
        self.is_running = False
        logger.info("ReminderManager stopped")

    async def _reminder_worker(self):
        """Фоновая задача для обработки напоминаний"""
        print("🔄 Reminder worker начал работу")
        iteration = 0

        while self.is_running:
            try:
                iteration += 1
                print(
                    f"🔍 Reminder worker итерация {iteration} в {datetime.now().strftime('%H:%M:%S')}"
                )

                await self._create_deadline_reminders()
                await self._create_overdue_reminders()
                await self.check_daily_overdue_notifications()
                await self._send_pending_reminders()
                await self._cleanup_old_reminders()

                print(f"✅ Итерация {iteration} завершена, ожидание 60 секунд...")
                await asyncio.sleep(60)

            except Exception as e:
                print(f"❌ Ошибка в reminder worker: {e}")
                logger.error(f"Error in reminder worker: {e}")
                await asyncio.sleep(60)

    def _parse_datetime(self, date_str: str) -> datetime:
        """Универсальный парсер дат"""
        try:
            if "T" in date_str:
                return datetime.fromisoformat(date_str)
            elif " " in date_str:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            else:
                return datetime.fromisoformat(date_str + "T00:00:00")
        except Exception as e:
            print(f"❌ Ошибка парсинга даты {date_str}: {e}")
            raise

    async def _create_deadline_reminders(self):
        """Создание напоминаний о приближающихся дедлайнах"""
        print("⏰ Создание напоминаний о дедлайнах...")

        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT 
                        t.id, t.user_id, t.due_date, 
                        COALESCE(rs.reminder_before_hours, 1) as reminder_hours
                    FROM tasks t
                    LEFT JOIN reminder_settings rs ON t.user_id = rs.user_id
                    WHERE t.status = 'pending'
                    AND t.is_deleted = 0
                    AND t.due_date IS NOT NULL
                    AND t.due_date > datetime('now')
                    AND NOT EXISTS (
                        SELECT 1 FROM task_reminders tr 
                        WHERE tr.task_id = t.id 
                        AND tr.reminder_type = 'deadline'
                    )
                    AND (rs.enable_reminders = 1 OR rs.enable_reminders IS NULL)
                """
                )

                tasks_for_reminders = await cursor.fetchall()

            print(
                f"🔍 Найдено задач для напоминаний о дедлайнах: {len(tasks_for_reminders)}"
            )

            for task_id, user_id, due_date_str, reminder_hours in tasks_for_reminders:
                try:
                    due_date = self._parse_datetime(due_date_str)
                    reminder_time = due_date - timedelta(hours=reminder_hours)
                    now = datetime.now()

                    if reminder_time > now:
                        await self.create_task_reminder(
                            user_id=user_id,
                            task_id=task_id,
                            reminder_type="deadline",
                            scheduled_time=reminder_time,
                        )
                        print(
                            f"✅ Создано напоминание для задачи {task_id} на {reminder_time}"
                        )
                    else:
                        print(f"⏰ Время напоминания для задачи {task_id} уже прошло")

                except Exception as e:
                    print(
                        f"❌ Ошибка при создании напоминания для задачи {task_id}: {e}"
                    )

        except Exception as e:
            print(f"❌ Ошибка в _create_deadline_reminders: {e}")

    async def _debug_overdue_tasks(self):
        """Диагностика почему не находятся просроченные задачи"""
        print("🔍 [OVERDUE DEBUG] Диагностика просроченных задач...")

        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT 
                        t.id, t.user_id, t.due_date, t.status, t.is_deleted,
                        rs.enable_overdue_reminders,
                        EXISTS (
                            SELECT 1 FROM task_reminders tr 
                            WHERE tr.task_id = t.id 
                            AND tr.reminder_type = 'overdue_immediate'
                        ) as has_reminder
                    FROM tasks t
                    LEFT JOIN reminder_settings rs ON t.user_id = rs.user_id
                    WHERE t.status = 'pending'
                    AND t.is_deleted = 0
                    AND t.due_date IS NOT NULL
                    AND t.due_date < datetime('now')
                    ORDER BY t.due_date DESC
                    LIMIT 10
                    """
                )
                all_overdue = await cursor.fetchall()

                print(
                    f"🔍 [OVERDUE DEBUG] Всего просроченных задач: {len(all_overdue)}"
                )

                for task in all_overdue:
                    (
                        task_id,
                        user_id,
                        due_date,
                        status,
                        is_deleted,
                        enable_overdue,
                        has_reminder,
                    ) = task
                    print(
                        f"   - Задача {task_id}: due_date={due_date}, status={status}, "
                        f"deleted={is_deleted}, enable_overdue={enable_overdue}, "
                        f"has_reminder={has_reminder}"
                    )
                cursor = await conn.execute(
                    """
                    SELECT DISTINCT t.id, t.user_id, t.due_date
                    FROM tasks t
                    LEFT JOIN reminder_settings rs ON t.user_id = rs.user_id
                    WHERE t.status = 'pending'
                    AND t.is_deleted = 0
                    AND t.due_date IS NOT NULL
                    AND t.due_date < datetime('now')
                    AND NOT EXISTS (
                        SELECT 1 FROM task_reminders tr 
                        WHERE tr.task_id = t.id 
                        AND tr.reminder_type = 'overdue_immediate'
                    )
                    AND (rs.enable_overdue_reminders = 1 OR rs.enable_overdue_reminders IS NULL)
                    """
                )
                found_tasks = await cursor.fetchall()

                print(f"🔍 [OVERDUE DEBUG] Задачи для напоминаний: {len(found_tasks)}")
                for task in found_tasks:
                    print(f"   - Будет создано напоминание для задачи {task[0]}")

        except Exception as e:
            print(f"❌ [OVERDUE DEBUG] Ошибка диагностики: {e}")

    async def _create_overdue_reminders(self):
        """Создание ОДНОРАЗОВЫХ напоминаний о новых просроченных задачах - МАКСИМАЛЬНАЯ ОТЛАДКА"""
        print("⚠️ Создание напоминаний о новых просрочках...")

        try:
            async with aiosqlite.connect(self.db_path) as conn:
                print("🔍 [OVERDUE] Подключились к БД")

                cursor = await conn.execute("SELECT datetime('now', 'localtime')")
                db_time = (await cursor.fetchone())[0]
                print(f"🕒 [OVERDUE] Время в БД: {db_time}")

                cursor = await conn.execute(
                    """
                    SELECT DISTINCT
                        t.id, t.user_id, t.content, t.due_date
                    FROM tasks t
                    LEFT JOIN reminder_settings rs ON t.user_id = rs.user_id
                    WHERE t.status = 'pending'
                    AND t.is_deleted = 0
                    AND t.due_date IS NOT NULL
                    AND datetime(t.due_date) < datetime('now', 'localtime')
                    AND NOT EXISTS (
                        SELECT 1 FROM task_reminders tr 
                        WHERE tr.task_id = t.id 
                        AND tr.reminder_type = 'overdue_immediate'
                    )
                    AND (rs.enable_overdue_reminders = 1 OR rs.enable_overdue_reminders IS NULL)
                    """
                )
                print("🔍 [OVERDUE] Запрос выполнен")

                new_overdue_tasks = await cursor.fetchall()
                print(
                    f"🔍 [OVERDUE] Получены результаты: {len(new_overdue_tasks)} задач"
                )

            print(
                f"🔍 [OVERDUE] Найдено новых просроченных задач: {len(new_overdue_tasks)}"
            )

            for task_id, user_id, content, due_date_str in new_overdue_tasks:
                try:
                    reminder_id = await self.create_task_reminder(
                        user_id=user_id,
                        task_id=task_id,
                        reminder_type="overdue_immediate",
                        scheduled_time=datetime.now(),
                    )

                    if reminder_id:
                        print(f"✅ [OVERDUE] Напоминание создано! ID: {reminder_id}")
                    else:
                        print(
                            f"❌ [OVERDUE] create_task_reminder вернул None для задачи {task_id}"
                        )

                except Exception as e:
                    print(
                        f"❌ [OVERDUE] Ошибка при создании напоминания для задачи {task_id}: {e}"
                    )
                    import traceback

                    traceback.print_exc()

            print(f"✅ [OVERDUE] Обработка завершена")

        except Exception as e:
            print(f"❌ [OVERDUE] Ошибка в _create_overdue_reminders: {e}")
            import traceback

            traceback.print_exc()

    async def check_daily_overdue_notifications(self):
        """Проверяет и отправляет ежедневные уведомления о просроченных задачах"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT 
                        u.id, 
                        COALESCE(rs.daily_overdue_time, '09:00') as notification_time,
                        rs.enable_overdue_reminders
                    FROM users u
                    LEFT JOIN reminder_settings rs ON u.id = rs.user_id
                    WHERE rs.enable_overdue_reminders = 1 OR rs.enable_overdue_reminders IS NULL
                """
                )
                users_settings = await cursor.fetchall()

            current_time = datetime.now().strftime("%H:%M")
            sent_count = 0

            for user_id, notification_time, enable_overdue in users_settings:
                if not enable_overdue:
                    continue

                if current_time == notification_time:
                    overdue_tasks = await self.get_overdue_tasks_for_user_daily(user_id)
                    if overdue_tasks:
                        sent_count += await self.send_daily_overdue_notification(
                            user_id, overdue_tasks
                        )
                        print(
                            f"✅ Отправлено ежедневное уведомление пользователю {user_id}"
                        )

            if sent_count > 0:
                print(f"📨 Всего отправлено ежедневных уведомлений: {sent_count}")

        except Exception as e:
            print(f"❌ Ошибка при проверке ежедневных уведомлений: {e}")

    async def get_overdue_tasks_for_user_daily(self, user_id: int):
        """Получает просроченные задачи для ежедневного уведомления пользователя"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                """
                SELECT 
                    t.id, t.content, t.due_date, t.priority,
                    t.last_overdue_notification
                FROM tasks t
                WHERE t.user_id = ? 
                AND t.status = 'pending' 
                AND t.is_deleted = 0
                AND t.due_date IS NOT NULL
                AND t.due_date < datetime('now')
                AND (
                    t.last_overdue_notification IS NULL 
                    OR date(t.last_overdue_notification) < date('now')
                )
                ORDER BY t.due_date ASC
            """,
                (user_id,),
            )
            return await cursor.fetchall()

    async def send_daily_overdue_notification(self, user_id: int, overdue_tasks):
        """Отправляет ежедневное уведомление о просроченных задачах"""
        if not overdue_tasks:
            return 0

        try:
            high_priority = []
            medium_priority = []
            low_priority = []

            for task in overdue_tasks:
                task_id, content, due_date, priority, last_notification = task
                task_info = {
                    "id": task_id,
                    "content": content,
                    "due_date": due_date,
                    "days_overdue": self.calculate_days_overdue(due_date),
                }

                if priority == "high":
                    high_priority.append(task_info)
                elif priority == "medium":
                    medium_priority.append(task_info)
                else:
                    low_priority.append(task_info)

            message = self.format_daily_overdue_message(
                high_priority, medium_priority, low_priority
            )

            await self.bot.send_message(
                chat_id=user_id, text=message, parse_mode="HTML"
            )

            for task in overdue_tasks:
                await db.update_last_overdue_notification(task[0])

            return 1

        except exceptions.BotBlocked:
            print(f"❌ Пользователь {user_id} заблокировал бота")
            return 0
        except Exception as e:
            print(
                f"❌ Ошибка отправки ежедневного уведомления пользователю {user_id}: {e}"
            )
            return 0

    def calculate_days_overdue(self, due_date_str):
        """Вычисляет количество дней просрочки"""
        try:
            due_date = self._parse_datetime(due_date_str)
            overdue_days = (datetime.now() - due_date).days
            return max(1, overdue_days)
        except:
            return 1

    def format_daily_overdue_message(
        self, high_priority, medium_priority, low_priority
    ):
        """Форматирует сообщение для ежедневного уведомления"""
        total_tasks = len(high_priority) + len(medium_priority) + len(low_priority)

        message = f"🌅 <b>ЕЖЕДНЕВНЫЙ ОБЗОР ПРОСРОЧЕННЫХ ЗАДАЧ</b>\n\n"
        message += f"📊 Всего просроченных задач: <b>{total_tasks}</b>\n\n"

        if high_priority:
            message += f"🔴 <b>ВЫСОКИЙ ПРИОРИТЕТ ({len(high_priority)})</b>\n"
            for task in high_priority[:5]:
                message += f"• #{task['id']} {task['content'][:30]}... ({task['days_overdue']} дн.)\n"
            if len(high_priority) > 5:
                message += f"• ... и еще {len(high_priority) - 5} задач\n"
            message += "\n"

        if medium_priority:
            message += f"🟡 <b>СРЕДНИЙ ПРИОРИТЕТ ({len(medium_priority)})</b>\n"
            for task in medium_priority[:3]:
                message += f"• #{task['id']} {task['content'][:30]}... ({task['days_overdue']} дн.)\n"
            if len(medium_priority) > 3:
                message += f"• ... и еще {len(medium_priority) - 3} задач\n"
            message += "\n"

        if low_priority:
            message += f"🟢 <b>НИЗКИЙ ПРИОРИТЕТ ({len(low_priority)})</b>\n"
            message += f"• Всего задач: {len(low_priority)}\n"
            message += "\n"

        message += (
            "💡 <i>Используйте /complete [ID] чтобы отметить задачу выполненной</i>\n"
        )
        message += "⏰ <i>Это уведомление приходит раз в день</i>"

        return message

    async def create_task_reminder(
        self, user_id: int, task_id: int, reminder_type: str, scheduled_time: datetime
    ):
        """Создает напоминание в базе данных"""
        try:
            await db.create_task_reminder(
                user_id=user_id,
                task_id=task_id,
                reminder_type=reminder_type,
                scheduled_time=scheduled_time,
            )
            logger.info(f"Created {reminder_type} reminder for task {task_id}")

        except Exception as e:
            print(f"❌ Ошибка при создании напоминания: {e}")
            logger.error(f"Error creating reminder: {e}")

    async def _send_pending_reminders(self):
        """Отправляет готовые напоминания"""
        print("📤 Отправка готовых напоминаний...")

        try:
            reminders = await db.get_pending_reminders()
            sent_count = 0

            for reminder in reminders:
                try:
                    (
                        reminder_id,
                        user_id,
                        task_id,
                        reminder_type,
                        scheduled_time,
                        sent,
                        created_at,
                        sent_at,
                        task_content,
                        due_date,
                        priority,
                    ) = reminder

                    if reminder_type == "deadline":
                        message = await self._format_deadline_reminder(
                            task_content, due_date, priority, task_id
                        )
                    else:
                        message = await self._format_overdue_reminder(
                            task_content, due_date, priority, task_id, reminder_type
                        )

                    await self.bot.send_message(
                        chat_id=user_id, text=message, parse_mode="HTML"
                    )

                    await db.mark_reminder_sent(reminder_id)
                    sent_count += 1
                    print(
                        f"✅ Отправлено напоминание {reminder_id} для задачи {task_id}"
                    )

                    await asyncio.sleep(0.3)

                except exceptions.BotBlocked:
                    print(f"❌ Пользователь {user_id} заблокировал бота")
                    await db.mark_reminder_sent(reminder_id)
                except Exception as e:
                    print(f"❌ Ошибка при отправке напоминания {reminder[0]}: {e}")

            if sent_count > 0:
                print(f"📨 Всего отправлено напоминаний: {sent_count}")

        except Exception as e:
            print(f"❌ Ошибка в _send_pending_reminders: {e}")

    async def _format_deadline_reminder(
        self, task_content: str, due_date_str: str, priority: str, task_id: int
    ) -> str:
        """Форматирует сообщение о приближающемся дедлайне"""
        try:
            due_date = self._parse_datetime(due_date_str)
            time_left = due_date - datetime.now()

            priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            priority_icon = priority_icons.get(priority, "🟡")

            display_content = task_content
            if len(display_content) > 50:
                display_content = display_content[:50] + "..."

            if time_left.total_seconds() <= 3600:
                minutes = int(time_left.total_seconds() / 60)
                time_text = f"⏰ <b>Осталось: {minutes} минут</b>"
                urgency = "🔴 СРОЧНО!"
            elif time_left.total_seconds() <= 7200:
                hours = int(time_left.total_seconds() / 3600)
                minutes = int((time_left.total_seconds() % 3600) / 60)
                time_text = f"⏰ <b>Осталось: {hours} ч {minutes} мин</b>"
                urgency = "🟠 Внимание!"
            else:
                hours = int(time_left.total_seconds() / 3600)
                time_text = f"⏰ <b>Осталось: {hours} часов</b>"
                urgency = "🟡 Напоминание"

            message = (
                f"{urgency}\n\n"
                f"{priority_icon} <b>Задача:</b> {display_content}\n"
                f"📅 <b>Срок:</b> {due_date.strftime('%d.%m.%Y %H:%M')}\n"
                f"{time_text}\n\n"
                f"<i>ID задачи: {task_id}</i>"
            )

            return message

        except Exception as e:
            print(f"❌ Ошибка форматирования напоминания: {e}")
            return f"🔔 Напоминание о задаче: {task_content}"

    async def _format_overdue_reminder(
        self,
        task_content: str,
        due_date_str: str,
        priority: str,
        task_id: int,
        reminder_type: str = "overdue",
    ) -> str:
        """Форматирует сообщение о просроченной задаче"""
        try:
            due_date = self._parse_datetime(due_date_str)
            overdue_time = datetime.now() - due_date
            overdue_days = overdue_time.days

            priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            priority_icon = priority_icons.get(priority, "🟡")

            display_content = task_content
            if len(display_content) > 50:
                display_content = display_content[:50] + "..."

            if overdue_days > 0:
                if overdue_days == 1:
                    overdue_text = f"📅 <b>Просрочена на: 1 день</b>"
                else:
                    overdue_text = f"📅 <b>Просрочена на: {overdue_days} дней</b>"
            else:
                hours = int(overdue_time.total_seconds() / 3600)
                overdue_text = f"📅 <b>Просрочена на: {hours} часов</b>"

            if reminder_type == "overdue_immediate":
                urgency_emoji = "🔴"
                urgency_text = "НОВАЯ ПРОСРОЧЕННАЯ ЗАДАЧА!"
                footer = "🚨 Эта задача только что стала просроченной"
            else:
                if overdue_days >= 7:
                    urgency_emoji = "🔴"
                    urgency_text = "КРИТИЧЕСКИЙ уровень!"
                elif overdue_days >= 3:
                    urgency_emoji = "🟠"
                    urgency_text = "Высокий уровень!"
                else:
                    urgency_emoji = "🟡"
                    urgency_text = "Внимание!"
                footer = "🚨 Пожалуйста, выполните задачу как можно скорее!"

            message = (
                f"{urgency_emoji} <b>ЗАДАЧА ПРОСРОЧЕНА! {urgency_text}</b>\n\n"
                f"{priority_icon} <b>Задача:</b> {display_content}\n"
                f"⏰ <b>Был срок:</b> {due_date.strftime('%d.%m.%Y %H:%M')}\n"
                f"{overdue_text}\n\n"
                f"{footer}\n"
                f"<i>ID задачи: {task_id}</i>"
            )

            return message

        except Exception as e:
            print(f"❌ Ошибка форматирования напоминания о просрочке: {e}")
            return f"⚠️ Задача просрочена: {task_content}"

    async def _cleanup_old_reminders(self):
        """Очищает старые отправленные напоминания"""
        print("🧹 Очистка старых напоминаний...")
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "DELETE FROM task_reminders WHERE sent = 1 AND sent_at < datetime('now', '-3 days')"
                )
                deleted_count = cursor.rowcount
                await conn.commit()

            if deleted_count > 0:
                print(f"✅ Очищено старых напоминаний: {deleted_count}")

        except Exception as e:
            print(f"❌ Ошибка при очистке напоминаний: {e}")

    async def create_reminder_for_new_task(
        self, user_id: int, task_id: int, due_date: datetime
    ):
        """Создает напоминание для новой задачи с дедлайном"""
        try:
            settings = await db.get_reminder_settings(user_id)

            if not settings or not settings[1]:
                print(f"🔕 Напоминания выключены для пользователя {user_id}")
                return

            reminder_hours = settings[2] or 1

            reminder_time = due_date - timedelta(hours=reminder_hours)
            now = datetime.now()

            if reminder_time > now:
                await self.create_task_reminder(
                    user_id=user_id,
                    task_id=task_id,
                    reminder_type="deadline",
                    scheduled_time=reminder_time,
                )
                print(f"✅ Создано напоминание для новой задачи {task_id}")
            else:
                print(f"⏰ Время напоминания для новой задачи {task_id} уже прошло")

        except Exception as e:
            print(f"❌ Ошибка при создании напоминания для новой задачи: {e}")
            logger.error(f"Error creating reminder for new task: {e}")


reminder_manager = None


async def init_reminder_manager(bot: Bot):
    """Инициализирует менеджер напоминаний"""
    global reminder_manager
    reminder_manager = ReminderManager(bot)
    await reminder_manager.start()
    return reminder_manager
