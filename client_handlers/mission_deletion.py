import asyncio

from peewee import DoesNotExist
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from client_handlers.base import *
from controllers import MissionController
from database.models import Notifications, SendTime, NotificationQueue


class RmMission(BaseHandler):
    __name__ = "RmMission"
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and q.data.startswith("rm_mission"))

    async def func(self):
        to_delete: Notifications = Notifications.get_by_id(int(self.request.data.split()[1]))
        SendTime.delete_by_id(to_delete.send_at.id)
        try:
            pass
        except DoesNotExist:
            pass

        Notifications.delete_by_id(to_delete.id)

        await self.request.message.edit(
            "Напоминание удалено!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("К напоминаниям", callback_data="missions_list")
            ]])
        )
        await asyncio.sleep(1)
        await MissionController().reload()
