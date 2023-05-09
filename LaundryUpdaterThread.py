import redis
import time
import asyncio
import threading
from telegram import *
from telegram.ext import *
from datetime import datetime

import logging

from GUI import create_reply_markup, LOCALIZATION, get_localization

from ApplicationHolder import ext_bot, application

EXPIRATION_DAYS = 2

redis_server = redis.Redis(host='localhost', port=6379, decode_responses=True)


class LaundryUpdaterThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.break_sleep = False
        self.loop = asyncio.get_event_loop()
        self.administrators = []
        self.daemon = True

    def run(self):
        while self.is_alive():
            try:
                time.sleep(1)
                expiration_date_dict = redis_server.hgetall("expiration_date")
                timestamp = int(datetime.now().timestamp())
                min_delay = 340282366920938463463374607431768211456  # 2 ** 128

                user_ids = []
                for key, value in expiration_date_dict.items():
                    if timestamp > int(value):
                        user_ids.append(int(key))
                    if int(value) - timestamp > 0:
                        min_delay = min(min_delay, int(value) - timestamp)
                    else:
                        min_delay = 0
                if len(user_ids) > 0:
                    clear(user_ids)

                for i in range(min_delay):
                    if self.break_sleep:
                        self.break_sleep = False
                        break
                    time.sleep(1)
            except Exception:
                time.sleep(1)


laundry_updater = LaundryUpdaterThread()


async def skip_exceptions(awaitable):
    try:
        return await awaitable
    except Exception:
        pass


async def create_log(number, user_id):
    chat = await ext_bot.get_chat(chat_id=user_id)
    log_text = f"{datetime.now()} | @{chat.username} | {number}"
    print(log_text)


def wait(user_id, numbers):
    if len(numbers) == 0:
        return
    pipe = redis_server.pipeline()
    expiration_date = int(datetime.now().timestamp() + 60 * 60 * 24 * EXPIRATION_DAYS)
    pipe.hset(f"expiration_date", user_id, expiration_date)
    laundry_updater.break_sleep = True
    pipe.lpush(f"numbers_wait_{user_id}", *numbers)
    for number in numbers:
        pipe.sadd(f"user_id_wait_{number}", user_id)
    pipe.execute()


def took(user_id):
    numbers_wait = redis_server.lrange(f"numbers_wait_{user_id}", 0, -1)
    clear([user_id])
    return len(numbers_wait) > 0


def clear(user_ids, message_clear=True):
    if len(user_ids) == 0:
        return
    for user_id in user_ids:
        pipe = redis_server.pipeline()
        pipe.hdel(f"expiration_date", user_id)
        numbers_wait = redis_server.lrange(f"numbers_wait_{user_id}", 0, -1)
        pipe.delete(f"numbers_wait_{user_id}")
        for number in numbers_wait:
            pipe.srem(f"user_id_wait_{number}", user_id)
            if len(redis_server.smembers(f"user_id_wait_{number}")) == 0:
                pipe.delete(f"user_id_wait_{number}")
        pipe.execute()

        if message_clear:
            last_message_id = redis_server.lrange(f"messages_{user_id}", -2, -1)[0]
            new_text = LOCALIZATION[get_localization(user_id)]["help"]
            asyncio.run_coroutine_threadsafe(
                skip_exceptions(ext_bot.edit_message_text(
                    text=new_text,
                    chat_id=user_id,
                    message_id=last_message_id,
                    reply_markup=create_reply_markup(user_id)
                )),
                laundry_updater.loop
            )


async def new(numbers):
    user_ids = []
    for number in numbers:
        for user_wait_id in redis_server.smembers(f"user_id_wait_{number}"):
            user_ids.append(int(user_wait_id))
            asyncio.create_task(create_log(number, int(user_wait_id)))
    return user_ids
