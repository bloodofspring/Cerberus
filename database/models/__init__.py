from database.models.creation_process import CreatedTimePoints
from database.models.expectation import IsWaiting
from database.models.notifications import SendTime, Notifications
from database.models.users import BotUsers, ChatToSend

active_models = [
    BotUsers,

    CreatedTimePoints,
    IsWaiting,

    ChatToSend,
    SendTime,
    Notifications,
]
