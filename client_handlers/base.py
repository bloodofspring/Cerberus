from datetime import datetime

from pyrogram.filters import command, regex, create
from pyrogram import Client, filters, types, handlers
from colorama import Fore

from database.models import BotUsers

request_type = types.Message | types.CallbackQuery
__all__ = ["BaseHandler", "request_type", "Client", "command", "regex", "create"]


class BaseHandler:
    """Базовый обработчик-исполнитель"""
    __name__ = ""
    HANDLER: handlers.MessageHandler | handlers.CallbackQueryHandler = handlers.MessageHandler
    FILTER: filters.Filter | None = None

    def __init__(self):
        self.request: request_type | None = None
        self.client: Client | None = None

    @property
    def db_user(self):
        if isinstance(self.request, types.CallbackQuery):
            user_id = self.request.message.chat.id
        else:
            user_id = self.request.chat.id

        db, created = BotUsers.get_or_create(tg_id=user_id)

        if created:
            print(
                Fore.YELLOW + f"[{datetime.now()}][!]>>-||--> " +
                Fore.GREEN + f"Новый пользователь! [total={len(BotUsers.select())}; id={user_id}]"
            )

        return db

    async def func(self):
        raise NotImplementedError

    async def execute(self, client: Client, request: request_type):
        self.client = client
        self.request = request

        # try:
        #     await self.func()
        # except Exception as e:
        #     print(
        #         Fore.YELLOW + f"[{datetime.now()}][!]>>-||--> " +
        #         Fore.RED + f"Ошибка в {self.__name__}! [type={type(e)}; text={str(e)}]"
        #     )
        await self.func()

    @property
    def de_pyrogram_handler(self):
        return self.HANDLER(self.execute, self.FILTER)
