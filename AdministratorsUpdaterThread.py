import json
import time
import threading
import asyncio

from telegram.ext import MessageHandler, filters

from ApplicationHolder import application, ext_bot, DATA
from Handlers import global_chat_admin_handler


class AdministratorsUpdaterThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.delay = 1
        self.loop = asyncio.get_event_loop()
        self.administrators = []
        self.daemon = True

    def run(self):
        while self.is_alive():
            try:
                chat_administrators = asyncio.run_coroutine_threadsafe(
                    ext_bot.get_chat_administrators(chat_id=DATA["chat_id"]),
                    self.loop
                ).result(timeout=self.delay)
                chat_administrators = [admin.user.id for admin in chat_administrators]
                if self.administrators != chat_administrators and type(chat_administrators) == list:
                    self.administrators = chat_administrators
                    if application.handlers.get(-1) is not None:
                        for handler in application.handlers.get(-1):
                            application.remove_handler(handler, group=-1)
                    application.add_handler(MessageHandler(filters.ChatType.GROUPS &
                                                           filters.Chat(chat_id=DATA["chat_id"]) &
                                                           filters.User(user_id=self.administrators),
                                                           global_chat_admin_handler), -1)
                time.sleep(self.delay)
            except Exception as e:
                time.sleep(self.delay)


administrators_updater = AdministratorsUpdaterThread()
