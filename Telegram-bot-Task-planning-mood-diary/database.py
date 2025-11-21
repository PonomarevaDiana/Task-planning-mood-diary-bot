import aiosqlite
from config import Config
from datetime import datetime, timedelta


class Database:
    def __init__(self):
        self.db_path = Config.DATABASE_URL.replace("sqlite:///", "")

    async def initialize(self):
        """Инициализация базы данных - создание таблиц"""
        await self.create_tables()

    async def create_tables(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    content TEXT NOT NULL,
                    due_date TIMESTAMP,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    sent BOOLEAN DEFAULT 0,
                    is_deleted BOOLEAN DEFAULT 0,
                    deleted_at TIMESTAMP,
                    last_overdue_notification TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                );

            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS moods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    mood TEXT NOT NULL,
                    notes TEXT,
                    date DATE DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    color TEXT DEFAULT '#007ACC',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, name)
                )
            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS task_tags (
                    task_id INTEGER,
                    tag_id INTEGER,
                    PRIMARY KEY (task_id, tag_id),
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                )
            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS task_reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    task_id INTEGER NOT NULL,
                    reminder_type TEXT NOT NULL DEFAULT 'deadline',
                    scheduled_time DATETIME NOT NULL,
                    sent BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sent_at DATETIME NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_settings (
                    user_id INTEGER PRIMARY KEY,
                    enable_reminders BOOLEAN DEFAULT 1,
                    reminder_before_hours INTEGER DEFAULT 1,
                    enable_overdue_reminders BOOLEAN DEFAULT 1,
                    daily_overdue_time TEXT DEFAULT '09:00',
                    overdue_reminder_interval_hours INTEGER DEFAULT 24,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
                """
            )

            await db.commit()

    async def add_user(self, user_id: int, username: str, first_name: str):
        """Добавляет пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name),
            )
            await db.commit()

    async def user_exists(self, user_id: int):
        """Проверяет существует ли пользователь"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            return await cursor.fetchone() is not None

    async def add_task(self, user_id: int, content: str, due_date: datetime):
        """Добавляет задачу"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO tasks (user_id, content, due_date, status) VALUES (?, ?, ?, ?)",
                (
                    user_id,
                    content,
                    due_date.isoformat() if due_date else None,
                    "pending",
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def add_task_with_priority(
        self, user_id: int, content: str, due_date: datetime, priority: str = "medium"
    ):
        """Добавляет задачу с приоритетом"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO tasks (user_id, content, due_date, priority, status) VALUES (?, ?, ?, ?, ?)",
                (
                    user_id,
                    content,
                    due_date.isoformat() if due_date else None,
                    priority,
                    "pending",
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_user_tasks(
        self, user_id: int, status: str = None, include_deleted: bool = False
    ):
        """Получает задачи пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            base_query = "SELECT id, user_id, content, due_date, priority, status, created_at, is_deleted FROM tasks WHERE user_id = ?"
            params = [user_id]

            if not include_deleted:
                base_query += " AND is_deleted = 0"

            if status:
                base_query += " AND status = ?"
                params.append(status)

            base_query += " ORDER BY due_date"

            cursor = await db.execute(base_query, params)
            return await cursor.fetchall()

    async def get_user_tasks_with_priority(
        self, user_id: int, status: str = None, include_deleted: bool = False
    ):
        """Получает задачи пользователя с информацией о приоритете"""
        async with aiosqlite.connect(self.db_path) as db:
            base_query = "SELECT id, user_id, content, due_date, priority, status, created_at, is_deleted FROM tasks WHERE user_id = ?"
            params = [user_id]

            if not include_deleted:
                base_query += " AND is_deleted = 0"

            if status:
                base_query += " AND status = ?"
                params.append(status)

            base_query += " ORDER BY due_date"

            cursor = await db.execute(base_query, params)
            return await cursor.fetchall()

    async def get_task(self, task_id: int):
        """Получает задачу по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            return await cursor.fetchone()

    async def complete_task(self, task_id: int):
        """Отмечает задачу как выполненную"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE tasks SET status = "completed", completed_at = CURRENT_TIMESTAMP WHERE id = ? AND is_deleted = 0',
                (task_id,),
            )
            await db.commit()

    async def delete_task(self, task_id: int):
        """Помечает задачу как удаленную вместо физического удаления"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
                (task_id,),
            )
            await db.commit()

    async def restore_task(self, task_id: int):
        """Восстанавливает удаленную задачу"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET is_deleted = 0, deleted_at = NULL WHERE id = ?",
                (task_id,),
            )
            await db.commit()

    async def permanently_delete_task(self, task_id: int):
        """Физически удаляет задачу"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            await db.commit()

    async def postpone_task(self, task_id: int, new_date: datetime):
        """Откладывает задачу"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET due_date = ?, sent = 0 WHERE id = ? AND is_deleted = 0",
                (new_date.isoformat(), task_id),
            )
            await db.commit()

    async def update_task_priority(self, task_id: int, priority: str):
        """Обновляет приоритет задачи"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET priority = ? WHERE id = ? AND is_deleted = 0",
                (priority, task_id),
            )
            await db.commit()

    async def update_task_content(self, task_id: int, new_content: str):
        """Обновляет текст задачи"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET content = ? WHERE id = ? AND is_deleted = 0",
                (new_content, task_id),
            )
            await db.commit()

    async def update_task_due_date(self, task_id: int, new_due_date: datetime):
        """Обновляет срок выполнения задачи"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET due_date = ?, sent = 0 WHERE id = ? AND is_deleted = 0",
                (new_due_date.isoformat() if new_due_date else None, task_id),
            )
            await db.commit()

    async def update_task_full(
        self, task_id: int, new_content: str, new_due_date: datetime
    ):
        """Обновляет и текст и дату задачи"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET content = ?, due_date = ?, sent = 0 WHERE id = ? AND is_deleted = 0",
                (
                    new_content,
                    new_due_date.isoformat() if new_due_date else None,
                    task_id,
                ),
            )
            await db.commit()

    async def get_tasks_by_priority(self, user_id: int, priority: str):
        """Получает задачи по приоритету"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id,content, due_date, priority, status, created_at 
                FROM tasks 
                WHERE user_id = ? AND priority = ? AND status = 'pending' AND is_deleted = 0
                ORDER BY due_date
                """,
                (user_id, priority),
            )
            return await cursor.fetchall()

    async def get_tasks_grouped_by_priority(self, user_id: int):
        """Получает задачи сгруппированные по приоритету"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT priority, COUNT(*) as count 
                FROM tasks 
                WHERE user_id = ? AND status = 'pending' AND is_deleted = 0
                GROUP BY priority
                ORDER BY 
                    CASE priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 4
                    END
                """,
                (user_id,),
            )
            return await cursor.fetchall()

    async def get_tasks_by_date(self, user_id: int, target_date: datetime):
        """Получает задачи на конкретную дату"""
        async with aiosqlite.connect(self.db_path) as db:
            date_str = target_date.date().isoformat()
            cursor = await db.execute(
                """
                SELECT id, content, due_date, priority, status 
                FROM tasks 
                WHERE user_id = ? 
                AND date(due_date) = ? 
                AND status = 'pending' 
                AND is_deleted = 0
                ORDER BY due_date
                """,
                (user_id, date_str),
            )
            return await cursor.fetchall()

    async def get_tasks_for_reminder(self):
        """Получает задачи для напоминания"""
        async with aiosqlite.connect(self.db_path) as db:
            reminder_time = (
                datetime.now() + timedelta(hours=Config.REMINDER_HOURS_BEFORE)
            ).isoformat()
            cursor = await db.execute(
                """
                SELECT t.*, u.id as user_id 
                FROM tasks t 
                JOIN users u ON t.user_id = u.id 
                WHERE t.status = 'pending' 
                AND t.due_date <= ? 
                AND t.sent = 0
                AND t.is_deleted = 0
            """,
                (reminder_time,),
            )
            return await cursor.fetchall()

    async def mark_reminder_sent(self, task_id: int):
        """Отмечает что напоминание отправлено"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE tasks SET sent = 1 WHERE id = ?", (task_id,))
            await db.commit()

    async def get_today_mood(self, user_id: int):
        """Получает сегодняшнее настроение с заметкой"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT id, user_id, mood, notes, date FROM moods WHERE user_id = ? AND date = date("now")',
                (user_id,),
            )
            return await cursor.fetchone()

    async def get_mood_by_date(self, user_id: int, date: str):
        """Получает настроение за конкретную дату"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, mood, notes FROM moods WHERE user_id = ? AND date = ?",
                (user_id, date),
            )
            return await cursor.fetchone()

    async def add_mood_with_notes(self, user_id: int, mood: str, notes: str = None):
        """Добавляет настроение с заметкой"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM moods WHERE user_id = ? AND date = CURRENT_DATE",
                (user_id,),
            )
            existing = await cursor.fetchone()

            if existing:
                await db.execute(
                    "UPDATE moods SET mood = ?, notes = ? WHERE user_id = ? AND date = CURRENT_DATE",
                    (mood, notes, user_id),
                )
            else:
                await db.execute(
                    "INSERT INTO moods (user_id, mood, notes) VALUES (?, ?, ?)",
                    (user_id, mood, notes),
                )

            await db.commit()

    async def update_mood(self, user_id: int, new_mood: str):
        """Обновляет настроение"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE moods SET mood = ? WHERE user_id = ? AND date = date("now")',
                (new_mood, user_id),
            )
            await db.commit()

    async def update_mood_with_notes(self, user_id: int, mood: str, notes: str = None):
        """Обновляет сегодняшнее настроение с заметкой"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE moods SET mood = ?, notes = ? WHERE user_id = ? AND date = date("now")',
                (mood, notes, user_id),
            )
            await db.commit()

    async def update_mood_notes(self, user_id: int, notes: str):
        """Обновляет только заметку к сегодняшнему настроению"""
        try:

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT id, mood, notes FROM moods WHERE user_id = ? AND date = date("now")',
                    (user_id,),
                )
                existing_mood = await cursor.fetchone()

                if not existing_mood:
                    print("❌ [UPDATE_MOOD_NOTES] Нет записи настроения на сегодня")
                    return False

                result = await db.execute(
                    'UPDATE moods SET notes = ? WHERE user_id = ? AND date = date("now")',
                    (notes, user_id),
                )
                await db.commit()

                changes = result.rowcount

                return changes > 0

        except Exception as e:
            print(f"❌ [UPDATE_MOOD_NOTES] Ошибка: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def get_mood_statistics(self, user_id: int, days: int = 30):
        """Получает статистику настроений"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT mood, date 
                FROM moods 
                WHERE user_id = ? AND date >= date('now', ?) 
                ORDER BY date DESC
            """,
                (user_id, f"-{days} days"),
            )
            return await cursor.fetchall()

    async def get_task_statistics(self, user_id: int, days: int = 30):
        """Получает статистику задач"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT status, COUNT(*) as count 
                FROM tasks 
                WHERE user_id = ? AND created_at >= date('now', ?) AND is_deleted = 0
                GROUP BY status
            """,
                (user_id, f"-{days} days"),
            )
            return await cursor.fetchall()

    async def create_tag(self, user_id: int, tag_name: str, color: str = "#007ACC"):
        """Создает тег или возвращает ID существующего"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM tags WHERE user_id = ? AND name = ?",
                (user_id, tag_name.lower().strip()),
            )
            existing_tag = await cursor.fetchone()

            if existing_tag:
                return existing_tag[0]

            cursor = await db.execute(
                "INSERT INTO tags (user_id, name, color) VALUES (?, ?, ?)",
                (user_id, tag_name.lower().strip(), color),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_user_tags(self, user_id: int):
        """Получает все теги пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, name, color FROM tags WHERE user_id = ? ORDER BY name",
                (user_id,),
            )
            return await cursor.fetchall()

    async def delete_tag(self, tag_id: int):
        """Удаляет тег"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
            await db.commit()

    async def add_tag_to_task(self, task_id: int, tag_id: int):
        """Добавляет тег к задаче"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)",
                (task_id, tag_id),
            )
            await db.commit()

    async def remove_tag_from_task(self, task_id: int, tag_id: int):
        """Убирает тег с задачи"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM task_tags WHERE task_id = ? AND tag_id = ?",
                (task_id, tag_id),
            )
            await db.commit()

    async def get_task_tags(self, task_id: int):
        """Получает все теги задачи"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT t.id, t.name, t.color 
                FROM tags t 
                JOIN task_tags tt ON t.id = tt.tag_id 
                WHERE tt.task_id = ?
            """,
                (task_id,),
            )
            return await cursor.fetchall()

    async def get_tasks_by_tag(self, user_id: int, tag_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT ts.*  
                FROM tasks ts
                JOIN task_tags tt ON ts.id = tt.task_id
                JOIN tags tg ON tg.id = tt.tag_id
                WHERE tg.user_id = ? AND tg.name = ? AND ts.status = 'pending' AND ts.is_deleted = 0
                """,
                (user_id, tag_name.lower()),
            )
            return await cursor.fetchall()

    async def get_tasks_grouped_by_tags(self, user_id: int):
        """Получает задачи сгруппированные по тегам"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT t.name, t.color, COUNT(tt.task_id) as task_count,
                       GROUP_CONCAT(tt.task_id) as task_ids
                FROM tags t
                LEFT JOIN task_tags tt ON t.id = tt.tag_id
                LEFT JOIN tasks ts ON tt.task_id = ts.id AND ts.status = 'pending' AND ts.is_deleted = 0
                WHERE t.user_id = ?
                GROUP BY t.id, t.name
                HAVING task_count > 0
                ORDER BY task_count DESC
                """,
                (user_id,),
            )
            return await cursor.fetchall()

    async def get_deleted_tasks(self, user_id: int):
        """Получает удаленные задачи пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, user_id, content, due_date, priority, status, created_at, deleted_at FROM tasks WHERE user_id = ? AND is_deleted = 1 ORDER BY deleted_at DESC",
                (user_id,),
            )
            return await cursor.fetchall()

    async def cleanup_old_completed_tasks(self, days_old: int = 30):
        """Удаляет выполненные задачи старше X дней"""
        async with aiosqlite.connect(self.db_path) as db:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

            await db.execute(
                """
                DELETE FROM task_tags 
                WHERE task_id IN (
                    SELECT id FROM tasks 
                    WHERE status = 'completed' 
                    AND completed_at <= ?
                )
                """,
                (cutoff_date,),
            )

            result = await db.execute(
                """
                DELETE FROM tasks 
                WHERE status = 'completed' 
                AND completed_at <= ?
                """,
                (cutoff_date,),
            )

            await db.commit()
            return result.rowcount

    async def cleanup_old_moods(self, days_old: int = 90):
        """Удаляет записи настроений старше X дней"""
        async with aiosqlite.connect(self.db_path) as db:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).date().isoformat()

            result = await db.execute(
                "DELETE FROM moods WHERE date < ?", (cutoff_date,)
            )

            await db.commit()
            return result.rowcount

    async def cleanup_old_deleted_tasks(self, days_old: int = 30):
        """Физически удаляет задачи, помеченные как удаленные больше X дней назад"""
        async with aiosqlite.connect(self.db_path) as db:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
            await db.execute(
                """
                DELETE FROM task_tags 
                WHERE task_id IN (
                    SELECT id FROM tasks 
                    WHERE is_deleted = 1 
                    AND deleted_at <= ?
                )
                """,
                (cutoff_date,),
            )

            result = await db.execute(
                "DELETE FROM tasks WHERE is_deleted = 1 AND deleted_at <= ?",
                (cutoff_date,),
            )

            await db.commit()
            return result.rowcount

    async def get_storage_statistics(self, user_id: int):
        """Получает статистику хранилища"""
        async with aiosqlite.connect(self.db_path) as db:
            month_ago = (datetime.now() - timedelta(days=30)).isoformat()
            cursor = await db.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'completed' AND completed_at <= ?",
                (user_id, month_ago),
            )
            old_completed = (await cursor.fetchone())[0]

            three_months_ago = (datetime.now() - timedelta(days=90)).date().isoformat()
            cursor = await db.execute(
                "SELECT COUNT(*) FROM moods WHERE user_id = ? AND date < ?",
                (user_id, three_months_ago),
            )
            old_moods = (await cursor.fetchone())[0]

            return {"old_completed_tasks": old_completed, "old_moods": old_moods}

    async def get_reminder_settings(self, user_id: int):
        """Получает настройки напоминаний пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM reminder_settings WHERE user_id = ?", (user_id,)
            )
            settings = await cursor.fetchone()

            if not settings:
                await db.execute(
                    "INSERT INTO reminder_settings (user_id, enable_reminders, reminder_before_hours, enable_overdue_reminders) VALUES (?, 1, 1, 1)",
                    (user_id,),
                )
                await db.commit()

                cursor = await db.execute(
                    "SELECT * FROM reminder_settings WHERE user_id = ?", (user_id,)
                )
                settings = await cursor.fetchone()

            if settings:
                settings_list = list(settings)
                if settings_list[1] is None:
                    settings_list[1] = 1
                if settings_list[2] is None:
                    settings_list[2] = 1
                if settings_list[3] is None:
                    settings_list[3] = 1
                return tuple(settings_list)

            return settings

    async def update_reminder_settings(self, user_id: int, **settings):
        """Обновляет настройки напоминаний"""
        async with aiosqlite.connect(self.db_path) as db:
            set_clause = ", ".join([f"{key} = ?" for key in settings.keys()])
            values = list(settings.values())
            values.append(user_id)

            await db.execute(
                f"UPDATE reminder_settings SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                values,
            )
            await db.commit()

    async def create_task_reminder(
        self, user_id: int, task_id: int, reminder_type: str, scheduled_time: datetime
    ):
        """Создает напоминание для задачи"""
        async with aiosqlite.connect(self.db_path) as db:

            try:
                if reminder_type == "overdue_immediate":
                    actual_scheduled_time = datetime.now() - timedelta(minutes=1)
                else:
                    actual_scheduled_time = scheduled_time

                scheduled_time_str = actual_scheduled_time.strftime("%Y-%m-%d %H:%M:%S")

                cursor = await db.execute(
                    "INSERT INTO task_reminders (user_id, task_id, reminder_type, scheduled_time) VALUES (?, ?, ?, ?)",
                    (
                        user_id,
                        task_id,
                        reminder_type,
                        scheduled_time_str,
                    ),
                )
                await db.commit()
                reminder_id = cursor.lastrowid
                return reminder_id
            except Exception as e:
                print(f"❌ [CREATE_REMINDER] Ошибка при создании напоминания: {e}")
                return None

    async def get_pending_reminders(self, limit: int = 100):
        """Получает готовые к отправке напоминания"""
        try:

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT datetime('now'), datetime('now', 'localtime')"
                )
                times = await cursor.fetchone()
                current_utc, current_local = times
                cursor = await db.execute(
                    """
                    SELECT 
                        tr.id, tr.user_id, tr.task_id, tr.reminder_type, 
                        tr.scheduled_time, tr.sent, tr.created_at, tr.sent_at,
                        t.content, t.due_date, t.priority
                    FROM task_reminders tr
                    JOIN tasks t ON tr.task_id = t.id
                    WHERE tr.sent = 0
                    AND datetime(tr.scheduled_time) <= datetime('now', 'localtime')
                    ORDER BY tr.scheduled_time ASC
                    LIMIT ?
                    """,
                    (limit,),
                )
                found_reminders = await cursor.fetchall()

                for rem in found_reminders:
                    (
                        reminder_id,
                        user_id,
                        task_id,
                        reminder_type,
                        scheduled_time,
                        sent,
                        created_at,
                        sent_at,
                        content,
                        due_date,
                        priority,
                    ) = rem

                    cursor_check = await db.execute(
                        "SELECT ? <= datetime('now') as is_due_utc",
                        (scheduled_time,),
                    )
                    is_due_utc = (await cursor_check.fetchone())[0]

                return found_reminders

        except Exception as e:
            print(f"❌ Ошибка в get_pending_reminders: {e}")
            import traceback

            traceback.print_exc()
            return []

    async def mark_reminder_sent(self, reminder_id: int):
        """Отмечает напоминание как отправленное"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE task_reminders SET sent = 1, sent_at = CURRENT_TIMESTAMP WHERE id = ?",
                (reminder_id,),
            )
            await db.commit()

    async def get_tasks_needing_reminders(self):
        """Получает задачи, для которых нужно создать напоминания о дедлайнах"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT 
                    t.id, t.user_id, t.content, t.due_date, t.priority, t.status,
                    t.created_at, t.completed_at, t.is_deleted,
                    rs.enable_reminders, 
                    COALESCE(rs.reminder_before_hours, 1) as reminder_before_hours,  -- Исправлено на 1
                    rs.enable_overdue_reminders
                FROM tasks t
                JOIN users u ON t.user_id = u.id
                JOIN reminder_settings rs ON u.id = rs.user_id
                WHERE t.status = 'pending'
                AND t.is_deleted = 0
                AND t.due_date IS NOT NULL
                AND t.due_date > datetime('now')
                AND NOT EXISTS (
                    SELECT 1 FROM task_reminders tr 
                    WHERE tr.task_id = t.id 
                    AND tr.reminder_type = 'deadline'
                    AND tr.sent = 0
                )
                AND rs.enable_reminders = 1
                ORDER BY t.due_date ASC
                """
            )
            return await cursor.fetchall()

    async def get_active_reminder_for_task(self, task_id: int, reminder_type: str):
        """Проверяет есть ли активное напоминание для задачи"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM task_reminders WHERE task_id = ? AND reminder_type = ? AND sent = 0",
                (task_id, reminder_type),
            )
            return await cursor.fetchone()

    async def get_overdue_tasks_stats(self, user_id: int):
        """Получает статистику по просроченным задачам"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*) 
                FROM tasks 
                WHERE user_id = ? 
                AND status = 'pending'
                AND is_deleted = 0
                AND due_date IS NOT NULL
                AND due_date < datetime('now')
                """,
                (user_id,),
            )
            total_overdue = (await cursor.fetchone())[0]

            cursor = await db.execute(
                """
                SELECT priority, COUNT(*)
                FROM tasks 
                WHERE user_id = ? 
                AND status = 'pending'
                AND is_deleted = 0
                AND due_date IS NOT NULL
                AND due_date < datetime('now')
                GROUP BY priority
                """,
                (user_id,),
            )
            overdue_by_priority = await cursor.fetchall()

            return {
                "total_overdue": total_overdue,
                "overdue_by_priority": overdue_by_priority,
            }

    async def update_last_overdue_notification(self, task_id: int):
        """Обновляет время последнего уведомления о просрочке"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "UPDATE tasks SET last_overdue_notification = datetime('now') WHERE id = ?",
                (task_id,),
            )
            await conn.commit()

    async def update_reminder_settings_with_time(self, user_id: int, **settings):
        """Обновляет настройки напоминаний с временем уведомлений"""
        async with aiosqlite.connect(self.db_path) as conn:
            set_clause = ", ".join([f"{key} = ?" for key in settings.keys()])
            values = list(settings.values())
            values.append(user_id)

            await conn.execute(
                f"UPDATE reminder_settings SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                values,
            )
            await conn.commit()

    async def get_filtered_tasks(self, user_id: int, filters: dict) -> list:
        """Получает задачи по фильтрам через SQL"""
        async with aiosqlite.connect(self.db_path) as db:
            base_query = """
                SELECT * FROM tasks 
                WHERE user_id = ? 
                AND is_deleted = 0
            """
            params = [user_id]

            if filters.get("status") == "completed":
                base_query += " AND status = 'completed'"
            elif filters.get("status") == "pending":
                base_query += " AND status = 'pending'"
            elif filters.get("status") == "deleted":
                base_query += " AND is_deleted = 1"

            if filters.get("priority"):
                base_query += " AND priority = ?"
                params.append(filters["priority"])

            if filters.get("tag"):
                base_query += """
                    AND id IN (
                        SELECT task_id FROM task_tags 
                        JOIN tags ON task_tags.tag_id = tags.id 
                        WHERE tags.user_id = ? AND tags.name = ?
                    )
                """
                params.extend([user_id, filters["tag"].lower()])

            if filters.get("date"):
                today = datetime.now().date()
                if filters["date"] == "today":
                    base_query += " AND date(due_date) = date(?)"
                    params.append(today.isoformat())
                elif filters["date"] == "tomorrow":
                    base_query += " AND date(due_date) = date(?, '+1 day')"
                    params.append(today.isoformat())
                elif filters["date"] == "week":
                    base_query += (
                        " AND date(due_date) BETWEEN date(?) AND date(?, '+7 days')"
                    )
                    params.extend([today.isoformat(), today.isoformat()])
                elif filters["date"] == "overdue":
                    base_query += " AND due_date < datetime(?) AND status = 'pending'"
                    params.append(datetime.now().isoformat())

            base_query += " ORDER BY due_date ASC"

            cursor = await db.execute(base_query, params)
            return await cursor.fetchall()

    async def get_tasks_grouped_by_priority_detailed(self, user_id: int) -> dict:
        """Получает задачи сгруппированные по приоритетам с деталями"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT 
                    priority,
                    COUNT(*) as total,
                    SUM(CASE WHEN due_date < datetime('now') THEN 1 ELSE 0 END) as overdue,
                    SUM(CASE WHEN due_date IS NULL THEN 1 ELSE 0 END) as no_date
                FROM tasks 
                WHERE user_id = ? AND status = 'pending' AND is_deleted = 0
                GROUP BY priority
                ORDER BY 
                    CASE priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2  
                        WHEN 'low' THEN 3
                        ELSE 4
                    END
            """,
                (user_id,),
            )

            return await cursor.fetchall()

    async def get_urgent_tasks(self, user_id: int) -> list:
        """Получает срочные задачи (сегодня + просроченные)"""
        async with aiosqlite.connect(self.db_path) as db:
            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_end = datetime.now().replace(
                hour=23, minute=59, second=59, microsecond=999999
            )

            cursor = await db.execute(
                """
                SELECT * FROM tasks 
                WHERE user_id = ? 
                AND status = 'pending'
                AND is_deleted = 0
                AND due_date IS NOT NULL
                AND due_date >= ? 
                AND due_date <= ?
                ORDER BY due_date ASC
                """,
                (user_id, today_start.isoformat(), today_end.isoformat()),
            )
            today_tasks = await cursor.fetchall()

            cursor = await db.execute(
                """
                SELECT * FROM tasks 
                WHERE user_id = ? 
                AND status = 'pending'
                AND is_deleted = 0
                AND due_date IS NOT NULL
                AND due_date < ?
                ORDER BY due_date ASC
                """,
                (datetime.now().isoformat(),),
            )
            overdue_tasks = await cursor.fetchall()

            return today_tasks + overdue_tasks

    async def get_today_tasks(self, user_id: int) -> list:
        """Получает задачи на сегодня"""
        async with aiosqlite.connect(self.db_path) as db:
            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_end = datetime.now().replace(
                hour=23, minute=59, second=59, microsecond=999999
            )

            cursor = await db.execute(
                """
                SELECT * FROM tasks 
                WHERE user_id = ? 
                AND status = 'pending'
                AND is_deleted = 0
                AND due_date IS NOT NULL
                AND due_date >= ? 
                AND due_date <= ?
                ORDER BY due_date ASC
                """,
                (user_id, today_start.isoformat(), today_end.isoformat()),
            )
            return await cursor.fetchall()

    async def get_overdue_tasks(self, user_id: int) -> list:
        """Получает просроченные задачи"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                now = datetime.now().isoformat()

                cursor = await db.execute(
                    """
                    SELECT * FROM tasks 
                    WHERE user_id = ? 
                    AND status = 'pending'
                    AND is_deleted = 0
                    AND due_date IS NOT NULL
                    AND datetime(due_date) < datetime(?)
                    ORDER BY due_date ASC
                    """,
                    (user_id, now),
                )
                return await cursor.fetchall()

            except Exception as e:
                print(f"❌ Ошибка в get_overdue_tasks: {e}")
                return []

    async def get_upcoming_tasks(self, user_id: int, days: int = 7) -> list:
        """Получает ближайшие задачи на указанное количество дней"""
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now()
            period_end = now + timedelta(days=days)

            cursor = await db.execute(
                """
                SELECT * FROM tasks 
                WHERE user_id = ? 
                AND status = 'pending'
                AND is_deleted = 0
                AND due_date IS NOT NULL
                AND due_date >= ? 
                AND due_date <= ?
                ORDER BY due_date ASC
                """,
                (user_id, now.isoformat(), period_end.isoformat()),
            )
            return await cursor.fetchall()

    async def get_tasks_for_deadline_reminders(self):
        """Получает задачи для создания напоминаний о дедлайнах"""
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
            return await cursor.fetchall()

    async def get_overdue_tasks_for_debug(self):
        """Получает просроченные задачи для диагностики"""
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
            return await cursor.fetchall()

    async def get_overdue_tasks_without_reminders(self):
        """Получает просроченные задачи без напоминаний"""
        async with aiosqlite.connect(self.db_path) as conn:
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
            return await cursor.fetchall()

    async def get_database_local_time(self):
        """Получает локальное время базы данных"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("SELECT datetime('now', 'localtime')")
            return (await cursor.fetchone())[0]

    async def get_new_overdue_tasks_for_reminders(self):
        """Получает новые просроченные задачи для создания напоминаний"""
        async with aiosqlite.connect(self.db_path) as conn:
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
            return await cursor.fetchall()

    async def get_users_for_daily_overdue_notifications(self):
        """Получает пользователей и их настройки для ежедневных уведомлений"""
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
            return await cursor.fetchall()

    async def get_overdue_tasks_for_user_daily(self, user_id: int):
        """Получает просроченные задачи пользователя для ежедневного уведомления"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                """
                SELECT 
                    t.id, t.user_id, t.content, t.due_date, t.priority,
                    t.last_overdue_notification,
                    rs.enable_overdue_reminders,
                    u.first_name
                FROM tasks t
                JOIN users u ON t.user_id = u.id
                LEFT JOIN reminder_settings rs ON t.user_id = rs.user_id
                WHERE t.status = 'pending' 
                AND t.is_deleted = 0
                AND t.due_date IS NOT NULL
                AND t.due_date < datetime('now')
                AND (rs.enable_overdue_reminders = 1 OR rs.enable_overdue_reminders IS NULL)
                AND (
                    t.last_overdue_notification IS NULL 
                    OR date(t.last_overdue_notification) < date('now')
                )
                AND t.user_id = ?
                ORDER BY t.due_date ASC
                """,
                (user_id,),
            )
            return await cursor.fetchall()

    async def delete_task_reminders(self, task_id: int, reminder_type: str = None):
        """Удаляет напоминания для задачи"""
        async with aiosqlite.connect(self.db_path) as db:
            if reminder_type:
                result = await db.execute(
                    "DELETE FROM task_reminders WHERE task_id = ? AND reminder_type = ?",
                    (task_id, reminder_type),
                )
                deleted_count = result.rowcount
            else:
                result = await db.execute(
                    "DELETE FROM task_reminders WHERE task_id = ?", (task_id,)
                )
                deleted_count = result.rowcount
            await db.commit()
            return deleted_count


db = Database()
