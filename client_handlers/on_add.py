from pyrogram.handlers import ChatMemberUpdatedHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from client_handlers.base import *
from database.models import ChatToSend


class BotAdded(BaseHandler):
    __name__ = "BotAdded"
    HANDLER = ChatMemberUpdatedHandler
    FILTER = create(lambda _, __, u: u.old_chat_member is None)

    async def func(self):
        if self.request.chat.type not in [self.request.chat.type.SUPERGROUP, self.request.chat.type.GROUP]:
            await self.client.send_message(self.request.chat.id, "Чат не является группой или супергруппой!")
            await self.client.leave_chat(chat_id=self.request.chat.id)
            return

        _, created = ChatToSend.get_or_create(tg_id=self.request.chat.id, user=self.db_user)

        if not created:
            return

        try:
            await self.client.send_message(
                self.request.from_user.id,
                f"Чат {self.request.chat.title} добавлен!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Обновить список чатов", callback_data="CHAT")
                ]])
            )
        except (Exception,):
            pass
