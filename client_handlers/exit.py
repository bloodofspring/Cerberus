from datetime import datetime

from colorama import Fore

from client_handlers.base import *
from config import ADMINS


async def is_admin(_, __, m):
    if m and m.from_user and m.from_user.id in ADMINS:
        return True

    await m.reply("Nice try :3")

    return False


is_admin_filter = create(is_admin)


class ExitCmd(BaseHandler):
    __name__ = "ExitCmd"
    FILTER = (command("exit") | command("stop_bot")) & is_admin_filter

    async def func(self):
        await self.request.reply("Команда принята!")
        exit(
            Fore.LIGHTWHITE_EX + f"[{datetime.now()}][!]>>-||--> " +
            Fore.LIGHTWHITE_EX + "Поступила команда о выключении. Отрубаюсь..."
        )
