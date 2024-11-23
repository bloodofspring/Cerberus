from peewee import ForeignKeyField, CharField, IntegerField

from database.models.base import BaseModel
from database.models.notifications import SendTime
from database.models.users import BotUsers


class CreationSession(BaseModel):
    user = ForeignKeyField(BotUsers, backref="created_tp")
    time_point = ForeignKeyField(SendTime)
    chat_to_send_id = IntegerField()
    text = CharField()
