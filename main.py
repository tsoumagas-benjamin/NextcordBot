#!/usr/bin/env python
import asyncio
import atexit
from os import getenv, listdir

from dotenv import load_dotenv
from stoat import ReadyEvent, ServerMemberRemoveEvent

from log import log
from utilities import ChaosBot, collection_names, db

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


# Define bot behaviour on start up
@bot.listen()
async def on_ready(event: ReadyEvent):
    """When bot is connected to Stoat"""
    # Set up loop for recurring daily/weekly functions
    if active_loop := asyncio.get_running_loop():
        bot.loop = active_loop

    # Add functionality from gears
    for filename in listdir("./gears"):
        if filename.endswith(".py"):
            try:
                # Reload the gear if it already exists, otherwise load the new gear
                if bot.get_gear(filename[:-3]):
                    await bot.reload_extension(f"gears.{filename[:-3]}")
                else:
                    await bot.load_extension(f"gears.{filename[:-3]}")
            except Exception as e:
                print(f"Gear Error: {e}")

    # Print loaded extensions
    print(f"Extensions: {bot.extensions.keys()}")

    # Print commands per gear
    for gear_name, gear in bot.gears.items():
        gear_commands = gear.get_commands()
        print(f"{gear_name}: {[command.name for command in gear_commands]}")

    # Print database collections
    print(f"Collections: {collection_names}")

    # Print that the bot is set up
    print(f"We have set up as {bot.user}")


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
bot.run(token=bot_token, asyncio_debug=True)
