from peewee import ForeignKeyField

from database.models.base import BaseModel
from database.models.notifications import SendTime
from database.models.users import Users


class CreatedTimePoints(BaseModel):
    user = ForeignKeyField(Users, backref="created_tp")
    time_point = ForeignKeyField(SendTime)
