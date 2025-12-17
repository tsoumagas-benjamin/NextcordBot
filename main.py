import nextcord
from os import getenv, listdir
from nextcord.ext import commands
from log import log
from utilities import db, collections, collection_names

# Allows privileged intents for monitoring members joining, roles editing, and role assignments
# These need to be enabled in the developer portal as well
my_intents = nextcord.Intents.all()

# Instantiate the bot
bot = commands.AutoShardedBot(
    intents=my_intents,
    status=nextcord.Status.online,
    activity=nextcord.Activity(
        type=nextcord.ActivityType.listening, name="Type / to look for commands!"
    ),
)


# Define bot behaviour on start up
@bot.event
async def on_ready():
    """When bot is connected to Discord"""
    # Initialize default collections
    for c in collection_names:
        if c not in collections:
            db.create_collection(c)

    # Add functionality from cogs
    for filename in listdir("./cogs"):
        if filename.endswith(".py"):
            bot.load_extension(f"cogs.{filename[:-3]}")

    # Ensure all commands are added and synced
    bot.add_all_application_commands()
    try:
        await bot.sync_application_commands()
    except Exception as e:
        print(f"Error syncing: {e}")

    print(f"Registered commands: {bot.commands}")

    print(f"Collections: {collections}")
    print(f"Intents: {dict(bot.intents)}")
    print(f"We have logged in as {bot.user}")


# When leaving a server, delete all collections pertaining to that server.
@bot.event
async def on_guild_remove(guild):
    for collection in db.list_collection_names():
        mycol = db[collection]
        mycol.delete_many({"_id": guild.id})


# Remove user from birthdays if they no longer share servers with the bot.
@bot.event
async def on_member_remove(member):
    if member.mutual_guilds is None:
        if db.birthdays.find_one({"_id": member.id}):
            db.birthdays.delete_many({"_id": member.id})


# Tell the bot to store logs in nextcord.log
log()

# Run Discord bot
bot.run(getenv("DISCORD_TOKEN"))
