from datetime import time

from database.models import Notifications, SendTime, CreationSession, ChatToSend, BotUsers
from instances import client

weekdays = {
    0: "в понедельник",
    1: "во вторник",
    2: "в среду",
    3: "в четверг",
    4: "в пятницу",
    5: "в субботу",
    6: "в воскресенье"
}


def remove_microsecond(time_value: time) -> str:
    return str(time_value)[:-7]


async def render_notification(notification: Notifications) -> str:
    send_at: SendTime = notification.send_at

    if send_at.consider_date:
        t = f"{send_at.send_date} {remove_microsecond(send_at.send_time)}".capitalize()
    elif 0 <= send_at.weekday <= 6:
        t = f"{weekdays[send_at.weekday]}, {remove_microsecond(send_at.send_time)}".capitalize()
    else:
        t = f"каждый день, в {remove_microsecond(send_at.send_time)}".capitalize()

    if send_at.delete_after_execution:
        t = t.strip("каждый день, ")
        t += " (Удалится после отправки)"

    send_chat = await client.get_chat(notification.chat_to_send.tg_id)

    return (
        "__Текст напоминания:__\n<pre>{}</pre>\n"
        "##================##\n"
        "__Время отправки:__\n<pre>{}</pre>\n"
        "##================##\n"
        "__Чат для отправки:__\n<pre>{}</pre>\n".format(
            notification.text, t,
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
