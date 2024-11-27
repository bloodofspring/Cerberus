from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from client_handlers.base import *
from controllers import MissionController
from util import render_notification


class Main(BaseHandler):
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and q.data == "main")

    @property
    async def message_text(self):
        n_for_cur_user = MissionController().today_missions_for_user(user=self.db_user)

        if n_for_cur_user is None:
            format_data = 'У вас не запланировано напоминаний на сегодня'
        else:
            format_data = await render_notification(n_for_cur_user)

        text = (
            "Привет! Я **Церберус**, бот для напоминаний.\n"
            "##================##\n"
            "**Ближайшее сообщение на сегодня:**\n"
            "{}".format(format_data)
        )

        return text

    @property
    def keyboard(self):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Добавить напоминание", callback_data="get_dt")],
            [InlineKeyboardButton("Мои напоминания", callback_data="missions_list")],
        ])

        return keyboard

    async def func(self):
        if isinstance(self.request, CallbackQuery):
            await self.request.message.edit(await self.message_text, reply_markup=self.keyboard)

        if isinstance(self.request, Message):
            await self.request.reply(await self.message_text, reply_markup=self.keyboard)


class StartCmd(BaseHandler):
    __name__ = "StartCmd"
    FILTER = command("start")

    async def func(self):
        await Main().execute(client=self.client, request=self.request)
        await MissionController().update()
