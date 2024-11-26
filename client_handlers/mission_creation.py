import asyncio
from datetime import datetime, timedelta

from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from client_handlers.base import *
from controllers import MissionController
from database.models import ChatToSend, SendTime, CreationSession
from util import create_mission, get_last_session, WEEKDAYS


class ChatRegister(BaseHandler):
    __name__ = "ChatRegister"
    FILTER = create(lambda _, __, m: m and m.text and (len(m.text)) == 14 and m.text.startswith("-") and m.text.strip(
        "-").isalnum())

    async def func(self):
        try:
            chat = await self.client.get_chat(int(self.request.text))
            me = await self.client.get_me()
            me_in_chat = await self.client.get_chat_member(int(self.request.text), me.id)

            if me_in_chat.status != me_in_chat.status.ADMINISTRATOR:
                raise

            if me_in_chat.permissions is not None and not me_in_chat.permissions.can_send_messages:
                raise
        except (ValueError, TypeError, Exception) as e:
            print(type(e), e)
            await self.request.reply("Чата с таким ID  не существует или бот не добавлен в него!")
            await self.request.reply(
                "Пожалуйста, добавьте бота в чат, назначьте его администратором и проверьте корректность ID")
            return

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Да", callback_data=f"CHAT-SAVE-1={self.request.text}"),
            InlineKeyboardButton("Нет", callback_data="CHAT-SAVE-0")
        ]])
        await self.request.reply(f"Сохранить чат {chat.title}?", reply_markup=keyboard)


class NotificationTextRegister(BaseHandler):
    __name__ = "NotificationTextRegister"
    FILTER = create(lambda _, __, m: m and m.text and m.text.startswith("!"))

    async def func(self):
        session = get_last_session(self.db_user)
        if session is None:
            return

        session.text = self.request.text.lstrip("!")
        CreationSession.save(session)

        create_mission(session=session)
        await self.request.reply("Напоминание создано!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "Список напоминаний", callback_data="missions_list"
        )]]))
        await asyncio.sleep(1)
        await MissionController().update()

class GetChatToSend(BaseHandler):
    __name__ = "GetChatToSend"
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and q.data.startswith("CHAT"))

    @property
    async def chats_keyboard(self) -> InlineKeyboardMarkup:
        if ChatToSend.get_or_none(tg_id=self.request.message.chat.id) is None:
            ChatToSend.create(tg_id=self.request.message.chat.id, user=self.db_user)

        keyboard = InlineKeyboardMarkup([])

        for c in self.db_user.chats:
            try:
                chat = await self.client.get_chat(c.tg_id)
            except Exception as e:
                cannot_get_chat = e
                ChatToSend.delete_by_id(c.id)

                continue

            keyboard.inline_keyboard.append([InlineKeyboardButton(
                chat.title if chat.title is not None else f"Чат c @{chat.username}",
                callback_data=f"CHAT-{c.tg_id}-{'PRV' if chat.type == chat.type.PRIVATE else 'PUB'}"
            )])

        keyboard.inline_keyboard.append([
            InlineKeyboardButton("Этот чат", callback_data="CHAT-THIS")
        ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton("+ Добавить чат", callback_data="CHAT-ADD")
        ])

        return keyboard

    async def add_chat(self):
        await self.request.message.edit((
            "Отправьте сообщением ниже ID чата.\n"
            "Пример: **-1002207320665**\n"
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
        session = get_last_session(self.db_user)
        if session is None:
            return

        ChatToSend.get_or_create(tg_id=chat_id, user=self.db_user)
        session.chat_to_send_id = chat_id
        CreationSession.save(session)

        await self.request.message.edit("Чат выбран!")
        await asyncio.sleep(0.5)
        await self.request.message.edit("Отправьте текст напоминания ниже! Сообщение начните с символа '!'")

    async def main(self):
        await self.request.message.edit(
            "Выберите чат для отправки напоминаний", reply_markup=await self.chats_keyboard
        )

    async def func(self):
        match self.request.data:
            case "CHAT":
                await self.main()

            case "CHAT-ADD":
                await self.add_chat()

            case "CHAT-THIS":
                await self.apply_chat(chat_id=self.request.message.chat.id)

            case _ as c if c.startswith("CHAT-SAVE-"):
                await self.save_chat(save=int(self.request.data[10]))

            case _ as c if c.strip("CHAT-PUBPRV").isalnum():
                if c.split("-")[2] == "PUB":
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
            ] if self.reg_weekday else [],
            [InlineKeyboardButton(
                "Не учитывать день недели" if self.reg_weekday else "Учитывать день недели",
                callback_data=self.to_call_data(reg_weekday=not self.reg_weekday)
            )],
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

        if self.reg_weekday:
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
