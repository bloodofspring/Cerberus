from datetime import datetime

from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from client_handlers.base import *
from database.models import Notifications
from util import render_notification


class MissionsList(BaseHandler):
    __name__ = "MissionsList"
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and q.data == "missions_list")

    @property
    def keyboard(self):  # , page: int
        user = self.db_user
        all_n = Notifications.select().where(Notifications.created_by == user)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                n.text[:29] + ("..." if len(n.text) > 29 else ""),
                callback_data=f"at_mission {n.id}"
            )
        ] for n in all_n])

        keyboard.inline_keyboard.append([InlineKeyboardButton(
            "+ Добавить напоминание",
            callback_data=f"CHANGE-{str(datetime.now()).replace(' ', '-').replace(':', '-')[:-7]}-1-1-0"
        )])
        keyboard.inline_keyboard.append([InlineKeyboardButton(
            "<---<<< На главную",
            callback_data="main"
        )])

        return keyboard

    async def func(self):
        keyboard = self.keyboard
        await self.request.message.edit(
            "Список напоминаний{}".format(" (у вас нет напоминаний)" if len(keyboard.inline_keyboard) == 1 else ":"),
            reply_markup=keyboard
        )


class Mission(BaseHandler):
    __name__ = "Mission"
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and q.data.startswith("at_mission"))

    async def func(self):
        _, id_ = self.request.data.split()
        id_ = int(id_)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Удалить напоминание", callback_data=f"rm_mission {id_}")],
            [InlineKeyboardButton("К напоминаниям", callback_data="missions_list")],
        ])

        await self.request.message.edit(
            await render_notification(Notifications.get_by_id(id_)),
            reply_markup=keyboard,
        )
