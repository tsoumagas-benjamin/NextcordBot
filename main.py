#!/usr/bin/env python
import asyncio
import atexit
from os import getenv

from dotenv import load_dotenv
from stoat import ReadyEvent, ServerMemberRemoveEvent

from log import log
from utilities import ChaosBot, db

# Get the ID and Token for the bot
load_dotenv("./.env")
bot_ID = getenv("STOAT_ID")
bot_token = getenv("STOAT_TOKEN")

# Instantiate the bot
bot = ChaosBot(
    case_insensitive=True,
    description="Multi-purpose Stoat bot\nAuthor: ChaosHerald2\nUsing Stoat.py, hosted locally.\nPorted from Discord",
    self_bot=True,
    strip_after_prefix=True,
    token=bot_token,
    owner_ids=["01KHMEY5VV8E9NF0NY840EFF4R"],
)


# Handle when the bot is ready
@bot.listen()
async def on_ready(event: ReadyEvent):

    # Print that the bot is set up
    print(f"We have set up as {bot.user.name}")


# Handle when a user leaves a server
@bot.listen()
async def on_member_remove(event: ServerMemberRemoveEvent):
    # If user and this bot have no mutual servers, remove their member information
    mutual_servers: list[str] | None = await event.member.mutual_server_ids()
    if mutual_servers is None:
        with db.cursor() as cur:
            cur.execute("DELETE FROM members WHERE user_id = %s", (event.user_id))
            db.commit()

    # If user is this bot, delete all collections pertaining to that server
    if event.user_id == bot_ID:
        with db.cursor() as cur:
            cur.execute("DELETE FROM servers WHERE server_id = %s", (event.server_id))
            db.commit()


# Handle closing of processes when the bot shuts down
def teardown():
    if bot.loop:
        bot.loop.stop()
        bot.loop.close()


atexit.register(teardown)


# Tell the bot to store logs in nextcord.log
log()

# Run Discord bot
bot.run(token=bot_token)
