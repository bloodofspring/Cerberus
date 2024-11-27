from client_handlers.exit import ExitCmd
from client_handlers.mission_creation import GetChatToSend, GetDateTime
from client_handlers.mission_deletion import RmMission
from client_handlers.mission_list import MissionsList, Mission
from client_handlers.on_add import BotAdded
from client_handlers.start import StartCmd, Main
from instances import client

active_handlers = [
    Main,
    StartCmd,
    ExitCmd,

    MissionsList,
    Mission,

    RmMission,

    GetChatToSend,
    GetDateTime,

    BotAdded
]


def add_handlers() -> None:
    for handler in active_handlers:
        client.add_handler(handler().de_pyrogram_handler)
