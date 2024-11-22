import asyncio
from datetime import datetime, timedelta

from colorama import Fore

from database.models import SendTime, BotUsers, Notifications, IsWaiting
from instances import client


class MissionController:
    @property
    def today_missions(self) -> tuple[tuple[Notifications, ...], SendTime] | tuple[None, None]:
        now = datetime.now()
        today_missions = SendTime.select().where(
            SendTime.is_used & (SendTime.send_time > now.time()) & (
                    (SendTime.consider_date & (SendTime.send_date == now.date())) |
                    (SendTime.weekday.between(0, 6) & (SendTime.weekday == now.weekday())) |
                    ((~SendTime.consider_date) & (~SendTime.weekday.between(0, 6)))
            )
        ).order_by(SendTime.send_time)[:]

        if not today_missions:
            return None, None

        nearest: SendTime = today_missions[0]
        nearest_operations: tuple[Notifications, ...] = tuple(map(
            lambda t: t.oper[0], filter(lambda t: t.send_time == nearest.send_time, today_missions)
        ))

        return nearest_operations, nearest.send_time

    @staticmethod
    def delete_unused_time_points(period=1):
        SendTime.delete().where(
            (~SendTime.is_used) & (SendTime.updated_at < datetime.now() - timedelta(days=period))
        ).execute()

    @staticmethod
    def nearest_mission_for_current_user(user: BotUsers):
        now = datetime.now()
        nearest = Notifications.select().where(
            (Notifications.created_by == user)
        )
        result = tuple(sorted(nearest, key=lambda t: (
            t.send_at.send_time >= now.time(), t.send_at.send_time,
        ), reverse=True))

        if not result:
            return None

        return result[0]

    async def reload(self):
        print(
            Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
            Fore.GREEN + f"Перезагрузка..."
        )
        IsWaiting.truncate_table()
        await self.run()

    @staticmethod
    def to_seconds(value: timedelta) -> float:
        return value.days * 86400 + value.seconds + value.microseconds / 1000000

    async def run(self):
        if IsWaiting.select()[:]:
            return

        missions, send_time = self.today_missions
        print(
            Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
            Fore.GREEN + f"Миссии: {missions}; [send_time={send_time}]"
        )
        now = datetime.now()

        if missions is None or send_time is None:
            time_to = datetime(day=now.day + 1, month=now.month, year=now.year, hour=0, minute=0, second=0,
                               microsecond=0)
        else:
            time_to = datetime(
                day=now.day, month=now.month, year=now.year,
                hour=send_time.hour, minute=send_time.minute, second=send_time.second, microsecond=send_time.microsecond
            )

        delta = time_to - now
        seconds = self.to_seconds(delta)
        print(
            Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
            Fore.GREEN + f"Ожидание... [period={now} -> {time_to}; delta={delta}; seconds={seconds}]"
        )
        IsWaiting.create()
        await asyncio.sleep(seconds)
        await self.execute_missions(missions)

    async def execute_missions(self, missions: tuple[Notifications] | None):
        IsWaiting.truncate_table()
        if missions is None:
            print(
                Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
                Fore.GREEN + f"Нечего отправить! Обновляюсь.."
            )
            await self.run()

            return

        print(
            Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
            Fore.GREEN + f"Выполнение миссий... [missions={len(missions)}]"
        )

        for m in missions:
            try:
                await client.send_message(chat_id=m.chat_to_send.tg_id, text=m.text)
            except Exception as e:
                cannot_send = e

        await self.run()
