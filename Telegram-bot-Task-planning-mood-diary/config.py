import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///task_mood_bot.db")

    ADMIN_IDS = (
        list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
        if os.getenv("ADMIN_IDS")
        else []
    )

    REMINDER_HOURS_BEFORE = 1

    CLEANUP_COMPLETED_TASKS_DAYS = 30
    CLEANUP_DELETED_TASKS_DAYS = 30
    CLEANUP_MOODS_DAYS = 90
    AUTO_CLEANUP_HOUR = 3
