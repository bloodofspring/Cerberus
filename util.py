from datetime import time

from database.models import Notifications, SendTime, CreationSession, ChatToSend, BotUsers
from instances import client

WEEKDAYS = {
    0: "в понедельник",
    1: "во вторник",
    2: "в среду",
    3: "в четверг",
    4: "в пятницу",
    5: "в субботу",
    6: "в воскресенье"
}
MIDNIGHT: time = time(hour=0, minute=0, second=0)


async def render_notification(notification: Notifications) -> str:
    send_at: SendTime = notification.send_at
    send_time_text = ""

    if send_at.consider_date:
        send_time_text += "**Дата:** {}/{}/{}\n".format(
            str(send_at.send_date.day).rjust(2, "0"),
            str(send_at.send_date.month).rjust(2, "0"),
            str(send_at.send_date.year).rjust(4, "0"),
        )

    send_time_text += "**Время:** {}:{}:{}\n".format(
        str(send_at.send_time.hour).rjust(2, "0"),
        str(send_at.send_time.minute).rjust(2, "0"),
        str(send_at.send_time.second).rjust(2, "0")
    )

    if 0 <= send_at.weekday <= 6 and not send_at.delete_after_execution and not send_at.consider_date:
        send_time_text += "Ближайшее напоминание будет отправлено {} и ".format(WEEKDAYS[send_at.weekday])

    if send_at.delete_after_execution or send_at.consider_date:
        send_time_text += "будет удалено после исполнения " + ("(Отправка по дате)" if send_at.consider_date else "")
    elif not 0 <= send_at.weekday <= 6:
        send_time_text += "будет отправляться каждый день"
    else:
        send_time_text = send_time_text.strip(" и")

    send_time_text = send_time_text.replace("и будет", "и")

    send_chat = await client.get_chat(notification.chat_to_send.tg_id)

    return (
        "__Текст напоминания:__\n<pre>{}</pre>\n"
        "##================##\n"
        "__Время отправки:__\n<pre>{}</pre>\n"
        "##================##\n"
        "__Чат для отправки:__\n<pre>{}</pre>\n".format(
            notification.text, send_time_text,
            send_chat.title if send_chat.title is not None else f"Чат с @{send_chat.username}"
        )
    )


def create_mission(session: CreationSession):
    send_time: SendTime = session.time_point

    send_time.is_used = True
    SendTime.save(send_time)

    Notifications.create(
        text=session.text,
        send_at=send_time,
        chat_to_send=ChatToSend.get(tg_id=session.chat_to_send_id),
        created_by=session.user,
    )

    CreationSession.delete_by_id(session.id)


def get_last_session(db_user: BotUsers) -> CreationSession | None:
    try:
        session: CreationSession = CreationSession.select().where(
            CreationSession.user == db_user
        ).order_by(CreationSession.updated_at.desc())[0]

        return session
    except IndexError:
        return None
