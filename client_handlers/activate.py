from client_handlers.mission_creation import GetChatToSend, ChatRegister, GetDateTime
from client_handlers.mission_deletion import RmMission
from client_handlers.mission_list import MissionsList, Mission
from client_handlers.start import StartCmd
from instances import client

active_handlers = [
    StartCmd,

    MissionsList,
    Mission,

    RmMission,

    GetChatToSend,
    ChatRegister,
    GetDateTime
]


def add_handlers() -> None:
    for handler in active_handlers:
        client.add_handler(handler().de_pyrogram_handler)
