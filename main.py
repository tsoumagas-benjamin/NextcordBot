#!/usr/bin/env python
import asyncio
import atexit
from os import getenv, listdir

from dotenv import load_dotenv
from stoat import Permissions, ReadyEvent, ServerMemberRemoveEvent

from log import log
from utilities import ChaosBot, Client, collection_names, db

# Load our .env file for later use
load_dotenv("./.env")

# Define bot permissions, see: enums / UserPermissions
permissions = Permissions(
    manage_channels=False,
    manage_server=False,
    manage_roles=True,
    manage_customization=True,
    kick_members=True,
    ban_members=True,
    timeout_members=True,
    assign_roles=True,
    change_nickname=False,
    manage_nicknames=False,
    change_avatar=False,
    remove_avatars=False,
    view_channel=False,
    read_message_history=True,
    send_messages=True,
    manage_messages=True,
    manage_webhooks=False,
    create_invites=False,
    send_embeds=True,
    upload_files=True,
    use_masquerade=False,
    react=True,
    mention_everyone=False,
    mention_roles=False,
    connect=False,
    speak=False,
    video=False,
    mute_members=False,
    deafen_members=False,
    move_members=False,
    listen=False,
)


# Instantiate the bot
bot = ChaosBot(
    case_insensitive=True,
    description="Multi-purpose Stoat bot\nAuthor: ChaosHerald2\nUsing Stoat.py, hosted locally.\nPorted from Discord",
    self_bot=True,
    strip_after_prefix=True,
    token=getenv("STOAT_TOKEN"),
    owner_ids=["01KHMEY5VV8E9NF0NY840EFF4R"],
)


# Define bot behaviour on start up
@bot.listen()
async def on_ready(event: ReadyEvent):
    """When bot is connected to Stoat"""
    # If the ClientSession for GET/POST requests isn't initialized, do so here
    if bot.client:
        await bot.client.close()
    bot.client = Client()

    # Set up loop for recurring daily/weekly functions
    if bot.loop:
        print("LOOP EXISTS")
        bot.loop.stop()
        bot.loop.close()
    else:
        print("LOOP DOESN'T EXIST")
    bot.loop = asyncio.new_event_loop()
    bot.loop.run_forever()

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


# Handle closing of processes when the bot shuts down
def teardown():
    bot.loop.stop()
    bot.loop.close()


atexit.register(teardown)


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
    if event.user_id == getenv("STOAT_ID"):
        with db.cursor() as cur:
            cur.execute("DELETE FROM servers WHERE server_id = %s", (event.server_id))
            db.commit()


# Tell the bot to store logs in nextcord.log
log()

# Run Discord bot
bot.run(getenv("STOAT_TOKEN"))
