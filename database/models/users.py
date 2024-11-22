from peewee import IntegerField, ForeignKeyField

from database.models.base import BaseModel


class BotUsers(BaseModel):
    tg_id = IntegerField()


class ChatToSend(BaseModel):
    tg_id = IntegerField()
    user = ForeignKeyField(BotUsers, backref="chats")
