import asyncio
import logging
import logging.config
import os

from aiogram import Bot, Dispatcher
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode, setup_dialogs
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.exc import NoResultFound

from src.config import BOT_TOKEN, LOGGING_CONFIG, UPDATE_EACH_MINUTES
from src.database import Base, engine, make_session
from src.dialog import SG, dialog
from src.service import add_user, get_user, update_prices_and_notify_subscribers
from src.utils import cast_away_optional

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()


@dp.message(Command("start"))
async def start(message: Message, dialog_manager: DialogManager):
    with make_session() as session:
        try:
            get_user(cast_away_optional(message.from_user).id, session)
        except NoResultFound:
            add_user(cast_away_optional(message.from_user).id, session)
    await dialog_manager.start(SG.HOME, mode=StartMode.RESET_STACK)


async def main():
    os.makedirs("logs", exist_ok=True)
    logging.config.dictConfig(LOGGING_CONFIG)

    Base.metadata.create_all(engine)

    dp.include_router(dialog)
    setup_dialogs(dp)

    scheduler.add_job(
        update_prices_and_notify_subscribers,
        CronTrigger(minute=f"*/{UPDATE_EACH_MINUTES}"),
        args=(bot,),
        id="update_prices_and_notify_subscribers",
    )

    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
