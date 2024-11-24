from peewee import CharField, BooleanField, IntegerField, ForeignKeyField, DateField, TimeField

from database.models.base import BaseModel
from database.models.users import ChatToSend, BotUsers


class SendTime(BaseModel):
    send_date = DateField()
    send_time = TimeField()
    consider_date = BooleanField()
    weekday = IntegerField()  # pass -1 if week day is unimportant
    delete_after_execution = BooleanField()
    is_used = BooleanField()


class Notifications(BaseModel):
    text = CharField()
    send_at = ForeignKeyField(SendTime, backref="operation")
    chat_to_send = ForeignKeyField(ChatToSend, backref="operation")
    created_by = ForeignKeyField(BotUsers, backref="notifications")
    is_sent = BooleanField()
