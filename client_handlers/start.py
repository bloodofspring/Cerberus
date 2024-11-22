from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton

from client_handlers.base import *
from domain import MissionsController
from util import render_notification


class StartCmd(BaseHandler):
    FILTER = command("start")

    async def func(self):
        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("Добавить напоминание"), KeyboardButton("Мои напоминания")],
        ], resize_keyboard=True, one_time_keyboard=True)
        MissionsController.delete_unused_time_points()
        nmfcu = MissionsController().nearest_mission_for_current_user(user=self.db_user)
        await MissionsController().run()

        await self.request.reply(
            (
                f"Ближайшее напоминание:\n"
                f"{'У вас не добавлено напоминаний' if nmfcu is None else render_notification(nmfcu)}"
            ),
            reply_markup=keyboard
        )
