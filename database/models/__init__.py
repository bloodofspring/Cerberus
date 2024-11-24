from database.models.creation_process import CreationSession
from database.models.send_process import SendQueue, NotificationGroups
from database.models.notifications import SendTime, Notifications, ChatToSend
from database.models.users import BotUsers

active_models = [
    BotUsers,

    CreationSession,
    SendQueue,

    ChatToSend,
    SendTime,
    Notifications,
    NotificationGroups,
]
