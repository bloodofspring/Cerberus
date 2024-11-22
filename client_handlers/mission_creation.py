import asyncio
from datetime import datetime, timedelta

from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from client_handlers.base import *
from controllers import MissionController
from database.models import ChatToSend, SendTime, CreatedTimePoints, Notifications


class GetChatToSend(BaseHandler):
    __name__ = "GetChatToSend"
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and q.data.startswith("CHAT"))

    @property
    def chats_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"Чат {c.tg_id}", callback_data=f"CHAT-{c.tg_id}")
        ] for c in self.db_user.chats] + [[InlineKeyboardButton("+ Добавить чат", callback_data="CHAT-ADD")]])

        return keyboard

    async def add_chat(self):
        await self.request.message.edit((
            "Отправьте сообщением ниже ID чата.\n"
            "Пример: ```-1002207320665```\n"
            "Получить ID чата можно с помощью @LeadConverterToolkitBot"
        ), reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Отмена", callback_data="CHAT")
        ]]))

    async def save_chat(self, save: int | bool):
        if isinstance(save, int):
            save = bool(save)

        if not save:
            await self.request.message.edit(
                "Чат не будет сохранен. Отправка на предыдущую страницу произойдет через полсекунды"
            )
            await asyncio.sleep(0.5)
            await self.main()
            return

        save_chat_id = int(self.request.data.split("=")[1])
        chat = await self.client.get_chat(save_chat_id)
        ChatToSend.create(tg_id=save_chat_id, user=self.db_user)
        await self.request.message.edit(
            f"Чат {chat.title} сохранен! Отправка на предыдущую страницу произойдет через полсекунды"
        )
        await asyncio.sleep(0.5)
        await self.main()

    async def apply_chat(self, chat_id: int):
        if chat_id > 0:
            raise Exception("ID чата не может быть положительным")

        try:
            db_user = self.db_user
            send_time: SendTime = CreatedTimePoints.select().where(
                CreatedTimePoints.user == db_user
            ).order_by(CreatedTimePoints.updated_at)[-1].time_point
        except IndexError:
            await self.request.message.edit("К сожалению, произошла ошибка! Попробуйте заново создать напоминание!")
            return

        send_time.is_used = True
        SendTime.save(send_time)

        Notifications.create(
            text=f"test notification. Created at {datetime.now()}",
            send_at=send_time,
            chat_to_send=ChatToSend.get_or_create(tg_id=chat_id, user=db_user)[0],
            created_by=db_user,
        )
        CreatedTimePoints.delete_by_id(send_time.id)
        await self.request.message.edit("Напоминание создано!")
        await MissionController().reload()

    async def main(self):
        await self.request.message.edit(
            "Выберите чат для отправки напоминаний", reply_markup=self.chats_keyboard
        )

    async def func(self):
        match self.request.data:
            case "CHAT":
                await self.main()

            case "CHAT-ADD":
                await self.add_chat()

            case _ as c if c.startswith("CHAT-SAVE-"):
                await self.save_chat(save=int(self.request.data[10]))

            case _ as c if c.strip("CHAT-").isalnum():
                await self.apply_chat(chat_id=int("-" + c.strip("CHAT-")))


class ChatRegister(BaseHandler):
    __name__ = "ChatRegister"
    FILTER = create(lambda _, __, m: m and m.text and (len(m.text)) == 14 and m.text.startswith("-") and m.text.strip(
        "-").isalnum())

    async def func(self):
        try:
            chat = await self.client.get_chat(int(self.request.text))
        except (ValueError, TypeError, Exception):
            await self.request.reply("Чата с таким ID  не существует или бот не добавлен в него!")
            await self.request.reply(
                "Пожалуйста, добавьте бота в чат, назначьте его администратором и проверьте корректность ID")
            return

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Да", callback_data=f"CHAT-SAVE-1={self.request.text}"),
            InlineKeyboardButton("Нет", callback_data="CHAT-SAVE-0")
        ]])
        await self.request.reply(f"Сохранить чат {chat.title}?", reply_markup=keyboard)


