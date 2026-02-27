from stoat.ext import commands
from stoat import Permissions, ReadyEvent, ServerMemberRemoveEvent
from os import getenv, listdir
from log import log
from utilities import db, collections, collection_names

# TODO: Define bot permissions, see: enums / UserPermissions
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
bot = commands.Bot(
    case_insensitive=True,
    command_prefix=commands.when_mentioned_or("/"),
    description="Multi-purpose Stoat bot\nAuthor: ChaosHerald2\nUsing Stoat.py, hosted locally.\nWIP Porting from Discord",
    self_bot=True,
    strip_after_prefix=True,
    token=getenv("STOAT_TOKEN"),
    owner_ids=["01KHMEY5VV8E9NF0NY840EFF4R"],
)


# Define bot behaviour on start up
@bot.listen()
async def on_ready(event: ReadyEvent):
    """When bot is connected to Stoat"""
    # Initialize default collections
    for collection in collection_names:
        if collection not in collections:
            db.create_collection(collection)

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
    for name, gear in bot.gears.items():
        gear_commands = gear.get_commands()
        print(f"{name}: {gear_commands}")

    # Print database collections
    print(f"Collections: {collections}")

    # Print that the bot is set up
    print(f"We have set up as {bot.user}")


# Handle when a user leaves a server
@bot.listen()
async def on_member_remove(event: ServerMemberRemoveEvent):
    # If user and this bot have no mutual servers, remove their birthday information
    mutual_servers: list[str] | None = await event.member.mutual_server_ids()
    if mutual_servers is None:
        if db.birthdays.find_one({"_id": event.member.id}):
            db.birthdays.delete_many({"_id": event.member.id})

    # If user is this bot, delete all collections pertaining to that server
    if event.user_id == getenv("STOAT_ID"):
        for collection in db.list_collection_names():
            mycol = db[collection]
            mycol.delete_many({"_id": event.server_id})


# Tell the bot to store logs in nextcord.log
log()

# Run Discord bot
bot.run(getenv("STOAT_TOKEN"))
