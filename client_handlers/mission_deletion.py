class RmMission(BaseHandler):
    HANDLER = CallbackQueryHandler
    FILTER = create(lambda _, __, q: q and q.data and q.data.startswith("rm_mission"))

    async def func(self):
        _, id_ = self.request.data.split()
        id_ = int(id_)

        Notifications.delete_by_id(id_)

        await self.request.message.edit(
            "Напоминание удалено!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("К напоминаниям", callback_data="notifications_main")
            ]])
        )