class GetDateTime(BaseHandler):
    __name__ = "GetDateTime"
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and q.data.startswith("CHANGE"))

    def __init__(self):
        super().__init__()
        self.datetime = datetime(
            year=4444, month=6, day=5,
            hour=4, minute=44, second=44,
        )
        self.reg_weekday = False
        self.reg_date = False
        self.del_after_exec = False

    @property
    def date_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("<<", callback_data=self.to_call_data(time_delta=timedelta(days=-1))),
                InlineKeyboardButton("День: {}".format(self.datetime.day), callback_data="none"),
                InlineKeyboardButton(">>", callback_data=self.to_call_data(time_delta=timedelta(days=1)))
            ] if self.reg_date else [],
            [
                InlineKeyboardButton("<<", callback_data=self.to_call_data(time_delta=timedelta(days=-30))),
                InlineKeyboardButton("Месяц: {}".format(self.datetime.month), callback_data="none"),
                InlineKeyboardButton(">>", callback_data=self.to_call_data(time_delta=timedelta(days=30)))
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
                InlineKeyboardButton("<<", callback_data=self.to_call_data(time_delta=timedelta(hours=-1))),
                InlineKeyboardButton("Час: {}".format(self.datetime.hour), callback_data="none"),
                InlineKeyboardButton(">>", callback_data=self.to_call_data(time_delta=timedelta(hours=1)))
            ],
            [
                InlineKeyboardButton("<<", callback_data=self.to_call_data(time_delta=timedelta(minutes=-1))),
                InlineKeyboardButton("минута: {}".format(self.datetime.minute), callback_data="none"),
                InlineKeyboardButton(">>", callback_data=self.to_call_data(time_delta=timedelta(minutes=1)))
            ],
            [
                InlineKeyboardButton("<<", callback_data=self.to_call_data(time_delta=timedelta(seconds=-1))),
                InlineKeyboardButton("Секунда: {}".format(self.datetime.second), callback_data="none"),
                InlineKeyboardButton(">>", callback_data=self.to_call_data(time_delta=timedelta(seconds=1)))
            ],
            [InlineKeyboardButton(
                "Не учитывать день недели" if self.reg_weekday else "Учитывать день недели",
                callback_data=self.to_call_data(reg_weekday=not self.reg_weekday)
            )],
            [InlineKeyboardButton(
                "Не удалять после исполнения" if self.del_after_exec else "Удалить после исполнения",
                callback_data=self.to_call_data(del_after_exec=not self.del_after_exec)
            )],
            [InlineKeyboardButton("Готово", callback_data="CHANGE-SUBMIT")],
        ])

        return keyboard

    def set_values(self):  # call data format "CHANGE-YYYY-MM-DD-HH-MM-SS-1-0-1" (reg_weekday, reg_date, del_after_exec)
        self.datetime = datetime(*map(int, self.request.data.split("-")[1:7]))
        self.reg_weekday = bool(int(self.request.data.split("-")[7]))
        self.reg_date = bool(int(self.request.data.split("-")[8]))
        self.del_after_exec = bool(int(self.request.data.split("-")[9]))

    def to_call_data(self, time_delta: timedelta = timedelta(), reg_weekday=None, reg_date=None,
                     del_after_exec=None) -> str:
        call_data = "CHANGE-"
        call_data += str(self.datetime + time_delta).replace(' ', '-').replace(':', '-')
        call_data += (
            f"-{int(self.reg_weekday) if reg_weekday is None else int(reg_weekday)}"
            f"-{int(self.reg_date) if reg_date is None else int(reg_date)}-"
            f"{int(self.del_after_exec) if del_after_exec is None else int(del_after_exec)}"
        )

        return call_data

    async def submit(self):
        created_send_time = SendTime.create(
            send_date=self.datetime.date(),
            send_time=self.datetime.time(),
            consider_date=self.reg_date,
            weekday=self.datetime.weekday() if self.reg_weekday else -1,
            delete_after_execution=self.del_after_exec,
            is_used=False,
        )
        CreatedTimePoints.create(time_point=created_send_time, user=self.db_user)

        await self.request.message.edit(
            "Время отправки сохранено!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Дальше", callback_data="CHAT")]])
        )

    async def func(self):
        if self.request.data == "CHANGE-SUBMIT":
            await self.submit()
            return
        self.set_values()
        await self.request.message.edit("Выберите время отправки", reply_markup=self.date_keyboard)
