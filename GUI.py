import json
import redis
from telegram import *
from telegram.ext import *

with open('localization.json') as f:
    LOCALIZATION = json.load(f)

redis_server = redis.Redis(host='localhost', port=6379, decode_responses=True)


def create_reply_markup(user_id=None):
    localization = get_localization(user_id)
    keyboard = [
        [
            InlineKeyboardButton(LOCALIZATION[localization]["took"], callback_data="took")]
        ,
        [
            InlineKeyboardButton("ru", callback_data="ru"),
            InlineKeyboardButton("eng", callback_data="eng"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_localization(user_id):
    localization = redis_server.hget("localization", user_id)
    if localization is None:
        return "eng"
    else:
        return localization
