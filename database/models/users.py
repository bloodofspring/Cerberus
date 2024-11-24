from peewee import IntegerField

from database.models.base import BaseModel


class BotUsers(BaseModel):
    tg_id = IntegerField()
