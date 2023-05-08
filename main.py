import json
from telegram.ext import filters

with open('secret.json') as f:
    DATA = json.load(f)

GLOBAL_CHAT_FILTER = filters.Chat(chat_id=DATA["chat_id"])
if len(DATA["alert_user_id"]) > 0:
    user_filter = filters.User(user_id=DATA["alert_user_id"][0])
    for i in range(1, len(DATA["alert_user_id"])):
        user_filter = user_filter | filters.User(user_id=DATA["alert_user_id"][i])
    GLOBAL_CHAT_FILTER = GLOBAL_CHAT_FILTER & user_filter

from telegram import Chat, ChatMember, ChatMemberUpdated, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


async def global_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("-" * 10)
    print(update.message.from_user.full_name)
    print(update.message.from_user.id)
    print(update.message.chat.id)

    await update.message.forward(update.message.from_user.id)

    return


async def private_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("-" * 10)
    print(update.message.from_user.full_name)
    print(update.message.from_user.id)
    print(update.message.chat.id)

    return


def main() -> None:
    application = Application.builder().token(DATA["token"]).build()

    application.add_handler(MessageHandler(GLOBAL_CHAT_FILTER, global_chat_handler))

    application.add_handler(MessageHandler(filters.ALL, private_chat_handler))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
