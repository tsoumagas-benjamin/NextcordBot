import nextcord
import os
import pymongo
import random
import config
from nextcord.ext import commands
from log import log

# Allows privileged intents for monitoring members joining, roles editing, and role assignments
# These need to be enabled in the developer portal as well
my_intents = nextcord.Intents.default()   
my_intents.message_content = True
my_intents.members = True
my_intents.presences = True

# Database config
client = pymongo.MongoClient(os.getenv('CONN_STRING')) 

# Instantiate the bot
bot = commands.Aupbot.dbutoShardedBot(
    intents=my_intents,
    status=nextcord.Status.online,
    activity=nextcord.Activity(
    type=nextcord.ActivityType.listening, 
    name="/commands for help!"
    ))  

# Name our access to our client database
db = client.NextcordBot   

#Get all the existing collections
collections = db.list_collection_names()
    
# Define bot behaviour on start up
@bot.event
async def on_ready():
    """When bot is connected to Discord"""
    # Initialize default collections
    collections = db.list_collection_names()
    for c in ['birthdays', 'rules', 'keywords', 'Viktor', 'levels']:
        if c not in collections:
            db.create_collection(c)
    
    # Add functionality from cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            bot.load_extension(f'cogs.{filename[:-3]}')

    # Ensure all commands are added and synced
    bot.add_all_application_commands()
    await bot.sync_all_application_commands()

    print(f"Collections: {collections}")
    print(f"Intents: {dict(bot.intents)}")
    print(f'We have logged in as {bot.user}')

# Initialize starter words when joining a new server.
@bot.event
async def on_guild_join(guild):
    # Add an entry for starter keywords
    if db.keywords.find_one({"_id": guild.id}) == None:
        db.keywords.insert_one({
            "_id": guild.id, 
            "sad": config.sad_words, 
            "filter": config.filter_words, 
            "encouragements": config.encouragements,
            "status": False})
    
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
            
# Defining bot behaviour when a message is sent
@bot.listen("on_message")
async def word_filter(message):
    # If the message is from a bot, don't react
    if message.author.bot:
        return

    # If responding is on, remove messages with filtered words,
    # and respond to sad messages
    respond = db.keywords.find_one({"_id": message.guild.id})
    if respond["status"]:
        
        for word in respond["filter"]:
            if word.lower() in message.content.lower(): 
                await message.delete()
                break

        for word in respond["sad"]:
            if word.lower() in message.content.lower():
                await message.channel.send(random.choice(respond["encouragements"]))
                break

# Tell the bot to store logs in nextcord.log
log()

# Run Discord bot
bot.run(os.getenv('DISCORD_TOKEN'))