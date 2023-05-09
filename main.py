from Handlers import *

from ApplicationHolder import application

from LaundryUpdaterThread import laundry_updater
from AdministratorsUpdaterThread import administrators_updater

administrators_updater.start()
laundry_updater.start()

if __name__ == "__main__":
    application.add_handler(CommandHandler(["start", "help"], start_handler, filters=filters.ChatType.PRIVATE))

    application.add_handler(CallbackQueryHandler(button_handler))

    application.add_handler(MessageHandler(filters.ChatType.PRIVATE, private_chat_handler), 0)

    application.run_polling(allowed_updates=Update.ALL_TYPES)
