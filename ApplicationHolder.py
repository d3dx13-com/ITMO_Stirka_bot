from Handlers import *

with open('secret.json') as f:
    DATA = json.load(f)

ext_bot: ExtBot = ExtBot(DATA["token"])
application = Application.builder().token(DATA["token"]).build()
