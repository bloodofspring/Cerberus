import asyncio
from datetime import datetime, timedelta

from database.models import SendTime, BotUsers, Notifications, IsWaiting
from instances import client


class MissionController:
    def __init__(self):
        self.now = datetime.now()

    @property
    def today_missions(self) -> tuple[tuple[Notifications, ...], SendTime] | tuple[None, None]:
        today_missions = SendTime.select().where(
            SendTime.is_used & (SendTime.send_time >= self.now.time()) & (
                    (SendTime.consider_date & SendTime.send_date == self.now.date()) |
                    (SendTime.weekday.between(0, 6) & SendTime.weekday == self.now.weekday()) |
                    (~SendTime.consider_date & ~SendTime.weekday.between(0, 6))
            )
        ).order_by(SendTime.send_time.desc())[:]

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

    def nearest_mission_for_current_user(self, user: BotUsers): # ToDo: Починить вывод ближайшей миссии (Если работает--оставить как есть)
        nearest = Notifications.select().where(
            (Notifications.created_by == user)
        )
        result = tuple(sorted(nearest, key=lambda t: (
            t.send_at.send_time >= self.now.time(), t.send_at.send_time,
        ), reverse=True))

        if not result:
            return None

        return result[0]

    async def reload(self):
        print("Reloading...")
        IsWaiting.truncate_table()
        await self.run()

    async def run(self):  # ToDo: Протестировать
        if IsWaiting.select()[:]:
            print("Already waiting")
            pass

        IsWaiting.create()
        missions, send_time = self.today_missions
        print(missions, send_time)
        now = datetime.now()

        if missions is None or send_time is None:
            time_to = datetime(day=now.day + 1, month=now.month, year=now.year, hour=0, minute=0, second=0)
        else:
            time_to = datetime(
                day=now.day, month=now.month, year=now.year,
                hour=send_time.hour, minute=send_time.minute, second=send_time.second,
            )

        seconds = (time_to - now).seconds
        print(f"{now} to {time_to}")
        print(f"Sleep {seconds}...")
        await asyncio.sleep(seconds)
        await self.execute_missions(missions)

    async def execute_missions(self, missions: tuple[Notifications] | None):
        IsWaiting.truncate_table()
        if missions is None:
            print("Nothing to send.")
            await self.run()

            return

        print(f"{len(missions)} to send.")

        for m in missions:
            try:
                await client.send_message(chat_id=m.chat_to_send.tg_id, text=m.text)
            except Exception as e:
                cannot_send = e
                print("some error while sending", cannot_send)

        await asyncio.sleep(1.1)
        await self.run()
