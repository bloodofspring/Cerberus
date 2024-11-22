from database.models import Notifications, SendTime

weekdays = {
    0: "в понедельник",
    1: "во вторник",
    2: "в среду",
    3:"в четверг",
    4: "в пятницу",
    5: "в субботу",
    6: "в воскресенье"
}


def render_notification(notification: Notifications) -> str:
    send_at: SendTime = notification.send_at

    if send_at.consider_date:
        t = f"{send_at.send_date} {send_at.send_time}".capitalize()
    elif 0 <= send_at.weekday <= 6:
        t = f"{weekdays[send_at.weekday]}, {send_at.send_time}".capitalize()
    else:
        t = f"каждый день, в {send_at.send_time}".capitalize()

    if send_at.delete_after_execution:
        t += " (Удалится после отправки)"

    return ("Текст напоминания:"
            "\n{}"
            "\n\nВремя отправки: {}"
            "\nЧат для отправки: {}".format(notification.text, t, notification.chat_to_send.tg_id))
