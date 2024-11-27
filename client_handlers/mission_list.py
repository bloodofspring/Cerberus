import math

from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from client_handlers.base import *
from database.models import Notifications, SendTime
from util import render_notification


class MissionsList(BaseHandler):
    __name__ = "MissionsList"
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and "missions_list" in q.data)

    def __init__(self, page: int = 0, buttons_on_page: int = 2):
        super().__init__()
        self.buttons_on_page = buttons_on_page
        self.page = page

    @property
    def chats_sql(self) -> tuple[tuple[Notifications, ...], int]:
        data = Notifications.select().where(Notifications.created_by == self.db_user)
        on_page = data[self.page * self.buttons_on_page:(self.page + 1) * self.buttons_on_page]

        return tuple(on_page), math.ceil(len(data) / self.buttons_on_page)

    def base_keyboard(self, max_pages) -> list[list[InlineKeyboardButton]]:
        buttons = []

        if self.page != 0:
            buttons.append(InlineKeyboardButton("<---<<<", callback_data="missions_list-prev_page"))

        buttons.append(InlineKeyboardButton("На главную", callback_data="main"))

        if self.page + 1 != max_pages:
            buttons.append(InlineKeyboardButton(">>>--->", callback_data="missions_list-next_page"))

        return [buttons]

    @property
    def keyboard(self) -> tuple[InlineKeyboardMarkup, bool, int]:
        content, max_pages = self.chats_sql
        keyboard = InlineKeyboardMarkup([])

        if not content:
            keyboard.inline_keyboard += self.base_keyboard(max_pages=max_pages)

            return keyboard, False, -1

        for notification in content:
            if not notification.text:
                SendTime.delete_by_id(notification.send_at.id)
                Notifications.delete_by_id(notification.id)
                continue

            keyboard.inline_keyboard.append([InlineKeyboardButton(
                notification.text[:29] + ("..." if len(notification.text) > 29 else ""),
                callback_data=f"at_mission {notification.id}"
            )])

        keyboard.inline_keyboard += self.base_keyboard(max_pages=max_pages)

        return keyboard, True, max_pages

    async def menu(self):
        keyboard, true_data, max_pages = self.keyboard

        if not true_data:
            await self.request.reply("Список напоминаний (у вас нет напоминаний)", reply_markup=keyboard)
            return

        await self.request.message.edit(
            "Список напоминаний:\nСтраница {}".format(f"{self.page + 1}/{max_pages}"),
            reply_markup=keyboard
        )

    async def func(self):
        match self.request.data:
            case "missions_list-prev_page":
                self.page -= 1

            case "missions_list-next_page":
                self.page += 1

        await self.menu()


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
