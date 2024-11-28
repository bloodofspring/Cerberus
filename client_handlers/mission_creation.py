import asyncio
import math
from datetime import datetime

import dateparser
import pyrostep
from pyrogram import types
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrostep import steps

from client_handlers.base import *
from controllers import MissionController
from database.models import ChatToSend, SendTime, CreationSession
from util import create_mission, get_last_session, WEEKDAYS_ACCUSATIVE, WEEKDAYS_NOMINATIVE, render_time


class GetChatToSend(BaseHandler):
    __name__ = "GetChatToSend"
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and q.data.startswith("CHAT"))

    def __init__(self, page: int = 0, buttons_on_page: int = 6):
        super().__init__()
        self.buttons_on_page = buttons_on_page
        self.page = page

    @property
    def data_sql(self) -> tuple[tuple[ChatToSend, ...], int]:
        data = self.db_user.chats
        on_page = data[self.page * self.buttons_on_page:(self.page + 1) * self.buttons_on_page]

        return tuple(on_page), math.ceil(len(data) / self.buttons_on_page)

    def base_keyboard(self, max_pages) -> list[list[InlineKeyboardButton]]:
        buttons = []

        if self.page != 0:
            buttons.append(InlineKeyboardButton("<---<<<", callback_data="CHAT-prev_page"))

        buttons += [InlineKeyboardButton("Этот чат", callback_data="CHAT-THIS")]

        if self.page + 1 != max_pages:
            buttons.append(InlineKeyboardButton(">>>--->", callback_data="CHAT-next_page"))

        return [buttons]

    @property
    async def keyboard(self) -> tuple[InlineKeyboardMarkup, bool, int]:
        if ChatToSend.get_or_none(tg_id=self.request.message.chat.id) is None:
            ChatToSend.create(tg_id=self.request.message.chat.id, user=self.db_user)

        content, max_pages = self.data_sql
        keyboard = InlineKeyboardMarkup([])

        for db_chat in content:
            try:
                chat = await self.client.get_chat(db_chat.tg_id)
            except (Exception,):
                ChatToSend.delete_by_id(db_chat.id)
                continue

            if chat.title is not None:
                button_text = chat.title[:29] + ("..." if len(chat.title) > 29 else "")
            else:
                button_text = "Чат c @{}".format(chat.username[:22] + ("..." if len(chat.username) > 22 else ""))

            keyboard.inline_keyboard.append([InlineKeyboardButton(
                button_text, callback_data=f"CHAT-{db_chat.tg_id}-{'PRV' if chat.type == chat.type.PRIVATE else 'PUB'}"
            )])

            keyboard.inline_keyboard += self.base_keyboard(max_pages=max_pages)

        return keyboard, True, max_pages

    async def apply_chat(self, chat_id: int):
        session = get_last_session(self.db_user)
        if session is None:
            return

        ChatToSend.get_or_create(tg_id=chat_id, user=self.db_user)
        session.chat_to_send_id = chat_id
        CreationSession.save(session)

        await self.request.message.edit("Чат выбран!")
        await asyncio.sleep(0.5)
        await self.request.message.edit("Отправьте текст напоминания сообщением ниже")
        await steps.register_next_step(self.request.from_user.id, self.save_text)

    async def save_text(self, _, msg: types.Message):
        session = get_last_session(self.db_user)
        if session is None:
            return

        session.text = msg.text
        CreationSession.save(session)

        create_mission(session=session)
        await msg.reply("Напоминание создано!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "Список напоминаний", callback_data="missions_list"
        )]]))
        await asyncio.sleep(1)
        await MissionController().update()

    async def main(self):
        keyboard, _, max_pages = await self.keyboard

        try:
            await self.request.message.edit(
                (
                    f"Страница {self.page + 1}/{max_pages}\n"
                    "Выберите чат для отправки напоминаний\n"
                    "Чтобы чат появился в этом списке добавьте в него бота"
                ),
                reply_markup=keyboard
            )
        except (Exception,):
            await self.request.answer("Никаких изменений")

    async def func(self):
        match self.request.data:
            case "CHAT":
                await self.main()

            case "CHAT-prev_page":
                self.page -= 1
                await self.main()

            case "CHAT-next_page":
                self.page += 1
                await self.main()

            case "CHAT-THIS":
                await self.apply_chat(chat_id=self.request.message.chat.id)

            case _ as c if c.strip("CHAT-PUBPRV").isalnum():
                if "PUB" in c.split("-"):
                    await self.apply_chat(chat_id=int("-" + c.strip("CHAT-PUB")))
                    return

                await self.apply_chat(chat_id=int(c.strip("CHAT-PRV")))


class GetDateTime(BaseHandler):
    __name__ = "GetDateTime"
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and q.data.startswith("get_dt"))

    async def ask_time(self):
        await self.request.message.edit(
            (
                "Отправьте время для отправки напоминаний ниже.\n\n"
                "**Пример:**\n"
                "23 марта 2023 12:07 - __отправка 23 марта в 12:07__\n"
                "Среда 15:00 - __отправка по средам, в 15:00__\n"
                "11:11 - __отправка каждый день в 11:11__"
            ), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="get_dt-cancel")]])
        )
        await pyrostep.register_next_step(self.request.from_user.id, self.register_time)

    async def register_time(self, _, msg: types.Message):
        time = dateparser.parse(msg.text)

        if time is None:
            await msg.reply(
                "Указано время в неправильном формате!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Ввести заново", callback_data="get_dt")]])
            )
            return

        consider_weekday: bool = any(map(lambda x: x in msg.text.lower(), WEEKDAYS_ACCUSATIVE + WEEKDAYS_NOMINATIVE))
        consider_date: bool = time.date() != datetime.now().date() and not consider_weekday

        if consider_date and time < datetime.now():
            await msg.reply(
                "Данное напоминание будет удалено после исполнения;\n"
                f"Время его отправки должно быть больше {str(datetime.now())[:-7]}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Ввести заново", callback_data="get_dt")]])
            )
            return

        created_send_time = SendTime.create(
            send_date=time.date(),
            send_time=time.time(),
            consider_date=consider_date,
            weekday=time.weekday() if consider_weekday else -1,
        )
        CreationSession.create(
            user=self.db_user,
            time_point=created_send_time,
            chat_to_send_id=-1,
            text="",
        )

        await self.client.send_message(
            msg.chat.id, "{}\n\nСохранить?".format(
                render_time(
                    consider_date=consider_date,
                    consider_weekday=consider_weekday,
                    send_time=time.time(),
                    send_date=time.date()
            )),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Да", callback_data=f"get_dt-submit"),
                    InlineKeyboardButton("Нет", callback_data="get_dt-delete_created_data")
            ]])
        )

    async def delete_created_data(self):
        session = get_last_session(self.db_user)
        if session is None:
            return

        SendTime.delete_by_id(session.time_point.id)
        CreationSession.delete_by_id(session.id)

        await self.ask_time()

    async def submit(self):
        await self.request.message.edit(
            "Время отправки сохранено!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Дальше", callback_data="CHAT")]])
        )

    async def cancel(self):
        await pyrostep.unregister_steps(self.request.from_user.id)
        await self.request.message.edit(
            "Создание напоминания отменено!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("На главную", callback_data="main")]])
        )

    async def func(self):
        """
        Call data format:
        get_dt-<method_name>=par_1=par_2=par_N
        """
        match self.request.data:
            case "get_dt":
                await self.ask_time()

            case _ as c if hasattr(self, self.request.data.split("-")[1]):
                await getattr(self, c.split("-")[1])()
