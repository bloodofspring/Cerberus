from database.models.creation_process import CreationSession
from database.models.notifications import SendTime, Notifications, ChatToSend
from database.models.users import BotUsers

active_models = [
    BotUsers,

    CreationSession,

    ChatToSend,
    SendTime,
    Notifications,
]
