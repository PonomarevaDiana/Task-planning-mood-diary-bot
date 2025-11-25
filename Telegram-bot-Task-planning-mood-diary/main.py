import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from database import db
from reminders import init_reminder_manager
from handlers.notifications import router as notification_router
from handlers.tags import router as tags_router
from handlers.tasks import router as tasks_router
from handlers.moods import router as moods_router
from handlers.statistics import router as stats_router
from handlers.common import router as common_router
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def scheduled_cleanup():
    """Ежедневная автоматическая очистка"""
    while True:
        try:
            now = datetime.now()
            next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if now >= next_run:
                next_run += timedelta(days=1)

            wait_seconds = (next_run - now).total_seconds()
            await asyncio.sleep(wait_seconds)

            deleted_tasks = await db.cleanup_old_completed_tasks(30)
            deleted_moods = await db.cleanup_old_moods(90)
            deleted_removed = await db.cleanup_old_deleted_tasks(30)

            deleted_reminders = await db.cleanup_old_reminders(7)

            logger.info(
                f"✅ Автоочистка завершена: "
                f"задач {deleted_tasks}, "
                f"настроений {deleted_moods}, "
                f"удаленных {deleted_removed}, "
                f"напоминаний {deleted_reminders}"
            )

        except Exception as e:
            logger.error(f"❌ Ошибка автоочистки: {e}")
            await asyncio.sleep(3600)


async def main():
    try:

        await db.initialize()

        bot = Bot(token=Config.BOT_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        reminder_manager_instance = await init_reminder_manager(bot)
        from handlers.tasks import set_reminder_manager

        await set_reminder_manager(reminder_manager_instance)

        asyncio.create_task(scheduled_cleanup())
        dp.include_router(notification_router)
        dp.include_router(tags_router)
        dp.include_router(tasks_router)
        dp.include_router(moods_router)
        dp.include_router(stats_router)
        dp.include_router(common_router)

        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {e}")
        raise
    finally:
        try:
            from reminders import reminder_manager

            if reminder_manager:
                await reminder_manager.stop()
                logger.info("Менеджер напоминаний остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке менеджера напоминаний: {e}")

        try:
            await bot.session.close()
            logger.info("Сессия бота закрыта")
        except Exception as e:
            logger.error(f"Ошибка при закрытии сессии: {e}")

        logger.info("Бот полностью остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}")
