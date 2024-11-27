import asyncio
import math
from datetime import datetime, timedelta

from pyrogram import types
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrostep import steps

from client_handlers.base import *
from controllers import MissionController
from database.models import ChatToSend, SendTime, CreationSession
from util import create_mission, get_last_session, WEEKDAYS


class GetChatToSend(BaseHandler):
    __name__ = "GetChatToSend"
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and q.data.startswith("CHAT"))

    def __init__(self, page: int = 0, buttons_on_page: int = 1):
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
    FILTER = create(lambda _, __, q: q and q.data and q.data.startswith("CHANGE"))

    def __init__(self):
        super().__init__()
        self.datetime = datetime.now()
        self.reg_weekday = False
        self.reg_date = False
        self.del_after_exec = False

    @property
    def date_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("<<5", callback_data=self.to_call_data(time_delta=timedelta(days=-5))),
                InlineKeyboardButton("<<", callback_data=self.to_call_data(time_delta=timedelta(days=-1))),
                InlineKeyboardButton("День: {}".format(self.datetime.day), callback_data="none"),
                InlineKeyboardButton(">>", callback_data=self.to_call_data(time_delta=timedelta(days=1))),
                InlineKeyboardButton("5>>", callback_data=self.to_call_data(time_delta=timedelta(days=5))),
            ] if self.reg_date else [],
            [
                InlineKeyboardButton("<<3", callback_data=self.to_call_data(time_delta=timedelta(days=-90))),
                InlineKeyboardButton("<<", callback_data=self.to_call_data(time_delta=timedelta(days=-30))),
                InlineKeyboardButton("Мес: {}".format(self.datetime.month), callback_data="none"),
                InlineKeyboardButton(">>", callback_data=self.to_call_data(time_delta=timedelta(days=30))),
                InlineKeyboardButton("3>>", callback_data=self.to_call_data(time_delta=timedelta(days=90)))
            ] if self.reg_date else [],
            [
                InlineKeyboardButton("<<", callback_data=self.to_call_data(time_delta=timedelta(days=-365))),
                InlineKeyboardButton("Год: {}".format(self.datetime.year), callback_data="none"),
                InlineKeyboardButton(">>", callback_data=self.to_call_data(time_delta=timedelta(days=365)))
            ] if self.reg_date else [],
            [InlineKeyboardButton(
                "Не учитывать дату" if self.reg_date else "Учитывать дату",
                callback_data=self.to_call_data(reg_date=not self.reg_date)
            )],
            [
                InlineKeyboardButton("<<", callback_data=self.to_call_data(time_delta=timedelta(days=-1))),
                InlineKeyboardButton(WEEKDAYS[self.datetime.weekday()].capitalize(), callback_data="none"),
                InlineKeyboardButton(">>", callback_data=self.to_call_data(time_delta=timedelta(days=1))),
            ] if self.reg_weekday and not self.reg_date and not self.del_after_exec else [],
            [InlineKeyboardButton(
                "Не учитывать день недели" if self.reg_weekday else "Учитывать день недели",
                callback_data=self.to_call_data(reg_weekday=not self.reg_weekday)
            )] if not self.reg_date and not self.del_after_exec else [],
            [
                InlineKeyboardButton("<<5", callback_data=self.to_call_data(time_delta=timedelta(hours=-5))),
                InlineKeyboardButton("<<", callback_data=self.to_call_data(time_delta=timedelta(hours=-1))),
                InlineKeyboardButton("Час: {}".format(self.datetime.hour), callback_data="none"),
                InlineKeyboardButton(">>", callback_data=self.to_call_data(time_delta=timedelta(hours=1))),
                InlineKeyboardButton("5>>", callback_data=self.to_call_data(time_delta=timedelta(hours=5)))
            ],
            [
                InlineKeyboardButton("<<10", callback_data=self.to_call_data(time_delta=timedelta(minutes=-10))),
                InlineKeyboardButton("<<", callback_data=self.to_call_data(time_delta=timedelta(minutes=-1))),
                InlineKeyboardButton("Мин: {}".format(self.datetime.minute), callback_data="none"),
                InlineKeyboardButton(">>", callback_data=self.to_call_data(time_delta=timedelta(minutes=1))),
                InlineKeyboardButton("10>>", callback_data=self.to_call_data(time_delta=timedelta(minutes=10)))

            ],
            [InlineKeyboardButton(
                "Не удалять после исполнения" if self.del_after_exec else "Удалить после исполнения",
                callback_data=self.to_call_data(del_after_exec=not self.del_after_exec)
            )],
            [
                InlineKeyboardButton("Готово", callback_data="CHANGE-SUBMIT"),
                InlineKeyboardButton("Отмена", callback_data="main")
            ],
        ])

        return keyboard

    def set_values(self):
        """call data format "CHANGE-YYYY-MM-DD-HH-MM-SS-1-0-1" (reg_weekday, reg_date, del_after_exec)"""
        self.datetime = datetime(*map(int, self.request.data.split("-")[1:6]), second=0)
        self.reg_weekday = bool(int(self.request.data.split("-")[7]))
        self.reg_date = bool(int(self.request.data.split("-")[8]))
        self.del_after_exec = bool(int(self.request.data.split("-")[9]))

    def to_call_data(self, time_delta: timedelta = timedelta(), reg_weekday=None, reg_date=None, del_after_exec=None) -> str:
        """call data format "CHANGE-YYYY-MM-DD-HH-MM-SS-1-0-1" (reg_weekday, reg_date, del_after_exec)"""
        call_data = "CHANGE-"
        call_data += str(self.datetime + time_delta).replace(' ', '-').replace(':', '-')
        call_data += (
            f"-{int(self.reg_weekday) if reg_weekday is None else int(reg_weekday)}"
            f"-{int(self.reg_date) if reg_date is None else int(reg_date)}-"
            f"{int(self.del_after_exec) if del_after_exec is None else int(del_after_exec)}"
        )

        return call_data

    async def submit(self):
        if (self.reg_date or self.del_after_exec) and self.datetime < datetime.now():
            await self.request.answer(
                (
                    "Данное напоминание будет удалено после исполнения;\n"
                    f"Время его отправки должно быть больше {str(datetime.now())[:-7]}"
                ), show_alert=True
            )
            return

        created_send_time = SendTime.create(
            send_date=self.datetime.date(),
            send_time=self.datetime.time(),
            consider_date=self.reg_date,
            weekday=self.datetime.weekday() if self.reg_weekday else -1,
            delete_after_execution=self.del_after_exec,
        )
        CreationSession.create(
            user=self.db_user,
            time_point=created_send_time,
            chat_to_send_id=-1,
            text="",
        )

        await self.request.message.edit(
            "Время отправки сохранено!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Дальше", callback_data="CHAT")]])
        )

    def render_message(self) -> str:
        text = "**Выберите время отправки:**\n\n"

        if self.reg_date:
            text += "**Дата:** {}/{}/{}\n".format(
                str(self.datetime.day).rjust(2, "0"),
                str(self.datetime.month).rjust(2, "0"),
                str(self.datetime.year).rjust(4, "0"),
            )

        text += "**Время:** {}:{}:{}\n".format(
            str(self.datetime.hour).rjust(2, "0"),
            str(self.datetime.minute).rjust(2, "0"),
            str(self.datetime.second).rjust(2, "0")
        )

        if self.reg_weekday and not self.del_after_exec and not self.reg_date:
            text += "Ближайшее напоминание будет отправлено {} и ".format(WEEKDAYS[self.datetime.weekday()])

        if self.del_after_exec or self.reg_date:
            text += "будет удалено после исполнения " + ("(Отправка по дате)" if self.reg_date else "")
        elif not self.reg_weekday:
            text += "будет отправляться каждый день"
        else:
            text = text.strip(" и")

        text = text.replace("и будет", "и")

        return text


    async def func(self):
        match self.request.data:
            case "CHANGE-SUBMIT":
                await self.submit()

            case _:
                self.set_values()
                await self.request.message.edit(self.render_message(), reply_markup=self.date_keyboard)
