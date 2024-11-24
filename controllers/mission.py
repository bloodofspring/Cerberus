"""Плачущий призрак на пенсии"""
import asyncio
from datetime import datetime, timedelta

from colorama import Fore
from peewee import DoesNotExist

from database.models import SendTime, BotUsers, Notifications, CreationSession

import aioschedule as schedule

from instances import client


class MissionController:
    def __init__(self):
        self.delete_unused_creation_sessions()
        self.delete_unused_time_points()

    @property
    def today_missions_sql(self) -> tuple[SendTime, ...]:
        now = datetime.now()
        result = SendTime.select().where(
            (SendTime.send_time > now.time()) & (
                    (SendTime.consider_date & (SendTime.send_date == now.date())) |
                    (SendTime.weekday.between(0, 6) & (SendTime.weekday == now.weekday())) |
                    ((~SendTime.consider_date) & (~SendTime.weekday.between(0, 6)))
            )
        ).order_by(SendTime.send_time.desc())

        return tuple(result)

    @staticmethod
    def delete_unused_time_points():
        for st in SendTime.select():
            try:
                st.operation[0]
            except (DoesNotExist, IndexError):
                SendTime.delete_by_id(st.id)

    @staticmethod
    def delete_unused_creation_sessions(period: int = 1):
        CreationSession.delete().where(CreationSession.updated_at < (datetime.now() - timedelta(days=period))).execute()

    def today_missions_for_user(self, user: BotUsers):
        result: tuple[SendTime, ...] = tuple(
            filter(lambda t: t.operation[0].created_by == user, self.today_missions_sql)
        )

        if not result:
            return None

        return tuple(map(lambda t: t.operation[0], result))[0]

    async def run_until_all_jobs_completed(self):
        while True:
            await schedule.run_pending()
            if not schedule.default_scheduler.jobs:
                print(
                    Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
                    Fore.GREEN + "Finishing pending..."
                )
                break
            await asyncio.sleep(10)

        await asyncio.sleep(0.5)
        await self.update()

    async def update(self):
        print(
            Fore.LIGHTYELLOW_EX + f"[{datetime.now()}][!]>>-||--> " +
            Fore.LIGHTMAGENTA_EX + "Updating..."
        )
        schedule.clear("send_mission")
        today_missions = self.today_missions_sql

        if not today_missions:
            print(
                Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
                Fore.MAGENTA + "Next mission in midnight"
            )
            schedule.every(1).day.at("00:00").do(self.send, tuple()).tag("send_mission")
            return

        nearest = today_missions[0]
        print(
            Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
            Fore.MAGENTA + f"Next mission at {nearest.send_time}"
        )
        schedule.every(1).day.at(f"{nearest.send_time.hour}:{nearest.send_time.minute}").do(self.send, tuple(map(lambda t: t.operation[0], filter(
            lambda x: x.send_time == nearest.send_time, today_missions
        )))).tag("send_mission")

        if len(schedule.default_scheduler.jobs) == 1:
            await self.run_until_all_jobs_completed()

    @staticmethod
    async def send(notifications: tuple[Notifications, ...]):
        for notification in notifications:
            try:
                await client.send_message(chat_id=notification.chat_to_send.tg_id, text=notification.text)

                if notification.send_at.consider_date or notification.send_at.delete_after_execution:
                    SendTime.delete_by_id(notification.send_at.id)
                    Notifications.delete_by_id(notification.id)

            except Exception as e:
                print(Fore.RED + str(e))

        schedule.clear("send_mission")
