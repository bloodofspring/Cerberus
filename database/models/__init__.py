from database.models.creation_process import CreationSession
from database.models.send_process import SendSessions, NotificationQueue
from database.models.notifications import SendTime, Notifications, ChatToSend
from database.models.users import BotUsers

active_models = [
    BotUsers,

    CreationSession,
    SendSessions,

    ChatToSend,
    SendTime,
    Notifications,
    NotificationQueue,
]
