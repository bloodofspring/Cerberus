from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from client_handlers.base import *
from controllers import MissionController
from util import render_notification


class StartCmd(BaseHandler):
    FILTER = command("start")

    async def func(self):
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Добавить напоминание", callback_data=""),
            InlineKeyboardButton("Мои напоминания", callback_data=""),
        ]])
        MissionController.delete_unused_time_points()
        n_for_cur_user = MissionController().nearest_mission_for_current_user(user=self.db_user)
        await MissionController().run()

        await self.request.reply(
            (
                f"Ближайшее напоминание:\n"
                f"{'У вас не добавлено напоминаний' if n_for_cur_user is None else render_notification(n_for_cur_user)}"
            ),
            reply_markup=keyboard
        )
