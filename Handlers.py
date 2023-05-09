import json
import time
import asyncio
import redis
from telegram import *
from telegram.ext import *
import re
from datetime import datetime

import LaundryUpdaterThread
from GUI import *

redis_server = redis.Redis(host='localhost', port=6379, decode_responses=True)


def get_numbers(text: str) -> list:
    return sorted(list(set([int(number) for number in re.split(r'\D+', text) if len(number) > 0])))[:16]


def clear_messages(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    old_messages = redis_server.lrange(f"messages_{user_id}", 0, -1)
    redis_server.delete(f"messages_{user_id}")
    if old_messages is None:
        old_messages = []
    for old_message in old_messages:
        asyncio.create_task(skip_exceptions(context.bot.delete_message(user_id, old_message)))


async def skip_exceptions(awaitable):
    try:
        return await awaitable
    except Exception:
        pass


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data in {"ru", "eng"}:
        redis_server.hset(f"localization", query.from_user.id, query.data)

    new_text = LOCALIZATION[get_localization(query.from_user.id)]["help"] + "\n\n"
    if query.data == "took":
        if LaundryUpdaterThread.took(query.from_user.id):
            clear_messages(query.from_user.id, context)
            new_text += LOCALIZATION[get_localization(query.from_user.id)]["done"]
            message = await query.from_user.send_message(text=new_text,
                                                         reply_markup=create_reply_markup(query.from_user.id))
            await message.pin()
            message_id = message.message_id
            redis_server.rpush(f"messages_{query.from_user.id}", message_id)
            redis_server.hset(f"expiration_date", query.from_user.id, int(datetime.now().timestamp() + 60))
            LaundryUpdaterThread.laundry_updater.break_sleep = True
            return

    await skip_exceptions(query.message.edit_text(text=new_text, reply_markup=create_reply_markup(query.from_user.id)))


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_messages(update.message.from_user.id, context)
    asyncio.create_task(skip_exceptions(context.bot.delete_message(update.message.from_user.id, update.message.id)))

    new_text = LOCALIZATION[get_localization(update.message.from_user.id)]["help"]
    message = await update.message.chat.send_message(
        text=new_text,
        reply_markup=create_reply_markup(update.message.from_user.id))
    await message.pin()
    message_id = message.message_id
    redis_server.rpush(f"messages_{update.message.from_user.id}", message_id)


async def private_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    asyncio.create_task(context.bot.delete_message(update.message.chat.id, update.message.id))
    if update.message.text is None:
        return
    LaundryUpdaterThread.clear([update.message.from_user.id], message_clear=False)
    numbers = get_numbers(update.message.text)
    LaundryUpdaterThread.wait(update.message.from_user.id, numbers)

    last_message_id = redis_server.lrange(f"messages_{update.message.from_user.id}", 0, 1)[0]
    expiration_date = datetime.fromtimestamp(int(redis_server.hget(f"expiration_date", update.message.from_user.id)))
    new_text = LOCALIZATION[get_localization(update.message.from_user.id)]["help"] + "\n\n"
    new_text += LOCALIZATION[get_localization(update.message.from_user.id)]["wait_until"] + f": {expiration_date}\n"
    new_text += LOCALIZATION[get_localization(update.message.from_user.id)]["wait"] + f": {numbers}\n"

    await skip_exceptions(context.bot.edit_message_text(
        text=new_text,
        chat_id=update.message.from_user.id,
        message_id=last_message_id,
        reply_markup=create_reply_markup(update.message.from_user.id)
    ))


async def global_chat_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text is None:
        return
    numbers = get_numbers(update.message.text)
    user_ids = await LaundryUpdaterThread.new(numbers)
    if len(user_ids) == 0:
        return
    for user_id in user_ids:
        message = await update.message.forward(chat_id=user_id)
        message_id = message.message_id
        redis_server.rpush(f"messages_{user_id}", message_id)
