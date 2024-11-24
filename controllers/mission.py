import asyncio
from datetime import datetime, timedelta

from colorama import Fore
from peewee import DoesNotExist

from database.models import SendTime, BotUsers, Notifications, SendQueue, CreationSession, NotificationGroups
from instances import client
from util import MIDNIGHT


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
        ).order_by(SendTime.send_time)

        return tuple(result)

    @staticmethod
    def delete_unused_time_points(period: int = 1):
        pass

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

    @staticmethod
    def create_midnight_mission_if_not_exists():
        _, created = SendQueue.get_or_create(send_at=MIDNIGHT, delete_after_execution=True)
        if created:
            print("MC session created!")
        
    @staticmethod
    def to_seconds(value: timedelta) -> float:
        return value.days * 86400 + value.seconds + value.microseconds / 1000000
    
    @staticmethod
    def get_mission(send_time: SendTime) -> Notifications | None:
        try:
            return send_time.operation[0]
        except DoesNotExist:
            SendTime.delete_by_id(send_time.id)
            return

    def update(self):
        for ng in NotificationGroups.select():
            try:
                _ = ng.notification
            except DoesNotExist:
                if len(SendQueue.get_by_id(ng.session.id).to_send) == 1:
                    SendQueue.delete_by_id(ng.session.id)

                NotificationGroups.delete_by_id(ng.id)

        for st in self.today_missions_sql:
            mission = self.get_mission(send_time=st)

            if mission is None:
                continue

            if NotificationGroups.select().where(NotificationGroups.notification == mission)[:]:
                continue

            session, _ = SendQueue.get_or_create(send_at=st.send_time)
            NotificationGroups.create(notification=mission, session=session)

    @property
    def nearest_send_session_sql(self) -> SendQueue | None:
        if not SendQueue.select()[:]:
            self.update()
            return

        missions = SendQueue.select().where(~SendQueue.executing).order_by(SendQueue.send_at.desc())[:]

        if not missions:
            print("Next mission in midnight")
            return

        return missions[0]
  
    async def run(self):
        nearest = self.nearest_send_session_sql
        if nearest is None:
            return

        nearest.executing = True
        SendQueue.save(nearest)
        
        now_time = datetime.now()
        time_to = datetime(
            day=now_time.day, month=now_time.month, year=now_time.year,
            hour=nearest.send_at.hour,
            minute=nearest.send_at.minute,
            second=nearest.send_at.second,
            microsecond=nearest.send_at.microsecond
        )

        delta = time_to - now_time
        seconds = self.to_seconds(delta)

        print(
            Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
            Fore.GREEN + f"Ожидание... [period=({now_time} -> {time_to},); delta={delta}; seconds={seconds}]"
        )

        await asyncio.sleep(seconds)
        await self.send_group(session=nearest)
        await asyncio.sleep(0.1)
        await self.run()
    
    @staticmethod
    async def send_group(session: SendQueue):
        for notification_group in session.to_send:
            mission = notification_group.notification
            try:
                await client.send_message(chat_id=mission.chat_to_send.tg_id, text=mission.text)

                if mission.send_at.consider_date or mission.send_at.delete_after_execution:
                    SendTime.delete_by_id(mission.send_at.id)
                    Notifications.delete_by_id(mission.id)

            except Exception as e:
                cannot_send = e
                print(Fore.RED + str(cannot_send))

            NotificationGroups.delete_by_id(notification_group.id)

        SendQueue.delete_by_id(session.id)
