from datetime import datetime

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from client_handlers.base import *
from controllers import MissionController
from util import render_notification


class StartCmd(BaseHandler):
    FILTER = command("start")

    async def func(self):
        create_mission_call_data = f"CHANGE-{str(datetime.now()).replace(' ', '-').replace(':', '-')[:-7]}-1-1-0"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Добавить напоминание", callback_data=create_mission_call_data),
            InlineKeyboardButton("Мои напоминания", callback_data="missions_list"),
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
