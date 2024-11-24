import asyncio
from datetime import datetime, timedelta, time

from colorama import Fore
from peewee import DoesNotExist

from database.models import SendTime, BotUsers, Notifications, SendSessions, CreationSession, NotificationQueue
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
        _, created = SendSessions.get_or_create(send_at=MIDNIGHT, delete_after_execution=True)
        if created:
            print("MC session created!")

    def add_today_missions(self):
        for mission in map(lambda t: t.operation[0], self.today_missions_sql):
            # if mission.is_in_session_plan:
            #     print(f"{mission} already in session plan")
            #     continue

            # mission.is_in_session_plan = True
            # Notifications.save(mission)

            if not SendSessions.select().where(SendSessions.send_at == mission.send_at.send_time)[:]:
                session = SendSessions.create(send_at=mission.send_at.send_time)
            else:
                session = SendSessions.get(send_at=mission.send_at.send_time)

            NotificationQueue.get_or_create(notification=mission, session=session)

    def update(self):
        self.create_midnight_mission_if_not_exists()
        print(f"Start of update: sessions={len(SendSessions.select())}")
        self.add_today_missions()
        self.remove_deleted()
        print(f"End of update: sessions={len(SendSessions.select())}")

    async def run(self):
        self.update()
        await self.execute_()

    @property
    def nearest_send_session_sql(self) -> SendSessions | None:
        if not SendSessions.select()[:]:
            self.update()
            return

        missions = SendSessions.select().where(~SendSessions.executing).order_by(SendSessions.send_at.desc())[:]

        if not missions:
            print("Next mission in midnight")
            return

        return missions[0]

    async def execute_(self):
        nearest = self.nearest_send_session_sql
        if nearest is None:
            return

        nearest.executing = True
        SendSessions.save(nearest)

        now = datetime.now()
        time_to = datetime(
            day=now.day, month=now.month, year=now.year,
            hour=nearest.send_at.hour,
            minute=nearest.send_at.minute,
            second=nearest.send_at.second,
            microsecond=nearest.send_at.microsecond
        )

        delta = time_to - now
        seconds = self.to_seconds(delta)

        print(
            Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
            Fore.GREEN + f"Ожидание... [period=({now} -> {time_to},); delta={delta}; seconds={seconds}]"
        )

        await asyncio.sleep(seconds)
        await self.send(session=nearest)
        await asyncio.sleep(0.1)
        await self.run()

    async def send(self, session: SendSessions):
        for ts in map(lambda t: t.notification, session.to_send):


        SendSessions.delete_by_id(session.id)


        for m in missions:
            try:
                Notifications.get_by_id(m.id)
                # if m.is_in_session_plan:
                #     continue

                # m.is_in_session_plan = True
                # Notifications.save(m)

                await client.send_message(chat_id=m.chat_to_send.tg_id, text=m.text)

                if m.send_at.consider_date or m.send_at.delete_after_execution:
                    SendTime.delete_by_id(m.send_at.id)
                    Notifications.delete_by_id(m.id)

            except DoesNotExist:
                pass

            except Exception as e:
                cannot_send = e
                print(Fore.RED + str(cannot_send))

        await asyncio.sleep(1)
        await self.run()

    @staticmethod
    def to_seconds(value: timedelta) -> float:
        return value.days * 86400 + value.seconds + value.microseconds / 1000000



    # @property
    # def today_missions(self) -> tuple[tuple[Notifications, ...], SendTime] | tuple[None, None]:
    #     today_missions = self.today_missions_sql
    #
    #     if not today_missions:
    #         return None, None
    #
    #     nearest: SendTime = today_missions[0]
    #     nearest_operations: tuple[Notifications, ...] = tuple(map(
    #         lambda t: t.operation[0], filter(lambda t: t.send_time == nearest.send_time, today_missions)
    #     ))
    #
    #     return nearest_operations, nearest.send_time


    # def update(self):
    #
    #
    #
    # async def reload(self):
    #     print(
    #         Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
    #         Fore.GREEN + f"Перезагрузка..."
    #     )
    #     SendSessions.truncate_table()
    #     await self.run()
    #
    # @staticmethod
    # def to_seconds(value: timedelta) -> float:
    #     return value.days * 86400 + value.seconds + value.microseconds / 1000000
    #
    # async def run(self):
    #     if SendSessions.select()[:]:
    #         return
    #
    #     missions, send_time = self.today_missions
    #     print(
    #         Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
    #         Fore.GREEN + f"Миссии: {missions}; [send_time={send_time}]"
    #     )
    #     now = datetime.now()
    #
    #     if missions is None or send_time is None:
    #         time_to = datetime(day=now.day + 1, month=now.month, year=now.year, hour=0, minute=0, second=0, microsecond=0)
    #     else:
    #         time_to = datetime(
    #             day=now.day, month=now.month, year=now.year,
    #             hour=send_time.hour, minute=send_time.minute, second=send_time.second, microsecond=send_time.microsecond
    #         )
    #
    #     delta = time_to - now
    #     seconds = self.to_seconds(delta)
    #     print(
    #         Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
    #         Fore.GREEN + f"Ожидание... [period={now} -> {time_to}; delta={delta}; seconds={seconds}]"
    #     )
    #     SendSessions.create()
    #     await asyncio.sleep(seconds)
    #     await self.execute_missions(missions)
    #
    # async def execute_missions(self, missions: tuple[Notifications, ...] | None):
    #     SendSessions.truncate_table()
    #     if missions is None:
    #         print(Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " + Fore.GREEN + f"Нечего отправить! Обновляюсь..")
    #         Notifications.update({Notifications.is_in_session_plan: False}).where(Notifications.is_in_session_plan).execute()
    #         await self.run()
    #
    #         return
    #
    #     print(
    #         Fore.YELLOW + f"[{datetime.now()}][#]>>-||--> " +
    #         Fore.GREEN + f"Выполнение миссий... [missions={len(missions)}]"
    #     )
    #
    #     for m in missions:
    #         try:
    #             Notifications.get_by_id(m.id)
    #             if m.is_in_session_plan:
    #                 continue
    #
    #             m.is_in_session_plan = True
    #             Notifications.save(m)
    #
    #             await client.send_message(chat_id=m.chat_to_send.tg_id, text=m.text)
    #
    #             if m.send_at.consider_date or m.send_at.delete_after_execution:
    #                 SendTime.delete_by_id(m.send_at.id)
    #                 Notifications.delete_by_id(m.id)
    #
    #         except DoesNotExist:
    #             pass
    #
    #         except Exception as e:
    #             cannot_send = e
    #             print(Fore.RED + str(cannot_send))
    #
    #     await asyncio.sleep(1)
    #     await self.run()
