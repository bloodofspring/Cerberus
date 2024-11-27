from datetime import time, datetime

from database.models import Notifications, SendTime, CreationSession, ChatToSend, BotUsers
from instances import client

WEEKDAYS_ACCUSATIVE = ["в понедельник", "во вторник", "в среду", "в четверг", "в пятницу", "в субботу", "в воскресенье"]
WEEKDAYS_NOMINATIVE = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
MIDNIGHT: time = time(hour=0, minute=0, second=0)


def render_time(db_time: SendTime | tuple[datetime, bool, bool, bool]):
    send_time_text = ""
    
    if isinstance(db_time, SendTime):
        delete_after_execution = db_time.delete_after_execution
        consider_date = db_time.consider_date
        consider_weekday = 0 <= db_time.weekday <= 6
        send_date = db_time.send_date
        send_time = db_time.send_time
    else:
        delete_after_execution = db_time[1]
        consider_date = db_time[2]
        consider_weekday = db_time[3]
        send_date = db_time[0].date()
        send_time = db_time[0].time()

    if consider_date:
        send_time_text += "**Дата:** {}/{}/{}\n".format(
            str(send_date.day).rjust(2, "0"),
            str(send_date.month).rjust(2, "0"),
            str(send_date.year).rjust(4, "0"),
        )

    send_time_text += "**Время:** {}:{}:{}\n".format(
        str(send_time.hour).rjust(2, "0"),
        str(send_time.minute).rjust(2, "0"),
        str(send_time.second).rjust(2, "0")
    )

    if consider_weekday and not delete_after_execution and not consider_date:
        send_time_text += "Ближайшее напоминание будет отправлено {} и ".format(WEEKDAYS_ACCUSATIVE[send_date.weekday()])

    if delete_after_execution or consider_date:
        send_time_text += "будет удалено после исполнения " + ("(Отправка по дате)" if consider_date else "")
    elif not consider_weekday:
        send_time_text += "будет отправляться каждый день"
    else:
        send_time_text = send_time_text.strip(" и")

    send_time_text = send_time_text.replace("и будет", "и")
    
    return send_time_text


async def render_notification(notification: Notifications) -> str:
    send_time_text = render_time(db_time=notification.send_at)
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
