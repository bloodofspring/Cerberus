from peewee import ForeignKeyField, TimeField, BooleanField

from database.models.notifications import Notifications
from database.models.base import BaseModel


class SendQueue(BaseModel):
    send_at = TimeField()
    executing = BooleanField(default=False)
    delete_after_execution = BooleanField(default=True)


class NotificationGroups(BaseModel):
    notification = ForeignKeyField(Notifications, backref="queue")
    session = ForeignKeyField(SendQueue, backref="to_send")
