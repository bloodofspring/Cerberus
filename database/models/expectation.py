from peewee import ForeignKeyField, TimeField, BooleanField

from database.models.notifications import Notifications
from database.models.base import BaseModel


class SendSessions(BaseModel):
    send_at = TimeField()
    executing = BooleanField(default=False)
    delete_after_execution = BooleanField(default=True)


class NotificationToSend(BaseModel):
    notification = ForeignKeyField(Notifications, backref="queue")
    session = ForeignKeyField(SendSessions, backref="to_send")
